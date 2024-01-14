import os
import json
import datetime
import pytz

from typing import Set

from smrti_quant_alerts.settings import Config


def write_exclude_coins_to_file(input_exclude_coins: str) -> None:
    """
    write exclude coins to json file

    :param input_exclude_coins: str "xxx, xxx, xxx"
    """
    with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json"), "r") as f:
        exclude_coins = json.load(f)
        exclude_coins_set = set(exclude_coins)
        for coin in input_exclude_coins.split(","):
            if coin.strip().upper() not in exclude_coins_set:
                exclude_coins.append(coin.strip().upper())
    with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json")) as f:
        json.dump(exclude_coins, f)


def read_exclude_coins_from_file() -> Set[str]:
    """
    read exclude coins from json file

    :return: set of exclude coins
    """
    exclude_coins = set()
    if os.path.exists(os.path.join(Config.PROJECT_DIR, "stable_coins.json")):
        with open(os.path.join(Config.PROJECT_DIR, "stable_coins.json")) as f:
            exclude_coins.update(json.load(f))

    if os.path.exists(os.path.join(Config.PROJECT_DIR, "exclude_coins.json")):
        with open(os.path.join(Config.PROJECT_DIR, "exclude_coins.json"), "r") as f:
            exclude_coins.update(json.load(f))
    return exclude_coins


def get_datetime_now(timezone: str = "US/Eastern") -> datetime.datetime:
    """
    get datetime now with timezone

    :param timezone: str
    :return: datetime.datetime
    """
    return datetime.datetime.now(pytz.timezone(timezone))
