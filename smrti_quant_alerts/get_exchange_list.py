import logging
import time
import math
import requests
from decimal import Decimal

import numpy as np
from pycoingecko import CoinGeckoAPI

from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class GetExchangeList:
    COINGECKO_API_KEY = Config.TOKENS["COINGECKO_API_KEY"]
    BINANCE_SPOT_API_URL = "https://api.binance.com/api/v3/"
    BINANCE_FUTURES_API_URL = "https://fapi.binance.com/fapi/v1/"

    def __init__(self, tg_type="TEST", active_binance_spot_exchanges=None):
        self.cg = CoinGeckoAPI(api_key=self.COINGECKO_API_KEY)
        self.tg_bot = TelegramBot(alert_type=tg_type)

        # data
        self.active_binance_spot_exchanges = []
        self.active_exchanges_timestamp = 0
        if active_binance_spot_exchanges is not None:
            self.active_binance_spot_exchanges = active_binance_spot_exchanges
            self.active_exchanges_timestamp = time.time()

        self.active_binance_spot_exchanges_set = set(self.active_binance_spot_exchanges)
        # self.active_binance_spot_exchanges = self.get_all_binance_exchanges()

    def _update_active_binance_spot_exchanges(self):
        """
        Update popular exchanges if last update was more than 1 hour ago
        """
        if (time.time() - self.active_exchanges_timestamp) >= 3600:
            self.active_binance_spot_exchanges = self.get_all_binance_spot_exchanges()
            self.active_binance_spot_exchanges_set = set(self.active_binance_spot_exchanges)
            self.active_exchanges_timestamp = time.time()

    @error_handling("binance", "get_all_binance_spot_exchanges")
    def get_all_binance_spot_exchanges(self):
        """
        Get all exchanges on binance

        :return: [BinanceExchange]
        """
        api_url = f'{self.BINANCE_SPOT_API_URL}exchangeInfo?permissions=SPOT'

        response = requests.get(api_url, timeout=2)
        response = response.json()

        res = []
        for exchange in response['symbols']:
            if exchange['status'] == 'TRADING':
                res.append(BinanceExchange(exchange['baseAsset'], exchange['quoteAsset']))
        return res

    @error_handling("binance", "get_popular_quote_binance_spot_exchanges")
    def get_popular_quote_binance_spot_exchanges(self):
        """
        BTC, ETH, USDT, BUSD spot binance exchanges

        :return: [BinanceExchange]
        """
        self._update_active_binance_spot_exchanges()
        res = []

        # choose BTC, ETH, USDT, BUSD exchanges
        for exchange in self.active_binance_spot_exchanges:
            if exchange.quote_symbol in {"BTC", "ETH", "USDT", "BUSD"}:
                res.append(exchange)

        return res

    @error_handling("binance", "get_all_binance_future_exchanges")
    def get_all_binance_future_exchanges(self):
        """
        Get all future exchanges on binance

        :return: [[exchange, contract_type],...]
        """
        api_url = f'{self.BINANCE_FUTURES_API_URL}exchangeInfo'

        response = requests.get(api_url, timeout=2)
        response = response.json()
        return [[exchange["symbol"], exchange["contractType"]] for exchange in response["symbols"]]

    @error_handling("coingecko", "get_all_coingecko_coins")
    def get_all_coingecko_coins(self):
        """
        Get all coins on coingecko

        :return: [[coin_id, coin_symbol_upper], ...]
        """
        res = self.cg.get_coins_list()
        return [[coin["id"], coin["symbol"].upper()] for coin in res]

    @error_handling("binance", "get_future_exchange_funding_rate")
    def get_future_exchange_funding_rate(self, exchange):
        """
        Get funding rate of a future exchange

        :param exchange: future exchange
        :return: funding rate
        """
        api_url = f'{self.BINANCE_FUTURES_API_URL}premiumIndex?symbol={exchange}'

        response = requests.get(api_url, timeout=2)
        response = response.json()
        return Decimal(response["lastFundingRate"])

    @error_handling("coingecko", "get_top_n_market_cap_coins")
    def get_top_n_market_cap_coins(self, n=100):
        """
        get the top n market cap coins on coingecko

        :param n: number of coins to get

        :return: [(coin_id, coin_symbol_upper), ...]
        """
        # coingecko only allows 250 coins per page
        pages = math.ceil(n / 250)

        market_list = []
        for page in range(1, pages + 1):
            market_list += self.cg.get_coins_markets(
                vs_currency='usd', order='market_cap_desc', per_page=250,
                page=page, sparkline=False)
        market_list = market_list[:n]
        market_list = [(market['id'], market['symbol'].upper()) for market in market_list]

        # remove duplicate coins and maintain the order
        seen = set()
        res = []
        for coin in market_list:
            if coin not in seen:
                res.append(coin)
                seen.add(coin)

        return res

    @error_handling("coingecko", "get_coins_market_info")
    def get_coins_market_info(self, coin_ids, market_attribute_name_list):
        """
        get coin market info from coingecko

        :param coin_ids: [coin_id, ...]
        :param market_attribute_name_list: [market_attribute_name, ...]
        :param order: order of the results

        :return: [{"id": <id>, "symbol": <symbol>, <market_attribute_name>: value, ...}]
        """
        pages = math.ceil(len(coin_ids) / 250)
        market_info = []
        for page in range(pages):
            cur_full_info = self.cg.get_coins_markets(
                vs_currency='usd', ids=coin_ids[page * 250:(page + 1) * 250],
                per_page=250, page=1, sparkline=False,
                price_change_percentage='24h', locale='en')

            for info in cur_full_info:
                cur_info = {"id": info['id'], "symbol": info['symbol'].upper()}
                for market_attribute_name in market_attribute_name_list:
                    cur_info[market_attribute_name] = info[market_attribute_name]

                market_info.append(cur_info)

        return market_info

    @error_handling("coingecko", "get_coins_with_24h_volume_larger_than_threshold")
    def get_coins_with_24h_volume_larger_than_threshold(self, threshold=3000000):
        """
        Get all coins with 24h volume larger than threshold (in USD)
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [exchanges_on_binance]
        if not on binance, get coin_id, and coin_name from coingeco:
            [coin_ids_on_coingeco], [coin_names_on_coingeco]
        :param threshold: threshold of 24h volume in USD

        :return: [exchanges_on_binance], [coin_ids_on_coingeco], [coin_symbols_on_coingeco]
        """
        self._update_active_binance_spot_exchanges()
        coins = self.get_all_coingecko_coins()

        # pagination by 250
        pages = math.ceil(len(coins) / 250)
        coin_ids_on_coingeco = []
        coin_symbols_on_coingeco = []
        binance_exchanges = []
        postfix = ['USDT', 'BUSD', 'BTC', 'ETH']

        for page in range(pages):
            cur_full_info = self.cg.get_coins_markets(
                vs_currency='usd', ids=[coin[0] for coin in coins[page * 250:(page + 1) * 250]],
                per_page=250, page=1)

            for info in cur_full_info:
                coin_id, symbol = info['id'], info['symbol'].upper()
                if info["total_volume"] and int(info['total_volume']) >= threshold:
                    binance_coin = False
                    for pf in postfix:
                        exchange = symbol + pf
                        if exchange in self.active_binance_spot_exchanges_set:
                            binance_exchanges.append(exchange)
                            binance_coin = True
                    if not binance_coin:
                        coin_ids_on_coingeco.append(coin_id)
                        coin_symbols_on_coingeco.append(symbol)

        return binance_exchanges, coin_ids_on_coingeco, coin_symbols_on_coingeco

    @error_handling("coingecko", "get_coin_market_info")
    def get_coin_market_info(self, coin_id, market_attribute_name_list, days, interval="daily"):
        """
        get coin market info from coingecko

        :param coin_id: coin_id
        :param market_attribute_name_list: [market_attribute_name, ...]
        :param days: number of days to get
        :param interval: interval of the data

        :return: [{"id": <id>, "symbol": <symbol>, <market_attribute_name>: value, ...}]
        """
        coin_info = self.cg.get_coin_market_chart_by_id(
            id=coin_id, vs_currency='usd', days=days, interval=interval)

        return {name: coin_info[name] for name in market_attribute_name_list}

    def get_top_market_cap_exchanges(self, num=300, tg_alert=False):
        """
        get the top <num> market cap
        coin/usdt coin/eth coin/busd coin/btc exchanges on binance:
            [exchanges_on_binance]
        if not on binance, get coin_id, and coin_name from coingeco:
            [coin_ids_on_coingeco], [coin_names_on_coingeco]


        :param num: number of exchanges to get
        :param tg_alert: whether to send telegram alert

        :return: [exchanges_on_binance], [coin_ids_on_coingeco], [coin_names_on_coingeco]
        """
        self._update_active_binance_spot_exchanges()

        res = []
        coingeco_coins = []
        coingeco_names = []

        market_list = self.get_top_n_market_cap_coins(n=num)
        for i, coin in enumerate(market_list):
            coin_id, symbol = coin
            if f"{symbol}USDT" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BTC" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}ETH" not in self.active_binance_spot_exchanges_set and \
                    f"{symbol}BUSD" not in self.active_binance_spot_exchanges_set:
                coingeco_coins.append(coin_id)
                coingeco_names.append(symbol)
            else:
                if f"{symbol}USDT" in self.active_binance_spot_exchanges_set:
                    res.append(f"{symbol}USDT")
                elif f"{symbol}BUSD" in self.active_binance_spot_exchanges_set:
                    res.append(f"{symbol}BUSD")
                if f"{symbol}BTC" in self.active_binance_spot_exchanges_set:
                    res.append(f"{symbol}BTC")
                if f"{symbol}ETH" in self.active_binance_spot_exchanges_set:
                    res.append(f"{symbol}ETH")

        if tg_alert:
            self.tg_bot.send_message(f"Top {num} coins that are not on Binance:\n {coingeco_names}\n"
                                     f"Top {num} coin exchanges that are on Binance:\n {res}")

        return res, coingeco_coins, coingeco_names
        
    def get_all_spot_exchanges_in_usdt_busd_btc(self):
        """
        Get all exchanges in either USDT, BUSD, or BTC format on binance

        :return: [exchanges]
        """
        self._update_active_binance_spot_exchanges()
        res = []
        coins = set()
        for i in self.active_binance_spot_exchanges:
            if i[-4:] == "USDT":
                res.append(i)
                coins.add(i[:-4])
        for i in self.active_binance_spot_exchanges:
            if i[-4:] == "BUSD" and i[:-4] not in coins:
                res.append(i)
                coins.add(i[:-4])
        for i in self.active_binance_spot_exchanges:
            if i[-3:] == "BTC" and i[:-3] not in coins:
                res.append(i)
        res = list(set(res))
        logging.info(f"Got {len(res)} coins in USDT, BUSD, or BTC format")
        return res

    @error_handling("coingecko", "get_coins_with_weekly_volume_increase")
    def get_coins_with_weekly_volume_increase(self, volume_threshold=1.3, num=500, tg_alert=False):
        """
        Get top <num> market cap coins with weekly volume increase larger than volume_threshold
        for alt/btc, alt/eth, ignore the volume increase threshold

        After the filtering,
        if a coin exchange is on binance, put its exchange name into [exchanges_on_binance]
        if a coin exchange is not on binance, put its coin_id and coin_name from coingeco
        into [coin_ids_on_coingeco], [coin_names_on_coingeco]

        :param volume_threshold: weekly volume increase threshold
        :param num: top <num> market cap coins
        :param tg_alert: whether to send telegram alert

        :return: [exchanges_on_binance], [coin_ids_on_coingeco], [coin_names_on_coingeco]
        """
        self._update_active_binance_spot_exchanges()
        market_list = self.get_top_n_market_cap_coins(num)

        res = []
        coingeco_coins, coingeco_names, exchange = [], [], []

        for i, coin in enumerate(market_list):
            coin_id, symbol = coin
            # add alt/btc, alt/eth exchanges
            if f"{symbol}BTC" in self.active_binance_spot_exchanges:
                exchange.append(f"{symbol}BTC")
            if f"{symbol}ETH" in self.active_binance_spot_exchanges:
                exchange.append(f"{symbol}ETH")

            # get volume increase ratio
            data = self.get_coin_market_info(coin_id, ["total_volumes"], days=13, interval='daily')

            data = np.array(data['total_volumes'])
            if np.sum(data[:7, 1]) == 0:
                continue
            volume_increase = np.sum(data[7:, 1]) / np.sum(data[:7, 1])

            if volume_increase >= volume_threshold:
                res.append([volume_increase, symbol, coin_id])
 
        res = sorted(res, key=lambda x: x[0], reverse=True)

        for volume_increase, symbol, coin_id in res:
            if f"{symbol}USDT" not in self.active_binance_spot_exchanges and \
                    f"{symbol}BTC" not in self.active_binance_spot_exchanges and \
                    f"{symbol}ETH" not in self.active_binance_spot_exchanges and \
                    f"{symbol}BUSD" not in self.active_binance_spot_exchanges:
                coingeco_coins.append(coin_id)
                coingeco_names.append(symbol)
            else:
                if f"{symbol}USDT" in self.active_binance_spot_exchanges:
                    exchange.append(f"{symbol}USDT")
                elif f"{symbol}BUSD" in self.active_binance_spot_exchanges:
                    exchange.append(f"{symbol}BUSD")

        if tg_alert:
            self.tg_bot.send_message(f"Top 500 coins that has weekly "
                                     f"volume increase > 30%:\n {res}")

        return exchange, coingeco_coins, coingeco_names


if __name__ == '__main__':
    cg = GetExchangeList(tg_type='TEST')
    print(cg.get_popular_quote_binance_spot_exchanges())


