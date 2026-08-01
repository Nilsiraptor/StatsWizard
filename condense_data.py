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

import os
import glob
import pandas as pd
from datetime import datetime
from tqdm import tqdm

# Step 1: Define the input directory containing all the game CSV files.
# We use a glob pattern to match any file ending in .csv inside the folder.
input_folder = os.path.join(os.path.dirname(__file__), "GameData", "CLASSIC")
csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

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
    base = os.path.splitext(filename)[0]  # e.g. "2023-04-15_01-18-16"
    parts = base.split("_")
    # Rejoin the parts with no separator to form a single integer.
    parts[1] = ":".join(parts[1].split("-"))
    timestamp_str = " ".join(parts)
    return int(datetime.fromisoformat(timestamp_str).timestamp())

# Step 4: Load all CSV files into a single pandas DataFrame.
# read_csv handles parsing, type inference, and missing values automatically.
# We pass `dtype=str` to keep all columns as strings (safer for mixed data).
# tqdm wraps the loop to show a progress bar with estimated time remaining.
all_dataframes = []
for csv_file in tqdm(csv_files, desc="Loading game files", unit="file"):
    df = pd.read_csv(csv_file, index_col=0)
    if not "result" in df.columns: continue

    # Drop duplicate datapoints
    df = df.drop_duplicates()
    cols = df.columns.drop(["gameMode", "gameTime", "result"])
    df = df.sort_values("gameTime").drop_duplicates(subset=cols)

    # Add the game ID column so each row knows which game it belongs to.
    game_id = parse_game_id(os.path.basename(csv_file))
    df["game_id"] = game_id
    all_dataframes.append(df)

# Step 5: Concatenate all DataFrames into one combined dataset.
# ignore_index=True renumbers the rows so there are no duplicate indices.
combined_df = pd.concat(all_dataframes, ignore_index=True)

combined_df = combined_df.sort_index(axis=1)

# Step 7: Save the cleaned combined data to a new CSV file.
# This replaces the commented-out save from the first version.
output_path = os.path.join(os.path.dirname(__file__),
                           "GameData", "CLASSIC.csv")
combined_df.to_csv(output_path, index=False)

# Print a summary of what was done.
print(f"Loaded {len(csv_files)} game files.")
print(f"Combined rows: {len(combined_df)}")
print(f"Output saved to: {output_path}")
