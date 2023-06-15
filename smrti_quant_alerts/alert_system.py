import sys
import logging
import threading
from time import sleep

from smrti_quant_alerts.crawl_exchange_list import CrawlExchangeList
from smrti_quant_alerts.alerts.coingecko_market_cap_alert import CoingeckoMarketCapReport
from smrti_quant_alerts.alerts.binance_price_volume_alert import BinancePriceVolumeAlert
from smrti_quant_alerts.alerts.coingecko_alts_alert import CGAltsAlert
from smrti_quant_alerts.alerts.top_market_cap_spot_over_ma_alert import alert_spot_cross_ma
from smrti_quant_alerts.telegram_api import TelegramBot

MODE = "CG_SUM"
# MODE = "TEST"
tg_bot = TelegramBot(MODE)
cg = CrawlExchangeList("CG_SUM_RAW")

logging.disable(logging.INFO)
# def alert_indicator(alert_type="alert_100"):
#     logging.info(f"{alert_type} start")
#     if alert_type == "alert_100":
#         exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=100)
#     else:
#         exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase()
#     logging.warning("start coingecko alert")
#     tg_type = "CG_ALERT"
#     coins_thread = alert_coins(coin_ids, coin_symbols, alert_type=alert_type, tg_type=tg_type)
#     execution_time = 60 * 60 * 24 * 3 + 60 * 35
#     logging.warning(f"start binance indicator alert")
#     logging.warning(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
#     binance_alert = BinanceIndicatorAlert(exchanges, alert_type=alert_type, execution_time=execution_time, tg_type=tg_type)
#     binance_alert.run()
#
#     close_all_threads(coins_thread)
#     logging.warning(f"{alert_type} finished")


def report_market_cap():
    """
    market cap alerts
    """
    logging.info("report_market_cap start")
    nums = [100, 200, 300, 400, 500]
    for num in nums:
        thread = threading.Thread(target=CoingeckoMarketCapReport, args=(num,))
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


def alert_100_300_500(alert_type):
    """
    alert 100/300/500 coins

    :param alert_type: alert type
    """
    while True:
        alert_spot_cross_ma([], [], [], alert_type, tg_mode=MODE)
        sleep(2 * 24 * 60 * 60)


def alts_alert():
    """
    alert alt coins
    """
    CGAltsAlert()


if __name__ == "__main__":
    # sys.argv[1] is the mode
    if sys.argv[1] == "market_cap":
        report_market_cap()
    elif sys.argv[1] == "price_volume":
        price_volume()
    elif sys.argv[1] == "sequential":
        routinely_sequential_alert_100_300_500()
    elif sys.argv[1] == "alts":
        alts_alert()
    elif sys.argv[1] == ("alert_100" or "alert_300" or "alert_500"):
        alert_100_300_500(sys.argv[1])
