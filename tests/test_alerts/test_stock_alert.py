import unittest
from unittest.mock import patch, ANY

from smrti_quant_alerts.alerts import StockAlert
from smrti_quant_alerts.data_type import StockSymbol


class TestFutureFundingRate(unittest.TestCase):
    def setUp(self) -> None:
        self.alert = StockAlert("TEST", "Stork_Alert", ["1D"])

    # def test_get_sorted_price_increased_stocks(self) -> None:
    #     stock1, stock2, stock3 = StockSymbol("TEST1", "test1"), \
    #         StockSymbol("TEST2", "test2"), StockSymbol("TEST3", "testETF")
    #     with patch.object(StockAlert, "get_sp_500_list", return_value=[stock1]), \
    #         patch.object(StockAlert, "get_nasdaq_list", return_value=[stock2, stock3]), \
    #         patch.object(StockAlert, "get_stock_price_change_percentage", return_value={
    #             stock1: {"1D": 24.098}, stock3: {"1D": 12.162}, stock2: {"1D": -23.234}}):
    #         top_stocks = self.alert.get_sorted_price_increased_stocks()
    #         self.assertEqual(top_stocks, {"1D": [(stock1, 24.098), (stock2, -23.234)]})

    def test_run(self) -> None:
        stock1, stock2 = StockSymbol("TEST1", "test1", "t", "t", "t", "t", "2000", True), \
            StockSymbol("TEST2", "test2", "t", "t", "t", "t", "2000", False, True)
        with patch.object(StockAlert, "get_top_n_price_increased_stocks", return_value={
                "1D": [(stock1, 24.098), (stock2, -23.234)]}), \
                patch.object(StockAlert, "get_stock_info", return_value=[stock1, stock2]):
            with patch.object(self.alert._tg_bot, "send_message") as mock_send_message, \
                    patch.object(self.alert._tg_bot, "send_data_as_csv_file") as mock_send_file:
                self.alert.run()
                mock_send_message.assert_called()
                mock_send_message.assert_called_once_with("Top 20 stocks from SP500 and Nasdaq with the highest "
                                                          "price increase with timeframe 1D: \n"
                                                          "Stock: Price Change Percentage\n"
                                                          "['TEST1: 24.1%', 'TEST2: -23.23%']")
                mock_send_file.assert_called()
                mock_send_file.assert_called_once_with(
                    ANY, headers=["Symbol", "Name", "GICS Sector", "Sub Sector", "Headquarter Location",
                                  "Founded Year/IPO Date", "is SP500", "is Nasdaq"],
                    data=[["TEST1", "test1", "t", "t", "t", "2000", True, False],
                          ["TEST2", "test2", "t", "t", "t", "2000", False, True]])
