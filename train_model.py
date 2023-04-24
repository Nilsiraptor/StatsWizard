import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Define directory path for data
dir_path = "GameData\\CLASSIC"

# Load data from CSV files in the directory
data_frames = []
for file_name in os.listdir(dir_path):
    if file_name.endswith(".csv"):
        file_path = os.path.join(dir_path, file_name)
        data_frames.append(pd.read_csv(file_path, index_col=0))
data = pd.concat(data_frames)

# Split data into features and target variable
X = data.drop(columns=["result", "gameMode"]).fillna(0)
y = data["result"]

print(X)

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.1, random_state=42)

# Train a random forest classifier
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)

# Predict on the testing set
y_pred = rf.predict(X_test)

# Evaluate model performance
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

# Save model
filename = 'random_forest.pkl'
pickle.dump(rf, open(filename, 'wb'))
