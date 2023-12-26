import math
from typing import List, Dict, Set, Union
from collections import defaultdict

import requests
import pandas as pd

from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import StockSymbol


class StockApi:
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]
    SP_500_SOURCE_URL = Config.API_ENDPOINTS["SP_500_SOURCE_URL"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]

    PWD = Config.PROJECT_DIR

    def __init__(self) -> None:
        pass

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

    @error_handling("financialmodelingprep", default_val=[])
    def get_stock_price_change_percentage(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, Dict[str, float]]:
        """
        Get stock price change percentage, 1D, 5D, 1M, 3M, 6M, 1Y, 3Y, 5Y

        :param stock_list: [StockSymbol, ...]

        :return: price change percentage. 1 means 1%
                {StockSymbol: {"1D": 0.01, "5D": 0.01, "1M": 0.01, "3M": 0.01,
                "6M": 0.01, "1Y": 0.01, "3Y": 0.01}}
        """
        # preprocess the StockSymbol list
        stocks = set(stock_list)
        stock_list = []
        for stock_symbol in stocks:
            stock_list.append(stock_symbol.ticker)
            if stock_symbol.ticker_alias:
                stock_list.append(stock_symbol.ticker_alias)

        responses = []
        step = 1200  # FMP supports 1500 stocks per request
        for i in range(math.ceil(len(stock_list) / step)):
            stock_str = ",".join(stock_list[i * step: (i + 1) * step])

            api_url = f"{self.FMP_API_URL}stock-price-change/{stock_str}?apikey={self.FMP_API_KEY}"

            response = requests.get(api_url, timeout=5)
            responses += response.json()

        stock_price_change = defaultdict(dict)
        for stock in responses:
            stock_symbol = StockSymbol.get_symbol_object(stock["symbol"])
            for key in ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]:
                if key not in stock or not stock[key] or stock[key] > 100000:
                    stock[key] = 0
                stock_price_change[stock_symbol][key] = stock[key]

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
