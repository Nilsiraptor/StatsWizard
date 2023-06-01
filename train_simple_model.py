import random
import pickle

from sklearn.linear_model import LogisticRegression
import matplotlib.pyplot as plt
import numpy as np

def win(a, b):
    diff = a-b
    return 2*random.random() - 1 < diff/15000

def main():
    gold = [random.randint(10000, 60000) for _ in range(100)]
    gold_list = [(g + random.randint(-10000, 10000), g) for g in gold]

    win_list = [win(*gold) for gold in gold_list]

    wins_x = [g for (g, _), w in zip(gold_list, win_list) if w]
    wins_y = [g for (_, g), w in zip(gold_list, win_list) if w]

    loses_x = [g for (g, _), w in zip(gold_list, win_list) if not w]
    loses_y = [g for (_, g), w in zip(gold_list, win_list) if not w]

    model = LogisticRegression(warm_start=True, solver="saga")

    model.fit(gold_list, win_list)

    print(model.coef_)

    with open("simple_model.pkl", "wb") as file:
        pickle.dump(model, file)

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(10, 5))
    ax1.set_aspect("equal")
    ax1.grid()

    ax1.plot(wins_x, wins_y, "C0o")
    ax1.plot(loses_x, loses_y, "C1o")

    coords = np.linspace(0, 20000, 71)
    X, Y = np.meshgrid(coords, coords)

    Z = X/(X+Y)
    # ax2.contourf(X, Y, Z, cmap="RdYlGn", vmin=0, vmax=1, levels=1000)

    x = X.flatten()
    y = Y.flatten()

    z = model.predict_proba(list(zip(x, y)))[:, 1]
    Z = z.reshape(X.shape)
    ax2.contourf(X, Y, Z, cmap="RdYlGn", vmin=0, vmax=1, levels=1000)

    fig.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
