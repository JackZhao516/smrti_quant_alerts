from __future__ import annotations
from typing import Optional, Union, List
from collections import defaultdict

from .base_data_type import TradingSymbol, Tick


class ExchangeTick(Tick):
    @property
    def exchange(self) -> BinanceExchange:
        if isinstance(self.symbol, BinanceExchange):
            return self.symbol
        else:
            return BinanceExchange.get_symbol_object(self.symbol.str())


class BinanceExchange(TradingSymbol):
    symbol_base_quote_map = {}
    symbol_base_coingecko_id_map = {}

    def __init__(self, base_symbol: str, quote_symbol: str) -> None:
        self.base_symbol = base_symbol.upper()
        self.quote_symbol = quote_symbol.upper()
        self.symbol_base_quote_map[f"{self.base_symbol}{self.quote_symbol}"] = \
            (self.base_symbol, self.quote_symbol)

        super().__init__(f"{self.base_symbol}{self.quote_symbol}")

    @property
    def exchange(self) -> str:
        return self._symbol

    @staticmethod
    def get_symbol_object(symbol: str) -> Optional[BinanceExchange]:
        if symbol.upper() in BinanceExchange.symbol_base_quote_map:
            base_symbol, quote_symbol = BinanceExchange.symbol_base_quote_map[symbol.upper()]
            return BinanceExchange(base_symbol, quote_symbol)
        return None

    @staticmethod
    def get_coingecko_id_by_base(base: str) -> str:
        return BinanceExchange.symbol_base_coingecko_id_map.get(base.upper(), "")

    @staticmethod
    def add_base_coin_id_pair_to_dict(base: str, coin_id: str) -> None:
        BinanceExchange.symbol_base_coingecko_id_map[base] = coin_id


class CoingeckoCoin(TradingSymbol):
    symbol_id_map = defaultdict(set)

    def __init__(self, coin_id: str, coin_symbol: str) -> None:
        coin_symbol = coin_symbol.upper()

        self.coin_id = coin_id
        super().__init__(coin_symbol)
        self.symbol_id_map[coin_symbol].add(coin_id)

    @property
    def coin_symbol(self) -> str:
        return self._symbol

    @staticmethod
    def get_symbol_object(symbol: str, source: str = "database") \
            -> Union[Optional[CoingeckoCoin], List[CoingeckoCoin]]:
        if source == "database":
            # in database, symbol is stored as "<symbol>&&<coin_id>"
            pos = symbol.index("&&")
            return CoingeckoCoin(symbol[pos + 2:], symbol[:pos])
        elif source == "binance":
            coin_id = BinanceExchange.get_coingecko_id_by_base(symbol)
            if coin_id:
                return CoingeckoCoin(coin_id, symbol)
        else:
            coin_ids = CoingeckoCoin.symbol_id_map[symbol.upper()]
            if len(coin_ids) == 1:
                return CoingeckoCoin(list(coin_ids)[0], symbol)
            elif len(coin_ids) > 1:
                return [CoingeckoCoin(coin_id, symbol) for coin_id in coin_ids]
        return None

    def __eq__(self, other: Union[str, CoingeckoCoin]) -> bool:
        if isinstance(other, CoingeckoCoin):
            return self._symbol == other._symbol and self.coin_id == other.coin_id
        elif isinstance(other, str):
            return self._symbol == other.upper()
        return False

    def db_repr(self) -> str:
        return self._symbol + "&&" + self.coin_id

    def __hash__(self) -> int:
        return hash(self._symbol + self.coin_id)
