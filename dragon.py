import json
import os

import requests


def update():
    """Downloads the latest League of Legends item data from DataDragon.

    Fetches the current version from the DataDragon API, creates the
    local directory structure if needed, and downloads the item data
    for the latest version.

    Returns:
        The version string of the downloaded item data.
    """
    url = "https://ddragon.leagueoflegends.com/api/versions.json"
    versions = requests.get(url).json()
    if not os.path.exists("DataDragon"):
        os.mkdir("DataDragon")
    if not os.path.exists("DataDragon\\" + versions[0]):
        os.mkdir("DataDragon\\" + versions[0])

        url = (
            "http://ddragon.leagueoflegends.com/cdn/"
            + versions[0]
            + "/data/en_US/item.json"
        )
        data = requests.get(url).json()
        with open("DataDragon\\" + versions[0] + "\\item.json", "w") as file:
            json.dump(data, file)
    return versions[0]


def get_gold_value(items):
    """Calculates the total gold value of a list of item IDs.

    Downloads the latest item data if not already cached, then sums
    the total gold values for all provided item IDs.

    Args:
        items: A list of item ID strings to look up.

    Returns:
        The total gold value (integer) of all the provided items.
    """
    version = update()

    with open("DataDragon\\" + version + "\\item.json", "r") as file:
        data = json.load(file)["data"]

    total_value = 0
    for id in items:
        total_value += data[str(id)]["gold"]["total"]

    return total_value
