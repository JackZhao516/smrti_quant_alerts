"""Technical indicators used by alerts."""

import numpy as np
from talib import MACD


def calculate_macd(
    close: list[float], fastperiod: int = 12, slowperiod: int = 26, signalperiod: int = 9
) -> list[float]:
    """
    calculate MACD histogram

    :param close: list of close prices
    :param fastperiod: int
    :param slowperiod: int
    :param signalperiod: int
    :return: MACD histogram, from newest to oldest
    """
    close = np.array(close, dtype=np.float64)
    return (MACD(close, fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)[2])[::-1]
