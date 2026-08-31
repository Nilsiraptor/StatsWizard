from pathlib import Path

import joblib
import pandas as pd

for mode in Path("models").iterdir():
    if mode.suffix != ".joblib":
        continue

    model = joblib.load(mode)

    if "logisticregression" in model.named_steps:
        lr_model = model.named_steps["logisticregression"]
        features = model.named_steps["robustscaler"].feature_names_in_
        coefs = pd.Series(lr_model.coef_[0], index=features).sort_values()
        coefs.to_csv(f"LR_{mode.stem}_coefs.csv")
