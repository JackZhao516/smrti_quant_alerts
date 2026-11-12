"""Read and update coin exclusions in local configuration files."""

import json
import os

from smrti_quant_alerts.settings import Config


def write_exclude_coins_to_file(input_exclude_coins: str) -> None:
    """
    write exclude coins to json file

    :param input_exclude_coins: str "xxx, xxx, xxx"
    """
    with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json")) as f:
        exclude_coins = json.load(f)
        exclude_coins_set = set(exclude_coins)
        for coin in input_exclude_coins.split(","):
            if coin.strip().upper() not in exclude_coins_set:
                exclude_coins.append(coin.strip().upper())
    with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json"), "w") as f:
        json.dump(exclude_coins, f)


def read_exclude_coins_from_file() -> set[str]:
    """
    read exclude coins from json file

    :return: set of exclude coins
    """
    exclude_coins = set()
    if os.path.exists(os.path.join(Config.PROJECT_DIR, "stable_coins.json")):
        with open(os.path.join(Config.PROJECT_DIR, "stable_coins.json")) as f:
            exclude_coins.update(json.load(f))

    if os.path.exists(os.path.join(Config.PROJECT_DIR, "exclude_coins.json")):
        with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json")) as f:
            exclude_coins.update(json.load(f))
    return exclude_coins
