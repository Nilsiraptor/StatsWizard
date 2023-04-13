from collections import defaultdict
import requests

from authorization import get_pem_port, ConnectionError


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
            data = response.json()
        else:
            raise ConnectionError()

        return data

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


if __name__ ==  "__main__":
    try:
        state = GameState()
    except ConnectionError:
        print("No League Client found!")
    else:
        print(state.check_game_state())
