from typing import Optional, Type
from collections import defaultdict

from .base_data_type import TradingSymbol
from .stock import StockSymbol
from .crypto import BinanceExchange, CoingeckoCoin


def get_class(symbol_type: str) -> Optional[Type[TradingSymbol]]:
    """
    Get the class object for the given symbol type.
    """
    name_class_object_map = defaultdict(None, {"BinanceExchange": BinanceExchange,
                                               "CoingeckoCoin": CoingeckoCoin,
                                               "StockSymbol": StockSymbol,
                                               "TradingSymbol": TradingSymbol})
    return name_class_object_map[symbol_type]
