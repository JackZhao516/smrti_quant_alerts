import logging
import requests
import datetime
import threading
import time

import urllib3
import numpy as np
from pycoingecko import CoinGeckoAPI

from telegram_api import TelegramBot
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CoinGecKo:
    COINGECKO_API_KEY = "CG-wAukVxNxrR322gkZYEgZWtV1"
    DATA_DOWNLOAD_ROOT_URL = "https://data.binance.vision/data/spot/daily/klines/"

    def __init__(self, tg_type="TEST"):
        self.cg = CoinGeckoAPI(api_key=self.COINGECKO_API_KEY)
        self.tg_bot = TelegramBot(alert_type=tg_type)
        self.popular_exchanges = None
        self.popular_exchanges_lock = threading.Lock()

    def get_exchanges(self, num=300):
        exchanges = set(self.get_all_popular_exchanges())
        # exchanges = set(self.get_all_exchanges())
        res = []
        coingeco_coins = []
        coingeco_names = []

        if num == 300:
            market_list = self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=150, page=1,
                                                    sparkline=False)
            market_list += self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=150, page=2,
                                                     sparkline=False)
        else:
            market_list = self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=100, page=1,
                                                    sparkline=False)

        # ids = [market['id'].upper() for market in market_list]
        markets = [(market['symbol'].upper(), market['id']) for market in market_list]
        market_list = []
        market_set = set()
        for index, i in enumerate(markets):
            if i not in market_set:
                market_list.append(i)
                market_set.add(i)

        for i, coin in enumerate(market_list):
            symbol, coin_id = coin
            if f"{symbol}USDT" not in exchanges and f"{symbol}BTC" not in exchanges \
                    and f"{symbol}ETH" not in exchanges and f"{symbol}BUSD" not in exchanges:
                coingeco_coins.append(coin_id)
                coingeco_names.append(symbol)
            else:
                if f"{symbol}BUSD" in exchanges:
                    res.append(f"{symbol}BUSD")
                if f"{symbol}USDT" in exchanges:
                    res.append(f"{symbol}USDT")
                if f"{symbol}BTC" in exchanges:
                    res.append(f"{symbol}BTC")
                if f"{symbol}ETH" in exchanges:
                    res.append(f"{symbol}ETH")

        # self.tg_bot.send_message(f"{datetime.datetime.now()}: Top 300 coins:\n {market_list}")
        self.tg_bot.send_message(f"{datetime.datetime.now()}: Top {num} coins that are not on Binance:\n {coingeco_names}")
        l, r = res[:len(res)//2], res[len(res)//2:]
        self.tg_bot.send_message(f"{datetime.datetime.now()}: Top {num} coin exchanges that are on Binance:\n {l}")
        self.tg_bot.send_message(f"{r}")

        return res, coingeco_coins, coingeco_names

    def get_all_exchanges(self):
        """
        Get all exchanges on binance
        """
        api_url = f'https://api.binance.com/api/v3/exchangeInfo?permissions=SPOT'
        response = requests.get(api_url, timeout=10).json()
        exchanges = {exchange['symbol'] for exchange in response['symbols']}
        return exchanges

    def get_all_popular_exchanges(self, time_on_binance=102, num_threads=50):
        """
        BTC, ETH, USDT, BUSD exchanges older than time_on_binance days
        """
        exchanges = self.get_all_exchanges()
        print(f"{len(exchanges)} exchanges")
        res = []

        # choose BTC, ETH, USDT, BUSD exchanges
        for exchange in exchanges:
            if exchange[-3:] == "BTC" or exchange[-3:] == "ETH" or \
                    exchange[-4:] == "USDT" or exchange[-4:] == "BUSD":
                res.append(exchange)
        self.popular_exchanges = set(res)

        # test exchange old enough and still on binance
        start_time = datetime.datetime.now() - datetime.timedelta(days=time_on_binance)
        start_time_now = datetime.datetime.now() - datetime.timedelta(days=2)
        start_time_str = start_time.strftime("%Y-%m-%d")
        start_time_now_str = start_time_now.strftime("%Y-%m-%d")

        threads = []
        # res = ["BTCUSDT"]

        incr = len(res) // num_threads
        res = [res[i:i + incr] for i in range(0, len(res), incr)]

        for exchanges in res:
            t = threading.Thread(target=self.get_all_popular_exchanges_helper,
                                 args=(exchanges, start_time_str, start_time_now_str))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        res = list(self.popular_exchanges)
        print(res)
        return res

    def get_all_popular_exchanges_helper(self, exchanges, start_time_str, start_time_now_str):
        for exchange in exchanges:
            try:
                self.validate_popular_exchange_helper(exchange, start_time_str, start_time_now_str)
            except Exception as e:
                print(e)
                continue

    def validate_popular_exchange_helper(self, exchange, start_time_str, start_time_now_str):
        """
        Helper function for get_all_popular_exchanges
        """
        time_frames = ["12h", "4h", "1d"]

        for time_frame in time_frames:
            url = f"{self.DATA_DOWNLOAD_ROOT_URL}{exchange}/{time_frame}/" \
                  f"{exchange}-{time_frame}-{start_time_str}.zip"
            url_now = f"{self.DATA_DOWNLOAD_ROOT_URL}{exchange}/{time_frame}/" \
                      f"{exchange}-{time_frame}-{start_time_now_str}.zip"
            response = requests.get(url, timeout=1000, verify=False)
            response_now = requests.get(url_now, timeout=1000, verify=False)
            # print(f"{exchange} {start_time_now_str} {response.status_code} {response_now.status_code}")

            if response.status_code != 200 or response_now.status_code != 200:
                self.popular_exchanges_lock.acquire()
                self.popular_exchanges.remove(exchange)
                self.popular_exchanges_lock.release()

                return

    def get_500_usdt_exchanges(self, market_cap=True):
        exchanges = self.get_all_popular_exchanges(time_on_binance=2)
        # logger.info(f"Getting all {len(exchanges)}")
        res = []
        if market_cap:
            ids = self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=250, page=1,
                                            sparkline=False)
            ids += self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=250, page=2,
                                             sparkline=False)
            ids = [id['symbol'].upper() for id in ids]
            for i, symbol in enumerate(ids):
                if f"{symbol}USDT" in exchanges:
                    res.append(f"{symbol}USDT")
        else:
            coins = set()
            for i in exchanges:
                if i[-4:] == "USDT":
                    res.append(i)
                    coins.add(i[:-4])
            for i in exchanges:
                if i[-4:] == "BUSD" and i[:-4] not in coins:
                    res.append(i)
                    coins.add(i[:-4])
            for i in exchanges:
                if i[-3:] == "BTC" and i[:-3] not in coins:
                    res.append(i)
            res = list(set(res))
            print(len(res))
            logging.info(f"Got {len(res)} coins")
        return res

    def get_all_ids(self):
        ids = self.cg.get_coins_list()
        ids = [[id['id'], id['symbol'].upper()] for id in ids]
        return ids

    def get_coins_with_weekly_volume_increase(self, volume_threshold=1.3, usdt_only=False):
        ids = self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=250, page=1,
                                   sparkline=False)
        ids += self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=250, page=2,
                                    sparkline=False)
        ids = [[id['id'], id['symbol'].upper()] for id in ids]
        res = []

        for i, id in enumerate(ids):
            data = self.cg.get_coin_market_chart_by_id(id=id[0], vs_currency='usd', days=13, interval='daily')
            data = np.array(data['total_volumes'])
            if np.sum(data[:7, 1]) == 0:
                continue
            volume_increase = np.sum(data[7:, 1]) / np.sum(data[:7, 1])

            if volume_increase >= volume_threshold:
                res.append([volume_increase, id[1], id[0]])

        res = sorted(res, key=lambda x: x[0], reverse=True)
        exchanges = self.get_all_popular_exchanges()
        coingeco_coins, coingeco_names, ex = [], [], []

        for volume_increase, symbol, coin_id in res:
            if f"{symbol}USDT" not in exchanges and f"{symbol}BTC" not in exchanges\
                    and f"{symbol}ETH" not in exchanges and f"{symbol}BUSD" not in exchanges:
                coingeco_coins.append(coin_id)
                coingeco_names.append(symbol)
            else:
                if f"{symbol}USDT" in exchanges:
                    ex.append(f"{symbol}USDT")
                if not usdt_only:
                    if f"{symbol}BUSD" in exchanges:
                        ex.append(f"{symbol}BUSD")
                    if f"{symbol}BTC" in exchanges:
                        ex.append(f"{symbol}BTC")
                    if f"{symbol}ETH" in exchanges:
                        ex.append(f"{symbol}ETH")
        res = np.array(res)
        l, m1, m2, m3, m4, r = res[:len(res) // 6, :2], res[len(res) // 6: len(res) // 3, :2], res[len(res) // 3: len(res) // 2, :2], \
                               res[len(res) // 2: 2 * len(res) // 3, :2], res[2 * len(res) // 3: 5 * len(res) // 6, :2], \
                               res[5 * len(res) // 6:, :2]
        self.tg_bot.send_message(f"{datetime.datetime.now()}: Top 500 coins that has weekly volume increase > 30%:\n {l}")
        self.tg_bot.send_message(f"{m1}")
        self.tg_bot.send_message(f"{m2}")
        self.tg_bot.send_message(f"{m3}")
        self.tg_bot.send_message(f"{m4}")
        self.tg_bot.send_message(f"{r}")
        return ex, coingeco_coins, coingeco_names


if __name__ == '__main__':
    coin = CoinGecKo(tg_type='TEST')
    exchanges = coin.get_all_popular_exchanges()
    print(len(exchanges))
    # exchanges = set(exchanges)
    # coins = ["APTUSDT", "APTBTC", "BTTUSDT", "BTTBTC", "LUNABTC", "LUNAETH",
    #          "DAIBTC", "DAIUSDT", "HNTBTC", "HNTUSDT", "OSMOBTC", "OSMOUSDT",
    #          "RPLBTC", "RPLUSDT", "TUSDBTC", "TUSDETH", "TUSDUSDT", "USDCUSDT",
    #          "USDPUSDT"]
    #
    # for c in coins:
    #     if c in exchanges:
    #         print(c)
    #
    # ex, c, _ = coin.get_coins_with_weekly_volume_increase(volume_threshold=1.3)
    # print(len(ex), len(c))
