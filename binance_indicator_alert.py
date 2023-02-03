import os
import requests
import zipfile
import datetime
import glob
import csv
import logging
import threading
from time import sleep

import numpy as np
from binance.lib.utils import config_logging
from binance.websocket.spot.websocket_client import SpotWebsocketClient as Client

from telegram_api import TelegramBot
from utility import update_coins_exchanges_txt_300


class BinanceIndicatorAlert:
    """
    first download, then run a websocket
    """
    DATA_DOWNLOAD_ROOT_URL = "https://data.binance.vision/data/spot/daily/klines/"
    HTTP_URL = "https://api.binance.com/api/v3/klines?"
    MAX_ERROR = 5
    STABLE_EXCHANGES = {"wbtcbtc"}
    config_logging(logging, logging.INFO)
    csv_dir = os.path.join(os.getcwd(), "klines_csv")
    try:
        os.mkdir(csv_dir)
    except FileExistsError:
        pass

    def __init__(self, exchanges, alert_type="alert_100", execution_time=86400 * 7, tg_type="CG_ALERT"):
        exchanges = [exchange.lower() for exchange in exchanges]
        exchanges.sort()
        self.i = 0
        # self.id_count = id_count
        self.exchanges = exchanges
        self.exchanges_set = set(exchanges)
        self.alert_type = alert_type
        self.execution_time = execution_time
        self.window = 100 if self.alert_type == "alert_500" else 200

        # all mappings use lower case of exchange name
        self.close = {}
        self.close_lock = threading.Lock()

        if self.alert_type == "alert_100":
            self.close = {exchange: {
                "4": np.zeros(self.window),
                "12": np.zeros(self.window),
                } for exchange in exchanges
            }
        elif self.alert_type == "alert_500":
            self.close = {exchange: {
                "4": np.zeros(self.window),
                "24": np.zeros(self.window),
                } for exchange in exchanges
            }
        else:
            self.close = {exchange: {
                "12": np.zeros(self.window),
                } for exchange in exchanges
            }

        # for calculating spot over h12 exchanges
        self.spot_over_h12_300 = set()

        self.last_close_1m = {exchange: 0.0 for exchange in exchanges}

        self.tg_bot = TelegramBot(tg_type)

    def download_past_klines(self, time_frame, exchange_list):
        """
        Download and store all the kline data until last hour
        """
        for exchange in exchange_list:
            logging.warning(f"Downloading past klines {time_frame}h for {exchange}")
            exchange = exchange.upper()
            days_delta = time_frame * self.window // 24 + 1
            start_time = datetime.datetime.now() - datetime.timedelta(days=days_delta)
            time_frame_str = f"{time_frame}h" if int(time_frame) < 24 else "1d"
            i = 0
            error = 0
            cur_timestamp = None

            while days_delta > 0:
                # sleep(1)
                days_delta -= 1
                start_time_str = start_time.strftime("%Y-%m-%d")
                start_time += datetime.timedelta(days=1)
                url = f"{self.DATA_DOWNLOAD_ROOT_URL}{exchange}/{time_frame_str}/" \
                      f"{exchange}-{time_frame_str}-{start_time_str}.zip"

                try:
                    # download single day csv file
                    response = requests.get(url, timeout=100)
                    open(f"{exchange}.zip", "wb").write(response.content)
                    with zipfile.ZipFile(f"{exchange}.zip", "r") as zip_ref:
                        zip_ref.extractall(self.csv_dir)

                    files = glob.glob(f"{self.csv_dir}/*.csv")
                    target_csv = os.path.join(self.csv_dir, f"{exchange}-{time_frame_str}-{start_time_str}.csv")
                    if target_csv not in files:
                        logging.error(f"Error: {len(files)} files found")
                        raise Exception("No csv file found")

                    # process csv file and store kline information
                    with open(target_csv, "r") as f:
                        rows = [row for row in csv.reader(f)]
                        for row in rows:
                            start_timestamp, close_timestamp, close = int(row[0]), int(row[6]), float(row[4])
                            if cur_timestamp is None or start_timestamp == cur_timestamp + 1:
                                cur_timestamp = close_timestamp
                                i = self.update_close(time_frame, i, exchange, close)
                            else:
                                # missing data
                                while cur_timestamp + 1 < start_timestamp:
                                    i = self.update_close(time_frame, i, exchange, copy=True)
                                    cur_timestamp += time_frame * 3600 * 1000
                                cur_timestamp = close_timestamp
                                i = self.update_close(time_frame, i, exchange, close)
                    os.remove(target_csv)

                except Exception as e:
                    if error > self.MAX_ERROR:
                        return
                    error += 1
                    for count in range(24 // time_frame):
                        i = self.update_close(time_frame, i, exchange, copy=True)
                        if i != 0:
                            cur_timestamp += time_frame * 3600 * 1000

            os.remove(f"{exchange}.zip")
            # using http request to download the latest day
            cur_timestamp += 1
            http_url = f"{self.HTTP_URL}symbol={exchange}&interval={time_frame_str}" \
                       f"&startTime={cur_timestamp}&limit=1000"
            latest = list(requests.get(http_url).json())

            if len(latest) == 0:
                return
            # logging.info(f"{latest}")
            latest = latest[:-1]

            for candle in latest:
                start_timestamp, close_timestamp, close = int(candle[0]), int(candle[6]), float(candle[4])
                if cur_timestamp == start_timestamp:
                    cur_timestamp = close_timestamp + 1
                    i = self.update_close(time_frame, i, exchange, close)
                else:
                    # missing data
                    while cur_timestamp < start_timestamp:
                        i = self.update_close(time_frame, i, exchange, copy=True)
                        cur_timestamp += time_frame * 3600 * 1000
                    cur_timestamp = close_timestamp
                    i = self.update_close(time_frame, i, exchange, close)
            logging.warning(f"Download {exchange} {time_frame}h klines done")
            self.close_lock.acquire()
            logging.warning(f"{exchange} {time_frame}h:{np.mean(self.close[exchange.lower()][str(time_frame)])}")
            self.close_lock.release()

    def update_close(self, time_frame, i, exchange, close=None, copy=False, log=False):
        self.close_lock.acquire()
        time_frame = str(time_frame)
        exchange = exchange.lower()

        if not copy:
            if i == self.window:
                self.close[exchange][time_frame] = np.roll(self.close[exchange][time_frame], -1)
                self.close[exchange][time_frame][-1] = close
            else:
                self.close[exchange][time_frame][i] = close
                i += 1
        else:
            if i != 0 and i < self.window:
                self.close[exchange][time_frame][i] = self.close[exchange][time_frame][i - 1]
                i += 1
            elif i == self.window:
                self.close[exchange][time_frame] = np.roll(self.close[exchange][time_frame], -1)
                self.close[exchange][time_frame][-1] = self.close[exchange][time_frame][-2]

        # if log:
        #     logging.warning(f"{exchange} ma_{time_frame}h:{self.close[exchange][time_frame]}")
        self.close_lock.release()
        return i

    def download_past_klines_threads(self, time_frame, num_threads=20):
        """
        Download and store all the kline data until last hour
        """
        threads = []
        exchanges = [exchange for exchange in self.exchanges if exchange not in self.STABLE_EXCHANGES]
        incr = len(exchanges) // num_threads
        exchanges = [exchanges[i:i + incr] for i in range(0, len(exchanges), incr)]

        for exchange_list in exchanges:
            t = threading.Thread(target=self.download_past_klines, args=(time_frame, exchange_list))
            threads.append(t)
            t.start()
            # sleep(1)
        for t in threads:
            t.join()

    def run(self):
        """
        Run websocket
        """
        if self.alert_type == "alert_100":
            self.download_past_klines_threads(4)
            self.download_past_klines_threads(12)
        elif self.alert_type == "alert_500":
            self.download_past_klines_threads(4)
            self.download_past_klines_threads(24)
        else:
            self.download_past_klines_threads(12)

        id_count = 0
        client = Client()
        client.start()
        l, r = self.exchanges[:len(self.exchanges) // 2], self.exchanges[len(self.exchanges) // 2:]
        if self.alert_type == "alert_300":
            client.kline(
                symbol=l, id=id_count, interval="1m", callback=self.minute_alert_300
            )
            id_count += 1
            sleep(1)
            client.kline(
                symbol=r, id=id_count, interval="1m", callback=self.minute_alert_300
            )
        else:
            client.kline(
                symbol=self.exchanges, id=id_count, interval="1m", callback=self.minute_alert
            )

        id_count += 1
        sleep(5)

        if self.alert_type == "alert_100" or self.alert_type == "alert_500":
            client.kline(
                symbol=self.exchanges, id=id_count, interval="4h", callback=self.update_ma_4h
            )
            id_count += 1
            sleep(5)

            if self.alert_type == "alert_100":
                client.kline(
                    symbol=self.exchanges, id=id_count, interval="12h", callback=self.update_ma_12h
                )
            else:
                client.kline(
                    symbol=self.exchanges, id=id_count, interval="24h", callback=self.update_ma_24h
                )

        if self.alert_type == "alert_300":
            sleep(60*15)
        else:
            sleep(self.execution_time)
        client.stop()

        logging.warning(f"{self.spot_over_h12_300} done")
        if self.alert_type == "alert_300":
            return update_coins_exchanges_txt_300(self.spot_over_h12_300, "exchanges")

    def update_ma_4h(self, msg):
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"]:
            return
        msg = msg["data"]
        if msg["s"].lower() in self.exchanges_set and msg["k"]["x"] and msg["k"]["i"] == "4h":
            self.update_close("4", self.window, msg["s"], float(msg["k"]["c"]))

    def update_ma_12h(self, msg):
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"]:
            return
        msg = msg["data"]
        if msg["s"].lower() in self.exchanges_set and msg["k"]["x"] and msg["k"]["i"] == "12h":
            self.update_close("12", self.window, msg["s"], float(msg["k"]["c"]))

    def update_ma_24h(self, msg):
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"]:
            return
        msg = msg["data"]
        if msg["s"].lower() in self.exchanges_set and msg["k"]["x"] and msg["k"]["i"] == "1d":
            self.update_close("24", self.window, msg["s"], float(msg["k"]["c"]))

    def minute_alert_300(self, msg):
        # logging.warning(f"minute alert: {msg}")
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"]:
            return
        msg = msg["data"]
        if msg["s"].lower() in self.exchanges_set and msg["k"]["x"] and msg["k"]["i"] == "1m":
            exchange = msg["s"].lower()
            close = float(msg["k"]["c"])
            # self.close_lock.acquire()
            if self.alert_type == "alert_300":
                self.close_lock.acquire()
                print(f"close: {close}, ma: {np.mean(self.close[exchange]['12'])}")
                if close > np.mean(self.close[exchange]["12"]):
                    logging.warning(f"{exchange} over h12"
                                    f"close: {close}, ma: {np.mean(self.close[exchange]['12'])}")
                    self.spot_over_h12_300.add(exchange.upper())
                else:
                    if exchange.upper() in self.spot_over_h12_300:
                        self.spot_over_h12_300.remove(exchange.upper())
                self.close_lock.release()
                return

    def minute_alert(self, msg):
        # logging.warning(f"minute alert: {msg}")
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"]:
            return
        msg = msg["data"]
        if msg["s"].lower() in self.exchanges_set and msg["k"]["x"] and msg["k"]["i"] == "1m":
            exchange = msg["s"].lower()
            close = float(msg["k"]["c"])
            self.close_lock.acquire()
            if self.last_close_1m[exchange] == 0.0:
                self.last_close_1m[exchange] = close
                self.close_lock.release()
                return
            if self.alert_type == "alert_100":
                self.alert_helper_1m(close, 4, exchange)
                self.alert_helper_1m(close, 12, exchange)
            elif self.alert_type == "alert_500":
                self.alert_helper_1m(close, 4, exchange)
                self.alert_helper_1m(close, 24, exchange)
            self.last_close_1m[exchange] = close
            logging.warning(f"{exchange} 1m current {self.last_close_1m[exchange]}")
            self.close_lock.release()


    def alert_helper_1m(self, close, timeframe, exchange):
        timeframe = str(timeframe)
        current_ma = np.mean(self.close[exchange][timeframe])
        timeframe_str = f"H{timeframe}" if timeframe != "24" else "D1"
        mode = self.alert_type.split("_")[1]

        if close > current_ma > self.last_close_1m[exchange]:
            self.tg_bot.safe_send_message(f"{mode}_{exchange.upper()} spot: {close}"
                                          f" crossover {timeframe_str} ma{self.window}: {current_ma}")
            logging.warning(f"{exchange}_{mode} ma {current_ma}, close {close}")
        elif close < current_ma < self.last_close_1m[exchange]:
            self.tg_bot.safe_send_message(f"{mode}_{exchange.upper()} spot: {close}"
                                          f" crossunder {timeframe_str} ma{self.window}: {current_ma}")
            logging.warning(f"{exchange}_{mode} ma {current_ma}, close {close}")


if __name__ == "__main__":
    logging.info("test")
    from crawl_coingecko import CoinGecKo
    cg = CoinGecKo()
    ex, _, _ = cg.get_exchanges(num=300)
    print(f"---------------------------------------------------{len(ex)}")
    ex = ex[:40]
    alert = BinanceIndicatorAlert(ex, "alert_300", tg_type="TEST")
    ex, c, d = alert.run()
    print(ex, c, d)
    # alert.download_past_klines(12)
