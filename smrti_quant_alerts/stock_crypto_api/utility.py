import os
import json
import datetime
import pytz
import numpy as np

from typing import Set, List
from decimal import Decimal
from talib import MACD

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


def get_stock_market_close_timestamp_from_date(date: str) -> int:
    """
    get stock market close time stamp from date at 4pm EST

    :param date: str
    :return: timestamp in ms
    """
    timezone = pytz.timezone("US/Eastern")
    return int(timezone.localize(datetime.datetime.strptime(
        date, "%Y-%m-%d")).replace(hour=16, minute=0).timestamp()) * 1000


def get_date_from_timestamp(timestamp: int) -> str:
    """
    get date from timestamp

    :param timestamp: int
    :return: str
    """
    timezone = pytz.timezone("US/Eastern")
    return datetime.datetime.fromtimestamp(timestamp / 1000, timezone).strftime("%Y-%m-%d")


def calculate_macd(close: List[float], fastperiod: int = 12,
                   slowperiod: int = 26, signalperiod: int = 9) -> List[float]:
    """
    calculate MACD histogram

    :param close: list of close prices
    :param fastperiod: int
    :param slowperiod: int
    :param signalperiod: int
    :return: MACD histogram, from newest to oldest
    """
    close = np.array(close)
    return (MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)[2])[::-1]
