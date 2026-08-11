"""
condense_data.py
===================
Reads all individual game CSV files from GameData/CLASSIC/ and combines
them into a single consolidated dataset using pandas.

This script:
  1. Loads every game CSV into a single DataFrame
  2. Removes duplicate rows (redundant data)
  3. Parses the filename timestamp into an integer game ID
  4. Saves the result to a new CSV file
"""

from datetime import datetime
from pathlib import Path

import pandas as pd
from tqdm import tqdm


# Step 1: Define the input directory containing all the game CSV files.
# We use a glob pattern to match any file ending in .csv inside the folder.
base_path = Path(__file__).parent
input_folder = base_path / "GameData"

for mode_path in input_folder.iterdir():
    if mode_path.is_file(): continue

    print(f"Reading {mode_path.stem} data...")

    csv_files = list(mode_path.glob("*.csv"))

    # Step 2: Sort the file list so files are processed in chronological order.
    # The filenames follow the pattern YYYY-MM-DD_HH-MM-SS.csv, so lexicographic
    # sorting gives us the correct time-based ordering.
    csv_files.sort()

    # Step 3: Parse the filename timestamp into a game ID integer.
    # Example: "2023-04-15_01-18-16.csv" → 20230415011816
    # This gives each game a unique numeric identifier that can be used later
    # to distinguish between different games in the combined dataset.
    def parse_game_id(filename):
        # Strip the .csv extension and split on the underscore separator.
        base = Path(filename).stem  # e.g. "2023-04-15_01-18-16"
        time_str = base.replace("_", ":")
        return int(datetime.fromisoformat(time_str).timestamp())

    # Step 4: Load all CSV files into a single pandas DataFrame.
    # read_csv handles parsing, type inference, and missing values automatically.
    # We pass `dtype=str` to keep all columns as strings (safer for mixed data).
    # tqdm wraps the loop to show a progress bar with estimated time remaining.
    all_dataframes = []
    games_combined = 0
    for csv_file in tqdm(csv_files, desc="Loading game files", unit="file"):
        df = pd.read_csv(csv_file, index_col=0)
        if not "result" in df.columns: continue

        has_NONE_labels = True in ["NONE" in label for label in df.columns]
        has__labels = True in ["__" in label for label in df.columns]

        if mode_path.stem == "CLASSIC" and has_NONE_labels: continue
        if has__labels: continue

        games_combined += 1

        # Drop duplicate datapoints
        df = df.drop_duplicates()
        cols = df.columns.drop(["gameMode", "gameTime", "result"])
        df = df.sort_values("gameTime").drop_duplicates(subset=cols)

        # Add the game ID column so each row knows which game it belongs to.
        game_id = parse_game_id(csv_file)
        df["game_id"] = game_id
        all_dataframes.append(df)

    # Step 5: Concatenate all DataFrames into one combined dataset.
    # ignore_index=True renumbers the rows so there are no duplicate indices.
    if len(all_dataframes) == 0:
        print(f"No games left to combine. Continuing to next gamemode")
        print("_"*60, "\n")
        continue
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    combined_df = combined_df.sort_index(axis=1)

    # Step 7: Save the cleaned combined data to a new CSV file.
    # This replaces the commented-out save from the first version.
    output_path = mode_path.with_suffix(".csv")
    combined_df.to_csv(output_path, index=False)

    # Print a summary of what was done.
    print(f"Loaded {len(csv_files)} game files.")
    print(f"Used Data from {games_combined} games.")
    print(f"Combined rows: {len(combined_df)}")
    print(f"Output saved to: {output_path}")
    print("_"*60, "\n")
