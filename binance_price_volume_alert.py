import time
import math
import logging
import threading
from collections import defaultdict

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
        self.tg_bot_price = TelegramBot("PRICE")

        # symbol->[timestamp, close1, close2]
        # symbol->[timestamp, close]
        self.exchange_bar_dict = defaultdict(list)
        self.exchange_bar_dict_0 = defaultdict(list)
        self.dict_lock = threading.Lock()

        # monitored exchanges
        self.exchanges = self.cg.get_500_usdt_exchanges(market_cap=False)
        self.exchanges = [e.lower() for e in self.exchanges]
        self.exchanges.sort()

        # exchange count
        self.exchange_count = 0
        self.max_exchange_count = len(self.exchanges)

        # dict for 15min price alert: symbol->[price_change_rate, last_price]
        self.price_dict = defaultdict(list)
        self.price_lock = threading.Lock()

        # BTC_price
        self.BTC_price = 17000

        # for testing only
        self.tg_bot_test = TelegramBot("TEST")

    def monitor_price_change(self):
        """
        For price change alert
        """
        rate_threshold = 10.0
        while self.running:
            if self.exchange_count == 350:
                self.price_lock.acquire()
                self.exchange_count = 0
                price_lists = [[k, v[0]] for k, v in self.price_dict.items()]
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
                logging.info(f"price_lists: {price_lists}")
                for k, v in price_lists:
                    if v <= -1 * rate_threshold and len(smallest) < 5:
                        v = round(v, 2)
                        smallest.append([k, v])
                    if len(smallest) == 5:
                        break

                logging.info(f"largest price change: {largest}")
                logging.info(f"smallest price change: {smallest}")
                logging.info(f"exchange bar dict: {self.exchange_bar_dict}")
                logging.info(f"exchange bar dict 0: {self.exchange_bar_dict_0}")
                if len(largest) > 0:
                    self.tg_bot_price.safe_send_message(f"15 min top 5 positive price change in %: {largest}")
                if len(smallest) > 0:
                    self.tg_bot_price.safe_send_message(f"15 min top 5 negative price change in %: {smallest}")
                # logging.info(f"exchange_count: {self.exchange_count}")
                time.sleep(1)
                self.price_lock.release()

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
            monitor_thread = threading.Thread(target=self.monitor_price_change)
            monitor_thread.start()

            logging.info(f"exchanges: {len(self.exchanges)}")

            klines_client = Client()
            klines_client.start()
            klines_client.kline(
                symbol=self.exchanges, id=id_count, interval="15m", callback=self.volume_alerts
            )
            id_count += 1

            time.sleep(5)
            klines_client.kline(
                symbol=self.exchanges, id=id_count, interval="1h", callback=self.price_alerts
            )

            # time.sleep(88200.0 - ((time.time() - start_time) % 86400.0))
            time.sleep(86400.0 * 365)
            logging.info("closing ws connection")
            klines_client.stop()
            self.running = False
            self.tg_bot_volume.stop()
            monitor_thread.join()

        except Exception as e:
            error_count += 1
            if error_count > self.MAX_ERROR:
                raise e
            time.sleep(1)

    def volume_alerts(self, msg):
        """
        volume alert callback function

        alert if second bar is 10X first bar and third bar is 50X first bar
        alert if second bar is 50X first bar
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

        self.dict_lock.acquire()
        # update BTC_price
        if symbol == "BTCUSDT":
            self.BTC_price = close
            logging.info(f"BTC_price: {self.BTC_price}")

        # two bars alert
        if len(self.exchange_bar_dict_0[symbol]) == 2 and \
                vol >= 50 * self.exchange_bar_dict_0[symbol][1] and amount >= alert_threshold:
            self.tg_bot_volume.add_msg_to_queue(f"{symbol} 15 min volume alert 2 bars: volume "
                                                f"[{self.exchange_bar_dict_0[symbol][1]} "
                                                f"-> {vol}]\namount: ${math.ceil(amount)}")
        self.exchange_bar_dict_0[symbol] = [current_time, vol]
        # logging.info(f"exchange_bar_dict_0: {exchange_bar_dict_0}")

        # three bars alert
        if len(self.exchange_bar_dict[symbol]) == 2:
            if vol != 0.0 and vol >= 10 * self.exchange_bar_dict[symbol][1] and amount >= alert_threshold:
                self.exchange_bar_dict[symbol].append(vol)
                self.exchange_bar_dict[symbol][0] = current_time
            else:
                self.exchange_bar_dict[symbol] = [current_time, vol]
        elif len(self.exchange_bar_dict[symbol]) == 3:
            if vol != 0.0 and vol >= 50 * self.exchange_bar_dict[symbol][1] and amount >= alert_threshold:
                self.tg_bot_volume.add_msg_to_queue(f"{symbol} 15 min volume alert 3 bars: volume "
                                                    f"[{self.exchange_bar_dict[symbol][1]} "
                                                    f"-> {self.exchange_bar_dict[symbol][2]} -> {vol}]"
                                                    f"\namount: ${math.ceil(amount)}")
            self.exchange_bar_dict[symbol] = [current_time, vol]
        else:
            self.exchange_bar_dict[symbol] = [current_time, vol]
        # logging.info(exchange_bar_dict)

        # # price alert
        # self.exchange_count += 1
        # self.max_exchange_count = max(self.exchange_count, self.max_exchange_count)
        # # logging.info(f"exchange_count: {self.exchange_count}")
        #
        # if symbol not in self.price_dict:
        #     self.price_dict[symbol] = [0.0, close]
        # else:
        #     self.price_dict[symbol][0] = (close / self.price_dict[symbol][1] - 1) * 100
        #     self.price_dict[symbol][1] = close
        self.dict_lock.release()

    def price_alerts(self, msg):
        """
        For price alerts
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

        self.price_lock.acquire()
        # price alert
        self.exchange_count += 1
        self.max_exchange_count = max(self.exchange_count, self.max_exchange_count)
        logging.info(f"exchange_count: {self.exchange_count}")

        if symbol not in self.price_dict:
            self.price_dict[symbol] = [0.0, close]
        else:
            self.price_dict[symbol][0] = (close / self.price_dict[symbol][1] - 1) * 100
            self.price_dict[symbol][1] = close
        self.price_lock.release()


if __name__ == "__main__":
    BinancePriceVolumeAlert().klines_alert()
