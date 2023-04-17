import logging
import requests
import datetime
import threading
import json
import time

import urllib3
import numpy as np
from pycoingecko import CoinGeckoAPI

from telegram_api import TelegramBot
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CoinGecKo:
    COINGECKO_API_KEY = json.load(open("token.json"))["COINGECKO_API_KEY"]
    DATA_DOWNLOAD_ROOT_URL = "https://data.binance.vision/data/spot/daily/klines/"
    API_URL = "https://api.binance.com/api/v3/"

    def __init__(self, tg_type="TEST"):
        self.cg = CoinGeckoAPI(api_key=self.COINGECKO_API_KEY)
        self.tg_bot = TelegramBot(alert_type=tg_type)
        self.popular_exchanges = None
        self.popular_exchanges_lock = threading.Lock()
        self.popular_exchanges = self.get_all_binance_active_exchanges()
        # self.popular_exchanges = self.get_all_binance_exchanges()
        self.popular_exchanges_timestamp = time.time()

    def get_top_market_cap_exchanges(self, num=300):
        """
        get the top num market cap usdt eth busd btc exchanges
        """
        self.update_popular_exchanges()
        exchanges = set(self.popular_exchanges)
        # exchanges = set(self.get_all_exchanges())
        res = []
        coingeco_coins = []
        coingeco_names = []

        if num == 300:
            market_list = self.cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=150,
                page=1, sparkline=False)
            market_list += self.cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=150,
                page=2, sparkline=False)
        else:
            market_list = self.cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=100,
                page=1, sparkline=False)

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
        self.tg_bot.send_message(f"{datetime.datetime.now()}: "
                                 f"Top {num} coins that are not on Binance:\n {coingeco_names}")
        l, r = res[:len(res)//2], res[len(res)//2:]
        self.tg_bot.send_message(f"{datetime.datetime.now()}: "
                                 f"Top {num} coin exchanges that are on Binance:\n {l}")
        self.tg_bot.send_message(f"{r}")

        return res, coingeco_coins, coingeco_names

    def get_all_binance_exchanges(self):
        """
        Get all exchanges on binance
        """
        api_url = f'{self.API_URL}exchangeInfo?permissions=SPOT'
        response = requests.get(api_url, timeout=10).json()
        exchanges = {exchange['symbol'] for exchange in response['symbols']}
        return exchanges

    def get_all_binance_active_exchanges(self, time_on_binance=None):
        """
        BTC, ETH, USDT, BUSD exchanges older than time_on_binance days
        """
        start = time.time()
        exchanges = self.get_all_binance_exchanges()
        res = []

        # choose BTC, ETH, USDT, BUSD exchanges
        for exchange in exchanges:
            if exchange[-3:] == "BTC" or exchange[-3:] == "ETH" or \
                    exchange[-4:] == "USDT" or exchange[-4:] == "BUSD":
                res.append(exchange)
        self.popular_exchanges = set(res)
        logging.warning(f"{len(self.popular_exchanges)} exchanges")

        res = list(self.popular_exchanges)

        for exchange in res:
            url = f"{self.API_URL}klines?symbol={exchange}&interval=1m&" \
                  f"startTime={(int(time.time())-70)*1000}&limit=1000"
            response = requests.get(url, timeout=2)
            response = response.json()
            if type(response) == dict or len(response) == 0:
                self.popular_exchanges.remove(exchange)
                continue
        
            if time_on_binance:
                time_delta = time_on_binance * 24 * 60 * 60 * 1000
                time_now = int(time.time()) * 1000
                url = f"{self.API_URL}klines?symbol={exchange}&interval=1m&" \
                      f"startTime={time_now - time_delta}&" \
                      f"endTime={time_now - time_delta + 70000}&limit=1000"
                response = requests.get(url, timeout=2)
                response = response.json()
                if type(response) == dict or len(response) == 0:
                    self.popular_exchanges.remove(exchange)
    
        res = list(self.popular_exchanges)

        logging.warning(len(res))
        logging.warning(f"{time.time() - start} seconds")
        return res

    def update_popular_exchanges(self):
        """
        Update popular exchanges if last update was more than 1 hour ago
        """
        if time.time() - self.popular_exchanges_timestamp >= 3600:
            self.popular_exchanges = self.get_all_binance_active_exchanges()
            self.popular_exchanges_timestamp = time.time()
        
    def get_all_exchanges_in_usdt_busd_btc(self):
        """
        Get all exchanges in either USDT, BUSD, or BTC format
        """
        self.update_popular_exchanges()
        res = []
        coins = set()
        for i in self.popular_exchanges:
            if i[-4:] == "USDT":
                res.append(i)
                coins.add(i[:-4])
        for i in self.popular_exchanges:
            if i[-4:] == "BUSD" and i[:-4] not in coins:
                res.append(i)
                coins.add(i[:-4])
        for i in self.popular_exchanges:
            if i[-3:] == "BTC" and i[:-3] not in coins:
                res.append(i)
        res = list(set(res))
        print(len(res))
        logging.info(f"Got {len(res)} coins")
        return res

    def get_all_ids(self):
        """
        Get all coin ids on CoinGecko
        """
        ids = self.cg.get_coins_list()
        ids = [[id['id'], id['symbol'].upper()] for id in ids]
        return ids

    def get_coins_with_weekly_volume_increase(self, volume_threshold=1.3):
        """
        Get top 500 market cap coins with weekly volume increase larger than volume_threshold
        """
        self.update_popular_exchanges()
        ids = self.cg.get_coins_markets(vs_currency='usd',
                                        order='market_cap_desc', per_page=250,
                                        page=1, sparkline=False)
        ids += self.cg.get_coins_markets(vs_currency='usd',
                                         order='market_cap_desc', per_page=250,
                                         page=2, sparkline=False)
        ids = [[id['id'], id['symbol'].upper()] for id in ids]

        res = []
        coingeco_coins, coingeco_names, ex = [], [], []

        for i, id in enumerate(ids):
            data = self.cg.get_coin_market_chart_by_id(
                id=id[0], vs_currency='usd', days=13, interval='daily')
            data = np.array(data['total_volumes'])
            if np.sum(data[:7, 1]) == 0:
                continue
            volume_increase = np.sum(data[7:, 1]) / np.sum(data[:7, 1])

            if volume_increase >= volume_threshold:
                res.append([volume_increase, id[1], id[0]])
 
        res = sorted(res, key=lambda x: x[0], reverse=True)

        for volume_increase, symbol, coin_id in res:
            if f"{symbol}USDT" not in self.popular_exchanges and \
                    f"{symbol}BTC" not in self.popular_exchanges and \
                    f"{symbol}ETH" not in self.popular_exchanges and \
                    f"{symbol}BUSD" not in self.popular_exchanges:
                coingeco_coins.append(coin_id)
                coingeco_names.append(symbol)
            else:
                if f"{symbol}USDT" in self.popular_exchanges:
                    ex.append(f"{symbol}USDT")
                elif f"{symbol}BUSD" in self.popular_exchanges:
                    ex.append(f"{symbol}BUSD")
                elif f"{symbol}BTC" in self.popular_exchanges:
                    ex.append(f"{symbol}BTC")
                elif f"{symbol}ETH" in self.popular_exchanges:
                    ex.append(f"{symbol}ETH")

        res = np.array(res)
        l, m1, m2, m3, m4, r = res[:len(res) // 6, :2], res[len(res) // 6: len(res) // 3, :2], \
            res[len(res) // 3: len(res) // 2, :2], res[len(res) // 2: 2 * len(res) // 3, :2], \
            res[2 * len(res) // 3: 5 * len(res) // 6, :2], res[5 * len(res) // 6:, :2]
        self.tg_bot.send_message(f"{datetime.datetime.now()}: "
                                 f"Top 500 coins that has weekly volume increase > 30%:\n {l}")
        self.tg_bot.send_message(f"{m1}")
        self.tg_bot.send_message(f"{m2}")
        self.tg_bot.send_message(f"{m3}")
        self.tg_bot.send_message(f"{m4}")
        self.tg_bot.send_message(f"{r}")
        return ex, coingeco_coins, coingeco_names

    def get_alt_eth_btc_exchanges(self, market_cap_threshold=500):
        """
        Get top threshold market cap alt/ETH and alt/BTC exchanges
        """
        self.update_popular_exchanges()
        ids = self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc',
                                        per_page=market_cap_threshold//2, page=1,
                                        sparkline=False)
        ids += self.cg.get_coins_markets(vs_currency='usd', order='market_cap_desc',
                                         per_page=market_cap_threshold//2, page=2,
                                         sparkline=False)
        ids = [id['symbol'].upper() for id in ids]

        res = []

        for i, id in enumerate(ids):
            if f"{id}ETH" in self.popular_exchanges:
                res.append(f"{id}ETH")
            if f"{id}BTC" in self.popular_exchanges:
                res.append(f"{id}BTC")
        return res


if __name__ == '__main__':
    coin = CoinGecKo(tg_type='TEST')
    # exchanges = coin.get_all_binance_active_exchanges(time_on_binance=34)
    # print(len(exchanges))
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
