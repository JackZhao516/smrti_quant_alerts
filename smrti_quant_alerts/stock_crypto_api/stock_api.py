import datetime
import warnings
from functools import reduce
from multiprocessing.pool import ThreadPool
from typing import List, Dict, Union, Optional, Iterable, Tuple
from decimal import Decimal
from collections import defaultdict

import requests
import numpy as np

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.stock_crypto_api.utility import get_datetime_now, get_date_from_timestamp

warnings.filterwarnings('ignore', category=RuntimeWarning)


class StockApi:
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]
    EODHD_API_KEY = Config.TOKENS["EODHD_API_KEY"]
    SEC_API_KEY = Config.TOKENS["SEC_API_KEY"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]
    EODHD_API_URL = Config.API_ENDPOINTS["EODHD_API_URL"]
    SEC_API_URL = Config.API_ENDPOINTS["SEC_API_URL"]

    PWD = Config.PROJECT_DIR

    timeframe_dict = {
        "1D": 1, "5D": 5, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5, "10Y": 365 * 10,
        "d": 1, "w": 7, "m": 30
    }
    timeframe_dict_reverse = {v: k for k, v in timeframe_dict.items()}

    def __init__(self) -> None:
        super().__init__()

    @staticmethod
    def _parse_eodhd_symbol(symbol: StockSymbol) -> str:
        return f"{symbol.ticker}.{symbol.market}"

    @error_handling("sp500", default_val=[])
    def get_sp_500_list(self) -> List[StockSymbol]:
        """
        Get all stocks in SP 500

        :return: [StockSymbol, ...]
        """
        api_url = f"{self.FMP_API_URL}/v3/sp500_constituent?apikey={self.FMP_API_KEY}"
        response = requests.get(api_url, timeout=5)
        response = response.json()

        stock_list = [StockSymbol(stock["symbol"], stock["name"], stock["sector"],
                                  stock["subSector"], stock['headQuarter'], stock["cik"], stock["founded"],
                                  sp500=True) for stock in response
                      if stock["symbol"] and stock["name"]]

        return sorted(stock_list, key=lambda x: x.ticker)

    @error_handling("financialmodelingprep", default_val=[])
    def get_nasdaq_list(self) -> List[StockSymbol]:
        """
        Get all stocks in NASDAQ 100

        :return: [StockSymbol, ...]
        """
        api_url = f"{self.FMP_API_URL}/v3/available-traded/list?apikey={self.FMP_API_KEY}"
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
        api_url = f"{self.FMP_API_URL}/v3/available-traded/list?apikey={self.FMP_API_KEY}"
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
            url = f"{self.EODHD_API_URL}/eod-bulk-last-day/US?api_token=" \
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

        for i in range(len(stocks) // 100 + 1):
            stocks_sub = stocks[i * 100:(i + 1) * 100]
            stock_str = ",".join([stock.ticker for stock in stocks_sub])

            api_url = f"{self.FMP_API_URL}/v3/profile/{stock_str}?apikey={self.FMP_API_KEY}"
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
                api_url = f"{self.EODHD_API_URL}/screener?api_token={self.EODHD_API_KEY}" \
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

    @error_handling("financialmodelingprep", default_val=[])
    def get_top_market_cap_stocks_by_market_cap_threshold(self, market_cap_threshold: int = 10 ** 6) \
            -> List[StockSymbol]:
        """
        Get top market cap stocks by market cap threshold

        :param market_cap_threshold: int

        :return: [StockSymbol, ...]
        """
        all_stocks = self.get_nasdaq_list() + self.get_nyse_list()
        all_stocks = [stock for stock in all_stocks if stock.ticker and len(stock.ticker) < 5]
        res = []
        n = len(all_stocks) // 100 + 1
        for i in range(n):
            symbols = ",".join([stock.ticker for stock in all_stocks[i * 100:(i + 1) * 100]])
            api_url = f"{self.FMP_API_URL}/v3/quote/{symbols}?apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10)
            response = response.json()
            for stock in response:
                if stock.get("marketCap", 0) >= market_cap_threshold:
                    res.append(StockSymbol(stock["symbol"], stock["name"]))

        return res

    @error_handling("financialmodelingprep", default_val={})
    def get_close_price_sma_status(self, stock_list: List[StockSymbol], num_of_days_list: List[int],
                                   timeframes: List[str]) -> Dict[StockSymbol, Dict[str, bool]]:
        """
        Get the mapping for whether the close price is higher than sma
        :param stock_list: [StockSymbol, ...]
        :param num_of_days_list: [int, ...], e.g. [200, 400] for sma200, sma400
        :param timeframes: [str, ...], i.e. ["1min", "5min", "15min", "30min", "1hour", "4hour", "1day"]
        :return: {StockSymbol: {"1min": True, "5min": False, "15min": True, "30min": False}}
        """
        res = defaultdict(dict)
        for stock in stock_list:
            close_price_url = f"{self.FMP_API_URL}/v3/quote-short/{stock}?apikey={self.FMP_API_KEY}"
            response = requests.get(close_price_url, timeout=10).json()
            if not response:
                continue
            close_price = response[0].get("price", 0)

            for num_of_day, timeframe in zip(num_of_days_list, timeframes):
                from_day = get_datetime_now() - datetime.timedelta(days=2)
                sma_url = f"{self.FMP_API_URL}/v3/technical_indicator/{timeframe}/{stock}" \
                          f"?type=sma&period={num_of_day}&apikey={self.FMP_API_KEY}" \
                          f"&from={from_day.strftime('%Y-%m-%d')}"
                response = requests.get(sma_url, timeout=10).json()
                if not response:
                    continue
                sma = response[0].get("sma", 0)

                res[stock][timeframe] = close_price > sma
        return res

    @error_handling("financialmodelingprep", default_val={})
    def get_stocks_market_cap(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, Decimal]:
        """
        Get stock market cap

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: market_cap}
        """
        res = defaultdict(Decimal)
        for stock in stock_list:
            api_url = f"{self.FMP_API_URL}/v3/market-capitalization/{stock.ticker}?apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if response:
                res[stock] = Decimal(response[0].get("marketCap", 0))
        return res

    def get_stocks_stats_by_num_of_timeframe(self, stock_list: List[StockSymbol], timeframe: str, num: int) \
            -> Dict[StockSymbol, List[Dict[str, str]]]:
        """
        Get stock free cash flow, net income, free cash flow margin

        :param stock_list: [StockSymbol, ...]
        :param timeframe: str, "quarter" or "semi" or "annual"
        :param num: int, number of timeframes
        :return: {StockSymbol: {"free_cash_flow": str, "net_income": str,
                  "free_cash_flow_margin": str, "revenue": str,
                  "gross_margin": str, "operating_margin": str}}
        """
        res = defaultdict(list)
        timeframes = {"quarter": 1, "semi": 2, "annual": 4}
        empty_res = [defaultdict(lambda: "0")]

        @error_handling("financialmodelingprep", default_val=None)
        def get_stock_stats_by_num_of_quarter(stock: StockSymbol) -> None:
            api_url = f"{self.FMP_API_URL}/v3/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit={timeframes[timeframe] * num}&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=15).json()
            if not response:
                res[stock] = empty_res * num
                return
            revenues, net_incomes, gross_margins, operating_margins = \
                np.zeros(num), np.zeros(num), np.zeros(num), np.zeros(num)

            for i, quarter in enumerate(response):
                revenues[i // timeframes[timeframe]] += quarter.get("revenue", 0)
                net_incomes[i // timeframes[timeframe]] += quarter.get("netIncome", 0)
                gross_margins[i // timeframes[timeframe]] += quarter.get("grossProfitRatio", 0) * 100
                operating_margins[i // timeframes[timeframe]] += quarter.get("operatingIncomeRatio", 0) * 100

            api_url = f"{self.FMP_API_URL}/v3/cash-flow-statement/{stock.ticker}?" \
                      f"period=quarter&limit={timeframes[timeframe] * num}&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=15).json()
            if not response:
                res[stock] = empty_res * num
                return
            free_cash_flows = np.zeros(num)
            for i, quarter in enumerate(response):
                free_cash_flows[i // timeframes[timeframe]] += quarter.get("freeCashFlow", 0)

            free_cash_flow_margins = free_cash_flows / revenues
            res[stock] = [{"free_cash_flow": f"{round(free_cash_flow, 4)}", "net_income": f"{round(net_income, 4)}",
                          "free_cash_flow_margin": f"{round(free_cash_flow_margin, 4)}",
                           "revenue": f"{round(revenue, 4)}", "gross_margin": f"{round(gross_margin, 4)}",
                           "operating_margin": f"{round(operating_margin, 4)}"}
                          for free_cash_flow, net_income, free_cash_flow_margin,
                          revenue, gross_margin, operating_margin in
                          zip(free_cash_flows, net_incomes, free_cash_flow_margins,
                              revenues, gross_margins, operating_margins)]
        pool = ThreadPool(8)
        pool.map(get_stock_stats_by_num_of_quarter, stock_list)
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
            api_url = f"{self.FMP_API_URL}/v3/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit=24&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=15).json()
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

    @error_handling("eodhd", default_val=[])
    def get_stock_close_prices_by_timeframe_num_of_ticks(
            self, stock: StockSymbol, timeframe: str, num_of_ticks: int) -> List[Tuple[str, float]]:
        """
        Get stock close prices by timeframe and num of ticks

        :param stock: StockSymbol
        :param timeframe: str
        :param num_of_ticks: int
        :return: [(date, close_price), ...], with the newest date first
        """
        timeframe_int = int(timeframe[0])
        timeframe = timeframe.lower()
        from_date = get_datetime_now() - \
            datetime.timedelta(days=2 * (self.timeframe_dict[timeframe[-1]] * num_of_ticks * timeframe_int + 1))
        from_str = from_date.strftime("%Y-%m-%d")
        api_url = f"{self.EODHD_API_URL}/eod/{self._parse_eodhd_symbol(stock)}?api_token={self.EODHD_API_KEY}" \
                  f"&fmt=json&from={from_str}&period={timeframe[-1]}"
        response = requests.get(api_url, timeout=10).json()
        res = [(tick["date"], float(tick["adjusted_close"]))
               for i, tick in enumerate(response[::-1]) if i % timeframe_int == 0][:num_of_ticks]

        # prepend latest close price
        latest_close = self.get_stock_current_close_price(stock)
        if (latest_close[0] != res[0][0] and timeframe[-1] != "m") or latest_close[0][:7] != res[0][0][:7]:
            res.insert(0, latest_close)
        return res

    @error_handling("eodhd", default_val=[])
    def get_stock_current_close_price(self, stock: StockSymbol) -> Tuple[str, float]:
        """
        Get stock current close price

        :param stock: StockSymbol
        :return: (date, close_price)
        """
        api_url = f"{self.EODHD_API_URL}/real-time/{self._parse_eodhd_symbol(stock)}?api_token={self.EODHD_API_KEY}" \
                  f"&fmt=json"
        response = requests.get(api_url, timeout=10).json()
        return get_date_from_timestamp(response["timestamp"] * 1000), float(response["close"])

    @error_handling("financialmodelingprep", default_val=[])
    def get_all_8k_filings_for_today(self) -> List[Dict[str, Union[str, bool]]]:
        """
        Get all 8k filings for today

        :return: [{"title": str, "date": str, "symbol": str, "cik": str,
            "process": bool, "link": str, "hasFinancials": bool}, ...]
        """
        today = get_datetime_now().strftime("%Y-%m-%d")
        api_url = f"{self.FMP_API_URL}/v4/rss_feed_8k?from={today}&to={today}&apikey={self.FMP_API_KEY}&limit=1000"
        page = 0
        res = []
        while True:
            url = f"{api_url}&page={page}"
            response = requests.get(url, timeout=10).json()
            if not response:
                break

            tmp = [filing for filing in response if filing.get("date")[:10] == today]
            res.extend(tmp)
            if len(tmp) != len(response):
                break
            page += 1

        # filter out repeated filings
        symbol_set = set([filing.get("symbol", None) for filing in res])
        if None in symbol_set:
            symbol_set.remove(None)

        filtered_res = []
        for filing in res:
            if filing.get("symbol", None) in symbol_set:
                filtered_res.append(filing)
                symbol_set.remove(filing.get("symbol", None))
        return filtered_res

    @error_handling("secapi", default_val=defaultdict(list))
    def get_outstanding_shares(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, List[Union[str, float]]]:
        """
        Get outstanding shares

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: [period_new, shares_new, period_old, shares_old]}
        """
        res = defaultdict(list)
        for stock in stock_list:
            api_url = f"{self.SEC_API_URL}/float?ticker={stock.ticker}&token={self.SEC_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            data = response.get("data", [])
            if len(data) >= 2:
                for i in range(2):
                    outstanding_shares = data[i].get("float", {}).get("outstandingShares", [])
                    if len(outstanding_shares) == 0:
                        res[stock] = []
                        break
                    res[stock].append(outstanding_shares[0].get("period", ""))
                    res[stock].append(outstanding_shares[0].get("value", 0))
        return res

    @error_handling("financialmodelingprep", default_val=defaultdict(lambda: 0))
    def get_stocks_enterprise_value(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, float]:
        """
        Get enterprise value

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: enterprise_value}
        """
        res = defaultdict(lambda: 0)
        for stock in stock_list:
            api_url = f"{self.FMP_API_URL}/v3/enterprise-value/{stock.ticker}?period=quarter&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if response and len(response) > 0:
                res[stock] = response[0].get("enterpriseValue", 0)
        return res

    @error_handling("financialmodelingprep", default_val=defaultdict(lambda: 0))
    def get_stocks_revenue(self, stock_list: List[StockSymbol]) -> Dict[StockSymbol, float]:
        """
        Get stock revenue

        :param stock_list: [StockSymbol, ...]
        :return: {StockSymbol: revenue}
        """
        res = defaultdict(lambda: 0)
        for stock in stock_list:
            api_url = f"{self.FMP_API_URL}/v3/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit=1&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if response and len(response) > 0:
                res[stock] = response[0].get("revenue", 0)
        return res

    @error_handling("financialmodelingprep", default_val=defaultdict(dict))
    def get_stocks_growth_score(self, stock_list: List[StockSymbol], full: bool = False) \
            -> Dict[StockSymbol, Dict[str, str]]:
        """
        Get stock growth score
        Growth Score = most 2 recent quarterly revenue YOY growth + avg(2 recent quarterly FCF margin)

        :param stock_list: [StockSymbol, ...]
        :param full: bool, whether to return full stats
        :return: {StockSymbol: {"growth_score": str}}
        """
        res = defaultdict(dict)
        stock_stats = self.get_stocks_stats_by_num_of_timeframe(stock_list, "quarter", 6)
        for stock, stats in stock_stats.items():
            res[stock]["growth_score"] = "0"
            if stats and len(stats) == 6 and float(stats[4]["revenue"]) > 0 and float(stats[5]["revenue"]) > 0:
                revenue_yoy_growth_0 = (float(stats[0]["revenue"]) / float(stats[4]["revenue"]) - 1) * 100
                revenue_yoy_growth_1 = (float(stats[1]["revenue"]) / float(stats[5]["revenue"]) - 1) * 100
                revenue_yoy_sum = revenue_yoy_growth_0 + revenue_yoy_growth_1
                fcf_margin_0 = float(stats[0]["free_cash_flow_margin"]) * 100
                fcf_margin_1 = float(stats[1]["free_cash_flow_margin"]) * 100
                avg_fcf_margin = (fcf_margin_0 + fcf_margin_1) / 2
                growth_score = str(revenue_yoy_growth_0 + revenue_yoy_growth_1 + avg_fcf_margin)

                res[stock]["growth_score"] = growth_score if growth_score != "inf" else "0"
                if full:
                    res[stock]["revenue_yoy_growth_latest"] = f"{revenue_yoy_growth_0:.2f}%"
                    res[stock]["revenue_yoy_growth_second_latest"] = f"{revenue_yoy_growth_1:.2f}%"
                    res[stock]["revenue_yoy_growth_sum"] = f"{revenue_yoy_sum:.2f}%"
                    res[stock]["fcf_margin_latest"] = f"{fcf_margin_0:.2f}%"
                    res[stock]["fcf_margin_second_latest"] = f"{fcf_margin_1:.2f}%"
                    res[stock]["fcf_margin_avg"] = f"{avg_fcf_margin:.2f}%"

        return res

    @error_handling("financialmodelingprep", default_val=defaultdict(list))
    def get_stocks_quarterly_revenue_yoy_growth(self, stock_list: List[StockSymbol], num_of_quarters: int) \
            -> Dict[StockSymbol, List[str]]:
        """
        Get stock quarterly revenue growth

        :param stock_list: [StockSymbol, ...]
        :param num_of_quarters: int
        :return: {StockSymbol: ["<revenue_growth>", ...]}
        """
        res = defaultdict(list)
        for stock in stock_list:
            res[stock] = [0] * num_of_quarters
            api_url = f"{self.FMP_API_URL}/v3/income-statement/{stock.ticker}?" \
                      f"period=quarter&limit={num_of_quarters * 2}&apikey={self.FMP_API_KEY}"
            response = requests.get(api_url, timeout=10).json()
            if not response:
                continue
            revenues = [quarter.get("revenue", 0) for quarter in response]
            if len(revenues) < num_of_quarters * 2:
                continue
            for i in range(num_of_quarters):
                if revenues[i + num_of_quarters] == 0:
                    break
                revenue_growth = (revenues[i] / revenues[i + num_of_quarters] - 1) * 100
                res[stock][i] = f"{revenue_growth:.2f}"

        return res


if __name__ == "__main__":
    stock_api = StockApi()
    #
    # top_market_cap_stocks = stock_api.get_top_market_cap_stocks_by_market_cap_threshold(10 ** 6)
    # print(len(top_market_cap_stocks))
    #
    # revenue_growth = stock_api.get_stocks_quarterly_revenue_yoy_growth([StockSymbol("HOOD")], 8)
    # print(revenue_growth)

    stock_stats = stock_api.get_stocks_stats_by_num_of_timeframe([StockSymbol("PGR")], "quarter", 8)
    print(stock_stats)

    # growth_score = stock_api.get_stocks_growth_score([StockSymbol("NYC")], full=True)
    # print(growth_score)

