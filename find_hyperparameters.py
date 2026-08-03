from pathlib import Path
from collections import defaultdict
from time import perf_counter as time

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, RandomizedSearchCV
from sklearn.preprocessing import MaxAbsScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import make_scorer, log_loss, brier_score_loss
from scipy.stats import uniform, loguniform
import joblib as jl


input_folder = Path("GameData")

for mode_file in input_folder.glob("*.csv"):
    t = time()

    mode = mode_file.stem

    df = pd.read_csv(mode_file)

    target = "result"
    features = df.columns.drop(["result", "gameMode", "gameTime", "game_id"])

    df = df.fillna(0)
    df[target] = df[target].map({"WIN": 1, "LOSE": 0})
    print(mode, df[target].unique())

    gss = GroupShuffleSplit(n_splits=10) # Number of split for each model

    X = df[features]
    y = df[target]
    groups = df["game_id"]

    model = LogisticRegression(
        C=1.0,
        l1_ratio=0.2,
        class_weight="balanced",
        solver="saga",
        max_iter=2000
    )

    pipeline = make_pipeline(MaxAbsScaler(), model)

    params = {
        "logisticregression__C": loguniform(0.01, 2.0),
        "logisticregression__l1_ratio": uniform(0.2, 0.7)
    }

    scorers = {
        "neg_log_loss": make_scorer(
            log_loss,
            response_method="predict_proba",
            greater_is_better=False,
            labels=[0, 1]
        ),
        "neg_brier_score": make_scorer(
            brier_score_loss,
            response_method="predict_proba",
            greater_is_better=False,
            labels=[0, 1]
        )
    }

    search = RandomizedSearchCV(
        pipeline,
        param_distributions=params,
        n_iter=100, # Number different hyperparameters to test
        cv=gss,
        scoring=scorers,
        n_jobs=-1,
        refit="neg_log_loss",
        verbose=1
    )

    search.fit(X, y, groups=groups)

    # 1. Convert to DataFrame
    results_df = pd.DataFrame(search.cv_results_)

    # 2. Select the most relevant columns for a clean view
    # We look at the parameters, the score, and how it ranked
    param_cols = [col for col in results_df.columns if col.startswith('param_')]

    # Combine them with the score columns for a clean table
    cols_to_show = param_cols + [
        'mean_test_neg_log_loss',
        'mean_test_neg_brier_score',
        'rank_test_neg_log_loss',
        'rank_test_neg_brier_score'
    ]

    # 3. Sort by rank and display
    results_clean = results_df[cols_to_show].set_index('rank_test_neg_log_loss').sort_index()

    # Display the top 5 models
    print(results_clean.head(10))

    print(f"This took {time()-t:.3} seconds")
    print("_"*60, "\n")

    # Save model
    model_file = (Path("models") / mode).with_suffix(".joblib")
    model_file.parent.mkdir(parents=True, exist_ok=True)

    jl.dump(search.best_estimator_, model_file)
