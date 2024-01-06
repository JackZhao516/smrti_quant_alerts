import datetime
import pytz
from typing import List, Dict, Set, Union, Tuple, Optional
from collections import defaultdict

import requests
import pandas as pd
from polygon import RESTClient

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import StockSymbol


class StockApi:
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]
    SP_500_SOURCE_URL = Config.API_ENDPOINTS["SP_500_SOURCE_URL"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]

    PWD = Config.PROJECT_DIR

    def __init__(self) -> None:
        self._poly_client = RESTClient(Config.TOKENS["POLYGON_IO_API_KEY"])

    @error_handling("sp500", default_val=[])
    def get_sp_500_list(self) -> List[StockSymbol]:
        """
        Get all stocks in SP 500

        :return: [StockSymbol, ...]
        """
        stock_list = []
        link = self.SP_500_SOURCE_URL
        df = pd.read_html(link, header=0)[0]
        for i, row in df.iterrows():
            stock_list.append(StockSymbol(row["Symbol"], row["Security"], row["GICS Sector"],
                                          row["GICS Sub-Industry"], row["Headquarters Location"],
                                          row["CIK"], row["Founded"], sp500=True))
        return stock_list

    @error_handling("financialmodelingprep", default_val=[])
    def get_nasdaq_list(self) -> List[StockSymbol]:
        """
        Get all stocks in NASDAQ 100

        :return: [StockSymbol, ...]
        """
        api_url = f"{self.FMP_API_URL}available-traded/list?apikey={self.FMP_API_KEY}"
        response = requests.get(api_url, timeout=5)
        response = response.json()

        stock_list = [StockSymbol(stock["symbol"], stock["name"], nasdaq=True) for stock in response
                      if stock["exchangeShortName"] and stock["exchangeShortName"].upper() == "NASDAQ"]

        return stock_list

    @error_handling("polygon", default_val=(None, {}))
    def _get_stocks_close_price_with_given_date(self, date: str, adjusted: bool = True) \
            -> Tuple[str, Dict[StockSymbol, float]]:
        """
        Get stock price with given date

        :param date: date in the format of YYYY-MM-DD
        """
        grouped = []
        while not grouped:
            grouped = self._poly_client.get_grouped_daily_aggs(
                date, adjusted
            )
            date = (datetime.datetime.strptime(date, "%Y-%m-%d") - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        date = (datetime.datetime.strptime(date, "%Y-%m-%d") + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        stock_price = {}
        for g in grouped:
            stock = StockSymbol.get_symbol_object(g.ticker)
            if stock and g.close is not None:
                stock_price[stock] = g.close
        return date, stock_price

    def get_stock_price_change_percentage(
            self, stock_list: List[StockSymbol],
            timeframe_list: Optional[List[str]] = None,
            adjusted: bool = True) -> Dict[StockSymbol, Dict[str, float]]:
        """
        Get adjusted/unadjusted stock price change percentage, 1D, 5D, 1M, 3M, 6M, 1Y, 3Y, 5Y

        :param stock_list: [StockSymbol, ...]
        :param timeframe_list: ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]
        :param adjusted: True/False

        :return: price change percentage. 1 means 1%
                {StockSymbol: {"1D": 0.01, "5D": 0.01, "1M": 0.01, "3M": 0.01,
                "6M": 0.01, "1Y": 0.01, "3Y": 0.01}}
        """
        if not timeframe_list:
            timeframe_list = ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]

        # transform the timeframe_list to number of days
        timeframe_dict = {
            "1D": 1,
            "5D": 5,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "3Y": 365 * 3,
            "5Y": 365 * 5,
        }

        us_eastern = pytz.timezone('US/Eastern')
        # get end date in the format of YYYY-MM-DD
        end_date = datetime.datetime.now(tz=us_eastern).strftime("%Y-%m-%d")
        end_date, end_stock_price = self._get_stocks_close_price_with_given_date(end_date, adjusted)

        # calculate the price change percentage
        stock_price_change = defaultdict(dict)
        for timeframe in timeframe_list:
            days = timeframe_dict[timeframe]
            start_date = (datetime.datetime.strptime(end_date, "%Y-%m-%d") -
                          datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            _, start_stock_price = self._get_stocks_close_price_with_given_date(start_date, adjusted)

            for stock in stock_list:
                if stock in start_stock_price and stock in end_stock_price and start_stock_price[stock]:
                    stock_price_change[stock][timeframe] = \
                        (end_stock_price[stock] - start_stock_price[stock]) / start_stock_price[stock] * 100
                else:
                    stock_price_change[stock][timeframe] = 0.0
        return stock_price_change

    @error_handling("financialmodelingprep", default_val=[])
    def get_stock_info(self, stock_list: Union[List[StockSymbol], Set[StockSymbol]]) -> List[StockSymbol]:
        """
        Get stock info, including gics_sector, gics_subsector, etc, ...

        :param stock_list: [StockSymbol, ...] with only ticker, without other info

        :return: [StockSymbol, ...] with all info
        """
        # preprocess the StockSymbol list
        res = []
        stocks = []
        for stock in stock_list:
            if stock.has_stock_info:
                res.append(stock)
            else:
                if stock.ticker_alias:
                    stocks.append(StockSymbol(stock.ticker_alias))
                stocks.append(stock)
        stock_str = ",".join([stock.ticker for stock in stocks])

        api_url = f"{self.FMP_API_URL}profile/{stock_str}?apikey={self.FMP_API_KEY}"
        response = requests.get(api_url, timeout=10)
        response = response.json()

        res += [StockSymbol(stock["symbol"], stock["companyName"], stock["sector"],
                            stock["industry"], f"{stock['city']}, {stock['state']}, {stock['country']}",
                            stock["cik"], stock["ipoDate"])
                for stock in response]
        return res
