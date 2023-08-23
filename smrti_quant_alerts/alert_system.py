import sys
import logging
import threading
from time import sleep

from .get_exchange_list import GetExchangeList
from smrti_quant_alerts.alerts.coingecko_market_cap_alert import CoingeckoMarketCapReport
from smrti_quant_alerts.alerts.binance_price_volume_alert import BinancePriceVolumeAlert
from smrti_quant_alerts.alerts.coingecko_alts_alert import CGAltsAlert
from smrti_quant_alerts.alerts.top_market_cap_spot_over_ma_alert import alert_spot_cross_ma
from smrti_quant_alerts.alerts.binance_bi_hourly_future_funding_rate_alert import FutureFundingRate
from .telegram_api import TelegramBot
from .settings import Config

MODE = "CG_SUM"
# MODE = "TEST"
tg_bot = TelegramBot(MODE)
cg = GetExchangeList("CG_SUM_RAW")

logging.disable(logging.INFO)


def report_market_cap():
    """
    market cap alerts
    """
    logging.info("report_market_cap start")
    nums = [100, 200, 300, 400, 500]
    thread = threading.Thread(target=CoingeckoMarketCapReport, args=(nums,))
    thread.start()
    sleep(60 * 60 * 24 * 365)
    logging.info("report_market_cap finished")


def price_volume():
    """
    price/volume alerts
    """
    BinancePriceVolumeAlert().klines_alert()


def routinely_sequential_alert_100_300_500():
    """
    sequentially alert 100, 300, 500 coins
    """
    logging.info("routinely_sequential_alert_100_300_500 start")
    while True:
        exclude_coins, exclude_newly_deleted_coins, exclude_newly_added_coin = set(), set(), set()
        for alert_type in ["alert_100", "alert_300", "alert_500"]:
            exclude_coins, exclude_newly_deleted_coins, exclude_newly_added_coin = \
                alert_spot_cross_ma(exclude_coins, exclude_newly_deleted_coins,
                                    exclude_newly_added_coin, alert_type, tg_mode=MODE)
        sleep(24 * 60 * 60)


def alert_spot_over_ma(alert_type):
    """
    alert 100/300/500 coins

    :param alert_type: alert type
    """
    while True:
        tg_mode = "ALERT_VOLUME_THRESHOLD" if alert_type == "alert_volume_threshold" else MODE
        alert_spot_cross_ma([], [], [], alert_type, tg_mode=tg_mode)
        sleep(24 * 60 * 60)


def alts_alert():
    """
    alert alt coins
    """
    CGAltsAlert()


def funding_rate():
    """
    alert funding rate
    """
    future_funding_rate = FutureFundingRate(tg_type="FUNDING_RATE")
    future_funding_rate.bi_hourly_alert_funding_rate_over_threshold()


if __name__ == "__main__":
    Config()
    # sys.argv[1] is the mode
    if sys.argv[1] == "market_cap":
        report_market_cap()
    elif sys.argv[1] == "price_volume":
        price_volume()
    elif sys.argv[1] == "sequential":
        routinely_sequential_alert_100_300_500()
    elif sys.argv[1] == "alts":
        alts_alert()
    elif sys.argv[1] in ("alert_100", "alert_300", "alert_500", "alert_volume_threshold"):
        alert_spot_over_ma(sys.argv[1])
    elif sys.argv[1] == "funding_rate":
        funding_rate()
