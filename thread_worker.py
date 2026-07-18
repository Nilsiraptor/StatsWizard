from time import perf_counter as time
from time import sleep

from PyQt6.QtCore import QThread, pyqtSignal

from wizard import GameState, GameAPI
from authorization import ConnectionError


class ThreadWorker(QThread):

    state_changed = pyqtSignal(GameState)
    data_updated = pyqtSignal(dict)

    def __init__(self, freq=1.0):
        super().__init__()

        self.running = True

        self.pause = 1.0 / freq

    def run(self):
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
                    continue

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
                    continue

                if "result" in live_scores:
                    continue

                gold = self.api.get_item_gold()

                live_scores["ally_gold"] = gold[0]
                live_scores["enemy_gold"] = gold[1]

                self.data_updated.emit(live_scores)
