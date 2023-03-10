import sys
import logging
import threading
from time import sleep

from crawl_coingecko import CoinGecKo
from alert_coingecko import CoinGecKo4H, alert_coins, close_all_threads, CoinGecKoMarketCapReport
from telegram_api import TelegramBot
from binance_indicator_alert import BinanceIndicatorAlert

MODE = "CG_SUM"
tg_bot = TelegramBot(MODE)
cg = CoinGecKo("TEST")


def alert_indicator(alert_type="alert_100"):
    logging.info(f"{alert_type} start")
    if alert_type == "alert_100":
        exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=100)
    else:
        exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase()
    logging.warning("start coingecko alert")
    tg_type = "CG_ALERT"
    coins_thread = alert_coins(coin_ids, coin_symbols, alert_type=alert_type, tg_type=tg_type)
    execution_time = 60 * 60 * 24 * 3 + 60 * 35
    logging.warning(f"start binance indicator alert")
    logging.warning(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
    binance_alert = BinanceIndicatorAlert(exchanges, alert_type=alert_type, execution_time=execution_time, tg_type=tg_type)
    binance_alert.run()

    close_all_threads(coins_thread)
    logging.warning(f"{alert_type} finished")


def alert_spot_cross_ma(alert_type="alert_300"):
    while True:
        logging.info(f"{alert_type} start")
        count = alert_type.split("_")[1]
        if alert_type == "alert_100":
            exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=100)
        elif alert_type == "alert_500":
            exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase()
        else:
            exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=300)
        logging.warning("start coingecko alert")
        tg_type = "TEST"
        coingecko_res = CoinGecKo4H(coin_ids, coin_symbols, tg_type=tg_type, alert_type=count)
        coins, newly_deleted_coins, newly_added_coins = coingecko_res.run()
        logging.warning(f"start binance indicator alert")
        logging.warning(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
        binance_alert = BinanceIndicatorAlert(exchanges, alert_type=alert_type, tg_type=tg_type)
        exchanges, newly_deleted_exchanges, newly_added_exchanges = binance_alert.spot_cross_ma(4)
        coins.extend(exchanges)
        newly_deleted_coins.extend(newly_deleted_exchanges)
        newly_added_coins.extend(newly_added_exchanges)

        l, r = coins[:len(coins) // 2], coins[len(coins) // 2:]
        
        tg_bot.safe_send_message(f"{alert_type}: market cap top {count}")

        if alert_type == "alert_500":
            tg_bot.safe_send_message("and weekly volume increase >= 30%")
        tg_bot.safe_send_message(f"Top {count} coins/coin exchanges spot over H4 MA200:\n{l}")
        tg_bot.safe_send_message(f"{r}")

        tg_bot.safe_send_message(f"Top {count} coins/coin exchanges exchanges spot"
                                    f" over H4 MA200 newly added:\n{newly_added_coins}")
        tg_bot.safe_send_message(f"Top {count} coins/coin exchanges exchanges spot"
                                    f" over H4 MA200 newly deleted:\n{newly_deleted_exchanges}")

        logging.warning(f"{alert_type} finished")
        sleep(2 * 24 * 60 * 60)


def report_market_cap():
    logging.info("report_market_cap start")
    top_200 = threading.Thread(target=CoinGecKoMarketCapReport, args=(200,))
    top_200.start()
    top_500 = threading.Thread(target=CoinGecKoMarketCapReport, args=(500,))
    top_500.start()
    sleep(60 * 60 * 24 * 365)
    logging.warning("report_market_cap finished")


if __name__ == "__main__":
    # sys.argv[1] is the mode
    if sys.argv[1] == "market_cap":
        report_market_cap()
    else:
        alert_spot_cross_ma(sys.argv[1])
