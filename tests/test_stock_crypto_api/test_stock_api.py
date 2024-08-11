import unittest
import datetime
import importlib
from unittest import mock

import pandas as pd
import pytz

import smrti_quant_alerts.stock_crypto_api.stock_api
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.stock_crypto_api.utility import get_datetime_now


class MockStock:
    def __init__(self, symbol: str, close: float) -> None:
        self.ticker = symbol
        self.close = close


class TestStockApi(unittest.TestCase):
    def setUp(self) -> None:
        self.stock_api = StockApi()

    def test_get_sp_500_list(self) -> None:
        with mock.patch("pandas.read_html",
                        return_value=[pd.DataFrame({"Symbol": ["AAPL"], "Security": ["Apple Inc."],
                                                    "GICS Sector": ["Information Technology"],
                                                    "GICS Sub-Industry": ["Technology Hardware"],
                                                    "Headquarters Location": ["Cupertino, California"],
                                                    "CIK": ["320193"], "Founded": ["1977"]})]):
            stock_list = self.stock_api.get_sp_500_list()
            self.assertEqual(stock_list, [StockSymbol("AAPL", "Apple Inc.", "Information Technology",
                                                      "Technology Hardware", "Cupertino, California",
                                                      "320193", "1977", sp500=True)])

    def test_get_nasdaq_list(self) -> None:
        with mock.patch("requests.get", return_value=mock.Mock(json=lambda: [{"symbol": "AAPL", "name": "Apple Inc.",
                                                                              "exchangeShortName": "NASDAQ",
                                                                              "type": "stock"}])):
            stock_list = self.stock_api.get_nasdaq_list()
            self.assertEqual(stock_list, [StockSymbol("AAPL", "Apple Inc.", nasdaq=True)])

    def test_get_nyse_list(self) -> None:
        with mock.patch("requests.get", return_value=mock.Mock(json=lambda: [{"symbol": "AAPL", "name": "Apple Inc.",
                                                                              "exchangeShortName": "NYSE",
                                                                              "type": "stock"}])):
            stock_list = self.stock_api.get_nyse_list()
            self.assertEqual(stock_list, [StockSymbol("AAPL", "Apple Inc.", nyse=True)])

    @mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now")
    def test_get_all_stock_price_volume_by_day_delta(self, mock_time_now) -> None:
        mock_time_now.return_value = datetime.datetime(2024, 5, 19, 5, 0, 0)
        return_value = [{"code": "MSFT", "date": "2024-05-17", "adjusted_close": 300,
                         "volume": 180, "exchange_short_name": "US"},
                        {"code": "AAPL", "date": "2024-05-17", "adjusted_close": 100,
                         "volume": 2, "exchange_short_name": "US"}]
        with mock.patch("requests.get", return_value=mock.Mock(json=lambda: return_value, status_code=200)):
            prices, volumes = self.stock_api.get_all_stock_price_volume_by_day_delta(1)
            self.assertEqual(prices, {StockSymbol("MSFT"): 300, StockSymbol("AAPL"): 100})
            self.assertEqual(volumes, {StockSymbol("MSFT"): 180, StockSymbol("AAPL"): 2})

        with mock.patch("requests.get", return_value=Exception):
            prices, volumes = self.stock_api.get_all_stock_price_volume_by_day_delta(1)
            self.assertEqual(prices, {})
            self.assertEqual(volumes, {})

    @mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api.get_datetime_now")
    def test_get_all_stock_price_change_percentage(self, mock_time_now) -> None:
        mock_time_now.return_value = datetime.datetime(2024, 5, 19, 5, 0, 0)
        return_value = {1: ({StockSymbol("MSFT"): 300, StockSymbol("AAPL"): 100, StockSymbol("TEST"): 90}, {}),
                        2: ({StockSymbol("MSFT"): 150, StockSymbol("AAPL"): 100}, {})}
        with mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api."
                        "StockApi.get_all_stock_price_volume_by_day_delta",
                        side_effect=lambda date_delta: return_value[date_delta]):
            stock_price_change_percentage = self.stock_api.get_all_stock_price_change_percentage(["1D"])
            self.assertEqual(stock_price_change_percentage,
                             {StockSymbol("MSFT"): {"1D": 100}, StockSymbol("AAPL"): {"1D": 0},
                              StockSymbol("TEST"): {"1D": 0}})

            for i in [6, 31, 91, 181, 366, 1096, 1826, 3651]:
                return_value[i] = ({StockSymbol("MSFT"): 150, StockSymbol("AAPL"): 100}, {})
            stock_price_change_percentage = self.stock_api.get_all_stock_price_change_percentage()
            self.assertEqual(stock_price_change_percentage,
                             {StockSymbol("MSFT"): {"1D": 100, "5D": 100, "1M": 100, "3M": 100, "6M": 100,
                                                    "1Y": 100, "3Y": 100, "5Y": 100, "10Y": 100},
                              StockSymbol("AAPL"): {"1D": 0, "5D": 0, "1M": 0, "3M": 0, "6M": 0, "1Y": 0,
                                                    "3Y": 0, "5Y": 0, "10Y": 0},
                              StockSymbol("TEST"): {"1D": 0, "5D": 0, "1M": 0, "3M": 0, "6M": 0, "1Y": 0,
                                                    "3Y": 0, "5Y": 0, "10Y": 0}})

    def test_get_stock_info(self) -> None:
        stock_list = [StockSymbol("AAPL", "Apple Inc.", "Information Technology",
                                  "Technology Hardware", "Cupertino, California",
                                  "320193", "1977", sp500=True),
                      StockSymbol("MS.FT", sp500=True)]

        def has_same_info(left: StockSymbol, right: StockSymbol) -> bool:
            return left.security_name == right.security_name and left.gics_sector == right.gics_sector and \
                   left.gics_sub_industry == right.gics_sub_industry and left.location == right.location and \
                   left.cik == right.cik and left.founded_time == right.founded_time and \
                   left.is_sp500 == right.is_sp500 and left.is_nasdaq == right.is_nasdaq and \
                   left.ticker == right.ticker

        with mock.patch("requests.get",
                        return_value=mock.Mock(json=lambda: [{"symbol": "MS.FT", "companyName": "Microsoft",
                                                              "sector": "Information Technology",
                                                              "industry": "Technology Hardware",
                                                              "city": "Redmond",
                                                              "state": "Washington",
                                                              "country": "United States",
                                                              "cik": "789019",
                                                              "ipoDate": "1975"}])):
            stock_info = self.stock_api.get_stock_info(stock_list)
            self.assertTrue(has_same_info(stock_info[0], stock_list[0]))
            self.assertTrue(has_same_info(stock_info[1],
                                          StockSymbol("MS.FT", "Microsoft", "Information Technology",
                                                      "Technology Hardware", "Redmond, Washington, United States",
                                                      "789019", "1975", sp500=True)))

    def test_get_top_market_cap_stocks(self) -> None:
        with mock.patch("requests.get",
                        return_value=mock.Mock(json=lambda: {"data": [{"code": "AAPL", "name": "Apple Inc.",
                                                              "market_capitalization": 2000},
                                                             {"code": "MSFT", "name": "Microsoft",
                                                              "market_capitalization": 1500},
                                                             {"code": "AMZN", "name": "Amazon",
                                                              "market_capitalization": 1000}]})):
            stock_list = self.stock_api.get_top_market_cap_stocks(2)
            self.assertEqual(stock_list, [[StockSymbol("AAPL"), 2000], [StockSymbol("MSFT"), 1500]])
