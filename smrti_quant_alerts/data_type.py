from __future__ import annotations
from collections import defaultdict
from typing import Union, Type


class TradingSymbol:
    def __init__(self, symbol: str) -> None:
        self._symbol = symbol.upper()

    def __repr__(self) -> str:
        return self._symbol

    def __str__(self) -> str:
        return self._symbol

    def __eq__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol == other._symbol
        elif isinstance(other, str):
            return self._symbol == other.upper()
        return False

    def __lt__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol < other._symbol
        elif isinstance(other, str):
            return self._symbol < other.upper()
        return False

    def __gt__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol > other._symbol
        elif isinstance(other, str):
            return self._symbol > other.upper()
        return False

    def __le__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol <= other._symbol
        elif isinstance(other, str):
            return self._symbol <= other.upper()
        return False

    def __ge__(self, other: Union[str, TradingSymbol]) -> bool:
        if isinstance(other, self.__class__):
            return self._symbol >= other._symbol
        elif isinstance(other, str):
            return self._symbol >= other.upper()
        return False

    def __hash__(self) -> int:
        return hash(self._symbol)

    def lower(self) -> str:
        return self._symbol.lower()

    def upper(self) -> str:
        return self._symbol

    def str(self) -> str:
        return self._symbol

    @staticmethod
    def get_symbol_object(symbol: str) -> Union[TradingSymbol, None]:
        pass

    @classmethod
    def type(cls) -> str:
        return cls.__name__

    @staticmethod
    def get_class(symbol_type: str) -> Union[Type[TradingSymbol], None]:
        name_class_object_map = defaultdict(None, {"BinanceExchange": BinanceExchange,
                                                   "CoingeckoCoin": CoingeckoCoin,
                                                   "StockSymbol": StockSymbol,
                                                   "TradingSymbol": TradingSymbol})
        return name_class_object_map[symbol_type]


class BinanceExchange(TradingSymbol):
    symbol_base_quote_map = {}

    def __init__(self, base_symbol: str, quote_symbol: str) -> None:
        self.base_symbol = base_symbol.upper()
        self.quote_symbol = quote_symbol.upper()
        self.symbol_base_quote_map[f"{self.base_symbol}{self.quote_symbol}"] = \
            (self.base_symbol, self.quote_symbol)

        super().__init__(f"{self.base_symbol}{self.quote_symbol}")

    @property
    def exchange(self) -> str:
        return self._symbol

    @exchange.setter
    def exchange(self, value: str) -> None:
        self._symbol = value.upper()

    @staticmethod
    def get_symbol_object(symbol: str) -> Union[BinanceExchange, None]:
        if symbol.upper() in BinanceExchange.symbol_base_quote_map:
            base_symbol, quote_symbol = BinanceExchange.symbol_base_quote_map[symbol.upper()]
            return BinanceExchange(base_symbol, quote_symbol)
        return None


class CoingeckoCoin(TradingSymbol):
    symbol_id_map = {}

    def __init__(self, coin_id: str, coin_symbol: str) -> None:
        coin_symbol = coin_symbol.upper()

        self.coin_id = coin_id
        super().__init__(coin_symbol)
        self.symbol_id_map[coin_symbol] = self.coin_id

    @property
    def coin_symbol(self) -> str:
        return self._symbol

    @coin_symbol.setter
    def coin_symbol(self, value: str) -> None:
        self._symbol = value.upper()

    @staticmethod
    def get_symbol_object(symbol: str) -> Union[CoingeckoCoin, None]:
        if symbol.upper() in CoingeckoCoin.symbol_id_map:
            coin_id = CoingeckoCoin.symbol_id_map[symbol.upper()]
            return CoingeckoCoin(coin_id, symbol)
        return None


class StockSymbol(TradingSymbol):
    nasdaq_set = set()
    sp500_set = set()
    symbol_info_map = {}

    def __init__(self, symbol: str, security_name: str = "", gics_sector: str = "",
                 gics_sub_industry: str = "", location: str = "", cik: str = "",
                 founded_time: str = "", sp500: bool = False, nasdaq: bool = False) -> None:
        super().__init__(symbol.upper())

        self.security_name = security_name
        self.gics_sector = gics_sector
        self.gics_sub_industry = gics_sub_industry
        self.location = location
        self.cik = cik
        self.founded_time = founded_time

        if sp500:
            StockSymbol.sp500_set.add(self._symbol)
        if nasdaq:
            StockSymbol.nasdaq_set.add(self._symbol)

        self.symbol_info_map[self._symbol] = self

    @property
    def ticker(self) -> str:
        return self._symbol

    @ticker.setter
    def ticker(self, value: str) -> None:
        self._symbol = value.upper()

    @property
    def ticker_alias(self) -> str:
        if "." in self._symbol:
            return self._symbol.replace(".", "-")
        if "-" in self._symbol:
            return self._symbol.replace("-", ".")
        return ""

    @property
    def is_sp500(self) -> bool:
        return self._symbol in StockSymbol.sp500_set

    @property
    def is_nasdaq(self) -> bool:
        return self._symbol in StockSymbol.nasdaq_set

    @property
    def has_stock_info(self) -> bool:
        return self.security_name and self.gics_sector and self.gics_sub_industry and \
               self.location and self.cik and self.founded_time

    @staticmethod
    def get_symbol_object(symbol: str) -> StockSymbol:
        if symbol.upper() in StockSymbol.symbol_info_map:
            return StockSymbol.symbol_info_map[symbol.upper()]
        return StockSymbol(symbol)


if __name__ == "__main__":
    be = BinanceExchange("BTC", "usdt")
    print(be)
    cc = CoingeckoCoin("bitcoin", "Btc")
    print(cc)
    ss = StockSymbol("AAPL")
    print(ss)
