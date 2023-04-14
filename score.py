import pandas as pd
import time
import os

from wizard import GameState, GameOverWin, GameOverLose
from authorization import ConnectionError

def main():
    wizard = None
    state = None
    df = None
    while True:
        if wizard is None:
            try:
                wizard = GameState()
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

            if state == "InProgress":
                if df is None:
                    df = pd.DataFrame()
                    print("Game in progress. Starting data collection...")

                try:
                    scores = wizard.get_scores()
                except ConnectionError:
                    wizard = None
                    time.sleep(1)
                    continue
                except GameOverWin:
                    print("Game over. You won!")
                    try:
                        df.insert(len(df.columns), "result", "WIN")
                    except ValueError:
                        pass
                    continue
                except GameOverLose:
                    print("Game over. You lost!")
                    try:
                        df.insert(len(df.columns), "result", "LOSE")
                    except ValueError:
                        pass
                    continue

                new_row = pd.DataFrame([scores])

                df = pd.concat([df, new_row], ignore_index=True)

                time.sleep(8)

            else:
                if df is not None:
                    mode = df["gameMode"][0]
                    try:
                        df.to_csv(f"GameData\\{mode}\\{time.strftime(r'%Y-%m-%d_%H-%M-%S')}.csv", na_rep="0")
                    except OSError as e:
                        os.makedirs(f"GameData\\{mode}", exist_ok=True)
                    else:
                        df = None
                        print("Data saved!")

if __name__ == "__main__":
    main()
