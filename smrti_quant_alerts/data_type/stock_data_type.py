from __future__ import annotations
from typing import Tuple

from .base_data_type import TradingSymbol


class StockSymbol(TradingSymbol):
    nasdaq_set = set()
    sp500_set = set()
    nyse_set = set()
    symbol_info_map = {}

    def __init__(self, symbol: str, security_name: str = "", gics_sector: str = "",
                 gics_sub_industry: str = "", location: str = "", cik: str = "",
                 founded_time: str = "", sp500: bool = False, nasdaq: bool = False,
                 nyse: bool = False) -> None:
        symbol, self.market = StockSymbol.parse_symbol_market(symbol)
        super().__init__(symbol.upper())
        self._security_name = security_name
        self._gics_sector = gics_sector
        self._gics_sub_industry = gics_sub_industry
        self._location = location
        self._cik = cik
        self._founded_time = founded_time
        if symbol in StockSymbol.symbol_info_map and StockSymbol.symbol_info_map[symbol].has_stock_info:
            self.copy(StockSymbol.symbol_info_map[symbol])

        if sp500:
            StockSymbol.sp500_set.add(self._symbol)
        if nasdaq:
            StockSymbol.nasdaq_set.add(self._symbol)
        if nyse:
            StockSymbol.nyse_set.add(self._symbol)

        if self.has_stock_info:
            self.symbol_info_map[self._symbol] = self

    @property
    def ticker(self) -> str:
        return self._symbol

    @property
    def ticker_alias(self) -> str:
        if "." in self._symbol:
            return self._symbol.replace(".", "-")
        if "-" in self._symbol:
            return self._symbol.replace("-", ".")
        return ""

    @property
    def security_name(self) -> str:
        self._refresh()
        return self._security_name

    @property
    def gics_sector(self) -> str:
        self._refresh()
        return self._gics_sector

    @property
    def gics_sub_industry(self) -> str:
        self._refresh()
        return self._gics_sub_industry

    @property
    def location(self) -> str:
        self._refresh()
        return self._location

    @property
    def cik(self) -> str:
        self._refresh()
        return self._cik

    @property
    def founded_time(self) -> str:
        self._refresh()
        return self._founded_time

    @property
    def is_sp500(self) -> bool:
        return self._symbol in StockSymbol.sp500_set

    @property
    def is_nasdaq(self) -> bool:
        return self._symbol in StockSymbol.nasdaq_set

    @property
    def is_nyse(self) -> bool:
        return self._symbol in StockSymbol.nyse_set

    @property
    def has_stock_info(self) -> bool:
        self._refresh()
        return self._security_name != "" and self._gics_sector != "" and self._gics_sub_industry != "" \
            and self._location != "" and self._cik != "" and self._founded_time != ""

    @staticmethod
    def get_symbol_object(symbol: str) -> StockSymbol:
        if symbol.upper() in StockSymbol.symbol_info_map:
            return StockSymbol.symbol_info_map[symbol.upper()]
        return StockSymbol(symbol)

    @staticmethod
    def parse_symbol_market(symbol: str) -> Tuple[str, str]:
        if "@" in symbol:
            symbol, market = symbol.split("@")
            return symbol, market
        return symbol, "US"

    def copy(self, stock_symbol: StockSymbol):
        self._security_name = stock_symbol._security_name
        self._gics_sector = stock_symbol._gics_sector
        self._gics_sub_industry = stock_symbol._gics_sub_industry
        self._location = stock_symbol._location
        self._cik = stock_symbol._cik
        self._founded_time = stock_symbol._founded_time
        self.market = stock_symbol.market
        self._symbol = stock_symbol._symbol

    def _refresh(self):
        if self._symbol in StockSymbol.symbol_info_map:
            self.copy(StockSymbol.symbol_info_map[self._symbol])
