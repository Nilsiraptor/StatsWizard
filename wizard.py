from collections import defaultdict
import requests
import http

from authorization import get_pem_port, ConnectionError
from dragon import get_gold_value

class GameOver(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GameOverWin(GameOver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GameOverLose(GameOver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class GameState:

    def __init__(self):
        try:
            password, port = get_pem_port()
        except ConnectionError:
            raise ConnectionError("No League Client found!")
        else:
            self.user = "riot", password

            self.url = "https://127.0.0.1:" + port

        self.pem = "riotgames.pem"

    def check_game_state(self):
        # Make a request to the "ActiveProcess" endpoint of the Local Client API
        url = self.url + "/lol-gameflow/v1/gameflow-phase"

        try:
            response = requests.get(url, auth=self.user, verify=self.pem)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()

        # Check if the response contains the "gameData" field, which indicates the user is in a game
        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError()

    def get_data(self, data):
        url = "https://127.0.0.1:2999/liveclientdata/" + data

        try:
            response = requests.get(url, verify=self.pem)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError()
        except http.client.RemoteDisconnected as e:
            raise ConnectionError()

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError()

    def get_team(self, player=None):
        if player is None:
            url = "https://127.0.0.1:2999/liveclientdata/activeplayername"

            try:
                response = requests.get(url, verify=self.pem)
            except requests.exceptions.ConnectionError as e:
                raise ConnectionError()
            else:
                if response.status_code == 200:
                    name = response.json()
                else:
                    raise ConnectionError()
        else:
            name = player

        url = "https://127.0.0.1:2999/liveclientdata/playerlist"

        try:
            response = requests.get(url, verify=self.pem)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError
        else:
            if response.status_code == 200:
                players = response.json()

                for p in players:
                    if p["summonerName"] == name:
                        return p["team"]

    def get_scores(self):
        team = self.get_team()
        scores = defaultdict(int)
        ally_member = []
        enemy_member = []

        # Fetch basic game data
        game_data = self.get_data("gamestats")
        scores["gameMode"] = game_data["gameMode"]
        scores["gameTime"] = game_data["gameTime"]

        # Fetch player score
        player_data = self.get_data("playerlist")

        for player in player_data:
            if player["team"] == team:
                team_id = "ally"
                ally_member.append(player["summonerName"])
            else:
                team_id = "enemy"
                enemy_member.append(player["summonerName"])

            scores[f"{team_id}_{player['position']}_level"] += player["level"]

            for id, value in player["scores"].items():
                scores[f"{team_id}_{player['position']}_{id}"] += value

        # Fetch team scores
        event_data = self.get_data("eventdata")["Events"]

        for event in event_data:
            if event["EventName"] in ["HeraldKill", "DragonKill", "BaronKill"]:
                if event["KillerName"] in ally_member:
                    scores[f"ally_{event['EventName'][:-4].lower()}s"] += 1
                else:
                    scores[f"enemy_{event['EventName'][:-4].lower()}s"] += 1

            elif event["EventName"] == "Ace":
                if event["AcingTeam"] == team:
                    scores["ally_aces"] += 1
                else:
                    scores["enemy_aces"] += 1

            elif event["EventName"] == "TurretKilled":
                structure = event["TurretKilled"].split("_")[1]

                if structure == "T2" and team == "ORDER" or structure == "T1" and team == "CHAOS":
                    scores["ally_turrets"] += 1
                else:
                    scores["enemy_turrets"] += 1

            elif event["EventName"] == "InhibKilled":
                structure = event["InhibKilled"].split("_")[1]

                if structure == "T2" and team == "ORDER" or structure == "T1" and team == "CHAOS":
                    scores["ally_inhibs"] += 1
                else:
                    scores["enemy_inhibs"] += 1
            elif event["EventName"] == "GameEnd":
                if event["Result"] == "Win":
                    raise GameOverWin()
                else:
                    raise GameOverLose()

        return scores

    def get_item_gold(self, include_consumables=False):
        team = self.get_team()
        ally_items = []
        enemy_items = []

        player_data = self.get_data("playerlist")

        for p in player_data:
            items = [item["itemID"] for item in p["items"] if include_consumables or not item["consumable"]]
            if p["team"] == team:
                ally_items += items
            else:
                enemy_items += items

        ally_gold = get_gold_value(ally_items)
        enemy_gold = get_gold_value(enemy_items)

        return ally_gold, enemy_gold

if __name__ ==  "__main__":
    try:
        state = GameState()
    except ConnectionError:
        print("No League Client found!")
    else:
        print(state.check_game_state())
        print("\n", state.get_scores())
