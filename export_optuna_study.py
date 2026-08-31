import optuna

for mode in ["ARAM", "CLASSIC", "KIWI", "STRAWBERRY"]:
    if mode != "ARAM":
        pass

    try:
        study = optuna.load_study(
            study_name=mode, storage="sqlite:///hyperparameter_search.db"
        )

        df = study.trials_dataframe()

        df.to_csv(f"hyperparameter_search_{mode}.csv", index=False)
    except:
        print(f"{mode} skipped. No study found!")
