import os
import time
import math
import json
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
    config_logging(logging, logging.WARNING)

    def __init__(self):
        self.running = True
        self.cg = CoinGecKo("TEST")
        self.tg_bot = {
            "15m_price": TelegramBot("PRICE_15M", daemon=False),
            "1h_price": TelegramBot("PRICE_1H", daemon=False),
            "15m_volume": TelegramBot("VOLUME_15M", daemon=True),
            "1h_volume": TelegramBot("VOLUME_1H", daemon=True),
        }

        # symbol->[timestamp, close1, close2]
        # symbol->[timestamp, close]
        # symbol->[close, close1]
        # symbol->[close, close1]
        self.exchange_bar_dict = defaultdict(list)
        self.exchange_bar_dict_0 = defaultdict(list)
        self.exchange_bar_dict_1 = defaultdict(list)
        self.lock_15m = threading.Lock()
        self.exchange_bar_dict_1h = defaultdict(list)

        # alert monthly count
        self.exchange_alert_monthly_count = {
            "15m_price": defaultdict(list),
            "1h_price": defaultdict(list),
            "15m_volume": defaultdict(list),
            "1h_volume": defaultdict(list),
        }
        if os.path.isfile("monthly_count.json"):
            f = open("monthly_count.json", "r")
            ans = json.load(f)
            for k, v in ans.items():
                for k1, v1 in v.items():
                    self.exchange_alert_monthly_count[k][k1] = v1
            f.close()

        self.exchange_daily_new_alert = {
            "15m_price": defaultdict(lambda: 0), "1h_price": defaultdict(lambda: 0),
            "15m_volume": defaultdict(lambda: 0), "1h_volume": defaultdict(lambda: 0)
        }

        # monitored exchanges
        self.exchanges = self.cg.get_all_exchanges_in_usdt_busd_btc()
        self.exchanges = [e.lower() for e in self.exchanges]
        self.exchanges.sort()

        # all exchanges on binance
        self.all_exchanges = set(self.cg.get_all_binance_exchanges())

        # dict for 15min/1h price alert: symbol->price_change_rate
        self.price_dict = {
            "15m": {},
            "1h": {},
        }
        self.lock_1h = threading.Lock()

        # BTC_price
        self.BTC_price = 29000

        # binance websocket client
        self.klines_client = Client()
        self.id_count = 1

        # threshold for price/volume alert
        self.settings = json.load(open("settings.json"))

        # # for testing only
        # self.tg_bot_test = TelegramBot("TEST")

    def klines_alert(self):
        """
        For price/volume alert
        main function

        alert if second and third bar are both ten times larger than first bar
        for top 500 market cap USDT exchanges on binance
        """

        error_count = 0
        logging.info("start price_volume_alert")

        try:
            # setting up the tg volume alert thread
            monitor_threads = [
                threading.Thread(target=self._monthly_reset_volume_alert_count),
                threading.Thread(target=self._daily_reset_and_alert_volume_alert_count),
                threading.Thread(target=self._monitor_price_change,
                                 args=("15m",)),
                threading.Thread(target=self._monitor_price_change,
                                 args=("1h",))]

            for t in monitor_threads:
                t.start()
            logging.info(f"exchanges: {len(self.exchanges)}")

            self.klines_client.start()
            self.klines_client.kline(
                symbol=self.exchanges, id=self.id_count, interval="15m", callback=self._alert_15m
            )
            self.id_count += 1

            time.sleep(5)
            self.klines_client.kline(
                symbol=self.exchanges, id=self.id_count, interval="1h", callback=self._alert_1h
            )
            self.id_count += 1

            time.sleep(5)
            auto_subscribe = threading.Thread(target=self._ten_min_subscribe_new_exchange)
            auto_subscribe.start()
            monitor_threads.append(auto_subscribe)

            time.sleep(86400.0 * 365)
            logging.info("closing ws connection")
            self.klines_client.stop()
            self.running = False
            self.tg_bot["15m_volume"].stop()
            self.tg_bot["1h_volume"].stop()
            for t in monitor_threads:
                t.join()

        except Exception as e:
            error_count += 1
            if error_count > self.MAX_ERROR:
                raise e
            time.sleep(1)

    def _ten_min_subscribe_new_exchange(self):
        """
        Subscribe new exchange every ten minutes
        """
        logging.info("hourly subscribe new exchange start")
        while self.running:
            time_now = datetime.now().strftime('%M')
            if time_now[1] == "2":
                self.settings = json.load(open("settings.json"))
                logging.info("hourly subscribe new exchange start checking")
                all_exchanges = set(self.cg.get_all_binance_exchanges())
                if self.all_exchanges != all_exchanges:
                    exchange_diff = all_exchanges - self.all_exchanges
                    new_exchanges = []
                    for exchange in exchange_diff:
                        if exchange[-4:] == ("USDT" or "BUSD") or \
                                exchange[-3:] == "BTC":
                            new_exchanges.append(exchange.lower())
                    self.klines_client.kline(
                        symbol=new_exchanges, id=self.id_count, interval="15m", callback=self._alert_15m
                    )
                    self.id_count += 1
                    self.klines_client.kline(
                        symbol=new_exchanges, id=self.id_count, interval="1h", callback=self._alert_1h
                    )
                    self.id_count += 1

                    self.exchanges += new_exchanges
                    self.exchanges.sort()
                    self.all_exchanges = all_exchanges
                    logging.info(f"adding new exchanges: {new_exchanges}")
                time.sleep(550)

    def _daily_reset_and_alert_volume_alert_count(self):
        """
        Reset and alert volume alert monthly count daily, top 30
        Reset and alert new exchanges alert daily
        """
        logging.info(f"daily reset and alert volume start")
        while self.running:
            tz = pytz.timezone('Asia/Shanghai')
            shanghai_now = datetime.now(tz).strftime('%H:%M')
            if shanghai_now == "11:59":
                # store the monthly count
                f = open("monthly_count.json", "w")
                json.dump(self.exchange_alert_monthly_count, f)
                f.close()

                # alert the monthly count and daily new exchanges
                alerts = ["15m_price", "15m_volume", "1h_price", "1h_volume"]
                for alert_type in alerts:
                    if alert_type == "15m_price" or "15m_volume":
                        self.lock_15m.acquire()
                    else:
                        self.lock_1h.acquire()

                    message_string = ""
                    message_list = list(self.exchange_alert_monthly_count[alert_type].items())
                    message_list.sort(key=lambda x: x[1][0], reverse=True)
                    message_list = message_list[:30]
                    for exchange, count in message_list:
                        message_string += f"{exchange} monthly count: {count[0]}\n"
                        
                    self.tg_bot[alert_type].send_message(
                        f"Daily {alert_type} alert ticker count:\n"
                        f"{message_string}", blue_text=True
                    )
                    tmp = [[k, v] for k, v in self.exchange_daily_new_alert[alert_type].items() if v != 0]
                    tmp.sort(key=lambda x: x[1], reverse=True)
                    self.tg_bot[alert_type].send_message(
                        f"Daily {alert_type} new alerts:\n"
                        f"{tmp}",
                        blue_text=True
                    )
                    self.exchange_daily_new_alert[alert_type] = defaultdict(lambda: 0)

                    if alert_type == "15m_price" or "15m_volume":
                        self.lock_15m.release()
                    else:
                        self.lock_1h.release()
                time.sleep(86000)

    def _monthly_reset_volume_alert_count(self):
        """
        Reset volume alert count monthly
        """
        logging.info("monthly reset volume count start")
        while self.running:
            time.sleep(86400 * 30)
            self.lock_15m.acquire()
            self.lock_1h.acquire()
            self.exchange_alert_monthly_count = {
                "15m_price": defaultdict(list),
                "1h_price": defaultdict(list),
                "15m_volume": defaultdict(list),
                "1h_volume": defaultdict(list),
            }
            self.lock_1h.release()
            self.lock_15m.release()

    def _monitor_price_change(self, timeframe="15m"):
        """
        For price change alert

        :param timeframe: 15m or 1h
        """
        logging.info(f"monitor price change for {timeframe} start")
        rate_threshold = self.settings["1h_price_change_percentage"] \
            if timeframe == "1h" else self.settings["15m_price_change_percentage"]

        while self.running:
            time_now = datetime.now().strftime('%M:%S')
            time_set = {"00:58", "15:58", "30:58", "45:58"} if timeframe == "15m" \
                else {"01:00"}
            if time_now in time_set:
                if timeframe == "15m":
                    self.lock_15m.acquire()
                elif timeframe == "1h":
                    self.lock_1h.acquire()
                
                price_lists = [[k, v] for k, v in self.price_dict[timeframe].items()]
                largest, smallest = [], []
                self.price_dict[timeframe] = {}

                # get the largest five
                price_lists.sort(key=lambda x: x[1], reverse=True)
                # logging.warning(f"{timeframe}: {price_lists}")
                for k, v in price_lists:
                    if v >= rate_threshold and len(largest) < 5:
                        v = round(v, 2)
                        largest.append([k, v])
                    if len(largest) == 5:
                        break

                # get the smallest five
                price_lists.sort(key=lambda x: x[1], reverse=False)
                for k, v in price_lists:
                    if v <= -1 * rate_threshold and len(smallest) < 5:
                        v = round(v, 2)
                        smallest.append([k, v])
                    if len(smallest) == 5:
                        break

                alert_type = timeframe + "_price"
                for i, l in enumerate(largest):
                    self._update_monthly_count(l[0], alert_type)
                    largest[i].append(self.exchange_alert_monthly_count[alert_type][l[0]][0])

                for i, s in enumerate(smallest):
                    self._update_monthly_count(s[0], alert_type)
                    smallest[i].append(self.exchange_alert_monthly_count[alert_type][s[0]][0])

                price_type = "close" if timeframe == "15m" else "high/low"

                if len(largest) > 0:
                    self.tg_bot[alert_type].safe_send_message(
                        f"{timeframe} top {len(largest)} "
                        f"positive price({price_type}) change in % over {rate_threshold}%: {largest}")
                if len(smallest) > 0:
                    self.tg_bot[alert_type].safe_send_message(
                        f"{timeframe} top {len(smallest)} "
                        f"negative price({price_type}) change in % over {rate_threshold}%: {smallest}")

                time.sleep(1)
                if timeframe == "15m":
                    self.lock_15m.release()
                elif timeframe == "1h":
                    self.lock_1h.release()
                time.sleep(850 if timeframe == "15m" else 3550)

    def _update_monthly_count(self, exchange, alert_type="15m_volume"):
        """
        Update monthly count and daily new exchanges for alerts

        :param exchange: exchange name
        :param alert_type: 15m_volume or 1h_volume or 15m_price or 1h_price

        """
        self.exchange_daily_new_alert[alert_type][exchange] += 1
        # logging.warning(f"{self.exchange_daily_new_alert[alert_type]}")
        if exchange not in self.exchange_alert_monthly_count[alert_type]:
            self.exchange_alert_monthly_count[alert_type][exchange] = [1, int(time.time())]
        else:
            if int(time.time()) - self.exchange_alert_monthly_count[alert_type][exchange][1] > 1850:
                self.exchange_alert_monthly_count[alert_type][exchange][0] += 1
            self.exchange_alert_monthly_count[alert_type][exchange][1] = int(time.time())

    def _alert_15m(self, msg):
        """
        volume/price alert callback function for 15min klines

        Volume:
            alert if second bar is 10X first bar and third bar is 10X first bar
                , and volume over threshold
            alert if second bar is 50X first bar, and volume over threshold
            alert if third bar is 50X first bar, and volume over threshold
        Price:
            record the price change in % for close and open price

        """
        # logging.info(f"msg: {msg}")
        alert_threshold = self.settings["15m_volume_usd"]
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"] or \
                msg["data"]["k"]["x"] is False or msg["data"]["k"]["i"] != "15m":
            return

        if msg["data"]["k"]["s"].lower() not in self.exchanges:
            return

        kline = msg["data"]["k"]
        symbol = kline["s"]
        current_time = int(kline["t"])
        vol = float(kline["v"])
        close = float(kline["c"])
        open_p = float(kline["o"])
        amount = vol * close if symbol[-3:] != "BTC" else vol * close * self.BTC_price

        self.lock_15m.acquire()
        # update BTC_price
        if symbol == "BTCUSDT":
            self.BTC_price = close
            logging.info(f"BTC_price: {self.BTC_price}")

        # two bars alert
        if len(self.exchange_bar_dict_0[symbol]) == 2 and \
                vol >= 50 * self.exchange_bar_dict_0[symbol][1] and amount >= alert_threshold:
            self._update_monthly_count(symbol)
            self.tg_bot["15m_volume"].add_msg_to_queue(
                f"{symbol} 15 min volume alert 2nd bar 50X: volume "
                f"[{self.exchange_bar_dict_0[symbol][1]} "
                f"-> {vol}]\namount: ${math.ceil(amount)}"
                f"\nticker volume alert monthly count:"
                f" {self.exchange_alert_monthly_count['15m_volume'][symbol][0]}")
        self.exchange_bar_dict_0[symbol] = [current_time, vol]
        # logging.info(f"exchange_bar_dict_0: {exchange_bar_dict_0}")

        # third bar alert
        if len(self.exchange_bar_dict_1[symbol]) != 2:
            self.exchange_bar_dict_1[symbol].append(vol)
        elif len(self.exchange_bar_dict_1[symbol]) == 2 and \
                vol >= 50 * self.exchange_bar_dict_1[symbol][0] \
                and amount >= alert_threshold:
            self._update_monthly_count(symbol)
            self.tg_bot["15m_volume"].add_msg_to_queue(
                f"{symbol} 15 min volume alert 3rd bar 50X: volume "
                f"[{self.exchange_bar_dict_1[symbol][0]} "
                f"-> {self.exchange_bar_dict_1[symbol][1]} "
                f"-> {vol}]\namount: ${math.ceil(amount)}"
                f"\nticker volume alert monthly count:"
                f" {self.exchange_alert_monthly_count['15m_volume'][symbol][0]}")
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
                self._update_monthly_count(symbol)
                self.tg_bot["15m_volume"].add_msg_to_queue(
                    f"{symbol} 15 min volume alert 2nd, 3rd bar 10X: volume "
                    f"[{self.exchange_bar_dict[symbol][1]} "
                    f"-> {self.exchange_bar_dict[symbol][2]} -> {vol}]"
                    f"\namount: ${math.ceil(amount)}"
                    f"\nticker volume alert monthly count:"
                    f" {self.exchange_alert_monthly_count['15m_volume'][symbol][0]}")
            self.exchange_bar_dict[symbol] = [current_time, vol]
        else:
            self.exchange_bar_dict[symbol] = [current_time, vol]

        # price alert
        self.price_dict["15m"][symbol] = (close / open_p - 1) * 100
        self.lock_15m.release()

    def _alert_1h(self, msg):
        """
        volume/price alert callback function for 1h klines

        Volume:
            alert if second bar is 10X first bar, and volume over threshold
        Price:
            record the price change in % for high and low price
        """
        alert_threshold = self.settings["1h_volume_usd"]
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"] or \
                msg["data"]["k"]["x"] is False or msg["data"]["k"]["i"] != "1h":
            return

        if msg["data"]["k"]["s"].lower() not in self.exchanges:
            return

        kline = msg["data"]["k"]
        symbol = kline["s"]
        close = float(kline["c"])
        high = float(kline["h"])
        low = float(kline["l"])
        vol = float(kline["v"])
        current_time = int(kline["t"])
        amount = vol * close if symbol[-3:] != "BTC" else vol * close * self.BTC_price

        self.lock_1h.acquire()
        # two bar alert
        if len(self.exchange_bar_dict_1h[symbol]) == 2 and \
                vol >= 10 * self.exchange_bar_dict_1h[symbol][1] and amount >= alert_threshold:
            self._update_monthly_count(symbol, alert_type="1h_volume")
            self.tg_bot["1h_volume"].add_msg_to_queue(
                f"{symbol} 1h volume alert 2nd bar 10X: volume "
                f"[{self.exchange_bar_dict_1h[symbol][1]} "
                f"-> {vol}]\namount: ${math.ceil(amount)}"
                f"\nticker volume alert monthly count:"
                f" {self.exchange_alert_monthly_count['1h_volume'][symbol][0]}")
        self.exchange_bar_dict_1h[symbol] = [current_time, vol]

        # price alert
        self.price_dict["1h"][symbol] = (high / low - 1) * 100
        self.lock_1h.release()


if __name__ == "__main__":
    BinancePriceVolumeAlert().klines_alert()
