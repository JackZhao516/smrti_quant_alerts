import unittest

from smrti_quant_alerts.data_type import StockSymbol


class TestStockSymbol(unittest.TestCase):
    def test_ticker(self) -> None:
        symbol = StockSymbol("AAPL")
        self.assertEqual(symbol.ticker, "AAPL")

    def test_get_symbol_object(self) -> None:
        symbol = StockSymbol.get_symbol_object("AAPL")
        self.assertEqual(symbol, StockSymbol("AAPL"))
        self.assertEqual(StockSymbol("TSLA"), StockSymbol.get_symbol_object("TSLA"))

    def test_is_sp500(self) -> None:
        symbol = StockSymbol("AAPL")
        self.assertFalse(symbol.is_sp500)
        symbol = StockSymbol("AAPL", sp500=True)
        self.assertTrue(symbol.is_sp500)

    def test_is_nasdaq(self) -> None:
        symbol = StockSymbol("AAPL")
        self.assertFalse(symbol.is_nasdaq)
        symbol = StockSymbol("AAPL", nasdaq=True)
        self.assertTrue(symbol.is_nasdaq)

    def test_has_stock_info(self) -> None:
        symbol = StockSymbol("AAPL")
        self.assertFalse(symbol.has_stock_info)
        symbol = StockSymbol("AAPL", security_name="Apple Inc.", gics_sector="Technology",
                             gics_sub_industry="Technology Hardware, Storage & Peripherals",
                             location="Cupertino, California", cik="0000320193", founded_time="1977")
        self.assertTrue(symbol.has_stock_info)

    def test_ticker_alias(self) -> None:
        symbol = StockSymbol("AAPL")
        self.assertEqual(symbol.ticker_alias, "")
        symbol = StockSymbol("AAPL.", sp500=True)
        self.assertEqual(symbol.ticker_alias, "AAPL-")
        symbol = StockSymbol("AAPL-", sp500=True)
        self.assertEqual(symbol.ticker_alias, "AAPL.")
