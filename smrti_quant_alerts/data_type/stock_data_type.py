from __future__ import annotations

from .base_data_type import TradingSymbol


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
