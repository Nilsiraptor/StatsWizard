import pandas as pd


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

def make_diff_features(df, features, drop=["gameTime"]):
    diff_cols = {}
    paired = set()
    for col in features:
        if col.startswith("ally_"):
            counterpart = col.replace("ally", "enemy", 1)
            if counterpart in features:
                stat_name = col.replace("ally_", "", 1)
                diff_cols[stat_name + "_diff"] = df[col] - df[counterpart]
                paired.add(col)
                paired.add(counterpart)
    unpaired = [c for c in features if c not in paired and c not in drop]
    return pd.concat([pd.DataFrame(diff_cols, index=df.index), df[unpaired]], axis=1)
