import os
import pandas as pd


# Define directory path for data
dir_path = "GameData\\CLASSIC"

# Load data from CSV files in the directory
for file_name in os.listdir(dir_path):
    if file_name.endswith(".csv"):
        file_path = os.path.join(dir_path, file_name)
        data_frame = pd.read_csv(file_path, index_col=0)
        if "result" in data_frame.columns:
            continue
        else:
            os.remove(os.path.join(dir_path, file_name))
