from pathlib import Path
from time import perf_counter as time

import pandas as pd
import numpy as np
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, cross_val_score
from sklearn.preprocessing import RobustScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import make_scorer, log_loss
from scipy.stats import uniform, loguniform
import sklearn
import joblib
import optuna


def build_monotonic_cst(columns):
    positive = [
        "kills", "assists", "creepScore", "level", "turrets", "inhibs",
        "dragons", "barons", "heralds", "aces"
    ]
    negative = ["deaths"]

    cst = []
    for feat in columns:
        if feat.startswith("ally"):
            sign = 1
        elif feat.startswith("enemy"):
            sign = -1
        else:
            cst.append(0)
            continue

        if any(stat in feat for stat in positive):
            cst.append(sign)
        elif any(stat in feat for stat in negative):
            cst.append(-sign)
        else:
            cst.append(0)

    return cst


sklearn.set_config(enable_metadata_routing=True)

input_folder = Path("GameData")

for mode_file in input_folder.glob("*.csv"):
    t = time()

    mode = mode_file.stem

    df = pd.read_csv(mode_file)

    target = "result"
    features = df.columns.drop(["result", "gameMode", "game_id"])

    df = df.fillna(0)
    df[target] = df[target].map({"WIN": 1, "LOSE": 0})
    print(mode, len(features))

    X = df[features]
    y = df[target]
    groups = df["game_id"]
    n_games = len(groups.unique())

    # Number of split for each model
    if n_games < 50:
        gss = GroupKFold(
            n_splits=max(2, n_games//4),
            shuffle=True,
            random_state=137
        ).set_split_request(groups=True)
    else:
        gss = GroupShuffleSplit(
            n_splits=int(16*np.log2(4/50*n_games)),
            test_size=0.2,
            random_state=137
        ).set_split_request(groups=True)

    def objective(trial):
        if n_games >= 100:
            model_type = trial.suggest_categorical("model_type", ["LR", "RF", "HGBM"])
        else:
            model_type = "LR"

        if model_type == "LR":
            c = trial.suggest_float("C", 0.001, 0.02, log=True)
            l1 = trial.suggest_float("l1_ratio", 0.0, 0.5)

            model = LogisticRegression(
                C=c,
                l1_ratio=l1,
                class_weight="balanced",
                solver="saga",
                max_iter=2000
            )

            pipeline = make_pipeline(RobustScaler(
                with_centering=False,
                quantile_range=(0, 50)
            ), model)

        elif model_type == "RF":
            trees = trial.suggest_int("n_estimators", 100, 1000, step=50)
            samples_leaf = trial.suggest_int("min_samples_leaf", 5, 20)
            max_features = trial.suggest_int("max_features", 2, 16)

            model = RandomForestClassifier(
                n_estimators=trees,
                max_depth=None,
                # min_samples_split=samples_split,
                min_samples_leaf=samples_leaf,
                max_features=max_features,
                n_jobs=-1,
                class_weight="balanced",
                monotonic_cst=build_monotonic_cst(features)
            )

            pipeline = make_pipeline(model)

        else:
            lr = trial.suggest_float("learning_rate", 0.01, 1.0, log=True)
            trees = trial.suggest_int("max_iter", 100, 1000, step=50)
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
                max_iter=trees,
                max_depth=depth,
                max_leaf_nodes=None,
                min_samples_leaf=samples_leaf,
                l2_regularization=l2,
                early_stopping=True,
                validation_fraction=0.1,
                class_weight="balanced",
                monotonic_cst=build_monotonic_cst(features)
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

        return -np.quantile(scores, 1/16)

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    study = optuna.create_study(
        study_name=mode,
        direction="minimize",
        storage="sqlite:///hyperparameter_search.db",
        load_if_exists=True
    )

    study.optimize(
        objective,
        n_trials=100,
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
        final_model = RandomForestClassifier(
            **optimum,
            max_depth=None,
            n_jobs=-1,
            class_weight="balanced",
            monotonic_cst=build_monotonic_cst(features)
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=final_model,
            method="isotonic",
            cv=gss
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
            n_jobs=-1,
            max_leaf_nodes=None,
            early_stopping=True,
            validation_fraction=0.1,
            class_weight="balanced",
            monotonic_cst=build_monotonic_cst(features)
        )

        calibrated_model = CalibratedClassifierCV(
            estimator=final_model,
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
