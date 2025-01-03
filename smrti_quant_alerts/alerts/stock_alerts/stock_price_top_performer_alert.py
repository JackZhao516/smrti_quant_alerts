import logging
import time
import uuid
import csv
import os
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.data_type import StockSymbol, FinancialMetricType, FinancialMetricsData
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.llm_api import PerplexityAPI
from smrti_quant_alerts.pdf_api import PDFApi
from smrti_quant_alerts.db import close_database, StockAlertDBUtils

logging.basicConfig(level=logging.INFO)


class StockPriceTopPerformerAlert(BaseAlert, StockApi):
    def __init__(self, alert_name: str, tg_type: str = "TEST",
                 timeframe_list: Optional[List[str]] = None,
                 email: bool = True,
                 time_frame_sma_filter_ai_analysis: bool = False,
                 newly_added_stock_ai_analysis: bool = False,
                 growth_score_filter_ai_analysis: bool = False,
                 daily_volume_threshold: int = 0) -> None:
        """
        StockPriceTopPerformerAlert class for sending
        :param alert_name: alert name
        :param tg_type: telegram type
        :param timeframe_list: list of timeframe
        :param email: whether to send email
        :param time_frame_sma_filter_ai_analysis: whether to send ai analysis for time frame sma filtered stocks
        :param newly_added_stock_ai_analysis: whether to send ai analysis for newly added stocks
        :param growth_score_filter_ai_analysis: whether to send ai analysis for growth score filtered stocks
        :param daily_volume_threshold: daily volume threshold
        """
        BaseAlert.__init__(self, alert_name, tg_type=tg_type)
        StockApi.__init__(self)
        self._timeframe_list = [timeframe.upper() for timeframe in timeframe_list] \
            if timeframe_list else ["1D", "5D", "1M", "3M", "6M", "1Y", "3Y", "5Y"]
        self._daily_volume_threshold = daily_volume_threshold

        self._send_email = email
        self._email_api = EmailApi()

        self._time_frame_sma_filter_ai_analysis = time_frame_sma_filter_ai_analysis
        self._newly_added_stock_ai_analysis = newly_added_stock_ai_analysis
        self._growth_score_filter_ai_analysis = growth_score_filter_ai_analysis

        self._ai_api = PerplexityAPI()
        self._pdf_api = PDFApi()

        self._daily_volume = {}

    def send_stocks_info_as_csv(self, is_newly_added_dict: Dict[StockSymbol, bool],
                                timeframe_stocks_dict: Dict[str, List[StockSymbol]], email_message: str) -> None:
        """
        Send stock info as csv file

        :param is_newly_added_dict: {StockSymbol: is_newly_added, ...}
        :param timeframe_stocks_dict: {timeframe: [StockSymbol, ...]}, in the descending order of price increase
        :param email_message: email message
        """
        # get data to build csv file
        csv_file_name = f"stock_alert_{uuid.uuid4()}.csv"
        header = ["Symbol", "Name", "GICS Sector", "Sub Sector", "Headquarter Location",
                  "Founded Year/IPO Date", "Is SP500", "Is Nasdaq", "Is NYSE",
                  "Is Newly Added", "Timeframe Alerted", "Free Cash Flow", "Net Income",
                  "Free Cash Flow Margin", "Revenue 1Y CAGR", "Revenue 3Y CAGR",
                  "Revenue 5Y CAGR", "One Day Volume", "Market Cap", "Close > 4H SMA200", "Close > 1D SMA200"]
        stocks = sorted(is_newly_added_dict.keys(), key=lambda x: x.ticker)
        stock_stats_list = self.get_stocks_stats_by_num_of_timeframe(stocks, "semi", 1)
        stock_revenue_cagr = self.get_stocks_revenue_cagr(stocks)
        stocks_growth_score = self.get_stocks_growth_score(stocks)
        stock_stats = {}
        for k, v in stock_stats_list.items():
            if len(v) == 0:
                default_data = FinancialMetricsData()
                stock_stats[k] = {FinancialMetricType.FREE_CASH_FLOW: default_data,
                                  FinancialMetricType.NET_INCOME: default_data,
                                  FinancialMetricType.FREE_CASH_FLOW_MARGIN: default_data,
                                  FinancialMetricType.REVENUE: default_data}
            else:
                stock_stats[k] = v[0]
            stock_stats[k].update(stock_revenue_cagr[k])
            stock_stats[k].update(stocks_growth_score[k])

        stock_sma_data = self.get_close_price_sma_status(stocks, [200, 200], ["4hour", "1day"])

        market_caps = self.get_stocks_market_cap(stocks)

        stock_timeframes = defaultdict(list)
        for timeframe, timeframe_stocks in timeframe_stocks_dict.items():
            for stock in timeframe_stocks:
                stock_timeframes[stock].append(timeframe)
        stock_info = [[stock.ticker, stock.security_name, stock.gics_sector,
                       stock.gics_sub_industry, stock.location, stock.founded_time,
                       stock.is_sp500, stock.is_nasdaq, stock.is_nyse,
                       is_newly_added_dict[stock], stock_timeframes[stock],
                       stock_stats[stock][FinancialMetricType.FREE_CASH_FLOW],
                       stock_stats[stock][FinancialMetricType.NET_INCOME],
                       stock_stats[stock][FinancialMetricType.FREE_CASH_FLOW_MARGIN],
                       stock_stats[stock][FinancialMetricType.REVENUE_1Y_CAGR],
                       stock_stats[stock][FinancialMetricType.REVENUE_3Y_CAGR],
                       stock_stats[stock][FinancialMetricType.REVENUE_5Y_CAGR],
                       stock_stats[stock][FinancialMetricType.GROWTH_SCORE],
                       self._daily_volume.get(stock, 0), market_caps[stock],
                       stock_sma_data[stock].get("4hour", "SMA Data Unavailable"),
                       stock_sma_data[stock].get("1day", "SMA Data Unavailable")] for stock in stocks]

        self._tg_bot.send_data_as_csv_file(csv_file_name, headers=header, data=stock_info)

        # send stock ai analysis
        pdf_files = []
        if self._time_frame_sma_filter_ai_analysis:
            pdf_files.append(self.get_stocks_ai_analysis_for_timeframe_sma(
                self.filter_stock_with_timeframe_sma(stock_timeframes, [["1Y", "6M"], ["1Y", "3M"]], stock_sma_data),
                stock_stats))
            self._tg_bot.send_file(pdf_files[-1], "Stock AI Analysis With Timeframe SMA Filter.pdf")

        if self._newly_added_stock_ai_analysis:
            pdf_files.append(self.get_stocks_ai_analysis_for_newly_added(timeframe_stocks_dict, is_newly_added_dict,
                                                                         stock_stats))
            self._tg_bot.send_file(pdf_files[-1], "Newly Added Stock AI Analysis.pdf")

        if self._growth_score_filter_ai_analysis:
            pdf_files.append(self.get_stocks_ai_analysis_for_growth_score(stock_timeframes, stock_stats, 0.8))
            self._tg_bot.send_file(pdf_files[-1], "Stock AI Analysis With Growth Score Filter.pdf")

        # send email
        if self._send_email:
            with open(csv_file_name, "w", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(header)
                writer.writerows(stock_info)
            self._email_api.send_email("Weekly Stock Alert with Daily Volume Threshold: "
                                       f"{self._daily_volume_threshold}",
                                       email_message, [csv_file_name], pdf_files)
            if os.path.exists(csv_file_name):
                os.remove(csv_file_name)
        for pdf_file in pdf_files:
            if os.path.exists(pdf_file):
                os.remove(pdf_file)

    def get_stocks_ai_analysis_for_newly_added(self, timeframe_stocks_dict: Dict[str, List[StockSymbol]],
                                               is_newly_added_dict: Dict[StockSymbol, bool],
                                               stock_stats: Dict[StockSymbol, Dict[str, FinancialMetricsData]]) -> str:
        """
        Send stock ai analysis

        :param timeframe_stocks_dict: {timeframe: [StockSymbol, ...]}, in the descending order of price increase
        :param is_newly_added_dict: {StockSymbol: is_newly_added, ...}
        :param stock_stats: {StockSymbol: {stat_name: stat_value, ...}}
        :return: saved pdf file name
        """
        self._pdf_api.start_new_pdf(f"Newly Added Stock AI Analysis_{uuid.uuid4()}.pdf")
        for timeframe, stocks in timeframe_stocks_dict.items():
            self._pdf_api.append_text(f"Timeframe {timeframe}:")
            for stock in stocks:
                if is_newly_added_dict[stock]:
                    stock_increase_reason = \
                        ["Stock Stats: " + ", ".join([f"{k}: {v}" for k, v in stock_stats[stock].items()])]
                    stock_increase_reason.extend(self._ai_api.
                                                 get_stock_increase_reason(stock, timeframe).strip().split("\n"))
                    self._pdf_api.append_stock_info(stock, stock_increase_reason)
        self._pdf_api.save_pdf()
        return self._pdf_api.file_name

    def get_stocks_ai_analysis_for_timeframe_sma(self, stock_timeframe_dict: Dict[StockSymbol, List[str]],
                                                 stock_stats: Dict[StockSymbol, Dict[str, FinancialMetricsData]]) -> str:
        """
        Send stock ai analysis

        :param stock_timeframe_dict: {StockSymbol: [timeframe, ...]}
        :param stock_stats: {StockSymbol: {stat_name: stat_value, ...}}
        :return: saved pdf file name
        """
        self._pdf_api.start_new_pdf(f"Stock AI Analysis With Timeframe SMA Filter_{uuid.uuid4()}.pdf")
        for stock, timeframes in stock_timeframe_dict.items():
            stock_increase_reason = \
                ["Stock Stats: " + ", ".join([f"{k}: {v}" for k, v in stock_stats[stock].items()]),
                 "Timeframes: " + ", ".join(timeframes)]
            stock_increase_reason.extend(self._ai_api.
                                         get_stock_increase_reason(stock, timeframes).strip().split("\n"))
            self._pdf_api.append_stock_info(stock, stock_increase_reason)
        self._pdf_api.save_pdf()
        return self._pdf_api.file_name

    def get_stocks_ai_analysis_for_growth_score(self, stock_timeframe_dict: Dict[StockSymbol, List[str]],
                                                stock_stats: Dict[StockSymbol, Dict[str, FinancialMetricsData]],
                                                growth_score_threshold: float) -> str:
        """
        Send stock ai analysis based on growth score

        :param stock_timeframe_dict: {StockSymbol: [timeframe, ...]}
        :param stock_stats: {StockSymbol: {stat_name: stat_value, ...}}
        :param growth_score_threshold: growth score threshold
        :return: saved pdf file name
        """
        self._pdf_api.start_new_pdf(f"Stock AI Analysis With Growth Score Filter_{uuid.uuid4()}.pdf")
        sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1][FinancialMetricType.GROWTH_SCORE], reverse=True)
        for stock, stock_stat in sorted_stocks:
            if stock_stat[FinancialMetricType.GROWTH_SCORE] <= growth_score_threshold:
                break

            timeframes = stock_timeframe_dict[stock]
            stock_increase_reason = \
                ["Stock Stats: " + ", ".join([f"{k}: {v}" for k, v in stock_stats[stock].items()]),
                 "Timeframes: " + ", ".join(timeframes)]
            stock_increase_reason.extend(self._ai_api.
                                         get_stock_increase_reason(stock, timeframes).strip().split("\n"))
            self._pdf_api.append_stock_info(stock, stock_increase_reason)

        self._pdf_api.save_pdf()
        return self._pdf_api.file_name

    @staticmethod
    def filter_stock_with_timeframe_sma(stock_timeframe_dict: Dict[StockSymbol, List[str]],
                                        timeframe_combos: List[List[str]],
                                        sma_dict: Dict[StockSymbol, Dict[str, bool]]) \
            -> Dict[StockSymbol, List[str]]:
        """
        Filter stocks with the given timeframes combos and sma data

        :param stock_timeframe_dict: {StockSymbol: [timeframe, ...]}
        :param timeframe_combos: list of timeframe combos
        :param sma_dict: {StockSymbol: {timeframe: bool, ...}}
        :return: {StockSymbol: [timeframe, ...]}
        """
        res = {}
        for stock, timeframes in stock_timeframe_dict.items():
            if not all(sma_dict[stock].values()):
                continue

            for timeframe_combo in timeframe_combos:
                if all(timeframe in timeframes for timeframe in timeframe_combo):
                    res[stock] = timeframes
                    break
        return res

    def get_sorted_price_increased_stocks(self) -> Dict[str, List[Tuple[StockSymbol, Decimal]]]:
        """
        Get the stocks with in the price increase percentage order for different timeframes

        :return: { time_frame: [(StockSymbol, price_increase_percentage), ...] }

        """
        retry = True  # make sure the stock api returns non-zero price change
        while retry:
            stock_price_change = self.get_all_stock_price_change_percentage(self._timeframe_list)

            top_stocks = {}
            for timeframe in self._timeframe_list:
                top_stocks[timeframe] = sorted(stock_price_change.items(),
                                               key=lambda x: x[1][timeframe], reverse=True)

                top_stocks[timeframe] = [(stock, price_change[timeframe])
                                         for stock, price_change in top_stocks[timeframe]]
                retry = False
                if top_stocks[timeframe][0][1] == Decimal(0):
                    retry = True

        return top_stocks

    def get_top_n_non_etf_stocks(self, n: int, top_stocks: Dict[str, List[Tuple[StockSymbol, Decimal]]]) \
            -> Dict[str, List[Tuple[StockSymbol, Decimal]]]:
        """
        Get top n non-ETF stocks

        :param n: top n
        :param top_stocks: { time_frame: [(StockSymbol, price_increase_percentage), ...] }

        :return: { time_frame: [(StockSymbol, price_increase_percentage), ...] }
        """
        self.get_nasdaq_list()
        self.get_sp_500_list()
        self.get_nyse_list()
        for timeframe in self._timeframe_list:
            cur_top_stocks = []
            sp500_nasdaq_nyse_stocks = []
            for i in range(0, len(top_stocks[timeframe])):
                if top_stocks[timeframe][i][0].is_sp500 or top_stocks[timeframe][i][0].is_nasdaq\
                        or top_stocks[timeframe][i][0].is_nyse:
                    sp500_nasdaq_nyse_stocks.append(top_stocks[timeframe][i])
            for i in range(0, len(sp500_nasdaq_nyse_stocks), 40):
                stocks_price_increase = sp500_nasdaq_nyse_stocks[i:i + 40]
                stocks = {stock: percentage for stock, percentage in stocks_price_increase}
                stock_info = self.get_stock_info(list(stocks.keys()))
                for stock in stock_info:
                    if not stock.security_name:
                        logging.warning(f"Stock {stock.ticker} does not have security name")
                cur_top_stocks.extend(
                    [(stock, stocks[stock]) for stock in stock_info
                     if (stock.security_name and " ETF" not in stock.security_name
                     or not stock.security_name)
                     and len(stock.ticker) < 5
                     and self._daily_volume.get(stock, 0) >= self._daily_volume_threshold])
                if len(cur_top_stocks) >= n:
                    break
            top_stocks[timeframe] = cur_top_stocks[:n]

        return top_stocks

    def run(self) -> None:
        """
        This function is used to send daily report of top 50 stocks with the highest price increase
        """
        logging.info("Running Stock Alert")
        n = 50
        top_stocks = self.get_sorted_price_increased_stocks()
        _, self._daily_volume = self.get_all_stock_price_volume_by_day_delta(1)
        top_n_stocks = self.get_top_n_non_etf_stocks(n, top_stocks)

        is_newly_added_stock = {}
        timeframe_stocks_dict = defaultdict(list)

        last_stocks = StockAlertDBUtils.get_stocks()
        email_msg = ""
        for timeframe in self._timeframe_list:
            # send message and stock info file to telegram
            cur_top_stocks = []
            for stock, price_increase in top_n_stocks[timeframe]:
                stock_str = f"{stock.ticker}: {round(price_increase, 2)}%"
                is_newly_added_stock[stock] = False
                if stock.ticker not in last_stocks:
                    stock_str = f"{stock_str} (New)"
                    is_newly_added_stock[stock] = True
                cur_top_stocks.append(stock_str)
                timeframe_stocks_dict[timeframe].append(stock)
            msg = f"Top {n} stocks from SP500 and Nasdaq with the " \
                  f"highest price increase with timeframe {timeframe}: \n" \
                  "Stock: Price Change Percentage\n" \
                  f"{cur_top_stocks}"
            self._tg_bot.send_message(msg)
            email_msg += msg + "\n\n"

        StockAlertDBUtils.reset_stocks()
        StockAlertDBUtils.add_stocks(is_newly_added_stock.keys())

        time.sleep(10)
        # save stock info to csv file
        self.send_stocks_info_as_csv(is_newly_added_stock, timeframe_stocks_dict, email_msg)
        close_database()
        logging.info("Stock Alert Done")


if __name__ == '__main__':
    start = time.time()
    stock_alert = StockPriceTopPerformerAlert("stock_alert", tg_type="TEST", email=False,
                                              timeframe_list=["1m"],
                                              # timeframe_list=["1m", "3m", "6m", "1y", "3y", "5y", "10y"],
                                              # timeframe_list=["3m", "6m", "1y"],
                                              time_frame_sma_filter_ai_analysis=True,
                                              newly_added_stock_ai_analysis=True,
                                              growth_score_filter_ai_analysis=True,
                                              daily_volume_threshold=0)
    stock_alert.run()
    print(f"Time taken: {round(time.time() - start, 2)} seconds")
