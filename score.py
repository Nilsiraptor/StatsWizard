import pandas as pd
import time
import os

from wizard import GameState
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

                try:
                    scores = wizard.get_scores()
                except ConnectionError:
                    wizard = None
                    time.sleep(1)
                    continue

                new_row = pd.DataFrame([scores])

                df = pd.concat([df, new_row], ignore_index=True)

                time.sleep(10)

            else:
                if df is not None:
                    mode = df["gameMode"][0]
                    try:
                        df.to_csv(f"GameData\\{mode}\\{time.strftime(r'%Y-%m-%d_%H_%M_%S')}.csv")
                    except OSError as e:
                        os.makedirs(f"GameData\\{mode}", exist_ok=True)
                    else:
                        df = None

if __name__ == "__main__":
    main()
