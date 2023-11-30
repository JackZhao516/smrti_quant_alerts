import time
import uuid
import csv
import os

from smrti_quant_alerts.get_exchange_list import GetExchangeList


class StockAlert(GetExchangeList):
    if not os.path.exists("run_time_data"):
        os.mkdir("run_time_data")

    def __init__(self, tg_type="TEST", timeframe_list=None):
        super().__init__(tg_type=tg_type)
        self.timeframe_list = [timeframe.upper() for timeframe in timeframe_list] \
            if timeframe_list else None

    def get_top_n_price_increased_stocks(self, n):
        """
        Get the top n stocks with the highest price increase in the last 24 hours

        :return: { time_frame: [(StockSymbol, price_increase_percentage), ...] }

        """
        sp500 = self.get_sp_500_list()
        nasdaq100 = self.get_nasdaq_100_list()
        stocks = sp500 + nasdaq100
        stock_price_change = self.get_stock_price_change_percentage(stocks)

        top_stocks = {}
        for timeframe in self.timeframe_list:
            top_stocks[timeframe] = sorted(stock_price_change.items(),
                                           key=lambda x: x[1][timeframe], reverse=True)[:n]
            top_stocks[timeframe] = [(stock, price_change[timeframe])
                                     for stock, price_change in top_stocks[timeframe]]
        return top_stocks

    def run(self):
        """
        This function is used to send daily report of top 20 stocks with the highest price increase
        """
        n = 20
        top_stocks = self.get_top_n_price_increased_stocks(n)
        top_stocks_set = set()

        for timeframe in self.timeframe_list:
            top_stocks_set.update([stock[0] for stock in top_stocks[timeframe]])
            # send message and stock info file to telegram
            cur_top_stocks = [f"{stock}: {round(price_increase, 2)}%"
                              for stock, price_increase in top_stocks[timeframe]]
            self._tg_bot.send_message(f"Top {n} stocks from SP500 and Nasdaq100 with the "
                                      f"highest price increase with timeframe {timeframe}: \n"
                                      "Stock: Price Change Percentage\n"
                                      f"{cur_top_stocks}")

        time.sleep(10)
        # save stock info to csv file
        top_stocks = sorted(list(top_stocks_set), key=lambda x: x.ticker)
        file_name = f"stock_alert_{uuid.uuid4()}.csv"
        with open(f"run_time_data/{file_name}", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Symbol", "Name", "GICS Sector",
                             "Sub Sector", "Headquarter Location", "Founded Time",
                             "is SP500", "is Nasdaq100"])
            for stock in top_stocks:
                writer.writerow([stock.ticker, stock.security_name, stock.gics_sector,
                                 stock.gics_sub_industry, stock.location,
                                 stock.founded_time, stock.is_sp500, stock.is_nasdaq100])
        self._tg_bot.send_file(f"run_time_data/{file_name}", file_name)
        os.remove(f"run_time_data/{file_name}")


if __name__ == '__main__':
    stock_alert = StockAlert(tg_type="TEST", timeframe_list=["1d", "3m", "1y"])
    stock_alert.run()
