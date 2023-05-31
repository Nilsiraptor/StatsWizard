import os
import json
import requests

def update():
    url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(url).json()
    if not os.path.exists("DataDragon"):
        os.mkdir("DataDragon")
    if not os.path.exists("DataDragon\\" + versions[0]):
        os.mkdir("DataDragon\\" + versions[0])

        url = "http://ddragon.leagueoflegends.com/cdn/" + versions[0] + "/data/en_US/item.json"
        data = requests.get(url).json()
        with open("DataDragon\\" + versions[0] + "\\item.json", "w") as file:
            json.dump(data, file)
    return versions[0]

def get_gold_value(items):
    version = update()

    with open("DataDragon\\" + version + "\\item.json", "r") as file:
        data = json.load(file)["data"]

    total_value = 0
    for id in items:
        total_value += data[id]["gold"]["total"]

    return total_value
