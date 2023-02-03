import time
from time import sleep
import threading
import logging

import numpy as np
from binance.lib.utils import config_logging

from crawl_coingecko import CoinGecKo
from telegram_api import TelegramBot
from utility import update_coins_exchanges_txt_300

STABLE_COINS = {"USDT", "USDC", "DAI", "BUSD", "USDP", "GUSD",
                "TUSD", "FRAX", "CUSD", "USDD", "DEI", "USDK",
                "MIMATIC", "OUSD", "PAX", "FEI", "USTC", "USDN",
                "TRIBE", "LUSD", "EURS", "VUSDC", "USDX", "SUSD",
                "VAI", "RSV", "CEUR", "USDS", "CUSDT"}


class CoinGecKo12H(CoinGecKo):
    def __init__(self, coin_ids, coin_symbols, tg_type="CG_ALERT"):
        super().__init__(tg_type)
        self.coin_ids = coin_ids
        self.coin_symbols = coin_symbols
        self.spot_over_h12_300 = set()

    def h12_sma_180(self, coin_id, coin_symbol):
        try:
            price = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=90)
            price = price['prices']
            price = [i[1] for i in price]
            res = 0
            counter = 0
            for i in range(0, len(price), 12):
                if i == 2160:
                    break
                res += float(price[i])
                counter += 1
            sma = res / counter
            price = self.cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=1)
            price = float(price['prices'][-1][1])

            logging.warning(f"{coin_symbol}: {price}, {sma}")
            if price > sma:
                self.spot_over_h12_300.add(coin_symbol)
                return True

        except Exception as e:
            return False

    def run(self):
        for coin_id, coin_symbol in zip(self.coin_ids, self.coin_symbols):
            coin_symbol = coin_symbol.upper()
            if coin_symbol in STABLE_COINS:
                continue
            self.h12_sma_180(coin_id, coin_symbol)
        logging.warning(f"spot_over_h12_300: {self.spot_over_h12_300}")

        return update_coins_exchanges_txt_300(self.spot_over_h12_300, "coins")


############################################################################################################
running = True
config_logging(logging, logging.INFO)
class CoinGecKoAlert(CoinGecKo):
    def __init__(self, coin_id, symbol, alert_type="alert_100", tg_type="CG_ALERT"):
        super().__init__("TEST")
        self.coin_id = coin_id
        self.symbol = symbol
        self.less_90_days = False
        self.less_34_days = False
        self.less_17_days = False

        self.tg_bot = TelegramBot(tg_type, True)

        self.counter_12h = 0
        self.list_12h = None
        self.ma_12h = None
        self.spot_over_ma_12h = None

        self.counter_4h = 0
        self.list_4h = None
        self.ma_4h = None
        self.spot_over_ma_4h = None

        self.counter_4h_500 = 0
        self.list_4h_500 = None
        self.ma_4h_500 = None
        self.spot_over_ma_4h_500 = None

        self.counter_1d = 0
        self.list_1d = None
        self.ma_1d = None
        self.spot_over_ma_1d = None

        # for minute updates
        self.last_update_thread = None
        self.minute_counter_12h = 1
        self.minute_counter_4h = 1
        self.minute_counter_1d = 1

        # indicate whether for 100 or 500
        self.alert_type = alert_type

    def h12_init(self):
        # try:
        price = self.cg.get_coin_market_chart_by_id(id=self.coin_id, vs_currency='usd', days=90)
        price = price['prices']
        if len(price) < 2150:
            self.less_90_days = True
        # price = [i[1] for i in price]
        self.list_12h = np.zeros(180, dtype=np.float64)
        price.reverse()
        counter = 0
        print(len(price))
        for i in range(0, len(price), 12):
            if i == 2160:
                break
            self.list_12h[counter] = price[i][1]
            counter += 1
            # self.current_time_12h = price[i][0]
        # self.current_time = price[-1][0]
        self.counter_12h = len(price) // 12
        self.ma_12h = np.sum(self.list_12h)/self.counter_12h
        self.spot_over_ma_12h = price[0][1] > self.ma_12h
        # print(f"h12 init: {self.coin_id}, ma_12h: {self.ma_12h}, list_12h{self.list_12h}, spot_over_ma_12h: {self.spot_over_ma_12h}")
        # except Exception as e:
        #     sleep(60)
        #     self.h12_init()

    def h4_init(self):
        # try:
        price = self.cg.get_coin_market_chart_by_id(id=self.coin_id, vs_currency='usd', days=34)
        price = price['prices']
        if len(price) < 790:
            self.less_34_days = True

        self.list_4h = np.zeros(200, dtype=np.float64)
        price.reverse()
        counter = 0
        for i in range(0, min(len(price), 800), 4):
            if i == 800:
                break
            self.list_4h[counter] = price[i][1]
            counter += 1

        self.counter_4h = min(len(price), 800) // 4
        self.ma_4h = np.sum(self.list_4h)/self.counter_4h
        self.spot_over_ma_4h = price[0][1] > self.ma_4h
        # print(f"h4 init: {self.coin_id}, ma_4h: {self.ma_4h}, list_4h: {self.list_4h},spot_over_ma_4h: {self.spot_over_ma_4h}")
        # except Exception as e:
        #     print("h4 init error")
        #     sleep(60)
        #     self.h4_init()

    def h4_500_init(self):
        # try:
        price = self.cg.get_coin_market_chart_by_id(id=self.coin_id, vs_currency='usd', days=17)
        price = price['prices']
        if len(price) < 395:
            self.less_17_days = True

        self.list_4h_500 = np.zeros(100, dtype=np.float64)
        price.reverse()
        counter = 0
        for i in range(0, min(len(price), 400), 4):
            if i == 400:
                break
            self.list_4h_500[counter] = price[i][1]
            counter += 1

        self.counter_4h_500 = min(len(price), 400) // 4
        self.ma_4h_500 = np.sum(self.list_4h_500)/self.counter_4h_500
        self.spot_over_ma_4h_500 = price[0][1] > self.ma_4h_500
        # print(f"h4 init: {self.coin_id}, ma_4h: {self.ma_4h_500}, spot_over_ma_4h: {self.spot_over_ma_4h_500}")
        # except Exception as e:
        #     print("h4 init error")
        #     sleep(60)
        #     self.h4_init()

    def d1_init(self):
        # try:
        price = self.cg.get_coin_market_chart_by_id(id=self.coin_id, vs_currency='usd', days=90)
        price = price['prices']
        if len(price) < 2150:
            self.less_90_days = True

        self.list_1d = np.zeros(90, dtype=np.float64)
        price.reverse()
        counter = 0
        for i in range(0, len(price), 24):
            if i == 2160:
                break
            self.list_1d[counter] = price[i][1]
            counter += 1

        self.counter_1d = len(price) // 24
        self.ma_1d = np.sum(self.list_1d)/self.counter_1d
        self.spot_over_ma_1d = price[0][1] > self.ma_1d
        # print(f"d1 init: {self.coin_id}, ma_1d: {self.ma_1d}, spot_over_ma_1d: {self.spot_over_ma_1d}")
        # except Exception as e:
        #     print("h4 init error")
        #     sleep(60)
        #     self.h4_init()

    def minute_update_100(self, price, update_ma_12=False, update_ma_4=False):
        # price = self.cg.get_price(ids=self.coin_id, vs_currencies='usd', include_last_updated_at=True,
        #                           precision="full")
        # price = np.float64(price[self.coin_id]["usd"])
        if update_ma_12:
            self.list_12h = np.roll(self.list_12h, 1)
            self.list_12h[0] = price
            if self.counter_12h < 180:
                self.counter_12h += 1
            self.ma_12h = np.sum(self.list_12h)/self.counter_12h

        if update_ma_4:
            self.list_4h = np.roll(self.list_4h, 1)
            self.list_4h[0] = price
            if self.counter_4h < 200:
                self.counter_4h += 1
            self.ma_4h = np.sum(self.list_4h) / self.counter_4h
            # print(price, self.list_4h, self.counter_4h, self.ma_4h, np.sum(self.list_4h))

        if self.spot_over_ma_12h and price < self.ma_12h:
            self.tg_bot.add_msg_to_queue(
                 f"100_{self.symbol} spot: {str(price)} crossunder H12 ma180: {str(self.ma_12h)}")
            self.spot_over_ma_12h = False
        elif not self.spot_over_ma_12h and price > self.ma_12h:
            self.tg_bot.add_msg_to_queue(
                 f"100_{self.symbol} spot: {str(price)} crossover H12 ma180: {str(self.ma_12h)}")
            self.spot_over_ma_12h = True

        if self.spot_over_ma_4h and price < self.ma_4h:
            self.tg_bot.add_msg_to_queue(
                f"100_{self.symbol} spot: {str(price)} crossunder H4 ma200: {str(self.ma_4h)}")
            self.spot_over_ma_4h = False
        elif not self.spot_over_ma_4h and price > self.ma_4h:
            self.tg_bot.add_msg_to_queue(
                f"100_{self.symbol} spot: {str(price)} crossover H4 ma200: {str(self.ma_4h)}")
            self.spot_over_ma_4h = True

        # logging.info(f"100_{self.symbol} spot: {str(price)} ma180: {str(self.ma_12h)} ma200: {str(self.ma_4h)}")
        # self.tg_bot.safe_send_message(f"{self.symbol} spot: {str(price)} H12 ma180: {str(self.ma_12h)} H4 ma200: {str(self.ma_4h)}, _____{time.time()}")
        # add_msg_to_queue(f"{self.symbol} spot: {str(price)} H4 ma200: {str(self.ma_4h)}, _____{time.time()}")

    def minute_update_500(self, price, update_ma_1d=False, update_ma_4=False):
        # price = self.cg.get_price(ids=self.coin_id, vs_currencies='usd', include_last_updated_at=True,
                                  # precision="full")
        # price = np.float64(price[self.coin_id]["usd"])
        if update_ma_1d:
            self.list_1d = np.roll(self.list_1d, 1)
            self.list_1d[0] = price
            if self.counter_1d < 90:
                self.counter_1d += 1
            self.ma_1d = np.sum(self.list_1d)/self.counter_1d

        if update_ma_4:
            self.list_4h_500 = np.roll(self.list_4h_500, 1)
            self.list_4h_500[0] = price
            if self.counter_4h_500 < 100:
                self.counter_4h_500 += 1
            self.ma_4h_500 = np.sum(self.list_4h_500) / self.counter_4h_500
            # print(price, self.list_4h, self.counter_4h, self.ma_4h, np.sum(self.list_4h))

        if self.spot_over_ma_1d and price < self.ma_1d:
            self.tg_bot.add_msg_to_queue(
                 f"500_{self.symbol} spot: {str(price)} crossunder D1 ma90: {str(self.ma_1d)}")
            self.spot_over_ma_1d = False
        elif not self.spot_over_ma_1d and price > self.ma_1d:
            self.tg_bot.add_msg_to_queue(
                 f"500_{self.symbol} spot: {str(price)} crossover D1 ma90: {str(self.ma_1d)}")
            self.spot_over_ma_1d = True

        if self.spot_over_ma_4h_500 and price < self.ma_4h_500:
            self.tg_bot.add_msg_to_queue(
                f"500_{self.symbol} spot: {str(price)} crossunder H4 ma100: {str(self.ma_4h_500)}")
            self.spot_over_ma_4h_500 = False
        elif not self.spot_over_ma_4h_500 and price > self.ma_4h_500:
            self.tg_bot.add_msg_to_queue(
                f"500_{self.symbol} spot: {str(price)} crossover H4 ma100: {str(self.ma_4h_500)}")
            self.spot_over_ma_4h_500 = True
        # print(f"{self.symbol} spot: {str(price)} D1: {str(self.ma_1d)} H4 ma100: {str(self.ma_4h_500)}")

    def alert_spot_init(self):
        if self.alert_type == "alert_100":
            self.h12_init()
            self.h4_init()
        else:
            self.d1_init()
            self.h4_500_init()
        logging.info(f"{self.alert_type}_{self.symbol} coingecko init done")
    def minute_update(self, price):
        if self.last_update_thread:
            self.last_update_thread.join()
        self.last_update_thread = \
            threading.Thread(target=self.minute_update_100,
                             args=(price, self.minute_counter_12h % 720 == 0,
                                   self.minute_counter_4h % 240 == 0)) \
            if self.alert_type == "alert_100" \
            else threading.Thread(target=self.minute_update_500,
                                  args=(price, self.minute_counter_1d % 1440 == 0,
                                        self.minute_counter_4h % 240 == 0))
        self.last_update_thread.start()
        self.minute_counter_12h %= 720
        self.minute_counter_12h += 1
        self.minute_counter_4h %= 240
        self.minute_counter_4h += 1
        self.minute_counter_1d %= 1440
        self.minute_counter_1d += 1

        return self.last_update_thread


def alert_coins(coin_ids, coin_symbols, alert_type="alert_100", tg_type="CG_ALERT"):
    logging.info(f"alert_coins coingecko init start")
    coins = {}
    coin_ids_without_stable = []

    # init coins
    for i, coin_id in enumerate(coin_ids):
        coin_symbol = coin_symbols[i]
        if coin_symbol in STABLE_COINS:
            continue
        coin_ids_without_stable.append(coin_id)
        coins[coin_id] = CoinGecKoAlert(coin_id, coin_symbol, alert_type, tg_type)
        coins[coin_id].alert_spot_init()

    # update coins
    logging.info(f"alert_coins coingecko update start")
    t = threading.Thread(target=loop_alert_helper, args=(coins, coin_ids_without_stable))
    t.start()
    return t


def loop_alert_helper(coins, coin_ids):
    coins_threads = {}
    cg = coins[coin_ids[0]].cg
    r = None
    if len(coin_ids) > 250:
        coin_ids, r = coin_ids[:250], coin_ids[250:]
    start_time = time.time()

    # # setting up the msg queue
    # msg_thread = threading.Thread(target=send_msg_from_queue, args=(coins[coin_ids[0]].tg_bot,))
    # msg_thread.start()
    global running
    running = True
    # minute update
    while running:
        prices = cg.get_coins_markets(vs_currency='usd', ids=coin_ids, per_page=250, page=1)
        if r:
            prices += cg.get_coins_markets(vs_currency='usd', ids=r, per_page=250, page=2)

        for p in prices:
            price = np.float64(p["current_price"])
            coins_threads[p["id"]] = coins[p["id"]].minute_update(price)

        sleep(60.0 - ((time.time() - start_time) % 60.0))

    for t in coins_threads.values():
        if t:
            t.join()

    for coin_item in coins.values():
        coin_item.tg_bot.stop()


def close_all_threads(thread):
    global running
    running = False
    thread.join()
    running = True


if __name__ == '__main__':
    test = CoinGecKo12H(["bitcoin"], ["BTC"], "TEST")
    res = test.run()


    # from crawl_coingecko import CoinGecKo
    # cg = CoinGecKo("TEST")
    # exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=100)
    # print(coin_ids, coin_symbols)
    # t = alert_coins(coin_ids, coin_symbols, "alert_100", "TEST")
    # sleep(1800)
    # print("here")
    # close_all_threads(t)
    # print("done")
    # from pycoingecko import CoinGeckoAPI
    # cg = CoinGeckoAPI(api_key="CG-wAukVxNxrR322gkZYEgZWtV1")
    # price = cg.get_price(ids="bitcoin", vs_currencies='usd', include_last_updated_at=True,
    #                      precision="full")
    # price = np.float64(price["bitcoin"]["usd"])
    # print(price)
