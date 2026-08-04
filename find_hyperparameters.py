from pathlib import Path
from time import perf_counter as time

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit, cross_val_score
from sklearn.preprocessing import MaxAbsScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
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

    gss = GroupShuffleSplit(n_splits=11) # Number of split for each model

    X = df[features]
    y = df[target]
    groups = df["game_id"]
    n_games = len(groups.unique())

    def objective(trial):
        if n_games >= 10000:
            model_type = trial.suggest_categorical("model_type", ["LR", "RF", "HGBM"])
        else:
            model_type = "LR"

        if model_type == "LR":
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

        elif model_type == "RF":
            # trees = trial.suggest_int("n_estimators", 100, 500)
            samples_leaf = trial.suggest_int("min_samples_leaf", 1, 20)
            features = trial.suggest_categorical("max_features", ["sqrt", "log2"])

            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=None,
                # min_samples_split=samples_split,
                min_samples_leaf=samples_leaf,
                max_features=features,
                n_jobs=-1,
                class_weight="balanced",
                # monotonic_cst={}
            )

            pipeline = make_pipeline(model)

        else:
            lr = trial.suggest_float("learning_rate", 0.01, 0.2, log=True)
            # trees = trial.suggest_int("max_iter", 100, 1000)
            # depth = trial.suggest_int("max_depth", 3, 20)
            # leaf_nodes = trial.suggest_int("min_leaf_nodes", 15, 200)
            samples_leaf = trial.suggest_int("min_samples_leaf", 1, 100)
            use_l2 = trial.suggest_categorical("use_l2", [True, False])
            if use_l2:
                l2 = trial.suggest_float("l2_regularization", 0.01, 10, log=True)
            else:
                l2 = 0.0

            model = HistGradientBoostingClassifier(
                learning_rate=lr,
                max_iter=100,
                max_depth=None,
                max_leaf_nodes=None,
                min_samples_leaf=samples_leaf,
                l2_regularization=l2,
                early_stopping=True,
                validation_fraction=0.1,
                class_weight="balanced",
                # monotonic_cst={}
            )

            pipeline = make_pipeline(model)

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

        return scores.mean() - scores.std()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        study_name=mode,
        direction="maximize",
    )

    study.optimize(
        objective,
        n_trials=500,
        n_jobs=-1,
        show_progress_bar=True
    )

    print(f"{len(study.trials)} Trials were performed")
    print(*[": ".join(map(str, param)) for param in study.best_params.items()], sep="\n")

    # Training model with optimal hyperparameters
    optimum = study.best_params
    model = optimum.pop("model_type", "LR")
    if model == "LR":
        final_model = LogisticRegression(
            **optimum,
            class_weight="balanced",
            solver="saga",
            max_iter=10_000
        )

        final_pipeline = make_pipeline(MaxAbsScaler(), final_model)

        final_pipeline.fit(X, y)

    elif model == "RF":
        if not optimum.pop("limit_depth"):
            optimum["max_depth"] = None

        final_model = RandomForestClassifier(
            **optimum,
            n_jobs=-1,
            class_weight="balanced",
            # monotonic_cst={}
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=model,
            method="isotonic",
            cv=gss
        )

        final_pipeline = calibrated_model

        final_pipeline.fit(X, y, groups=groups)

    else:
        if not optimum.pop("limit_depth"):
            optimum["max_depth"] = None
        if not optimum.pop("use_l2", True):
            optimum["l2_regularization"] = 0.0

        final_model = HistGradientBoostingClassifier(
            **optimum,
            n_jobs=-1,
            early_stopping=True,
            validation_fraction=0.1,
            class_weight="balanced",
            # monotonic_cst={}
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=model,
            method="isotonic",
            cv=gss
        )

        final_pipeline = calibrated_model

        final_pipeline.fit(X, y, groups=groups)

    # Save model
    model_file = (Path("models") / mode).with_suffix(".joblib")
    model_file.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(final_pipeline, model_file)

    print(f"This took {time()-t:.2f} seconds")
    print("_"*60, "\n")
