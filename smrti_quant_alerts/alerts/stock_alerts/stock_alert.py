import time
import uuid
import csv
import os
from decimal import Decimal
from typing import List, Dict, Tuple, Optional

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.data_type import StockSymbol
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.db import init_database_runtime, close_database, StockAlertDBUtils


class StockAlert(BaseAlert, StockApi):
    def __init__(self, alert_name: str, tg_type: str = "TEST",
                 timeframe_list: Optional[List[str]] = None,
                 email: bool = True) -> None:
        """
        StockAlert class for sending
        :param alert_name: alert name
        :param tg_type: telegram type
        :param timeframe_list: list of timeframe
        :param email: whether to send email
        """
        BaseAlert.__init__(self, tg_type=tg_type)
        StockApi.__init__(self)
        self._alert_name = alert_name
        self._timeframe_list = [timeframe.upper() for timeframe in timeframe_list] \
            if timeframe_list else ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]
        self._send_email = email
        self._email_api = EmailApi()

    def send_stocks_info_as_csv(self, stocks: List[StockSymbol],
                                is_newly_added_dict: Dict[StockSymbol, bool], email_message: str) -> None:
        """
        Send stock info as csv file

        :param stocks: [StockSymbol, ...]
        :param is_newly_added_dict: {StockSymbol: is_newly_added, ...}
        :param email_message: email message
        """
        file_name = f"stock_alert_{uuid.uuid4()}.csv"
        header = ["Symbol", "Name", "GICS Sector", "Sub Sector", "Headquarter Location",
                  "Founded Year/IPO Date", "is SP500", "is Nasdaq", "Is Newly Added"]
        stock_info = [[stock.ticker, stock.security_name, stock.gics_sector,
                       stock.gics_sub_industry, stock.location,
                       stock.founded_time, stock.is_sp500, stock.is_nasdaq, is_newly_added_dict[stock]]
                      for stock in stocks]

        self._tg_bot.send_data_as_csv_file(file_name, headers=header, data=stock_info)
        if self._send_email:
            with open(file_name, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(header)
                writer.writerows(stock_info)
            self._email_api.send_email("Weekly Stock Alert", email_message, file_name)
            if os.path.exists(file_name):
                os.remove(file_name)

    def get_sorted_price_increased_stocks(self) -> Dict[str, List[Tuple[StockSymbol, Decimal]]]:
        """
        Get the top n stocks with the highest price increase in the last 24 hours

        :param n: top n stocks

        :return: { time_frame: [(StockSymbol, price_increase_percentage), ...] }

        """
        stock_price_change = self.get_all_stock_price_change_percentage(self._timeframe_list)

        top_stocks = {}
        for timeframe in self._timeframe_list:
            top_stocks[timeframe] = sorted(stock_price_change.items(),
                                           key=lambda x: x[1][timeframe], reverse=True)
            top_stocks[timeframe] = [(stock, price_change[timeframe])
                                     for stock, price_change in top_stocks[timeframe]]
        return top_stocks

    def get_top_n_non_etf_stocks(self, n: int, top_stocks: Dict[str, List[Tuple[StockSymbol, Decimal]]]) \
            -> Dict[str, List[Tuple[StockSymbol, Decimal]]]:
        """
        Get top n non-ETF stocks

        :param n: top n
        :param top_stocks: { time_frame: [(StockSymbol, price_increase_percentage), ...] }

        :return: [StockSymbol, ...]
        """
        self.get_nasdaq_list()
        self.get_sp_500_list()
        for timeframe in self._timeframe_list:
            cur_top_stocks = []
            sp500_nasdaq_stocks = []
            for i in range(0, len(top_stocks[timeframe])):
                if top_stocks[timeframe][i][0].is_sp500 or top_stocks[timeframe][i][0].is_nasdaq:
                    sp500_nasdaq_stocks.append(top_stocks[timeframe][i])
            for i in range(0, len(sp500_nasdaq_stocks), 40):
                stocks_price_increase = sp500_nasdaq_stocks[i:i + 40]
                stocks = {stock: percentage for stock, percentage in stocks_price_increase}
                stock_info = self.get_stock_info(stocks.keys())
                cur_top_stocks.extend([(stock, stocks[stock]) for stock in stock_info
                                       if " ETF" not in stock.security_name])
                if len(cur_top_stocks) >= n:
                    break
            top_stocks[timeframe] = cur_top_stocks[:n]
        return top_stocks

    def run(self) -> None:
        """
        This function is used to send daily report of top 20 stocks with the highest price increase
        """
        database_name = f"{self.CONFIG.SETTINGS[self._alert_name]['database_name']}.db"
        init_database_runtime(database_name)
        n = 20
        top_stocks = self.get_sorted_price_increased_stocks()
        top_n_stocks = self.get_top_n_non_etf_stocks(n, top_stocks)

        top_stocks_dict = {}

        last_stocks = StockAlertDBUtils.get_stocks()
        email_msg = ""
        for timeframe in self._timeframe_list:
            # send message and stock info file to telegram
            cur_top_stocks = []
            for stock, price_increase in top_n_stocks[timeframe]:
                stock_str = f"{stock.ticker}: {round(price_increase, 2)}%"
                top_stocks_dict[stock] = False
                if stock.ticker not in last_stocks:
                    stock_str = f"{stock_str} (New)"
                    top_stocks_dict[stock] = True
                cur_top_stocks.append(stock_str)
            msg = f"Top {n} stocks from SP500 and Nasdaq with the " \
                  f"highest price increase with timeframe {timeframe}: \n" \
                  "Stock: Price Change Percentage\n" \
                  f"{cur_top_stocks}"
            self._tg_bot.send_message(msg)
            email_msg += msg + "\n\n"

        StockAlertDBUtils.reset_stocks()
        StockAlertDBUtils.add_stocks(top_stocks_dict.keys())

        time.sleep(10)
        # save stock info to csv file
        top_stocks = sorted(top_stocks_dict.keys(), key=lambda x: x.ticker)
        self.send_stocks_info_as_csv(top_stocks, top_stocks_dict, email_msg)
        close_database()


if __name__ == '__main__':
    start = time.time()
    stock_alert = StockAlert("stock_alert", tg_type="TEST", email=True,
                             timeframe_list=["1m", "3m", "6m", "1y", "3y", "5y", "10y"])
    stock_alert.run()
    print(f"Time taken: {round(time.time() - start, 2)} seconds")
