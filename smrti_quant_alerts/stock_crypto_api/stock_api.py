import datetime
import time
from typing import List, Dict, Set, Optional, Iterable
from collections import defaultdict
from multiprocessing import Lock
from multiprocessing.pool import ThreadPool
from threading import Thread

import requests
import pandas as pd

from smrti_quant_alerts.exception import error_handling
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.stock_crypto_api.utility import get_datetime_now


class StockApi:
    FMP_API_KEY = Config.TOKENS["FMP_API_KEY"]
    IEX_CLOUD_API_KEY = Config.TOKENS["IEX_CLOUD_API_KEY"]
    SP_500_SOURCE_URL = Config.API_ENDPOINTS["SP_500_SOURCE_URL"]
    FMP_API_URL = Config.API_ENDPOINTS["FMP_API_URL"]
    IEX_CLOUD_API_URL = Config.API_ENDPOINTS["IEX_CLOUD_API_URL"]

    PWD = Config.PROJECT_DIR

    timeframe_dict = {
        "1D": 1, "5D": 5, "1M": 30, "3M": 90, "6M": 180, "1Y": 365, "3Y": 365 * 3, "5Y": 365 * 5, "10Y": 365 * 10
    }
    timeframe_dict_reverse = {v: k for k, v in timeframe_dict.items()}

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

    def get_stock_price_change_percentage(
            self, stock_list: List[StockSymbol],
            timeframe_list: Optional[List[str]] = None) -> Dict[StockSymbol, Dict[str, float]]:
        """
        Get adjusted/unadjusted stock price change percentage, 1D, 5D, 1M, 3M, 6M, 1Y, 3Y, 5Y

        :param stock_list: [StockSymbol, ...]
        :param timeframe_list: ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]

        :return: price change percentage. 1 means 1%
                {StockSymbol: {"1D": 0.01, "5D": 0.01, "1M": 0.01, "3M": 0.01,
                "6M": 0.01, "1Y": 0.01, "3Y": 0.01}}
        """
        if not timeframe_list:
            timeframe_list = ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"]
        max_timeframe = timeframe_list[-1].lower()
        timeframe_deltas = {self.timeframe_dict[timeframe] for timeframe in timeframe_list}
        process_list = []
        process_lock = Lock()
        is_running = True
        res = defaultdict(dict)

        @error_handling("iex_cloud", default_val=(None))
        def download_stock_price_list(stocks):
            stock_str = ",".join([stock.ticker for stock in stocks])
            time.sleep(0.3)
            url = f"{self.IEX_CLOUD_API_URL}historical_prices/{stock_str}?" \
                  f"range={max_timeframe}&token={self.IEX_CLOUD_API_KEY}"
            response = requests.get(url, timeout=1000)
            if response.status_code != 200:
                print(response.status_code, response.text, url)
            response = response.json()
            process_lock.acquire()
            process_list.append(response)
            process_lock.release()

        def process_stock_list():
            while is_running or len(process_list) > 0:
                process_lock.acquire()
                if len(process_list) == 0:
                    process_lock.release()
                    time.sleep(0.1)
                    continue
                stocks = process_list.pop(0)
                process_lock.release()

                stock_price_change = defaultdict(dict)
                cur_stock, price_now = None, 0
                cur_stock_prices = []
                yesterday = get_datetime_now() - datetime.timedelta(days=1)
                yesterday_str = yesterday.strftime("%Y-%m-%d")
                timezone = yesterday.tzinfo

                for i, line in enumerate(stocks):
                    stock = StockSymbol.get_symbol_object(line["key"])
                    if stock != cur_stock or i == len(stocks) - 1:
                        if cur_stock:
                            # if cannot find exact date, use the closest date
                            if len(stock_price_change[cur_stock]) != len(timeframe_deltas):
                                time_diff = sorted(list(set(timeframe_deltas) - set(stock_price_change[cur_stock].keys())))
                                stock_price_counter = 0
                                for diff in time_diff:
                                    diff_timeframe = self.timeframe_dict_reverse[diff]
                                    if diff > cur_stock_prices[-1][0]:
                                        stock_price_change[cur_stock][diff_timeframe] = 0
                                        continue
                                    while cur_stock_prices[stock_price_counter][0] < diff:
                                        stock_price_counter += 1
                                    close_price = cur_stock_prices[stock_price_counter][1]
                                    stock_price_change[cur_stock][diff_timeframe] = \
                                        100 * (price_now - close_price) / close_price if close_price else 0
                            cur_stock = None
                        if line["priceDate"] == yesterday_str:
                            cur_stock = stock
                            price_now = line["fclose"]
                            cur_stock_prices = []
                    if stock == cur_stock:
                        if "priceDate" not in line or "fclose" not in line:
                            print(line)
                            continue
                        date = datetime.datetime.strptime(line["priceDate"], "%Y-%m-%d").astimezone(timezone)
                        # if the date is in the timeframe_deltas, get the price change
                        diff_days = (yesterday - date).days
                        if diff_days in timeframe_deltas and line["fclose"]:
                            stock_price_change[stock][self.timeframe_dict_reverse[diff_days]] = \
                                100 * (price_now - line["fclose"]) / line["fclose"] if line["fclose"] else 0
                        cur_stock_prices.append((diff_days, line["fclose"]))
                res.update(stock_price_change)
                time.sleep(0.1)

        # use process pool to get the stock price change percentage
        # cut the stock_list into 4 parts
        process_num = 5
        divide_num = 100

        process_pool = []
        for i in range(2):
            process_pool.append(Thread(target=process_stock_list))
            process_pool[-1].start()

        stock_list = [stock_list[i * len(stock_list) // divide_num: (i + 1) * len(stock_list) // divide_num]
                      for i in range(0, divide_num)]
        with ThreadPool(processes=process_num) as pool:
            pool.map(download_stock_price_list, stock_list)
        pool.close()
        time.sleep(1)
        is_running = False

        print(len(res))
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
        return res


if __name__ == "__main__":
    start = time.time()
    api = StockApi()
    # stock_list = api.get_nasdaq_list()
    # stock_list = api.get_nasdaq_list() + api.get_sp_500_list()
    stock_list = api.get_sp_500_list()
    stock_list = stock_list[:500]

    # print(len(stock_list))

    api.get_stock_price_change_percentage(stock_list, ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y"])

    print(time.time() - start)
