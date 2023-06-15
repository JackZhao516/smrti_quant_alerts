import logging
import time

import requests
from binance.lib.utils import config_logging

from .utility import update_coins_exchanges_txt
from smrti_quant_alerts.crawl_exchange_list import CrawlExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot

STABLE_COINS = {"USDT", "USDC", "DAI", "BUSD", "USDP", "GUSD",
                "TUSD", "FRAX", "CUSD", "USDD", "DEI", "USDK",
                "MIMATIC", "OUSD", "PAX", "FEI", "USTC", "USDN",
                "TRIBE", "LUSD", "EURS", "VUSDC", "USDX", "SUSD",
                "VAI", "RSV", "CEUR", "USDS", "CUSDT", "DOLA",
                "HAY", "MIM", "EDGT", "ALUSD"}


class CoingeckoAlert4H(CrawlExchangeList):
    def __init__(self, coin_ids, coin_symbols, active_exchanges=None, tg_type="CG_SUM", alert_type="300"):
        super().__init__(tg_type, active_exchanges=active_exchanges)
        self.coin_ids = coin_ids
        self.coin_symbols = coin_symbols
        self.spot_over_h4 = set()
        self.alert_type = alert_type

    def h4_sma_200(self, coin_id, coin_symbol):
        try:
            price = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=35)
            price = price['prices']
            price = [i[1] for i in price]
            res = 0
            counter = 0
            for i in range(0, len(price), 4):
                if i == 800:
                    break
                res += float(price[len(price) - 1 - i])
                counter += 1
            sma = res / counter
            price = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=1)
            price = float(price['prices'][-1][1])

            logging.warning(f"{coin_symbol}: {price}, {sma}")
            if price > sma:
                self.spot_over_h4.add(coin_symbol)
                return True

        except Exception as e:
            return False

    def run(self):
        for coin_id, coin_symbol in zip(self.coin_ids, self.coin_symbols):
            coin_symbol = coin_symbol.upper()
            if coin_symbol in STABLE_COINS:
                continue
            self.h4_sma_200(coin_id, coin_symbol)
        logging.warning(f"spot_over_h12_{self.alert_type}: {self.spot_over_h4}")

        return update_coins_exchanges_txt(self.spot_over_h4, "coins", self.alert_type)


class BinanceIndicatorAlert4H:
    """
    first download, then run a websocket
    """
    HTTP_URL = "https://api.binance.com/api/v3/klines?"
    STABLE_EXCHANGES = {"wbtcbtc", "busdusdt", "usdcbusd", "usdcusdt", "usdpusdt"}
    config_logging(logging, logging.INFO)

    def __init__(self, exchanges, alert_type="alert_100"):
        exchanges = [exchange.lower() for exchange in exchanges]
        exchanges.sort()
        self.exchanges = exchanges
        self.alert_type = alert_type
        self.window = 200

        # for calculating spot over h4 exchanges
        self.spot_over_h4 = set()

    def spot_cross_ma(self, time_frame):
        """
        find spot cross ma exchanges
        """
        for exchange in self.exchanges:
            if exchange.lower() in self.STABLE_EXCHANGES:
                continue
            logging.warning(f"Downloading past klines {time_frame}h for {exchange}")
            exchange = exchange.upper()
            days_delta = time_frame * self.window // 24 + 1
            start_time = (int(time.time()) - days_delta * 24 * 60 * 60) * 1000
            now_time = (int(time.time()) - 60) * 1000

            url = f"{self.HTTP_URL}symbol={exchange}&interval=4h&startTime={start_time}&limit=1000"
            url_now = f"{self.HTTP_URL}symbol={exchange}&interval=1m&startTime={now_time}&limit=1000"
            try:
                response = requests.get(url, timeout=2).json()
                response_now = requests.get(url_now, timeout=2).json()

                current_close = float(response_now[-1][4])

                count = 0
                cum_sum = 0.0

                for candle in reversed(response):
                    cum_sum += float(candle[4])
                    count += 1

                    if count == self.window:
                        break

                ma = cum_sum / min(self.window, count)
                if current_close > ma:
                    self.spot_over_h4.add(exchange)
                logging.warning(f"{exchange}: ma{time_frame}h {ma}, {current_close}")
                logging.warning(f"len: {len(self.spot_over_h4)}")
            except Exception as e:
                continue
        return update_coins_exchanges_txt(self.spot_over_h4, "exchanges", self.alert_type.split("_")[1])


def alert_spot_cross_ma(exclude_coins, exclude_newly_deleted_coins,
                        exclude_newly_added_coin, alert_type="alert_300", tg_mode="CG_SUM"):
    """
    if provided with excluded coins, deleted coins, and added coins,
    the function will not alert those coins
    :param exclude_coins: set of coins to be excluded
    :param exclude_newly_deleted_coins: set of coins to be excluded
    :param exclude_newly_added_coin: set of coins to be excluded
    :param alert_type: alert type
    :param tg_mode: telegram mode
    """
    logging.info(f"{alert_type} start")
    count = alert_type.split("_")[1]
    cg = CrawlExchangeList("CG_SUM_RAW")
    tg_bot = TelegramBot(tg_mode)
    # get coin list
    if alert_type == "alert_100":
        exchanges, coin_ids, coin_symbols = cg.get_top_market_cap_exchanges(num=100)
    elif alert_type == "alert_500":
        exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase(tg_alert=True)
    else:
        exchanges, coin_ids, coin_symbols = cg.get_top_market_cap_exchanges(num=300)

    logging.info("start coingecko alert")
    tg_type = "TEST"
    coingecko_res = CoingeckoAlert4H(coin_ids, coin_symbols, cg.active_exchanges,
                                     tg_type=tg_type, alert_type=count)
    coins, newly_deleted_coins, newly_added_coins = coingecko_res.run()
    logging.info(f"start binance indicator alert")
    logging.info(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
    binance_alert = BinanceIndicatorAlert4H(exchanges, alert_type=alert_type)
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
