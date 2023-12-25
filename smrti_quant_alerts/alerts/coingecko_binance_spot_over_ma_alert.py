import logging
import statistics
import csv
import os
import uuid
from collections import defaultdict
from time import sleep, time
from multiprocessing.pool import ThreadPool

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.utility import run_task_at_daily_time
from smrti_quant_alerts.data_type import CoingeckoCoin, BinanceExchange, TradingSymbol
from smrti_quant_alerts.db.utility import get_last_count, write_last_counts, \
    remove_older_count, init_database_runtime, update_last_counts, close_database


class SpotOverMABase(GetExchangeList):
    if not os.path.exists("run_time_data"):
        os.mkdir("run_time_data")

    def __init__(self, exclude_coins, trading_symbols, time_frame=1,
                 window=200, alert_type="alert_300"):
        super().__init__()
        self._trading_symbols = trading_symbols
        self._symbol_type = TradingSymbol
        self._get_exclude_coins(exclude_coins)

        self.alert_type = alert_type
        self.time_frame = time_frame
        self.window = window
        self._spot_over_ma = {}

    def _coin_spot_over_ma(self, trading_symbol):
        """
        return True if spot price is over ma
        """
        pass

    def _coins_spot_over_ma(self, threads=4):
        """
        get all spot over ma coins

        :param threads: number of threads to fill _spot_over_ma

        """
        pool = ThreadPool(threads)
        pool.map(self._coin_spot_over_ma, self._trading_symbols)
        pool.close()

        logging.info(f"spot_over_ma_{self.alert_type}: {self._spot_over_ma}")

    def _compare_last_time(self):
        """
        compare last time _spot_over_ma with current _spot_over_ma
        read/write to the database

        :return: newly_deleted, newly_added
        """
        last_time_spot_over_ma = get_last_count(self._symbol_type)
        last_time_spot_over_ma_alert_type = get_last_count(self._symbol_type, self.alert_type)

        newly_deleted = [coin for coin in last_time_spot_over_ma_alert_type
                         if coin not in self._spot_over_ma and coin not in self._exclude_coins]
        newly_added = []
        for coin in self._spot_over_ma:
            if coin not in last_time_spot_over_ma and coin not in self._exclude_coins:
                newly_added.append(coin)
            else:
                self._spot_over_ma[coin] = last_time_spot_over_ma[coin] + 1
        update_last_counts(self._spot_over_ma)
        write_last_counts(self._spot_over_ma, self.alert_type)
        return newly_deleted, newly_added

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
    def __init__(self, exclude_coins, coingecko_coins, time_frame=1,
                 window=200, alert_type="alert_300"):
        super().__init__(exclude_coins, coingecko_coins, time_frame, window, alert_type)
        self._symbol_type = CoingeckoCoin

    def _coin_spot_over_ma(self, coingecko_coin):
        """
        return True if spot price is over ma
        """
        try:
            if coingecko_coin in self._exclude_coins:
                return False
            sleep(2)
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
    def __init__(self, exclude_coins, binance_exchanges, time_frame=1,
                 window=200, alert_type="alert_300"):
        super().__init__(exclude_coins, binance_exchanges, time_frame, window, alert_type)
        self._symbol_type = BinanceExchange

    def _coin_spot_over_ma(self, binance_exchange):
        """
        return True if spot price is over ma
        """
        try:
            if binance_exchange in self._exclude_coins:
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

    def _coins_spot_over_ma(self, threads=6):
        """
        get all spot over ma binance exchanges, keep each base with only one quote
        plus the ETH quote if available. if multiple quotes are available,
        keep the one in the availability order of USDT, BUSD, BTC.
        Keep ETH quote even if other quotes are available
        """
        super()._coins_spot_over_ma(threads=threads)
        bases = defaultdict(set)
        for binance_exchange in self._spot_over_ma.keys():
            base = binance_exchange.base_symbol
            bases[base].add(binance_exchange.quote_symbol)
        self._spot_over_ma = {}
        for base, quotes in bases.items():
            for quote in ["USDT", "BUSD", "BTC"]:
                if quote in quotes:
                    self._spot_over_ma[BinanceExchange(base, quote)] = 1
                    break
            if "ETH" in quotes and base != "ETH":
                self._spot_over_ma[BinanceExchange(base, "ETH")] = 1


class SpotOverMAAlert(GetExchangeList):
    def __init__(self, time_frame, window, tg_mode="CG_SUM"):
        super().__init__(tg_mode)
        self._time_frame = time_frame
        self._window = window
        self._tg_mode = tg_mode
        self._coingecko_coins = []
        self._binance_exchanges = []

    def _get_coins_info_to_csv(self, coins, file_name):
        """
        get coins info to csv file

        :param coins: coins
        :param file_name: file name
        :return: file path
        """
        with open(f"run_time_data/{file_name}", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["symbol", "name", "website", "description"])
            for coin in coins:
                if isinstance(coin, BinanceExchange):
                    coin = CoingeckoCoin.get_symbol_object(coin.base_symbol)
                info = self.get_coin_info(coin)
                writer.writerow([info["symbol"], info["name"],
                                 info["website"], info["description"]])

        return f"run_time_data/{file_name}"

    def _alert_coins_info_to_telegram(self, coins):
        """
        alert coins info

        :param coins: coins
        """
        if coins:
            coins = sorted(coins)
            file_name = f"{uuid.uuid4()}_coins_info.csv"
            file_path = self._get_coins_info_to_csv(coins, file_name)
            self._tg_bot = TelegramBot(self._tg_mode)
            self._tg_bot.send_file(file_path, "coins info")
            if os.path.exists(file_path):
                os.remove(file_path)

    def _get_target_coins_by_alert_type(self, alert_type="alert_300"):
        """
        get target coins by alert type

        :param alert_type: alert type [alert_100, alert_300, alert_500, meme_alert]
        """
        # get coin list
        if alert_type == "alert_100":
            self._binance_exchanges, self._coingecko_coins = \
                self.get_top_market_cap_coins_with_volume_threshold(num=100)
        elif alert_type == "alert_500":
            self._binance_exchanges, self._coingecko_coins = \
                self.get_top_market_cap_coins_with_volume_threshold(
                    num=500, daily_volume_threshold=1000000, weekly_volume_threshold=7000000)
        elif alert_type == "alert_300":
            self._binance_exchanges, self._coingecko_coins = \
                self.get_top_market_cap_coins_with_volume_threshold(
                    num=300, daily_volume_threshold=1000000, weekly_volume_threshold=7000000)
        else:
            self._binance_exchanges, self._coingecko_coins = \
                self.get_2023_coins_with_daily_volume_threshold(threshold=3000000)

    def _alert_spot_cross_ma_by_alert_type(self, exclude_coins=None, alert_type="alert_300"):
        """
        if provided with excluded coins, deleted coins, and added coins,
        the function will not alert those coins

        :param exclude_coins: set of coins to be excluded
        :param alert_type: alert type [alert_100, alert_300, alert_500, meme_alert]

        :return: exclude_coins, coins
        """
        if exclude_coins is None:
            exclude_coins = set()
        logging.info(f"{alert_type} start")
        self._get_target_coins_by_alert_type(alert_type)

        # alert
        coingecko_alert = \
            CoingeckoSpotOverMA(exclude_coins, self._coingecko_coins, self._time_frame, self._window, alert_type)
        coins_count, newly_deleted_coins, newly_added_coins = coingecko_alert.run()

        binance_alert = \
            BinanceSpotOverMA(exclude_coins, self._binance_exchanges, self._time_frame, self._window, alert_type)
        exchanges, newly_deleted_exchanges, newly_added_exchanges = binance_alert.run()

        coins_count.extend(exchanges)
        newly_deleted_coins.extend(newly_deleted_exchanges)
        newly_added_coins.extend(newly_added_exchanges)

        # send alert and return
        ma_type = f"H{self._time_frame} MA{self._window}"
        if alert_type in ["alert_100", "alert_300", "alert_500"]:
            count = int(alert_type.split("_")[1])
            self._tg_bot.send_message(f"{alert_type}: market cap top {count}")
            if alert_type in ("alert_500", "alert_300"):
                self._tg_bot.send_message("and daily volume >= 1M USDT "
                                          "for alt/busd, alt/usdt pairs\n"
                                          "and weekly volume >= 7M USDT  "
                                          "for alt/busd, alt/usdt pairs\n")
            self._tg_bot.send_message(f"Top {count} coins/coin exchanges spot over {ma_type}:\n{coins_count}\n\n"
                                      f"Top {count} coins/coin exchanges exchanges spot"
                                      f" over {ma_type} newly added:\n{newly_added_coins}\n\n"
                                      f"Top {count} coins/coin exchanges exchanges spot"
                                      f" over {ma_type} newly deleted:\n{newly_deleted_coins}\n")
        else:
            self._tg_bot.send_message("For 2023 listed coins/exchanges with 24H volume larger than 3000000 USD")
            self._tg_bot.send_message(f"coins/coin exchanges spot over {ma_type}:\n{coins_count}\n\n"
                                      f"coins/coin exchanges exchanges spot"
                                      f" over {ma_type} newly added:\n{newly_added_coins}\n\n"
                                      f"coins/coin exchanges exchanges spot"
                                      f" over {ma_type} newly deleted:\n{newly_deleted_coins}\n")

        coins = [coin for coin, count in coins_count]

        return exclude_coins.union(set(coins + newly_added_coins)), coins

    def _sequential_alert(self):
        """
        sequentially alert 100, 300, 500 coins
        """
        exclude_coins, alert_coins = set(), set()
        for alert_type in ["alert_100", "alert_300", "alert_500"]:
            exclude_coin, coins = self._alert_spot_cross_ma_by_alert_type(
                exclude_coins, alert_type=alert_type)
            alert_coins.update(coins)
            exclude_coins.update(exclude_coin)

        return exclude_coins, alert_coins

    def run(self, alert_type: str, alert_coins_info: bool = True):
        """
        run the alert

        :param alert_type: alert type:
                            [alert_100, alert_300, alert_500, meme_alert, sequential]
        :param alert_coins_info: whether to alert coins info

        """
        self.get_all_coingecko_coins()
        self.get_all_binance_exchanges()

        database_name = f"{self.ALERT_SETTINGS[alert_type]['database_name']}.db"
        init_database_runtime(database_name)
        start_timestamp = time()

        if alert_type == "sequential":
            _, alert_coins = self._sequential_alert()
        else:
            _, alert_coins = self._alert_spot_cross_ma_by_alert_type(alert_type=alert_type)

        remove_older_count(start_timestamp)
        close_database()

        if alert_coins_info:
            self._alert_coins_info_to_telegram(alert_coins)


if __name__ == "__main__":
    start_time = time()
    alert_type = "meme_alert"

    kwargs = {"time_frame": 4, "window": 200, "tg_mode": "TEST"}
    spot_over_ma_alert = SpotOverMAAlert(**kwargs)

    kwargs = {"alert_type": alert_type, "alert_coins_info": False}
    spot_over_ma_alert.run(**kwargs)

    # run_task_at_daily_time(spot_over_ma_alert.run, "06:11", kwargs=kwargs)
    print(f"Time used: {time() - start_time} seconds")
