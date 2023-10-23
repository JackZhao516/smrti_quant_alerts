import time
from smrti_quant_alerts.get_exchange_list import GetExchangeList


class StockAlert(GetExchangeList):
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
                time.sleep(59)
        stock_price_change.sort(key=lambda x: x[1], reverse=True)
        print(stock_price_change)
        return stock_price_change[:n]

    def run(self):
        """
        This function is used to send daily report of top 10 stocks with the highest price increase
        """
        top_stocks = self.get_daily_top_n_price_increased_stocks(20)
        top_stocks = [f"{stock[0]}: {round(stock[1] * 100, 2)}%" for stock in top_stocks]
        self._tg_bot.send_message("Top 10 stocks from SP500 and Nasdaq100 with the "
                                  "highest price increase in the last 24 hours: \n"
                                  "Stock: Price Change Percentage\n"
                                  f"{top_stocks}")


if __name__ == '__main__':
    stock_alert = StockAlert(tg_type="TEST")
    stock_alert.run()
