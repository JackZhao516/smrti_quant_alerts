import sys
import logging
import threading
from time import sleep

from crawl_exchange_list import CrawlExchangeList
from alert_coingecko import CrawlExchangeList4H, alert_coins, close_all_threads, CrawlExchangeListMarketCapReport
from telegram_api import TelegramBot
from binance_indicator_alert import BinanceIndicatorAlert
from binance_price_volume_alert import BinancePriceVolumeAlert

MODE = "CG_SUM"
# MODE = "TEST"
tg_bot = TelegramBot(MODE)
cg = CrawlExchangeList("CG_SUM_RAW")

logging.disable(logging.WARNING)
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


def alert_spot_cross_ma(exclude_coins, exclude_newly_deleted_coins,
                        exclude_newly_added_coin, alert_type="alert_300"):
    """
    if provided with excluded coins, deleted coins, and added coins,
    the function will not alert those coins
    :param exclude_coins: set of coins to be excluded
    :param exclude_newly_deleted_coins: set of coins to be excluded
    :param exclude_newly_added_coin: set of coins to be excluded
    :param alert_type: alert type
    """
    logging.info(f"{alert_type} start")
    count = alert_type.split("_")[1]
    # get coin list
    if alert_type == "alert_100":
        exchanges, coin_ids, coin_symbols = cg.get_top_market_cap_exchanges(num=100)
    elif alert_type == "alert_500":
        exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase(tg_alert=True)
    else:
        exchanges, coin_ids, coin_symbols = cg.get_top_market_cap_exchanges(num=300)

    logging.info("start coingecko alert")
    tg_type = "TEST"
    coingecko_res = CrawlExchangeList4H(coin_ids, coin_symbols, cg.active_exchanges,
                                        tg_type=tg_type, alert_type=count)
    coins, newly_deleted_coins, newly_added_coins = coingecko_res.run()
    logging.info(f"start binance indicator alert")
    logging.info(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
    binance_alert = BinanceIndicatorAlert(exchanges, alert_type=alert_type, tg_type=tg_type)
    exchanges, newly_deleted_exchanges, newly_added_exchanges = binance_alert.spot_cross_ma(4)

    coins.extend(exchanges)
    newly_deleted_coins.extend(newly_deleted_exchanges)
    newly_added_coins.extend(newly_added_exchanges)

    # exclude coins
    coins = [coin for coin in coins if coin not in exclude_coins]
    newly_deleted_coins = [coin for coin in newly_deleted_coins if coin not in exclude_newly_deleted_coins]
    newly_added_coins = [coin for coin in newly_added_coins if coin not in exclude_newly_added_coin]

    # send alert and return
    tg_bot.send_message(f"{alert_type}: market cap top {count}")
    if alert_type == "alert_500":
        tg_bot.send_message("and weekly volume increase >= 30% "
                            "for alt/busd, alt/usdt pairs\n")
    tg_bot.send_message(f"Top {count} coins/coin exchanges spot over H4 MA200:\n{coins}\n"
                        f"Top {count} coins/coin exchanges exchanges spot"
                        f" over H4 MA200 newly added:\n{newly_added_coins}\n"
                        f"Top {count} coins/coin exchanges exchanges spot"
                        f" over H4 MA200 newly deleted:\n{newly_deleted_coins}\n")

    logging.warning(f"{alert_type} finished")
    return set(coins).union(exclude_coins), \
        set(newly_deleted_coins).union(exclude_newly_deleted_coins), \
        set(newly_added_coins).union(exclude_newly_added_coin)


def report_market_cap():
    """
    market cap alerts
    """
    logging.info("report_market_cap start")
    top_200 = threading.Thread(target=CrawlExchangeListMarketCapReport, args=(200,))
    top_200.start()
    top_500 = threading.Thread(target=CrawlExchangeListMarketCapReport, args=(500,))
    top_500.start()
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
                                    exclude_newly_added_coin, alert_type)
        sleep(2 * 24 * 60 * 60)


if __name__ == "__main__":
    # sys.argv[1] is the mode
    if sys.argv[1] == "market_cap":
        report_market_cap()
    elif sys.argv[1] == "price_volume":
        price_volume()
    elif sys.argv[1] == "sequential":
        routinely_sequential_alert_100_300_500()
    else:
        while True:
            alert_spot_cross_ma([], [], [], sys.argv[1])
            sleep(2 * 24 * 60 * 60)
