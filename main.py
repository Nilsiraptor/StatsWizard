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
top_frame.pack(fill=tk.BOTH)

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
canvas = tk.Canvas(top_frame)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, padx=10, pady=10)

# Add a Matplotlib plot to the canvas
fig, ax = subplots(figsize=(6, 3), dpi=100, facecolor="#f0f0f0")
ax.set_xlim(-10.1, 0.1)
ax.set_ylim(-0.02, 1.02)
ax.grid()
fig.tight_layout()
canvas = FigureCanvasTkAgg(fig, master=canvas)
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
        root.after(10000, wait_for_game_start)
        return

    status_bar.config(text="Ingame - Analysing data")

    # Check the team of the player
    if team is None:
        team = wizard.get_team()

    # Get gameMode and gameTime
    data = wizard.get_data("gamestats")

    mode = data["gameMode"]
    time = int(data["gameTime"])
    group_box.config(text=f"{mode} \u200A(\u200A{time//60:02}:{time%60:02}\u200A)")

    # Calculate playerStats
    data = wizard.get_data("playerlist")
    stats_ally = defaultdict(int)
    stats_enemy = defaultdict(int)
    for player in data:
        if player["team"] == team:
            stats_ally["level"] += player["level"]
            for id, value in player["scores"].items():
                stats_ally[id] += value
        else:
            stats_enemy["level"] += player["level"]
            for id, value in player["scores"].items():
                stats_enemy[id] += value

    # Calculating team stats
    data = wizard.get_data("eventdata")

    for event in data["Events"]:
        if event["EventName"] == "TurretKilled":
            if wizard.get_team(event["KillerName"]) == team:
                stats_ally["turrets"] += 1
            else:
                stats_enemy["turrets"] += 1

        elif event["EventName"] == "InhibKilled":
            if wizard.get_team(event["KillerName"]) == team:
                stats_ally["inhibs"] += 1
            else:
                stats_enemy["inhibs"] += 1

        elif event["EventName"] == "HeraldKill":
            if wizard.get_team(event["KillerName"]) == team:
                stats_ally["heralds"] += 1
            else:
                stats_enemy["heralds"] += 1

        elif event["EventName"] == "DragonKill":
            if wizard.get_team(event["KillerName"]) == team:
                stats_ally["dragons"] += 1
            else:
                stats_enemy["dragons"] += 1

        elif event["EventName"] == "BaronKill":
            if wizard.get_team(event["KillerName"]) == team:
                stats_ally["barons"] += 1
            else:
                stats_enemy["barons"] += 1

        elif event["EventName"] == "Ace":
            if event["AcingTeam"] == team:
                stats_ally["aces"] += 1
            else:
                stats_enemy["aces"] += 1


    for id in stat_objects.keys():
        stat_objects[id].left_stat.config(text=f"{stats_ally[id]}")
        stat_objects[id].right_stat.config(text=f"{stats_enemy[id]}")

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
            root.after(10000, update)
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


root.after(1000, search_league_client)
root.mainloop()
