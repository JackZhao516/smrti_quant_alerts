import datetime
from functools import reduce
from multiprocessing.pool import ThreadPool
from typing import List, Dict, Union, Optional, Iterable, Tuple
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

    @error_handling("financialmodelingprep", default_val=[])
    def get_nyse_list(self) -> List[StockSymbol]:
        """
        Get all stocks in NASDAQ 100

        :return: [StockSymbol, ...]
        """
        api_url = f"{self.FMP_API_URL}available-traded/list?apikey={self.FMP_API_KEY}"
        response = requests.get(api_url, timeout=5)
        response = response.json()

        stock_list = [StockSymbol(stock["symbol"], stock["name"], nasdaq=True) for stock in response
                      if stock["exchangeShortName"] and stock["exchangeShortName"].upper() == "NYSE"
                      and stock["type"] and stock["type"] == "stock"]

        return sorted(stock_list, key=lambda x: x.ticker)

    @error_handling("eodhd", default_val=({}, {}))
    def get_all_stock_price_volume_by_day_delta(self, day_delta: int = 0) \
            -> Tuple[Dict[StockSymbol, Decimal], Dict[StockSymbol, Decimal]]:
        """
        Get all stock prices for the <day_delta> day from today

        :param day_delta: int
        :return: {StockSymbol: price}, {StockSymbol: volume}
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

        prices = {}
        volumes = {}
        for stock in response.json():
            if stock.get("code") and stock.get("adjusted_close") and \
                    stock.get("adjusted_close") > 0 and stock.get("volume") > 0 and \
                    stock.get("date") == target_date_str and stock.get("exchange_short_name") == "US":
                prices[StockSymbol(stock["code"].upper())] = Decimal(stock["adjusted_close"])
                volumes[StockSymbol(stock["code"].upper())] = Decimal(stock["volume"])
        return prices, volumes

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

        today_price_dict, _ = self.get_all_stock_price_volume_by_day_delta(1)
        history_price_dicts = {}

        for i, timeframe_delta in enumerate(timeframe_deltas):
            history_price_dicts[timeframe_list[i]], _ = \
                self.get_all_stock_price_volume_by_day_delta(timeframe_delta)

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

    @error_handling("eodhd", default_val={})
    def get_top_market_cap_stocks(self, top_n: int = 100) -> List[List[Union[Decimal, StockSymbol]]]:
        """
        Get top market cap stocks

        :param top_n: int
        :return: [StockSymbol: market_cap]
        """
        res = []
        n = top_n
        last_market_cap = 10 ** 20
        while (n // 1000) + 1 and n > 0:
            cur_market_cap = 0
            offset = 0

            n = n - 1 if n % 1000 == 0 else n
            while n % 1000:
                api_url = f"{self.EODHD_API_URL}screener?api_token={self.EODHD_API_KEY}" \
                          f"&sort=market_capitalization.desc&filters=" \
                          f'[["market_capitalization","<",{last_market_cap}],' \
                          f'["exchange","=","us"]]&limit=100&offset={offset}'
                offset += 100 if n % 100 == 0 else n % 100
                response = requests.get(api_url, timeout=10)
                response = response.json().get("data", [])

                for stock in response:
                    if stock.get("code") and stock.get("market_capitalization"):
                        res.append([StockSymbol(stock["code"].upper()), Decimal(stock["market_capitalization"])])
                        cur_market_cap = stock["market_capitalization"]
                n = max(0, top_n - len(res))
            last_market_cap = cur_market_cap

        return res[:top_n]

    def get_semi_year_stocks_stats(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, Dict[str, str]]:
        """
        Get stock free cash flow, net income, free cash flow margin

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: {"free_cash_flow": Decimal, "net_income": Decimal,
                  "free_cash_flow_margin": Decimal}}
        """
        res = defaultdict(dict)

        @error_handling("financialmodelingprep", default_val=None)
        def get_semi_year_stock_stats(stock: StockSymbol) -> None:
            res[stock] = {"free_cash_flow": "0", "net_income": "0",
                          "free_cash_flow_margin": "0"}
            api_url = f"{self.FMP_API_URL}/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit=2&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if not response:
                return
            revenue, net_income = 0, 0

            for quarter in response:
                revenue += quarter.get("revenue", 0)
                net_income += quarter.get("netIncome", 0)

            api_url = f"{self.FMP_API_URL}/cash-flow-statement/{stock.ticker}?" \
                      f"period=quarter&limit=2&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if not response:
                return
            free_cash_flow = 0
            for quarter in response:
                free_cash_flow += quarter.get("freeCashFlow", 0)

            free_cash_flow_margin = free_cash_flow / revenue if revenue else 0
            res[stock] = {"free_cash_flow": f"{round(free_cash_flow, 4)}", "net_income": f"{round(net_income, 4)}",
                          "free_cash_flow_margin": f"{round(free_cash_flow_margin, 4)}"}

        pool = ThreadPool(8)
        pool.map(get_semi_year_stock_stats, stock_list)
        pool.close()
        pool.join()

        return res

    def get_stocks_revenue_cagr(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, Dict[str, str]]:
        """
        Get revenue CAGR

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: {"revenue_1y_cagr": str, "revenue_3y_cagr": str, "revenue_5y_cagr": str}}
        """
        res = defaultdict(dict)

        @error_handling("financialmodelingprep", default_val=None)
        def get_stock_revenue_cagr(stock: StockSymbol) -> None:
            api_url = f"{self.FMP_API_URL}/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit=24&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            res[stock] = {f"revenue_{i}y_cagr": "0%" for i in [1, 3, 5]}
            if not response:
                return
            revenue_this_year = reduce(lambda a, b: a + b,
                                       [quarter.get("revenue", 0) for quarter in response[:4]])
            if revenue_this_year:
                for i in [1, 3, 5]:
                    quarter_revenue = [quarter.get("revenue", 0) for quarter in response[i * 4:(i + 1) * 4]]
                    revenue = reduce(lambda a, b: a + b, quarter_revenue) if quarter_revenue else 0
                    if revenue == -revenue_this_year:
                        break

                    if revenue != 0:
                        division = (revenue_this_year / revenue) ** (1 / i)
                        if not isinstance(division, complex):
                            cagr_in_percentage = round(100 * (division - 1), 3)
                            res[stock][f"revenue_{i}y_cagr"] = f"{cagr_in_percentage}%"

        pool = ThreadPool(8)
        pool.map(get_stock_revenue_cagr, stock_list)
        pool.close()
        pool.join()

        return res


if __name__ == "__main__":
    stock_api = StockApi()
    revenue_cagr = stock_api.get_stocks_revenue_cagr(stock_list=[StockSymbol("CING")])
    print(revenue_cagr)
