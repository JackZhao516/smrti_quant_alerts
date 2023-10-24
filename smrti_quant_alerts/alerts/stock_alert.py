import time
import uuid
import csv
import os

from smrti_quant_alerts.get_exchange_list import GetExchangeList


class StockAlert(GetExchangeList):
    if not os.path.exists("run_time_data"):
        os.mkdir("run_time_data")

    def __init__(self, tg_type="TEST"):
        super().__init__(tg_type=tg_type)

    def get_daily_top_n_price_increased_stocks(self, n, finnhub_pro=False):
        """
        Get the top n stocks with the highest price increase in the last 24 hours
        """
        sp500 = self.get_sp_500_list()
        nasdaq100 = self.get_nasdaq_100_list()
        stocks = set(sp500 + nasdaq100)

        stock_price_change = []
        counter = 0
        for stock in stocks:
            stock_price_change.append((stock, self.get_stock_daily_price_change_percentage(stock)))
            counter += 1
            if counter % 60 == 0 and not finnhub_pro:
                time.sleep(60)
        stock_price_change.sort(key=lambda x: x[1], reverse=True)
        return stock_price_change[:n]

    def run(self):
        """
        This function is used to send daily report of top 10 stocks with the highest price increase
        """
        n = 20
        top_stocks = self.get_daily_top_n_price_increased_stocks(n)

        # save stock info to csv file
        file_name = f"stock_alert_{uuid.uuid4()}.csv"
        with open(f"run_time_data/{file_name}", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Symbol", "Name", "Price Change Percentage", "GICS Sector",
                             "Sub Sector", "Headquarter Location", "Founded Time",
                             "is SP500", "is Nasdaq100"])
            for stock in top_stocks:
                stock_info = stock[0]
                writer.writerow([stock_info.ticker, stock_info.security_name,
                                 f"{round(stock[1] * 100, 2)}%", stock_info.gics_sector,
                                 stock_info.gics_sub_industry, stock_info.location,
                                 stock_info.founded_time, stock_info.is_sp500, stock_info.is_nasdaq100])

        # send message and stock info file to telegram
        top_stocks = [f"{stock[0]}: {round(stock[1] * 100, 2)}%" for stock in top_stocks]
        self._tg_bot.send_message(f"Top {n} stocks from SP500 and Nasdaq100 with the "
                                  "highest price increase in the last 24 hours: \n"
                                  "Stock: Price Change Percentage\n"
                                  f"{top_stocks}")
        self._tg_bot.send_file(f"run_time_data/{file_name}", file_name)
        os.remove(f"run_time_data/{file_name}")


if __name__ == '__main__':
    stock_alert = StockAlert(tg_type="STOCK")
    stock_alert.run()
