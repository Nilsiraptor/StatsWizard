"""Collects game data and saves it to CSV files for model training.

This module runs as a background data collector that connects to the
League of Legends client, gathers game statistics at regular intervals,
and saves them as CSV files organized by game mode.
"""

import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from authorization import ConnectionError
from wizard import GameAPI, GameResult, GameState


def main():
    """Runs the continuous game data collection loop.

    Connects to the League client, collects scores every 8 seconds
    while a game is in progress, and saves the data as CSV files
    organized by game mode.
    """
    wizard = None
    state = None
    df = None
    while True:
        if wizard is None:
            try:
                wizard = GameAPI()
            except ConnectionError:
                time.sleep(1)
                continue
        else:
            try:
                state = wizard.check_game_state()
            except ConnectionError:
                wizard = None
                time.sleep(1)
                continue

            if state == GameState.RUNNING:
                if df is None:
                    df = pd.DataFrame()
                    print("Game in progress. Starting data collection...")
                    t = time.time()

                if time.time() - t >= 10:
                    try:
                        scores = wizard.get_scores()
                    except ConnectionError:
                        wizard = None
                        time.sleep(1)
                        continue

                    if "result" in scores:
                        if GameResult.WIN == scores["result"]:
                            print("Game over. You won!")
                            try:
                                df.insert(len(df.columns), "result", "WIN")
                            except ValueError:
                                pass
                            time.sleep(5)
                            continue
                        if GameResult.LOSE == scores["result"]:
                            print("Game over. You lost!")
                            try:
                                df.insert(len(df.columns), "result", "LOSE")
                            except ValueError:
                                pass
                            time.sleep(5)
                            continue

                    new_row = pd.DataFrame([scores])

                    df = pd.concat([df, new_row], ignore_index=True)

                    time.sleep(1)

            else:
                if df is not None:
                    mode = df["gameMode"][0]
                    mode_path = Path("GameData") / mode
                    file_name = (
                        datetime.now(datetime.timezone.utc)
                        .replace(microsecond=0)
                        .isoformat()
                    )
                    file_name = file_name.replace(":", "_")
                    csv_path = (mode_path / file_name).with_suffix(".csv")
                    try:
                        df.to_csv(
                            csv_path, na_rep="0", float_format="%.3f", index=False
                        )
                    except OSError:
                        mode_path.mkdir(parents=True, exist_ok=True)
                    else:
                        df = None
                        print("Data saved!")


if __name__ == "__main__":
    main()
