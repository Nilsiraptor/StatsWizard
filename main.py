from collections import defaultdict

import tkinter as tk
from tkinter import ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.pyplot import subplots

from authorization import ConnectionError
from wizard import GameState

class Stat:
    def __init__(self, name, parent=None):
        self.name = name.replace("_", " ").title()
        self.parent = parent

        self.label = tk.Label(parent, text=self.name)
        self.left_stat = tk.Label(parent, anchor="e", width=10, text="0")
        self.right_stat = tk.Label(parent, anchor="w", width=10, text="0")

    def grid(self, row):
        self.left_stat.grid(row=row, column=0)
        self.label.grid(row=row, column=1)
        self.right_stat.grid(row=row, column=2)


root = tk.Tk()
root.title('StatsWizard')
root.iconbitmap('my_icon.ico')

# Create a top-level frame for the window
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

# Create a frame for the top section
top_frame = tk.Frame(frame)
top_frame.pack(fill=tk.BOTH, expand=True)

# Add a group box to the top right
group_box = tk.LabelFrame(top_frame, text='Not in a game')
group_box.pack(side=tk.RIGHT, padx=10, pady=10)

# Create Stat objects for each stat and add it to the group box
stats = ["level", "kills", "deaths", "assists", "minions", "wards", "item_gold", "turrets", "inhibs", "heralds", "dragons", "barons", "aces"]
stat_objects = {}
for i, stat in enumerate(stats):
    stat_objects[stat] = Stat(stat, group_box)
    stat_objects[stat].grid(row=i)

# Add a canvas to the top left
parent_canvas = tk.Canvas(top_frame)
parent_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Add a Matplotlib plot to the canvas
fig, ax = subplots(figsize=(6.5, 3.25), dpi=96, facecolor="#f0f0f0")
ax.set_xlim(-10.1, 0.1)
ax.set_ylim(-0.02, 1.02)
ax.grid()
fig.tight_layout()
canvas = FigureCanvasTkAgg(fig, master=parent_canvas)
canvas.draw()
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Add a status bar to the window
status_bar = tk.Label(root, text='Ready - Searching League Client', bd=1, relief=tk.SUNKEN, anchor=tk.W)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

team = None

def update():
    global team

    # Check iff the game is still in Progress
    state = wizard.check_game_state()
    if state not in ["InProgress", "Reconnect"]:
        team = None
        status_bar.config(text="Game over - Waiting for new game")
        root.after(1000, wait_for_game_start)
        return

    status_bar.config(text="Ingame - Analysing data")

    scores = wizard.get_scores()

    stats_ally = defaultdict(int)
    stats_enemy = defaultdict(int)

    for key, value in scores.items():
        key_parts = key.split("_")

        if key_parts[0] == "ally":
            stats_ally[key_parts[-1]] += value
        else:
            stats_enemy[key_parts[-1]] += value


    for key, value in stat_objects.items():
        stat_objects[id].left_stat.config(text=f"{value}")
        stat_objects[id].right_stat.config(text=f"{value}")

    stat_objects["minions"].left_stat.config(text=f"{stats_ally['creepScore']}")
    stat_objects["minions"].right_stat.config(text=f"{stats_enemy['creepScore']}")

    stat_objects["wards"].left_stat.config(text=f"{stats_ally['wardScore']:.0f}")
    stat_objects["wards"].right_stat.config(text=f"{stats_enemy['wardScore']:.0f}")

    root.after(1000, update)


def wait_for_game_start():
    try:
        state = wizard.check_game_state()
    except ConnectionError:
        status_bar.config(text="Ready - Searching League Client")
        root.after(1000, search_league_client)
    else:
        if state == "None":
            status_bar.config(text=f"League Client found - Waiting for game start")
        elif state == "GameStart":
            status_bar.config(text="Game is starting")
            return
        elif state == "InProgress":
            status_bar.config(text="Game found - Waiting for data")
            group_box.config(text="Waiting for game data")
            root.after(1000, update)
            return
        else:
            status_bar.config(text=f"{state} - Waiting for game start")

        root.after(1000, wait_for_game_start)


def search_league_client():
    global wizard
    try:
        wizard = GameState()
    except ConnectionError:
        status_bar.config(text="Ready - Searching League Client")
        root.after(1000, search_league_client)
    else:
        status_bar.config(text="League Client found - Waiting for game start")
        root.after(1000,  wait_for_game_start)

# Set the minimum size to the current size
root.update_idletasks() # Updates the window dimensions
root.minsize(root.winfo_width(), root.winfo_height())

root.after(1000, search_league_client)
root.mainloop()
