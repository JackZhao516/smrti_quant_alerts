import datetime
import time
from typing import List, Dict, Set, Optional, Iterable
from decimal import Decimal
from collections import defaultdict


import requests
import pandas as pd

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.stock_crypto_api.utility import get_datetime_now


class StockApi:
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]
    EODHD_API_KEY = Config.TOKENS["EODHD_API_KEY"]
    SP_500_SOURCE_URL = Config.API_ENDPOINTS["SP_500_SOURCE_URL"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]
    EODHD_API_URL = Config.API_ENDPOINTS["EODHD_API_URL"]

    PWD = Config.PROJECT_DIR

    timeframe_dict = {
        "1D": 1, "5D": 5, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5, "10Y": 365 * 10
    }
    timeframe_dict_reverse = {v: k for k, v in timeframe_dict.items()}

    def __init__(self) -> None:
        super().__init__()

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
                      if stock["exchangeShortName"] and stock["exchangeShortName"].upper() == "NASDAQ"
                      and stock["type"] and stock["type"] == "stock"]

        return sorted(stock_list, key=lambda x: x.ticker)

    @error_handling("eodhd", default_val={})
    def get_all_stock_price_by_day_delta(self, day_delta: int = 0) -> Dict[StockSymbol, Decimal]:
        """
        Get all stock prices for the <day_delta> day from today

        :param day_delta: int
        :return: {StockSymbol: price}
        """
        today = get_datetime_now()
        target_date = today - datetime.timedelta(days=day_delta)
        if target_date.weekday() > 4:
            target_date -= datetime.timedelta(days=target_date.weekday() - 4)

        response = None
        target_date_str = target_date.strftime("%Y-%m-%d")
        while response is None or response.status_code != 200 or not response.json():
            target_date_str = target_date.strftime("%Y-%m-%d")
            url = f"{self.EODHD_API_URL}eod-bulk-last-day/US?api_token=" \
                  f"{self.EODHD_API_KEY}&date={target_date_str}&fmt=json"
            response = requests.get(url, timeout=50)
            target_date -= datetime.timedelta(days=1)

        res = {}
        for stock in response.json():
            if stock.get("code") and stock.get("adjusted_close") and \
                    stock.get("adjusted_close") > 0 and stock.get("volume") > 0 and \
                    stock.get("date") == target_date_str and stock.get("exchange_short_name") == "US":
                res[StockSymbol(stock["code"].upper())] = Decimal(stock["adjusted_close"])
        return res

    def get_all_stock_price_change_percentage(
            self, timeframe_list: Optional[List[str]] = None) \
            -> Dict[StockSymbol, Dict[str, Decimal]]:
        """
        Get adjusted stock price change percentage, 1D, 5D, 1M, 3M, 6M, 1Y, 3Y, 5Y

        :param timeframe_list: ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]

        :return: price change percentage. 1 means 1%
                {StockSymbol: {"1D": 0.01, "5D": 0.01, "1M": 0.01, "3M": 0.01,
                "6M": 0.01, "1Y": 0.01, "3Y": 0.01}}
        """
        if not timeframe_list:
            timeframe_list = ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"]

        timeframe_deltas = [self.timeframe_dict[timeframe] + 1 for timeframe in timeframe_list]

        res = defaultdict(dict)

        today_price_dict = self.get_all_stock_price_by_day_delta(1)
        history_price_dicts = {}
        for i, timeframe_delta in enumerate(timeframe_deltas):
            history_price_dicts[timeframe_list[i]] = self.get_all_stock_price_by_day_delta(timeframe_delta)

        # post processing
        for stock, today_price in today_price_dict.items():
            price_change = {}
            for timeframe, history_price_dict in history_price_dicts.items():
                if stock in history_price_dict:
                    price_change[timeframe] = \
                        100 * (today_price - history_price_dict[stock]) / history_price_dict[stock]
                else:
                    price_change[timeframe] = Decimal(0)
            res[stock] = price_change
        return res

    @error_handling("financialmodelingprep", default_val=[])
    def get_stock_info(self, stock_list: Iterable[StockSymbol]) -> List[StockSymbol]:
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

        # preserve the order
        result = []
        for stock in stock_list:
            result.append(res[res.index(stock)])

        return result


if __name__ == "__main__":
    stock_api = StockApi()
    stock_list = stock_api.get_sp_500_list()[:10]
    print(stock_list)

    stock_list = stock_api.get_stock_info(stock_list)
    print(stock_list)