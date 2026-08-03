from pathlib import Path
from time import perf_counter as time

import pandas as pd
from sklearn.model_selection import GroupShuffleSplit, cross_val_score
from sklearn.preprocessing import MaxAbsScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import make_scorer, log_loss
from scipy.stats import uniform, loguniform
import joblib
import optuna


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

    def objective(trial):
        c = trial.suggest_float("C", 0.01, 0.1, log=True)
        l1 = trial.suggest_float("l1_ratio", 0.0, 1.0)

        model = LogisticRegression(
                C=c,
                l1_ratio=l1,
            class_weight="balanced",
            solver="saga",
            max_iter=2000
        )

        pipeline = make_pipeline(MaxAbsScaler(), model)

        scorer = make_scorer(
            log_loss,
            response_method="predict_proba",
            greater_is_better=False,
            labels=[0, 1]
        )

        scores = cross_val_score(
            pipeline, X, y,
            groups=groups, cv=gss,
            scoring=scorer,
            n_jobs=-1
        )

        return scores.mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize")
    study.optimize(
        objective,
        timeout=120,
        n_jobs=-1,
        # show_progress_bar=True
    )

    print(f"{len(study.trials)} were performed")
    print(*[": ".join(map(str, param)) for param in study.best_params.items()], sep="\n")

    # Training model with optimal hyperparameters
    final_model = LogisticRegression(
        **study.best_params,
        class_weight="balanced",
        solver="saga",
        max_iter=10_000
    )

    final_pipeline = make_pipeline(MaxAbsScaler(), final_model)

    final_pipeline.fit(X, y)

    # Save model
    model_file = (Path("models") / mode).with_suffix(".joblib")
    model_file.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(final_pipeline, model_file)

    print(f"This took {time()-t:.2f} seconds")
    print("_"*60, "\n")
