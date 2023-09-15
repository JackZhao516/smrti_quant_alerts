import logging
import statistics
import csv
import os
from collections import defaultdict
from multiprocessing.pool import ThreadPool

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.data_type import BinanceExchange
from smrti_quant_alerts.utility import run_task_at_daily_time


class SpotOverMABase(GetExchangeList):
    STABLE_COINS = {"USD", "USDT", "USDC", "USDBC", "DAI", "BUSD",
                    "USDP", "GUSD", "USDC.E", "WSTUSDT", "AXLUSDC",
                    "TUSD", "FRAX", "CUSD", "USDD", "DEI", "USDK",
                    "MIMATIC", "OUSD", "PAX", "FEI", "USTC", "USDN",
                    "TRIBE", "LUSD", "EURS", "VUSDC", "USDX", "SUSD",
                    "VAI", "RSV", "CEUR", "USDS", "CUSDT", "DOLA",
                    "HAY", "MIM", "EDGT", "ALUSD", "WBTCBTC",
                    "BUSDUSDT", "USDCBUSD", "USDCUSDT", "USDPUSDT",
                    "FRXETH", "WBTCETH", "CETH", "CDAI", "CUSDC",
                    "AUSDC", "AETH"}
    if not os.path.exists("run_time_data"):
        os.mkdir("run_time_data")

    def __init__(self, exclude_coins, trading_symbols, time_frame=1,
                 window=200, alert_type="alert_300"):
        super().__init__()
        self._trading_symbols = trading_symbols
        self._symbol_type = ""
        self._exclude_coins = exclude_coins
        self._expand_exclude_coins()

        self.alert_type = alert_type
        self.time_frame = time_frame
        self.window = window
        self._spot_over_ma = {}

    def _expand_exclude_coins(self):
        """
        expand exclude coins to include all quotes for each base
        """
        for coin in self._exclude_coins.copy():
            if isinstance(coin, BinanceExchange):
                for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                    self._exclude_coins.add(BinanceExchange(coin.base_symbol, quote))

    def _coin_spot_over_ma(self, trading_symbol):
        """
        return True if spot price is over ma
        """
        pass

    def _coins_spot_over_ma(self):
        """
        get all spot over ma coins

        """
        pool = ThreadPool(8)
        pool.map(self._coin_spot_over_ma, self._trading_symbols)
        pool.close()

        logging.info(f"spot_over_ma_{self.alert_type}: {self._spot_over_ma}")

    def _compare_last_time(self):
        """
        compare last time _spot_over_ma with current _spot_over_ma
        _spot_over_ma stored with the format of <trading_symbol> <count> in
        <self.alert_type>_<self._symbol_type>.txt

        :return: _spot_over_ma with counts, newly_deleted, newly_added
        """
        newly_deleted = []
        newly_added = []
        if os.path.exists(f"run_time_data/{self.alert_type}_{self._symbol_type}.csv"):
            last_time_spot_over_ma = {}
            with open(f"run_time_data/{self.alert_type}_{self._symbol_type}.csv", "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row:
                        last_time_spot_over_ma[row[0]] = int(row[1])

            newly_deleted = [coin for coin in last_time_spot_over_ma
                             if coin not in self._spot_over_ma and coin not in self._exclude_coins]
            for coin in self._spot_over_ma:
                if coin not in last_time_spot_over_ma and coin not in self._exclude_coins:
                    newly_added.append(coin)
                else:
                    self._spot_over_ma[coin] = last_time_spot_over_ma[coin] + 1

        with open(f"run_time_data/{self.alert_type}_{self._symbol_type}.csv", "w") as f:
            writer = csv.writer(f)
            for key, value in self._spot_over_ma.items():
                writer.writerow([key, value])
        return newly_deleted, newly_added,

    def run(self):
        """
        run the alert

        :return: _spot_over_ma, newly_deleted, newly_added
        """
        self._coins_spot_over_ma()
        newly_deleted, newly_added = self._compare_last_time()
        spot_over_ma = list(sorted(self._spot_over_ma.items(), key=lambda x: (-x[1], x[0])))
        return spot_over_ma, newly_deleted, newly_added


class CoingeckoSpotOverMA(SpotOverMABase):
    def __init__(self, exclude_coins, coingecko_coins, time_frame=1, window=200, alert_type="alert_300"):
        super().__init__(exclude_coins, coingecko_coins, time_frame, window, alert_type)
        self.symbol_type = "CoingeckoCoin"

    def _coin_spot_over_ma(self, coingecko_coin):
        """
        return True if spot price is over ma
        """
        try:
            if coingecko_coin in self.STABLE_COINS or coingecko_coin in self._exclude_coins:
                return False
            days_delta = self.time_frame * self.window // 24 + 1
            current_price = self.get_coin_current_price(coingecko_coin)
            prices = self.get_coin_history_hourly_close_price(coingecko_coin, days_delta)
            prices = prices[:self.time_frame * self.window]
            ma = statistics.mean(prices[::self.time_frame])
            if current_price > ma:
                self._spot_over_ma[coingecko_coin] = 1
                return True
            return False
        except Exception as e:
            return False


class BinanceSpotOverMA(SpotOverMABase):
    def __init__(self, exclude_coins, binance_exchanges, time_frame=1, window=200, alert_type="alert_300"):
        super().__init__(exclude_coins, binance_exchanges, time_frame, window, alert_type)
        self.symbol_type = "BinanceExchange"

    def _coin_spot_over_ma(self, binance_exchange):
        """
        return True if spot price is over ma
        """
        try:
            if binance_exchange in self.STABLE_COINS or binance_exchange in self._exclude_coins:
                return False
            days_delta = self.time_frame * self.window // 24 + 1
            current_price = self.get_exchange_current_price(binance_exchange)
            prices = self.get_exchange_history_hourly_close_price(binance_exchange, days_delta)
            prices = prices[:self.time_frame * self.window]
            ma = statistics.mean(prices[::self.time_frame])
            if current_price > ma:
                self._spot_over_ma[binance_exchange] = 1
                return True
            return False
        except Exception as e:
            return False

    def _coins_spot_over_ma(self):
        """
        get all spot over ma binance exchanges, keep each base with only one quote
        if multiple quotes are available, keep the one in the availability order of
        USDT, BUSD, BTC, ETH
        """
        super()._coins_spot_over_ma()
        bases = defaultdict(set)
        for binance_exchange in self._spot_over_ma.keys():
            base = binance_exchange.base_symbol
            bases[base].add(binance_exchange.quote_symbol)
        self._spot_over_ma = {}
        for base, quotes in bases.items():
            for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                if quote in quotes:
                    self._spot_over_ma[BinanceExchange(base, quote)] = 1
                    break


def alert_spot_cross_ma(time_frame, window, exclude_coins=None, alert_type="alert_300", tg_mode="CG_SUM"):
    """
    if provided with excluded coins, deleted coins, and added coins,
    the function will not alert those coins

    :param time_frame: time frame
    :param window: window
    :param exclude_coins: set of coins to be excluded
    :param alert_type: alert type
    :param tg_mode: telegram mode

    :return: _exclude_coins
    """

    if exclude_coins is None:
        exclude_coins = set()
    logging.info(f"{alert_type} start")
    cg = GetExchangeList("CG_SUM_RAW")
    tg_bot = TelegramBot(tg_mode)

    # get coin list
    if alert_type == "alert_100":
        binance_exchanges, coingecko_coins = cg.get_top_market_cap_exchanges(num=100)
    elif alert_type == "alert_500":
        binance_exchanges, coingecko_coins = cg.get_coins_with_weekly_volume_increase(tg_alert=True)
    elif alert_type == "alert_300":
        binance_exchanges, coingecko_coins = cg.get_top_market_cap_exchanges(num=300)
    else:
        binance_exchanges, coingecko_coins = cg.get_coins_with_24h_volume_larger_than_threshold(threshold=3000000)

    # alert
    coingecko_alert = CoingeckoSpotOverMA(exclude_coins, coingecko_coins, time_frame, window, alert_type)
    coins, newly_deleted_coins, newly_added_coins = coingecko_alert.run()

    binance_alert = BinanceSpotOverMA(exclude_coins, binance_exchanges, time_frame, window, alert_type)
    exchanges, newly_deleted_exchanges, newly_added_exchanges = binance_alert.run()

    coins.extend(exchanges)
    newly_deleted_coins.extend(newly_deleted_exchanges)
    newly_added_coins.extend(newly_added_exchanges)

    # send alert and return
    ma_type = f"H{time_frame} MA{window}"
    if alert_type in ["alert_100", "alert_300", "alert_500"]:
        count = int(alert_type.split("_")[1])
        tg_bot.send_message(f"{alert_type}: market cap top {count}")
        if alert_type == "alert_500":
            tg_bot.send_message("and weekly volume increase >= 30% "
                                "for alt/busd, alt/usdt pairs\n")
        tg_bot.send_message(f"Top {count} coins/coin exchanges spot over {ma_type}:\n{coins}\n\n"
                            f"Top {count} coins/coin exchanges exchanges spot"
                            f" over {ma_type} newly added:\n{newly_added_coins}\n\n"
                            f"Top {count} coins/coin exchanges exchanges spot"
                            f" over {ma_type} newly deleted:\n{newly_deleted_coins}\n")
    else:
        tg_bot.send_message("For coins/exchanges with 24H volume larger than 3000000 USD")
        tg_bot.send_message(f"coins/coin exchanges spot over {ma_type}:\n{coins}\n\n"
                            f"coins/coin exchanges exchanges spot"
                            f" over {ma_type} newly added:\n{newly_added_coins}\n\n"
                            f"coins/coin exchanges exchanges spot"
                            f" over {ma_type} newly deleted:\n{newly_deleted_coins}\n")

    coins = [coin[0] for coin in coins]
    return exclude_coins.union(set(coins + newly_added_coins + newly_deleted_coins))


if __name__ == "__main__":
    alert_type = "meme_alert"
    tg_mode = "TEST"
    kwargs = {"time_frame": 4, "window": 200, "alert_type": alert_type, "tg_mode": tg_mode}
    run_task_at_daily_time(alert_spot_cross_ma, "06:11", kwargs=kwargs, duration=60 * 60 * 24)
