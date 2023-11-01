import logging
import time
import math
import os
import json
import datetime
import pytz
from decimal import Decimal
from multiprocessing.pool import ThreadPool

import requests
import finnhub
import pandas as pd
import numpy as np
from pycoingecko import CoinGeckoAPI

from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, StockSymbol


class GetExchangeList:
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]

    BINANCE_SPOT_API_URL = Config.API_ENDPOINTS["BINANCE_SPOT_API_URL"]
    BINANCE_FUTURES_API_URL = Config.API_ENDPOINTS["BINANCE_FUTURES_API_URL"]
    SP_500_SOURCE_URL = Config.API_ENDPOINTS["SP_500_SOURCE_URL"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]
    FINNHUB_API_KEY = Config.TOKENS["FINNHUB_API_KEY"]

    ALERT_SETTINGS = Config.SETTINGS

    PWD = __file__.split("get_exchange_list.py")[0]

    # global data
    active_binance_spot_exchanges = []
    active_exchanges_timestamp = 0
    active_binance_spot_exchanges_set = set()

    def __init__(self, tg_type="TEST"):
        self._cg = CoinGeckoAPI(api_key=self.COINGECKO_API_KEY)
        self._tg_bot = TelegramBot(alert_type=tg_type)
        self._exclude_coins = set()
        self.finnhub_client = finnhub.Client(api_key=self.FINNHUB_API_KEY)

    def _update_active_binance_spot_exchanges(self):
        """
        Update popular exchanges if last update was more than 1 hour ago
        """
        if (time.time() - self.active_exchanges_timestamp) >= 3600:
            self.active_binance_spot_exchanges = self.get_all_binance_exchanges()
            self.active_binance_spot_exchanges_set = set(self.active_binance_spot_exchanges)
            self.active_exchanges_timestamp = time.time()

    def _reset_timestamp(self):
        """
        Reset timestamp to 0, for testing purpose
        """
        self.active_exchanges_timestamp = 0

    def write_exclude_coins(self, input_exclude_coins):
        """
        write exclude coins to json file

        :param input_exclude_coins: str "xxx, xxx, xxx"
        """
        with open(f"{self.PWD}exclude_coins.json", "r") as f:
            exclude_coins = set(json.load(f))
            exclude_coins.update([coin.strip().upper() for coin in input_exclude_coins.split(",")])
        with open(f"{self.PWD}exclude_coins.json", "w") as f:
            json.dump(list(exclude_coins), f)

    def _get_exclude_coins(self, input_exclude_coins=None):
        """
        expand exclude coins to include all quotes for each base

        :param input_exclude_coins: [BinanceExchange, CoingeckoCoin, ...]
        """
        # process exclude coins from class input
        if input_exclude_coins:
            for coin in input_exclude_coins:
                if isinstance(coin, BinanceExchange):
                    for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                        self._exclude_coins.add(BinanceExchange(coin.base_symbol, quote))
                else:
                    self._exclude_coins.add(coin)

        # process exclude coins from stable coins and json file
        self.get_all_coingecko_coins()
        exclude_coins = set()
        if os.path.exists(f"{self.PWD}stable_coins.json"):
            with open(f"{self.PWD}stable_coins.json", "r") as f:
                exclude_coins.update(json.load(f))

        if os.path.exists(f"{self.PWD}exclude_coins.json"):
            with open(f"{self.PWD}exclude_coins.json", "r") as f:
                exclude_coins.update(json.load(f))

        for coin in exclude_coins:
            coingecok_coin = CoingeckoCoin.get_coingecko_coin(coin)
            if coingecok_coin:
                self._exclude_coins.add(coingecok_coin)
            for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                self._exclude_coins.add(BinanceExchange(coin, quote))

    @error_handling("sp500", default_val=[])
    def get_sp_500_list(self):
        """
        Get all stocks in SP 500

        :return: [StockSymbol, ...]
        """
        stock_list = []
        link = self.SP_500_SOURCE_URL
        df = pd.read_html(link, header=0)[0]
        for i, row in df.iterrows():
            stock_list.append(StockSymbol(row["Symbol"], row["Security"], row["GICS Sector"],
                                          row["GICS Sub-Industry"], row["Headquarters Location"],
                                          row["CIK"], row["Founded"], sp500=True))
        return stock_list

    @error_handling("nasdaq100", default_val=[])
    def get_nasdaq_100_list(self):
        """
        Get all stocks in NASDAQ 100

        :return: [StockSymbol, ...]
        """
        stock_list = []
        api_url = f"{self.FMP_API_URL}nasdaq_constituent?apikey={self.FMP_API_KEY}"

        response = requests.get(api_url, timeout=5)
        response = response.json()
        for stock in response:
            stock_list.append(StockSymbol(stock["symbol"], stock["name"], stock["sector"],
                                          stock["subSector"], stock["headQuarter"],
                                          stock["cik"], stock["founded"], nasdaq100=True))
        return stock_list

    @error_handling("finnhub", default_val=[])
    def get_stock_daily_price_change_percentage(self, stock):
        """
        Get stock daily price change percentage

        :param stock: StockSymbol

        :return: daily price change percentage. 0.01 means 1%
        """

        current_time = datetime.datetime.now(pytz.timezone('US/Eastern'))
        delta = datetime.timedelta(days=1)
        if current_time.hour < 9 or (current_time.hour == 9 and current_time.minute < 30):
            current_time -= delta
        while current_time.weekday() > 4:
            current_time -= delta

        market_data = self.finnhub_client.stock_candles(stock, 'D',
                                                        int((current_time - delta).timestamp()),
                                                        int(current_time.timestamp()))

        if market_data['s'] == 'ok':
            c = market_data['c'][-1]
            o = market_data['o'][-1]
            return (c - o) / o
        else:
            raise Exception(market_data['s'])

    @error_handling("binance", default_val=[])
    def get_all_binance_exchanges(self, exchange_type="SPOT"):
        """
        Get all exchanges on binance, default is SPOT

        :param exchange_type: SPOT or FUTURE
        :return: [BinanceExchange]
        """
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT' \
            if exchange_type == "SPOT" else f'{self.BINANCE_FUTURES_API_URL}exchangeInfo'

        response = requests.get(api_url, timeout=5)
        response = response.json()

        binance_exchanges = []
        for exchange in response['symbols']:
            if exchange['status'] == 'TRADING':
                binance_exchanges.append(BinanceExchange(exchange['baseAsset'], exchange['quoteAsset']))
        return binance_exchanges

    @error_handling("binance", default_val=[])
    def get_popular_quote_binance_spot_exchanges(self):
        """
        BTC, ETH, USDT, BUSD spot binance exchanges

        :return: [BinanceExchange]
        """
        self._update_active_binance_spot_exchanges()
        binance_exchanges = []

        # choose BTC, ETH, USDT, BUSD exchanges
        for exchange in self.active_binance_spot_exchanges:
            if exchange.quote_symbol in {"BTC", "ETH", "USDT", "BUSD"}:
                binance_exchanges.append(exchange)

        return binance_exchanges

    @error_handling("coingecko", default_val=[])
    def get_all_coingecko_coins(self):
        """
        Get all coins on coingecko

        :return: [CoingeckoCoin, ...]
        """
        coingecko_coins = self._cg.get_coins_list()
        return [CoingeckoCoin(coin["id"], coin["symbol"]) for coin in coingecko_coins]

    @error_handling("binance", default_val=0)
    def get_future_exchange_funding_rate(self, exchange):
        """
        Get funding rate of a future exchange

        :param exchange: future exchange
        :return: funding rate
        """
        api_url = f'{self.BINANCE_FUTURES_API_URL}premiumIndex?symbol={exchange}'

        response = requests.get(api_url, timeout=5)
        response = response.json()
        if isinstance(response, dict) and "lastFundingRate" in response and response["lastFundingRate"]:
            return Decimal(response["lastFundingRate"])
        return 0

    @error_handling("coingecko", default_val=[])
    def get_top_n_market_cap_coins(self, n=100):
        """
        get the top n market cap coins on coingecko

        :param n: number of coins to get

        :return: [CoingeckoCoin, ...]
        """
        # coingecko only allows 250 coins per page
        pages = math.ceil(n / 250)

        market_list = []
        for page in range(1, pages + 1):
            market_list += self._cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=250,
                page=page, sparkline=False)
        market_list = market_list[:n]

        seen = set()
        coingecko_coins = []
        for market in market_list:
            if market['id'] not in seen:
                coingecko_coins.append(CoingeckoCoin(market['id'], market['symbol']))
                seen.add(market['id'])

        return coingecko_coins

    @error_handling("coingecko", default_val=[])
    def get_coins_market_info(self, coingecko_coins, market_attribute_name_list):
        """
        get coin market info from coingecko

        :param coingecko_coins: [CoingeckoCoin, ...]
        :param market_attribute_name_list: [market_attribute_name, ...]

        :return: [{"coingecko_coin": CoingeckoCoin, <market_attribute_name>: value, ...}]
        """
        pages = math.ceil(len(coingecko_coins) / 250)
        market_info = []
        for page in range(pages):
            cur_full_info = self._cg.get_coins_markets(
                vs_currency='usd', ids=[coin.coin_id for coin in coingecko_coins[page * 250:(page + 1) * 250]],
                per_page=250, page=1, sparkline=False,
                price_change_percentage='24h', locale='en')

            for info in cur_full_info:
                cur_info = {"coingecko_coin": CoingeckoCoin(info['id'], info['symbol'])}
                for market_attribute_name in market_attribute_name_list:
                    cur_info[market_attribute_name] = info.get(market_attribute_name, None)

                market_info.append(cur_info)

        return market_info

    @error_handling("coingecko", default_val={})
    def get_coin_info(self, coingecko_coin):
        """
        get coin info from coingecko

        :param coingecko_coin: CoingeckoCoin

        :return: {"symbol": .., "name": .., "description": .. , "website:": ..}
        """
        coin_info = self._cg.get_coin_by_id(id=coingecko_coin.coin_id, localization='false',
                                            tickers='false', market_data='false',
                                            community_data='false', developer_data='false',
                                            sparkline='false')

        links = coin_info.get("links", {}).get("homepage", [])
        links = [link for link in links if link.startswith("http")]
        links = "; ".join(links) if links else ""
        return {"symbol": coingecko_coin.coin_symbol, "name": coin_info.get("name", ""),
                "description": coin_info.get("description", "").get("en", ""),
                "website": links, "genesis_date": coin_info.get("genesis_date", "")}

    @error_handling("coingecko", default_val={})
    def get_coin_market_info(self, coingecko_coin, market_attribute_name_list, days, interval="daily"):
        """
        get coin market info from coingecko

        :param coingecko_coin: CoingeckoCoin
        :param market_attribute_name_list: [market_attribute_name, ...]
        :param days: number of days to get
        :param interval: interval of the data

        :return: {<market_attribute_name>: value, ...}
        """
        coin_info = self._cg.get_coin_market_chart_by_id(
            id=coingecko_coin.coin_id, vs_currency='usd', days=days, interval=interval)

        return {market_attribute_name: coin_info.get(market_attribute_name, None)
                for market_attribute_name in market_attribute_name_list}

    @error_handling("coingecko", default_val=[])
    def get_coin_history_hourly_close_price(self, coingecko_coin, days=10):
        """
        Get coin past close price for the history <days> days

        :param coingecko_coin: CoingeckoCoin
        :param days: number of days to get

        :return: [close_price, ...] in the order from newest to oldest
        """
        respond = self._cg.get_coin_market_chart_by_id(id=coingecko_coin.coin_id,
                                                       vs_currency='usd', days=days,
                                                       precision="full")
        prices = respond.get("prices", [])
        prices = [Decimal(i[1]) for i in prices][::-1]

        return prices

    @error_handling("coingecko", default_val=0)
    def get_coin_current_price(self, coingecko_coin):
        """
        Get coin current close price

        :param coingecko_coin: CoingeckoCoin

        :return: close_price
        """
        respond = self._cg.get_price(ids=coingecko_coin.coin_id, vs_currencies='usd', precision='full')
        price = respond.get(coingecko_coin.coin_id, {}).get('usd', 0)
        return Decimal(price)

    @error_handling("binance", default_val=0)
    def get_exchange_current_price(self, binance_exchange):
        """
        Get exchange current close price

        :param binance_exchange: BinanceExchange

        :return: close_price
        """
        api_url = f'{self.BINANCE_SPOT_API_URL}ticker/price?symbol={binance_exchange.exchange}'
        response = requests.get(api_url, timeout=5)
        response = response.json()
        if isinstance(response, dict):
            return Decimal(response.get("price", 0))
        else:
            return Decimal(response[0].get("price", 0))

    @error_handling("binance", default_val=[])
    def get_exchange_history_hourly_close_price(self, exchange, days=10):
        """
        Get exchange past close price for the history <days> days

        :param exchange: BinanceExchange
        :param days: number of days to get

        :return: [close_price, ...] in the order from newest to oldest
        """
        start_time = (int(time.time()) - days * 24 * 60 * 60) * 1000
        api_url = f'{self.BINANCE_SPOT_API_URL}klines?symbol={exchange.exchange}' \
                  f'&interval=1h&startTime={start_time}&limit=1000'
        response = requests.get(api_url, timeout=5)
        response = response.json()
        prices = [Decimal(i[4]) for i in response][::-1]
        return prices

    @error_handling("coingecko", default_val=([], []))
    def get_2023_coins_with_daily_volume_threshold(self, threshold=3000000):
        """
        Get all coins with 24h volume larger than threshold (in USD)
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [BinanceExchange, ...]
        if not on binance, get coin_id, and coin_name from coingeco:
            [CoingeckoCoin, ...]
        :param threshold: threshold of 24h volume in USD

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()
        coins = self.get_all_coingecko_coins()

        # pagination by 250
        pages = math.ceil(len(coins) / 250)
        coingecko_coins = []
        binance_exchanges = []
        
        quotes = ['USDT', 'BUSD', 'BTC', 'ETH']

        for page in range(pages):
            cur_coins_info = self._cg.get_coins_markets(
                vs_currency='usd', ids=[coin.coin_id for coin in coins[page * 250:(page + 1) * 250]],
                per_page=250, page=1)

            for info in cur_coins_info:
                symbol = info['symbol']
                coin = CoingeckoCoin(info['id'], info['symbol'].upper())
                if 'atl_date' not in info or not info['atl_date'] \
                        or 'ath_date' not in info or not info['ath_date']:
                    continue
                atl_year = int(info['atl_date'][:4])
                ath_year = int(info['ath_date'][:4])
                if atl_year < 2023 or ath_year < 2023:
                    continue

                if info['total_volume'] and int(info['total_volume']) > threshold:
                    genesis_date = self.get_coin_info(coin)['genesis_date']
                    if not genesis_date or genesis_date and int(genesis_date[:4]) >= 2023:
                        binance_coin = False
                        for quote in quotes:
                            exchange = BinanceExchange(symbol, quote)
                            if exchange in self.active_binance_spot_exchanges_set:
                                binance_exchanges.append(BinanceExchange(symbol, quote))
                                binance_coin = True
                        if not binance_coin:
                            coingecko_coins.append(coin)

        return binance_exchanges, coingecko_coins

    def get_top_market_cap_coins_with_volume_threshold(self, num=300, daily_volume_threshold=None,
                                                       weekly_volume_threshold=None, tg_alert=False):
        """
        get the top <num> market cap
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [BinanceExchange, ...]
        if not on binance, get coin_id, and coin_name from coingeco:
            [CoingeckoCoin, ...]
        if volume_threshold is not None, all the coins should have weekly
           volume larger than threshold

        :param num: number of exchanges to get
        :param daily_volume_threshold: threshold of daily volume in USD
        :param weekly_volume_threshold: threshold of weekly volume in USD
        :param tg_alert: whether to send telegram alert

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()

        binance_exchanges = []
        coingeco_coins = []

        market_list = self.get_top_n_market_cap_coins(n=num)

        def filter_coin(coin):
            if weekly_volume_threshold or daily_volume_threshold:
                # get weekly volume
                data = self.get_coin_market_info(coin, ["total_volumes"], days=7, interval='daily')
                weekly_volume = np.sum(np.array(data.get('total_volumes', [])))
                daily_volume = data.get('total_volumes', [[0, 0]])[-1][1]
                if weekly_volume_threshold and weekly_volume < weekly_volume_threshold or \
                        daily_volume_threshold and daily_volume < daily_volume_threshold:
                    return

            symbol = coin.coin_symbol
            if f"{symbol}USDT" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BTC" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}ETH" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BUSD" not in self.active_binance_spot_exchanges_set:
                coingeco_coins.append(CoingeckoCoin(coin.coin_id, symbol))
            else:
                if f"{symbol}USDT" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "USDT"))
                elif f"{symbol}BUSD" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "BUSD"))
                if f"{symbol}BTC" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "BTC"))
                if f"{symbol}ETH" in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, "ETH"))

        pool = ThreadPool(6)
        pool.map(filter_coin, market_list)
        pool.close()

        if tg_alert:
            self._tg_bot.send_message(f"Top {num} coins that are not on Binance:\n {coingeco_coins}\n"
                                      f"Top {num} coin exchanges that are on Binance:\n {binance_exchanges}")
        return binance_exchanges, coingeco_coins
        
    def get_all_spot_exchanges_in_usdt_busd_btc(self):
        """
        Get all exchanges in either USDT, BUSD, or BTC format on binance

        :return: [BinanceExchange, ...]
        """
        self._update_active_binance_spot_exchanges()
        binance_exchanges = set()

        for exchange in self.active_binance_spot_exchanges_set:
            base = exchange.base_symbol
            for quote in ["USDT", "BUSD", "BTC"]:
                if BinanceExchange(base, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchanges.add(BinanceExchange(base, quote))
                    break

        logging.info(f"Got {len(binance_exchanges)} coins in USDT, BUSD, or BTC format")
        return list(binance_exchanges)

    @error_handling("coingecko", default_val=([], []))
    def get_coins_with_weekly_volume_increase(self, volume_threshold=1.3, num=500, tg_alert=False):
        """
        Get top <num> market cap coins with weekly volume increase larger than volume_threshold
        for alt/btc, alt/eth, ignore the volume increase threshold

        After the filtering,
        if a coin exchange is on binance, put its exchange name into [BinanceExchange, ...]
        if a coin exchange is not on binance, put its coin_id and coin_name from coingeco
        into [CoingeckoCoin, ...]

        :param volume_threshold: weekly volume increase threshold
        :param num: top <num> market cap coins
        :param tg_alert: whether to send telegram alert

        :return: [BinanceExchange, ...], [CoingeckoCoin, ...]
        """
        self._update_active_binance_spot_exchanges()
        market_list = self.get_top_n_market_cap_coins(num)
        coin_volume_increase_detail = []
        coingeco_coins, binance_exchanges = [], []

        for i, coin in enumerate(market_list):
            symbol = coin.coin_symbol
            coin_id = coin.coin_id
            # add alt/btc, alt/eth exchanges
            for quote in ["BTC", "ETH"]:
                if BinanceExchange(symbol, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchanges.append(BinanceExchange(symbol, quote))

            # get volume increase ratio
            data = self.get_coin_market_info(coin, ["total_volumes"], days=13, interval='daily')

            data = np.array(data['total_volumes'])
            if np.sum(data[:7, 1]) == 0:
                continue
            volume_increase = np.sum(data[7:, 1]) / np.sum(data[:7, 1])

            if volume_increase >= volume_threshold:
                coin_volume_increase_detail.append([volume_increase, symbol, coin_id])
 
        coin_volume_increase_detail = sorted(coin_volume_increase_detail, key=lambda x: x[0], reverse=True)
        for volume_increase, symbol, coin_id in coin_volume_increase_detail:
            binance_exchange = False
            for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                if BinanceExchange(symbol, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchange = True
                    if quote == "USDT" or quote == "BUSD":
                        binance_exchanges.append(BinanceExchange(symbol, quote))
                    break
            if not binance_exchange:
                coingeco_coins.append(CoingeckoCoin(coin_id, symbol))

        # send telegram alert
        if tg_alert:
            for i in range(0, len(coin_volume_increase_detail)):
                coin_volume_increase_detail[i][0] = \
                    f"volume increase: {100 * round(coin_volume_increase_detail[i][0] - 1, 4)}%"
            self._tg_bot.send_message(f"Top 500 coins that has weekly "
                                      f"volume increase > 30%:\n {coin_volume_increase_detail}")

        return binance_exchanges, coingeco_coins


if __name__ == '__main__':
    cg = GetExchangeList(tg_type='TEST')
    res = cg.get_stock_daily_price_change_percentage("AAPL")
    print(res)
