"""Connects to the League of Legends client and collects game data.

This module provides the core API for communicating with the League
of Legends client, including game state detection, score collection,
and item gold calculation.
"""

import http
from collections import defaultdict
from enum import Enum, auto

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from authorization import ConnectionError, get_pem_port
from dragon import get_gold_value

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class GameState(Enum):
    """Represents the current state of a League of Legends client.

    States range from no client detected through various game phases
    to game over.
    """

    NO_CLIENT = auto()
    CLIENT_FOUND = auto()
    LOBBY = auto()
    QUEUE = auto()
    READY_CHECK = auto()
    CHAMP_SELECT = auto()
    RUNNING = auto()
    GAME_OVER = auto()
    UNDEFINED = auto()


PHASE_MAPPING = {
    "None": GameState.CLIENT_FOUND,
    "Lobby": GameState.LOBBY,
    "Matchmaking": GameState.QUEUE,
    "ReadyCheck": GameState.READY_CHECK,
    "ChampSelect": GameState.CHAMP_SELECT,
    "InProgress": GameState.RUNNING,
    "EndOfGame": GameState.GAME_OVER,
}


class GameResult(Enum):
    """Represents the outcome of a League of Legends game."""

    WIN = auto()
    LOSE = auto()


class GameAPI:
    """API client for communicating with the League of Legends client.

    Handles authentication, game state detection, and data collection
    from the local League client API endpoints.
    """

    def __init__(self):
        """Initializes the API client by authenticating with the League client.

        Retrieves PEM credentials from the lockfile and establishes
        the base URL for API communication.

        Raises:
            ConnectionError: If no League Client is found.
        """
        try:
            password, port = get_pem_port()
        except ConnectionError:
            raise ConnectionError("No League Client found!")
        else:
            self.user = "riot", password

            self.url = "https://127.0.0.1:" + port

        self.pem = "riotgames.pem"

    def check_game_state(self):
        """Checks the current game flow phase from the League client.

        Queries the local client API to determine the current game
        phase and maps it to a GameState enum value.

        Returns:
            The current GameState enum value.
        """
        # Make a request to the "ActiveProcess" endpoint of the Local Client API
        url = self.url + "/lol-gameflow/v1/gameflow-phase"

        try:
            response = requests.get(url, auth=self.user, verify=False)
        except requests.exceptions.ConnectionError:
            return GameState.NO_CLIENT

        # Check if the response contains the "gameData" field, which indicates the user is in a game
        if response.status_code == 200:
            return PHASE_MAPPING.get(response.json(), GameState.UNDEFINED)
        else:
            return GameState.UNDEFINED

    def get_data(self, data):
        """Fetches live client data from the League client API.

        Args:
          data: The data endpoint to fetch (e.g. 'gamestats', 'playerlist').

        Returns:
            The parsed JSON response data.

        Raises:
            ConnectionError: If the request fails or returns a non-200 status.
        """
        url = "https://127.0.0.1:2999/liveclientdata/" + data

        try:
            response = requests.get(url, verify=False)
        except requests.exceptions.ConnectionError:
            raise ConnectionError()
        except http.client.RemoteDisconnected:
            raise ConnectionError()

        if response.status_code == 200:
            return response.json()
        else:
            raise ConnectionError()

    def get_team(self, player=None):
        """Determines the current player's team.

        If no player name is provided, uses the active player name.
        Otherwise, looks up the specified player's team from the
        player list.

        Args:
          player: An optional summoner name to look up. If None, uses
            the active player.

        Returns:
            The team name ('ORDER' or 'CHAOS') for the player.
        """
        if player is None:
            url = "https://127.0.0.1:2999/liveclientdata/activeplayername"

            try:
                response = requests.get(url, verify=False)
            except requests.exceptions.ConnectionError:
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
            response = requests.get(url, verify=False)
        except requests.exceptions.ConnectionError:
            raise ConnectionError
        else:
            if response.status_code == 200:
                players = response.json()

                for p in players:
                    if p["summonerName"] == name:
                        return p["team"]

    def get_scores(self):
        """Collects comprehensive game statistics for both teams.

        Fetches game stats, player data, and event data to build a
        complete score dictionary including levels, kills, deaths,
        assists, objective kills, turrets, inhibitors, and game result.

        Returns:
            A defaultdict mapping stat keys (e.g. 'ally_kills') to
            their current values.
        """
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
                structure = event["TurretKilled"]

                if self.get_team_from_structure(structure) == team:
                    scores["ally_turrets"] += 1
                else:
                    scores["enemy_turrets"] += 1

            elif event["EventName"] == "InhibKilled":
                structure = event["InhibKilled"]

                if self.get_team_from_structure(structure) == team:
                    scores["ally_inhibs"] += 1
                else:
                    scores["enemy_inhibs"] += 1
            elif event["EventName"] == "GameEnd":
                if event["Result"] == "Win":
                    scores["result"] = GameResult.WIN
                else:
                    scores["result"] = GameResult.LOSE

        return scores

    def get_team_from_structure(self, identifier):
        token = identifier.split("_")[1]

        if "Chaos" in token:
            return "ORDER"
        if "Order" in token:
            return "CHAOS"
        if "T1" == token:
            return "CHAOS"
        if "T2" == token:
            return "ORDER"

        raise ValueError(f"Unrecognized Structure Identifier: {identifier!r}")

    def get_item_gold(self, include_consumables=False):
        """Calculates the total item gold for both teams.

        Args:
          include_consumables: If True, includes consumable items in
            the gold calculation. Defaults to False.

        Returns:
            A tuple of (ally_gold, enemy_gold) integers.
        """
        team = self.get_team()
        ally_items = []
        enemy_items = []

        player_data = self.get_data("playerlist")

        for p in player_data:
            items = [
                item["itemID"]
                for item in p["items"]
                if include_consumables or not item["consumable"]
            ]
            if p["team"] == team:
                ally_items += items
            else:
                enemy_items += items

        ally_gold = get_gold_value(ally_items)
        enemy_gold = get_gold_value(enemy_items)

        return ally_gold, enemy_gold


if __name__ == "__main__":
    try:
        state = GameAPI()
    except ConnectionError:
        print("No League Client found!")
    else:
        print(state.check_game_state())
        print("\n", state.get_scores())
