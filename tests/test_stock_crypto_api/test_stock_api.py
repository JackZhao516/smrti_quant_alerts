import unittest
import datetime
import importlib
from unittest import mock

import pandas as pd

import smrti_quant_alerts.stock_crypto_api.stock_api
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.data_type import StockSymbol


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
                                                                              "exchangeShortName": "NASDAQ"}])):
            stock_list = self.stock_api.get_nasdaq_list()
            self.assertEqual(stock_list, [StockSymbol("AAPL", "Apple Inc.", nasdaq=True)])

    # def test_get_all_stock_price_by_day_delta(self) -> None:
    #     with mock.patch("datetime.datetime") as mock_datetime:
    #         mock_datetime.now.return_value = datetime.datetime(2024, 5, 19, 5, 0, 0)
    #         return_value = [{"code": "MSFT", "date": "2024-05-17", "adjusted_close": 300, "volume": 180},
    #                         {"code": "AAPL", "date": "2024-05-16", "adjusted_close": 100, "volume": 0}]
    #         with mock.patch("polygon.RESTClient.get_grouped_daily_aggs",
    #                         side_effect=lambda date, adjusted: return_value[date]):
    #             stock_symbol, stock_price = self.stock_api.get_all_stock_price_by_day_delta(1)
    #             self.assertEqual(stock_symbol, "2024-01-01")
    #             self.assertEqual(stock_price, {"AAPL": 200})
    #
    #         with mock.patch("polygon.RESTClient.get_grouped_daily_aggs",
    #                         return_value=Exception):
    #             stock_symbol, stock_price = self.stock_api._get_stocks_close_price_with_given_date("2024-01-02")
    #             self.assertEqual(stock_symbol, None)
    #             self.assertEqual(stock_price, {})
    #
    # def test_get_all_stock_price_change_percentage(self) -> None:
    #     return_value = {"2024-01-31": ("2024-01-31", {StockSymbol("AAPL"): 200, StockSymbol("MSFT"): 100}),
    #                     "2024-01-30": ("2024-01-30", {StockSymbol("AAPL"): 100, StockSymbol("MSFT"): 100}),
    #                     "2024-01-01": ("2024-01-01", {StockSymbol("AAPL"): 50, StockSymbol("MSFT"): 200})}
    #     with mock.patch("smrti_quant_alerts.stock_crypto_api.utility.get_datetime_now",
    #                     return_value=datetime.datetime(2024, 1, 31, 0, 0, 0, 0)):
    #         with mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api."
    #                         "StockApi._get_stocks_close_price_with_given_date",
    #                         side_effect=lambda date, _: return_value[date]):
    #             importlib.reload(smrti_quant_alerts.stock_crypto_api.stock_api)
    #             stock_price_change_percentage = self.stock_api.get_stock_price_change_percentage(
    #                 [StockSymbol("AAPL"), StockSymbol("MSFT"), StockSymbol("TEST")], ["1D", "1M"]
    #             )
    #             self.assertEqual(stock_price_change_percentage, {StockSymbol("AAPL"): {"1D": 100, "1M": 300},
    #                                                              StockSymbol("MSFT"): {"1D": 0, "1M": -50},
    #                                                              StockSymbol("TEST"): {"1D": 0, "1M": 0}})
    #
    #         with mock.patch("smrti_quant_alerts.stock_crypto_api.stock_api."
    #                         "StockApi._get_stocks_close_price_with_given_date",
    #                         return_value=(None, {})):
    #             importlib.reload(smrti_quant_alerts.stock_crypto_api.stock_api)
    #             stock_price_change_percentage = self.stock_api.get_stock_price_change_percentage(
    #                 [StockSymbol("AAPL"), StockSymbol("MSFT"), StockSymbol("TEST")]
    #             )
    #             self.assertEqual(stock_price_change_percentage, {})

    def test_get_stock_info(self) -> None:
        stock_list = [StockSymbol("AAPL", "Apple Inc.", "Information Technology",
                                  "Technology Hardware", "Cupertino, California",
                                  "320193", "1977", sp500=True),
                      StockSymbol("MSF-T", sp500=True)]

        def has_same_info(left: StockSymbol, right: StockSymbol) -> bool:
            return left.security_name == right.security_name and left.gics_sector == right.gics_sector and \
                   left.gics_sub_industry == right.gics_sub_industry and left.location == right.location and \
                   left.cik == right.cik and left.founded_time == right.founded_time and \
                   left.is_sp500 == right.is_sp500 and left.is_nasdaq == right.is_nasdaq and \
                   left.ticker == right.ticker

        with mock.patch("requests.get",
                        return_value=mock.Mock(json=lambda: [{"symbol": "MSFT", "companyName": "Microsoft",
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
                                          StockSymbol("MSFT", "Microsoft", "Information Technology",
                                                      "Technology Hardware", "Redmond, Washington, United States",
                                                      "789019", "1975", sp500=True)))
