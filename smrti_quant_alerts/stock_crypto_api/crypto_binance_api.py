import time
from decimal import Decimal
from typing import List, Union, Set, Optional, Tuple

from binance.spot import Spot
from binance.um_futures import UMFutures

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, TradingSymbol
from smrti_quant_alerts.stock_crypto_api.utility import read_exclude_coins_from_file, \
    get_date_from_timestamp, get_datetime_now


class BinanceApi:
    PWD = Config.PROJECT_DIR

    # global data
    active_binance_spot_exchanges = []
    active_exchanges_timestamp = 0
    active_binance_spot_exchanges_set = set()

    # timeframe to days
    timeframe_to_days = {"1d": 1, "2d": 2, "3d": 3, "1w": 7, "2w": 14, "1m": 30}

    def __init__(self) -> None:
        self._binance_spot_client = Spot()
        self._binance_futures_client = UMFutures()

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
                    for quote in ["USDT", "FDUSD", "BTC", "ETH"]:
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
                for quote in ["USDT", "FDUSD", "BTC", "ETH"]:
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
        client = self._binance_spot_client if exchange_type == "SPOT" else self._binance_futures_client
        args = {"permissions": ["SPOT"]} if exchange_type == "SPOT" else {}
        response = client.exchange_info(**args)

        binance_exchanges = []
        for exchange in response['symbols']:
            if exchange['status'] == 'TRADING':
                binance_exchanges.append(BinanceExchange(exchange['baseAsset'], exchange['quoteAsset']))
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
        response = self._binance_futures_client.mark_price(symbol=exchange)

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
        response = self._binance_spot_client.ticker_price(symbol=binance_exchange.exchange)

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
        response = self._binance_spot_client.klines(symbol=exchange, interval="1h",
                                                    startTime=start_time, limit=1000)

        prices = [Decimal(i[4]) for i in response][::-1]
        return prices

    def get_all_spot_exchanges_in_usdt_fdusd_btc(self) -> List[BinanceExchange]:
        """
        Get all exchanges in either USDT, FDUSD, or BTC format on binance

        :return: [BinanceExchange, ...]
        """
        self._update_active_binance_spot_exchanges()
        binance_exchanges = set()

        for exchange in self.active_binance_spot_exchanges_set:
            base = exchange.base_symbol
            for quote in ["USDT", "FDUSD", "BTC"]:
                if BinanceExchange(base, quote) in self.active_binance_spot_exchanges_set:
                    binance_exchanges.add(BinanceExchange(base, quote))
                    break

        return list(binance_exchanges)

    @error_handling("binance", default_val=[])
    def get_exchange_close_prices_by_timeframe_num_of_ticks(self, exchange: BinanceExchange, timeframe: str,
                                                            num_of_tick: int = 10) -> List[Tuple[str, float]]:
        """
        Get exchange past close price for the history <timeframe> number of ticks

        :param exchange: BinanceExchange
        :param timeframe: timeframe
        :param num_of_tick: number of ticks

        :return: [close_price, ...] in the order from newest to oldest
        """
        if not exchange:
            return []
        timeframe = timeframe.lower()
        start_time = (int(time.time()) -
                      self.timeframe_to_days[timeframe] * (num_of_tick + 1) * 24 * 60 * 60) * 1000
        binance_timeframe = "1M" if timeframe == "1m" else f"1{timeframe[1]}"

        response = self._binance_spot_client.klines(symbol=exchange, interval=binance_timeframe,
                                                    startTime=start_time, limit=1000)

        return [p for i, p in enumerate([(get_date_from_timestamp(i[0]), float(i[4]))
                for i in response][::-1]) if i % int(timeframe[0]) == 0][:num_of_tick]

    @error_handling("binance", default_val=0)
    def get_exchange_close_price_on_timestamp(self, exchange: BinanceExchange, timestamp: int) -> float:
        """
        Get exchange close price on a specific date time

        :param exchange: BinanceExchange
        :param timestamp: timestamp

        :return: close price
        """
        end_time = timestamp + 60000
        response = self._binance_spot_client.klines(symbol=exchange, interval="1m",
                                                    startTime=timestamp-1, endTime=end_time)
        return float(response[0][4])
