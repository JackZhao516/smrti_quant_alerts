import time
import math
import logging
import threading
from collections import defaultdict
from datetime import datetime

import pytz
from binance.lib.utils import config_logging
from binance.websocket.spot.websocket_client import SpotWebsocketClient as Client

from crawl_coingecko import CoinGecKo
from telegram_api import TelegramBot


class BinancePriceVolumeAlert:
    MAX_ERROR = 20
    config_logging(logging, logging.INFO)

    def __init__(self):
        self.running = True
        self.cg = CoinGecKo("TEST")
        self.tg_bot_volume = TelegramBot("VOLUME", daemon=True)
        self.tg_bot_price = {
            "15m": TelegramBot("PRICE_15M", daemon=False),
            "1h": TelegramBot("PRICE_1H", daemon=False)
        }

        # symbol->[timestamp, close1, close2]
        # symbol->[timestamp, close]
        # symbol->[close, close1]
        self.exchange_bar_dict = defaultdict(list)
        self.exchange_bar_dict_0 = defaultdict(list)
        self.exchange_bar_dict_1 = defaultdict(list)
        self.lock_15m = threading.Lock()

        # volume alert monthly count
        self.exchange_volume_alert_monthly_count = defaultdict(lambda: 0)

        # volume alert daily ticker count
        self.exchange_volume_alert_daily_count = set()

        # monitored exchanges
        self.exchanges = self.cg.get_500_usdt_exchanges(market_cap=False)
        self.exchanges = [e.lower() for e in self.exchanges]
        self.exchanges.sort()

        # exchange count
        self.exchange_count = {
            "15m": 0,
            "1h": 0,
        }
        self.max_exchange_count = {
            "15m": 355,
            "1h": 350,
        }

        # dict for 15min/1h price alert: symbol->[price_change_rate, last_price]
        self.price_dict = {
            "15m": defaultdict(list),
            "1h": defaultdict(list),
        }
        self.lock_1h = threading.Lock()

        # BTC_price
        self.BTC_price = 23000

        # for testing only
        self.tg_bot_test = TelegramBot("TEST")

    def daily_reset_and_alert_volume_alert_count(self):
        """
        Reset and alert volume alert count daily
        """
        logging.info(f"daily reset and alert volume start")
        while self.running:
            tz = pytz.timezone('Asia/Shanghai')
            shanghai_now = datetime.now(tz).strftime('%H:%M')
            if shanghai_now == "11:59":
                self.lock_15m.acquire()
                message_string = ""
                message_list = []
                for i in self.exchange_volume_alert_daily_count:
                    message_list.append([i, self.exchange_volume_alert_monthly_count[i]])
                message_list.sort(key=lambda x: x[1], reverse=True)
                for exchange, count in message_list:
                    message_string += f"{exchange} monthly count: {count}\n"
                self.tg_bot_volume.send_message(
                    f"Daily volume alert ticker count:\n"
                    f"{message_string}"
                )
                self.exchange_volume_alert_daily_count = set()
                self.lock_15m.release()
                time.sleep(86000)

    def monthly_reset_volume_alert_count(self):
        """
        Reset volume alert count monthly
        """
        logging.info("monthly reset volume count start")
        while self.running:
            time.sleep(86400 * 30)
            self.lock_15m.acquire()
            self.exchange_volume_alert_monthly_count = defaultdict(lambda: 0)
            self.lock_15m.release()

    def monitor_price_change(self, timeframe="15m"):
        """
        For price change alert

        :param timeframe: 15m or 1h
        """
        logging.info(f"monitor price change for {timeframe} start")
        rate_threshold = 10.0 if timeframe == "1h" else 5.0
        exchange_number = 350
        while self.running:
            if self.exchange_count[timeframe] == exchange_number:
                if timeframe == "15m":
                    self.lock_15m.acquire()
                elif timeframe == "1h":
                    self.lock_1h.acquire()
                self.exchange_count[timeframe] = 0
                price_lists = [[k, v[0]] for k, v in self.price_dict[timeframe].items()]
                largest, smallest = [], []

                # get the largest five
                price_lists.sort(key=lambda x: x[1], reverse=True)
                logging.info(f"price_lists: {price_lists}")
                for k, v in price_lists:
                    if v >= rate_threshold and len(largest) < 5:
                        v = round(v, 2)
                        largest.append([k, v])
                    if len(largest) == 5:
                        break

                # get the smallest five
                price_lists.sort(key=lambda x: x[1], reverse=False)
                # logging.info(f"price_lists: {price_lists}")
                for k, v in price_lists:
                    if v <= -1 * rate_threshold and len(smallest) < 5:
                        v = round(v, 2)
                        smallest.append([k, v])
                    if len(smallest) == 5:
                        break

                # logging.info(f"largest price change: {largest}")
                # logging.info(f"smallest price change: {smallest}")
                # logging.info(f"exchange bar dict 1: {self.exchange_bar_dict_1}")
                # logging.info(f"exchange bar dict: {self.exchange_bar_dict}")
                # logging.info(f"exchange bar dict 0: {self.exchange_bar_dict_0}")
                if len(largest) > 0:
                    self.tg_bot_price[timeframe].safe_send_message(
                        f"{timeframe} top {len(largest)} "
                        f"positive price change in % over {rate_threshold}%: {largest}")
                if len(smallest) > 0:
                    self.tg_bot_price[timeframe].safe_send_message(
                        f"{timeframe} top {len(smallest)} "
                        f"negative price change in % over {rate_threshold}%: {smallest}")
                # logging.info(f"exchange_count: {self.exchange_count}")
                time.sleep(1)
                if timeframe == "15m":
                    self.lock_15m.release()
                elif timeframe == "1h":
                    self.lock_1h.release()
                time.sleep(800 if timeframe == "15m" else 3400)

    def klines_alert(self):
        """
        For price/volume alert
        main function

        alert if second and third bar are both ten times larger than first bar
        for top 500 market cap USDT exchanges on binance
        """
        id_count = 1
        error_count = 0
        logging.info("start price_volume_alert")

        try:
            # setting up the tg volume alert thread
            monitor_threads = []
            monitor_threads.append(threading.Thread(target=self.monthly_reset_volume_alert_count))
            monitor_threads.append(threading.Thread(target=self.daily_reset_and_alert_volume_alert_count))
            monitor_threads.append(threading.Thread(target=self.monitor_price_change,
                                   args=("15m",)))
            monitor_threads.append(threading.Thread(target=self.monitor_price_change,
                                   args=("1h",)))

            for t in monitor_threads:
                t.start()
            logging.info(f"exchanges: {len(self.exchanges)}")

            klines_client = Client()
            klines_client.start()
            klines_client.kline(
                symbol=self.exchanges, id=id_count, interval="15m", callback=self.alert_15m
            )
            id_count += 1

            time.sleep(5)
            klines_client.kline(
                symbol=self.exchanges, id=id_count, interval="1h", callback=self.alert_1h
            )

            # time.sleep(88200.0 - ((time.time() - start_time) % 86400.0))
            time.sleep(86400.0 * 365)
            logging.info("closing ws connection")
            klines_client.stop()
            self.running = False
            self.tg_bot_volume.stop()
            for t in monitor_threads:
                t.join()

        except Exception as e:
            error_count += 1
            if error_count > self.MAX_ERROR:
                raise e
            time.sleep(1)

    def alert_15m(self, msg):
        """
        volume/price alert callback function for 15min klines

        alert if second bar is 10X first bar and third bar is 10X first bar
        alert if second bar is 50X first bar
        alert if third bar is 50X first bar

        """
        # logging.info(f"msg: {msg}")
        alert_threshold = 500000.0
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"] or \
                msg["data"]["k"]["x"] is False or msg["data"]["k"]["i"] != "15m":
            return

        if msg["data"]["k"]["s"].lower() not in self.exchanges:
            return

        kline = msg["data"]["k"]
        symbol = kline["s"]
        current_time = int(kline["t"])
        vol = float(kline["v"])
        # logging.info(f"symbol: {symbol}")
        close = float(kline["c"])
        amount = vol * close if symbol[-3:] != "BTC" else vol * close * self.BTC_price

        self.lock_15m.acquire()
        # update BTC_price
        if symbol == "BTCUSDT":
            self.BTC_price = close
            logging.info(f"BTC_price: {self.BTC_price}")

        # two bars alert
        if len(self.exchange_bar_dict_0[symbol]) == 2 and \
                vol >= 50 * self.exchange_bar_dict_0[symbol][1] and amount >= alert_threshold:
            self.exchange_volume_alert_monthly_count[symbol] += 1
            self.exchange_volume_alert_daily_count.add(symbol)
            self.tg_bot_volume.add_msg_to_queue(
                f"{symbol} 15 min volume alert 2nd bar 50X: volume "
                f"[{self.exchange_bar_dict_0[symbol][1]} "
                f"-> {vol}]\namount: ${math.ceil(amount)}"
                f"\nticker volume alert monthly count:"
                f" {self.exchange_volume_alert_monthly_count[symbol]}")
        self.exchange_bar_dict_0[symbol] = [current_time, vol]
        # logging.info(f"exchange_bar_dict_0: {exchange_bar_dict_0}")

        # third bar alert
        if len(self.exchange_bar_dict_1[symbol]) != 2:
            self.exchange_bar_dict_1[symbol].append(vol)
        elif len(self.exchange_bar_dict_1[symbol]) == 2 and \
                vol >= 50 * self.exchange_bar_dict_1[symbol][0] \
                and amount >= alert_threshold:
            self.exchange_volume_alert_monthly_count[symbol] += 1
            self.exchange_volume_alert_daily_count.add(symbol)
            self.tg_bot_volume.add_msg_to_queue(
                f"{symbol} 15 min volume alert 3rd bar 50X: volume "
                f"[{self.exchange_bar_dict_1[symbol][0]} "
                f"-> {self.exchange_bar_dict[symbol][1]} "
                f"-> {vol}]\namount: ${math.ceil(amount)}"
                f"\nticker volume alert monthly count:"
                f" {self.exchange_volume_alert_monthly_count[symbol]}")
            self.exchange_bar_dict_1[symbol].append(vol)
            self.exchange_bar_dict_1[symbol].pop(0)
        elif len(self.exchange_bar_dict_1[symbol]) == 2:
            self.exchange_bar_dict_1[symbol].append(vol)
            self.exchange_bar_dict_1[symbol].pop(0)

        # three bars alert
        if len(self.exchange_bar_dict[symbol]) == 2:
            if vol != 0.0 and vol >= 10 * self.exchange_bar_dict[symbol][1]:
                self.exchange_bar_dict[symbol].append(vol)
                self.exchange_bar_dict[symbol][0] = current_time
            else:
                self.exchange_bar_dict[symbol] = [current_time, vol]
        elif len(self.exchange_bar_dict[symbol]) == 3:
            if vol != 0.0 and vol >= 10 * self.exchange_bar_dict[symbol][1] \
                    and amount >= alert_threshold:
                self.exchange_volume_alert_monthly_count[symbol] += 1
                self.exchange_volume_alert_daily_count.add(symbol)
                self.tg_bot_volume.add_msg_to_queue(
                    f"{symbol} 15 min volume alert 2nd, 3rd bar 10X: volume "
                    f"[{self.exchange_bar_dict[symbol][1]} "
                    f"-> {self.exchange_bar_dict[symbol][2]} -> {vol}]"
                    f"\namount: ${math.ceil(amount)}"
                    f"\nticker volume alert monthly count:"
                    f" {self.exchange_volume_alert_monthly_count[symbol]}")
            self.exchange_bar_dict[symbol] = [current_time, vol]
        else:
            self.exchange_bar_dict[symbol] = [current_time, vol]
        # logging.info(exchange_bar_dict)

        # price alert
        self._price_alert_helper(symbol, close, "15m")
        self.lock_15m.release()

    def alert_1h(self, msg):
        """
        For price alerts 1h klines
        """
        # logging.info(f"msg: {msg}")
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"] or \
                msg["data"]["k"]["x"] is False or msg["data"]["k"]["i"] != "1h":
            return

        if msg["data"]["k"]["s"].lower() not in self.exchanges:
            return

        kline = msg["data"]["k"]
        symbol = kline["s"]
        close = float(kline["c"])

        self.lock_1h.acquire()
        # price alert
        self._price_alert_helper(symbol, close, "1h")
        self.lock_1h.release()

    def _price_alert_helper(self, symbol, close, timeframe="15m"):
        """
        Helper function for price alerts

        :param symbol: symbol of the price alert
        :param close: close price of the price alert
        :param timeframe: timeframe of the price alert
                            "15m" for 15 min, "1h" for 1 hour
        """
        self.exchange_count[timeframe] += 1
        # if timeframe == "15m":
            # logging.info(f"exchange_count: {self.exchange_count[timeframe]}")
        # self.max_exchange_count[timeframe] = \
            # max(self.exchange_count[timeframe], self.max_exchange_count[timeframe])
        # logging.info(f"exchange_count: {self.exchange_count}")

        if symbol not in self.price_dict[timeframe]:
            self.price_dict[timeframe][symbol] = [0.0, close]
        else:
            self.price_dict[timeframe][symbol][0] = \
                (close / self.price_dict[timeframe][symbol][1] - 1) * 100
            self.price_dict[timeframe][symbol][1] = close


if __name__ == "__main__":
    BinancePriceVolumeAlert().klines_alert()
