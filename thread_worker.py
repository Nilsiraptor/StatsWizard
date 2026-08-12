"""Runs background game state monitoring and data collection in a thread.

This module provides a Qt thread worker that periodically checks the
League of Legends client for game state changes and collects live
score data while a game is in progress.
"""
from time import perf_counter as time
from time import sleep
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
import joblib
import pandas as pd

from wizard import GameState, GameAPI
from authorization import ConnectionError
from model_tools import make_diff_features


class ModelCache:
    def __init__(self, models_dir="models"):
        self.dir = Path(models_dir)
        self.cache = {}

    def get(self, mode):
        if mode not in self.cache:
            model_path = (self.dir / mode).with_suffix(".joblib")
            self.cache[mode] = joblib.load(model_path)
        return self.cache[mode]


class ThreadWorker(QThread):
    """A background thread that monitors game state and collects live data.

    Emits signals when the game state changes or when new score data
    is available, allowing the GUI to update in real-time.
    """

    state_changed = pyqtSignal(GameState)
    data_updated = pyqtSignal(dict)
    prediction_updated = pyqtSignal(float, float)

    def __init__(self, freq=1.0):
        """Initializes the thread worker.

        Args:
          freq: The polling frequency in Hz. Defaults to 1.0 (1 Hz).
        """
        super().__init__()

        self.running = True

        self.pause = 1.0 / freq

        self.models = ModelCache()

    def predict_win_probability(self, scores):
        pipeline = self.models.get(scores["gameMode"])

        df = pd.DataFrame([scores])

        features = df.columns.drop(["gameMode"], errors="ignore")
        X_diff = make_diff_features(df, features)

        new_cols = X_diff.columns.difference(df.columns)
        X_combined = pd.concat([df, X_diff[new_cols]], axis=1)

        X = X_combined.reindex(
            columns=pipeline.feature_names_in_,
            fill_value=0
        )

        proba = pipeline.predict_proba(X)[0]
        classes = list(pipeline.classes_)
        return proba[classes.index(1)]

    def run(self):
        """The main loop that polls for game state and collects data."""
        last_state = GameState.NO_CLIENT
        t = time() - 1

        while self.running:
            run_time = time() - t
            if self.pause > run_time: sleep(self.pause - run_time)
            t = time()

            if GameState.NO_CLIENT == last_state:
                try:
                    self.api = GameAPI()
                except ConnectionError as e:
                    if self.running: continue

            curr_state = self.api.check_game_state()

            if last_state != curr_state:
                self.state_changed.emit(curr_state)
                last_state = curr_state

            if GameState.RUNNING == curr_state:
                try:
                    live_scores = self.api.get_scores()
                except ConnectionError as e:
                    self.state_changed.emit(GameState.NO_CLIENT)
                    last_state = GameState.NO_CLIENT
                    if self.running: continue

                if "result" in live_scores:
                    if self.running: continue

                try:
                    win_prob = self.predict_win_probability(live_scores)
                    self.prediction_updated.emit(live_scores["gameTime"], float(win_prob))
                except (FileNotFoundError, KeyError) as e:
                    print(e)

                gold = self.api.get_item_gold()

                live_scores["ally_gold"] = gold[0]
                live_scores["enemy_gold"] = gold[1]

                self.data_updated.emit(live_scores)
