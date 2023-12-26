import time
from decimal import Decimal
from typing import List, Union, Set, Optional

import requests

from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, TradingSymbol
from .utility import read_exclude_coins_from_file


class BinanceApi:
    BINANCE_SPOT_API_URL = Config.API_ENDPOINTS["BINANCE_SPOT_API_URL"]
    BINANCE_FUTURES_API_URL = Config.API_ENDPOINTS["BINANCE_FUTURES_API_URL"]
    PWD = Config.PROJECT_DIR

    # global data
    active_binance_spot_exchanges = []
    active_exchanges_timestamp = 0
    active_binance_spot_exchanges_set = set()

    def __init__(self) -> None:
        pass

    def _update_active_binance_spot_exchanges(self) -> None:
        """
        Update popular exchanges if last update was more than 1 hour ago
        """
        if (time.time() - self.active_exchanges_timestamp) >= 3600:
            self.active_binance_spot_exchanges = self.get_all_binance_exchanges()
            self.active_binance_spot_exchanges_set = set(self.active_binance_spot_exchanges)
            self.active_exchanges_timestamp = time.time()

    def _reset_timestamp(self) -> None:
        """
        Reset timestamp to 0, for testing purpose
        """
        self.active_exchanges_timestamp = 0

    def get_exclude_coins(
            self, input_exclude_coins: Union[List[TradingSymbol], Set[TradingSymbol], None] = None) \
            -> Set[BinanceExchange]:
        """
        expand exclude coins to include all quotes for each base

        :param input_exclude_coins: [BinanceExchange, CoingeckoCoin, ...]

        :return: [BinanceExchange, ...]
        """
        exclude_coins = set()
        self.get_all_binance_exchanges(exchange_type="SPOT")
        self.get_all_binance_exchanges(exchange_type="FUTURE")
        # process exclude coins from class input
        if input_exclude_coins:
            for coin in input_exclude_coins:
                if isinstance(coin, BinanceExchange):
                    exclude_coins.add(coin)
                elif isinstance(coin, CoingeckoCoin):
                    for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                        binance_exchange = BinanceExchange.get_symbol_object(f"{coin.coin_symbol}{quote}")
                        if binance_exchange:
                            exclude_coins.add(binance_exchange)

        # process exclude coins from stable coins and json file
        exclude_coin_symbols = read_exclude_coins_from_file()

        for coin in exclude_coin_symbols:
            binance_exchange = BinanceExchange.get_symbol_object(coin)
            if binance_exchange:
                exclude_coins.add(binance_exchange)
            else:
                for quote in ["USDT", "BUSD", "BTC", "ETH"]:
                    binance_exchange = BinanceExchange.get_symbol_object(f"{coin}{quote}")
                    if binance_exchange:
                        exclude_coins.add(binance_exchange)
        return exclude_coins

    @error_handling("binance", default_val=[])
    def get_all_binance_exchanges(self, exchange_type: str = "SPOT") -> List[BinanceExchange]:
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
    def get_popular_quote_binance_spot_exchanges(self) -> List[BinanceExchange]:
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

    @error_handling("binance", default_val=Decimal(0))
    def get_future_exchange_funding_rate(self, exchange: Optional[BinanceExchange]) -> Decimal:
        """
        Get funding rate of a future exchange

        :param exchange: future exchange
        :return: funding rate
        """
        if not exchange:
            return Decimal(0)
        api_url = f'{self.BINANCE_FUTURES_API_URL}premiumIndex?symbol={exchange}'

        response = requests.get(api_url, timeout=5)
        response = response.json()
        if isinstance(response, dict) and "lastFundingRate" in response and response["lastFundingRate"]:
            return Decimal(response["lastFundingRate"])
        return Decimal(0)

    @error_handling("binance", default_val=Decimal(0))
    def get_exchange_current_price(self, binance_exchange: Optional[BinanceExchange]) -> Decimal:
        """
        Get exchange current close price

        :param binance_exchange: BinanceExchange

        :return: close_price
        """
        if not binance_exchange:
            return Decimal(0)
        api_url = f'{self.BINANCE_SPOT_API_URL}ticker/price?symbol={binance_exchange.exchange}'
        response = requests.get(api_url, timeout=5)
        response = response.json()
        if isinstance(response, dict):
            return Decimal(response.get("price", 0))
        else:
            return Decimal(response[0].get("price", 0))

    @error_handling("binance", default_val=[])
    def get_exchange_history_hourly_close_price(
            self, exchange: Optional[BinanceExchange], days: int = 10) -> List[Decimal]:
        """
        Get exchange past close price for the history <days> days

        :param exchange: BinanceExchange
        :param days: number of days to get

        :return: [close_price, ...] in the order from newest to oldest
        """
        if not exchange:
            return []
        start_time = (int(time.time()) - days * 24 * 60 * 60) * 1000
        api_url = f'{self.BINANCE_SPOT_API_URL}klines?symbol={exchange.exchange}' \
                  f'&interval=1h&startTime={start_time}&limit=1000'
        response = requests.get(api_url, timeout=5)
        response = response.json()
        prices = [Decimal(i[4]) for i in response][::-1]
        return prices

    def get_all_spot_exchanges_in_usdt_busd_btc(self) -> List[BinanceExchange]:
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

        return list(binance_exchanges)
