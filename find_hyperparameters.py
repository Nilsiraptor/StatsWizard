from pathlib import Path
from time import perf_counter as time

import joblib
import numpy as np
import optuna
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, make_scorer
from sklearn.model_selection import (
    GroupShuffleSplit,
    StratifiedGroupKFold,
    cross_val_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from model_tools import build_monotonic_cst, make_diff_features

sklearn.set_config(enable_metadata_routing=True)

input_folder = Path("GameData")

for mode_file in input_folder.glob("*.csv"):
    t = time()

    mode = mode_file.stem

    df = pd.read_csv(mode_file)

    target = "result"
    features = df.columns.drop(["result", "gameMode", "game_id"])
    monotonic_cst = build_monotonic_cst(features)

    df = df.fillna(0)
    df[target] = df[target].map({"WIN": 1, "LOSE": 0})
    print(mode, len(features))

    X = df[features]
    X_lr = make_diff_features(df, features)
    y = df[target]
    groups = df["game_id"]
    n_games = len(groups.unique())

    # Number of split for each model
    if n_games < 50:
        gss = StratifiedGroupKFold(
            n_splits=max(2, n_games // 2), shuffle=True, random_state=137
        ).set_split_request(groups=True)
    else:
        gss = GroupShuffleSplit(
            n_splits=int(16 * np.log2(4 / 50 * n_games)),
            test_size=0.2,
            random_state=137,
        ).set_split_request(groups=True)

    def objective(trial):
        if n_games >= 100:
            model_type = trial.suggest_categorical("model_type", ["LR", "RF"])
        else:
            model_type = "LR"

        if model_type == "LR":
            c = trial.suggest_float("C", 1e-6, 1.0, log=True)
            l1 = trial.suggest_float("l1_ratio", 0.0, 0.5)

            model = LogisticRegression(
                C=c, l1_ratio=l1, class_weight="balanced", solver="saga", max_iter=2_000
            )

            pipeline = make_pipeline(
                RobustScaler(with_centering=False, quantile_range=(0, 75)), model
            )

            X_trial = X_lr

        elif model_type == "RF":
            # trees = trial.suggest_int("n_estimators", 100, 1000, step=50)
            samples_leaf = trial.suggest_int("min_samples_leaf", 1, 20)
            max_features = trial.suggest_int("max_features", 1, 16)

            model = RandomForestClassifier(
                n_estimators=100,
                min_samples_leaf=samples_leaf,
                max_features=max_features,
                max_depth=None,
                n_jobs=4,
                class_weight="balanced",
                monotonic_cst=monotonic_cst,
            )

            pipeline = make_pipeline(model)

            X_trial = X

        else:
            lr = trial.suggest_float("learning_rate", 0.01, 1.0, log=True)
            # trees = trial.suggest_int("max_iter", 100, 1000, step=50)
            limit_depth = trial.suggest_categorical("limit_depth", [True, False])
            if limit_depth:
                depth = trial.suggest_int("max_depth", 3, 20)
            else:
                depth = None
            leaf_nodes = trial.suggest_int("max_leaf_nodes", 10, 200)
            samples_leaf = trial.suggest_int("min_samples_leaf", 1, 100)
            use_l2 = trial.suggest_categorical("use_l2", [True, False])
            if use_l2:
                l2 = trial.suggest_float("l2_regularization", 0.01, 10, log=True)
            else:
                l2 = 0.0

            model = HistGradientBoostingClassifier(
                learning_rate=lr,
                max_iter=200,
                max_depth=depth,
                max_leaf_nodes=leaf_nodes,
                min_samples_leaf=samples_leaf,
                l2_regularization=l2,
                early_stopping=True,
                validation_fraction=0.1,
                class_weight="balanced",
                monotonic_cst=monotonic_cst,
            )

            pipeline = make_pipeline(model)

            X_trial = X

        scorer = make_scorer(
            log_loss,
            response_method="predict_proba",
            greater_is_better=False,
            labels=[0, 1],
        )

        scores = cross_val_score(
            pipeline, X_trial, y, groups=groups, cv=gss, scoring=scorer, n_jobs=4
        )

        return -np.quantile(scores, 1 / 4)

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        study_name=mode,
        direction="minimize",
        storage="sqlite:///hyperparameter_search.db",
        load_if_exists=True,
    )

    study.optimize(objective, n_trials=200, n_jobs=-1, show_progress_bar=True)

    print(f"{len(study.trials)} Trials were performed")
    print(
        *[": ".join(map(str, param)) for param in study.best_params.items()], sep="\n"
    )

    # Training model with optimal hyperparameters
    optimum = study.best_params
    model = optimum.pop("model_type", "LR")
    if model == "LR":
        final_model = LogisticRegression(
            **optimum, class_weight="balanced", solver="saga", max_iter=10_000
        )

        final_pipeline = make_pipeline(
            RobustScaler(with_centering=False, quantile_range=(0, 75)), final_model
        )

        final_pipeline.fit(X_lr, y)

    elif model == "RF":
        final_model = RandomForestClassifier(
            **optimum,
            n_estimators=500,
            max_depth=None,
            n_jobs=1,
            class_weight="balanced",
            monotonic_cst=monotonic_cst,
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=final_model, n_jobs=-1, method="isotonic", cv=gss
        )

        final_pipeline = calibrated_model

        final_pipeline.fit(X, y, groups=groups)

    else:
        if not optimum.pop("limit_depth", False):
            optimum["max_depth"] = None
        if not optimum.pop("use_l2", False):
            optimum["l2_regularization"] = 0.0

        final_model = HistGradientBoostingClassifier(
            **optimum,
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            class_weight="balanced",
            monotonic_cst=monotonic_cst,
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=final_model, n_jobs=-1, method="isotonic", cv=gss
        )

        final_pipeline = calibrated_model

        final_pipeline.fit(X, y, groups=groups)

    # Save model
    model_file = (Path("models") / mode).with_suffix(".joblib")
    model_file.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(final_pipeline, model_file)

    print(f"This took {time() - t:.2f} seconds")
    print("_" * 60, "\n")
