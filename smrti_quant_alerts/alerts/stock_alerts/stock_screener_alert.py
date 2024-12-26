import logging
import csv
import time
import os
import uuid
import threading
from multiprocessing.pool import ThreadPool
from typing import List, Dict, Tuple
from collections import defaultdict

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.data_type import StockSymbol, FinancialMetricType, FinancialMetricsData
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert

logging.basicConfig(level=logging.INFO)


class StockScreenerAlert(BaseAlert, StockApi):
    def __init__(self, alert_name: str, tg_type: str = "TEST", email: bool = True):
        BaseAlert.__init__(self, tg_type=tg_type)
        StockApi.__init__(self)
        self._alert_name = alert_name
        self._email_api = EmailApi()
        self._email = email
        self._stocks_ev_over_revenue = defaultdict(float)
        self._stocks_eight_quarters_stats = defaultdict(list)
        self._get_stock_info_thread = threading.Thread(target=self._get_all_stock_info)
        self._get_stock_info_thread.start()

    def _get_stocks(self) -> List[StockSymbol]:
        """
        Get stocks from the initial filter
        """
        return self.get_top_market_cap_stocks_by_market_cap_threshold(10 ** 6)

    def _get_all_stock_info(self) -> None:
        """
        Get stock info
        """
        stocks = self.get_nyse_list() + self.get_nasdaq_list()
        self.get_stock_info(stocks)

    def _get_enterprise_value_over_revenue(self, stocks: List[StockSymbol]) -> None:
        """
        Get enterprise value over revenue
        """
        # filter out already calculated stocks
        stocks = [stock for stock in stocks if stock not in self._stocks_ev_over_revenue]

        pool = ThreadPool(processes=2)
        enterprise_values = pool.apply_async(self.get_stocks_enterprise_value, (stocks,))
        revenues = pool.apply_async(self.get_stocks_revenue, (stocks,))
        enterprise_values = enterprise_values.get()
        revenues = revenues.get()
        pool.close()
        pool.join()

        self._stocks_ev_over_revenue.update(
            {stock: (enterprise_values[stock] / revenues[stock]) for stock in stocks})

    def _get_stocks_eight_quarters_stats(self, stocks: List[StockSymbol]) -> None:
        """
        Get eight quarters stats: quarterly revenue yoy growth, operating margin, gross margin, FCF margin

        :param stocks: list of stocks
        """
        # filter out already calculated stocks
        stocks = [stock for stock in stocks if stock not in self._stocks_eight_quarters_stats]

        pool = ThreadPool(processes=2)
        quarterly_revenue_yoy_growth = pool.apply_async(self.get_stocks_quarterly_revenue_yoy_growth, (stocks, 8))
        stock_stats = pool.apply_async(self.get_stocks_stats_by_num_of_timeframe, (stocks, "quarter", 8))
        quarterly_revenue_yoy_growth = quarterly_revenue_yoy_growth.get()
        stock_stats = stock_stats.get()
        pool.close()
        pool.join()

        for stock in stocks:
            stats = [{FinancialMetricType.REVENUE_YOY_GROWTH: quarterly_revenue_yoy_growth[stock][i],
                      FinancialMetricType.GROSS_MARGIN: stock_stats[stock][i][FinancialMetricType.GROSS_MARGIN],
                      FinancialMetricType.OPERATING_MARGIN: stock_stats[stock][i][FinancialMetricType.OPERATING_MARGIN],
                      FinancialMetricType.FREE_CASH_FLOW_MARGIN:
                          stock_stats[stock][i][FinancialMetricType.FREE_CASH_FLOW_MARGIN]} for i in range(8)]
            self._stocks_eight_quarters_stats[stock] = stats

    # ---------------------------screener rules--------------------------------
    def _growth_score_filter(self, stocks: List[StockSymbol]) \
            -> Tuple[List[StockSymbol], Dict[StockSymbol, Dict[str, FinancialMetricsData]]]:
        """
        last two quarterly revenue yoy growth + avg (last two quarters) FCF margin > 80%
        """
        filtered_stocks = []
        growth_scores = self.get_stocks_growth_score(stocks, True)
        for stock in stocks:
            if growth_scores[stock][FinancialMetricType.GROWTH_SCORE] > 0.8:
                filtered_stocks.append(stock)
        filtered_stocks = sorted(filtered_stocks,
                                 key=lambda x: growth_scores[x][FinancialMetricType.GROWTH_SCORE],
                                 reverse=True)
        return filtered_stocks, growth_scores

    def _quarterly_revenue_yoy_growth_operating_margin_filter(self, stocks: List[StockSymbol]) -> List[StockSymbol]:
        """
        latest quarterly revenue yoy growth + operating margin > 40%

        :param stocks: list of stocks

        :return: list of stocks
        """
        filtered_stocks = []
        revenue_yoy_growth = self.get_stocks_quarterly_revenue_yoy_growth(stocks, 1)
        stock_stats = self.get_stocks_stats_by_num_of_timeframe(stocks, "quarter", 1)
        for stock in stocks:
            if revenue_yoy_growth[stock][0] + stock_stats[stock][0][FinancialMetricType.OPERATING_MARGIN] > 0.4:
                filtered_stocks.append(stock)

        return filtered_stocks

    def _quarterly_revenue_yoy_growth_revenue_cagr_filter(self, stocks: List[StockSymbol]) -> List[StockSymbol]:
        """
        latest quarterly revenue yoy growth > 30% and
        3Y revenue CAGR > 30% or avg (last 6 quarterly revenue yoy growth) > 30%

        :param stocks: list of stocks

        :return: list of stocks
        """
        filtered_stocks = []
        revenue_yoy_growth = self.get_stocks_quarterly_revenue_yoy_growth(stocks, 6)
        revenue_cagr = self.get_stocks_revenue_cagr(stocks)
        for stock in stocks:
            if revenue_yoy_growth[stock][0] > 0.3 and \
                    (revenue_cagr[stock][FinancialMetricType.REVENUE_3Y_CAGR] > 0.3 or
                     sum([revenue_yoy_growth[stock][i] for i in range(6)]) / 6 > 0.3):
                filtered_stocks.append(stock)

        return filtered_stocks

    def _quarterly_revenue_yoy_growth_filter(self, stocks: List[StockSymbol]) -> List[StockSymbol]:
        """
        latest quarterly revenue yoy growth > 30% and avg(last 3 quarterly revenue yoy growth) > 30%
        """
        filtered_stocks = []
        revenue_yoy_growth = self.get_stocks_quarterly_revenue_yoy_growth(stocks, 3)
        for stock in stocks:
            if revenue_yoy_growth[stock][0] > 0.3 and \
                    sum([revenue_yoy_growth[stock][i] for i in range(3)]) / 3 > 0.3:
                filtered_stocks.append(stock)
        return filtered_stocks

    # ---------------------------build csv/xlsx-----------------------
    def _build_growth_filter_docs(self, stocks: List[StockSymbol],
                                  growth_scores: Dict[StockSymbol, Dict[str, FinancialMetricsData]],
                                  growth_score_file_break_threshold: int = 1) -> List[str]:
        """
        Build csv file

        :param stocks: list of stocks
        :param growth_scores: growth scores
        :param growth_score_file_break_threshold: growth score file break threshold

        :return: list of file names
        """
        file_name_less_than_threshold = \
            f"screener_1_growth_score_filter_lt_{growth_score_file_break_threshold}_" \
            f"{self._alert_name}_{uuid.uuid4()}.csv"
        file_name_greater_than_threshold = f"screener_1_growth_score_filter_gt_{growth_score_file_break_threshold}" \
                                           f"_{self._alert_name}_{uuid.uuid4()}.csv"
        headers = ["symbol", FinancialMetricType.REVENUE_YOY_GROWTH_LATEST,
                   FinancialMetricType.REVENUE_YOY_GROWTH_SECOND_LATEST,
                   FinancialMetricType.REVENUE_YOY_GROWTH_SUM,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_LATEST,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_SECOND_LATEST,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_AVG,
                   FinancialMetricType.GROWTH_SCORE]

        file_less_than_writer = csv.writer(open(file_name_less_than_threshold, mode="w"))
        file_greater_than_writer = csv.writer(open(file_name_greater_than_threshold, mode="w"))
        file_less_than_writer.writerow(headers)
        file_greater_than_writer.writerow(headers)

        for stock in stocks:
            writer = file_less_than_writer \
                if growth_scores[stock][FinancialMetricType.GROWTH_SCORE] < growth_score_file_break_threshold \
                else file_greater_than_writer
            writer.writerow([stock.ticker] + [str(growth_scores[stock][header]) for header in headers[1:]])
        return [file_name_less_than_threshold, file_name_greater_than_threshold]

    def _build_standard_filter_xlsx(self, stocks: List[StockSymbol], screener_name: str) -> str:
        """
        Build csv file

        :param stocks: list of stocks
        :param screener_name: screener name

        :return: file name
        """
        file_name = f"{screener_name}_{self._alert_name}_{uuid.uuid4()}.xlsx"
        self._get_enterprise_value_over_revenue(stocks)
        self._get_stocks_eight_quarters_stats(stocks)
        self._get_stock_info_thread.join()

        industry_to_stock_stats = defaultdict(list)
        for stock in stocks:
            rows = [[], [], [stock.ticker, f"{FinancialMetricType.ENTERPRISE_VALUE}/{FinancialMetricType.REVENUE}: ",
                             f"{self._stocks_ev_over_revenue[stock]}", stock.gics_sector],
                    ["quarter index (from newest to oldest)", "Quarterly Revenue YoY Growth",
                     "Operating Margin", "Gross Margin", "FCF Margin"]]
            for i, stats in enumerate(self._stocks_eight_quarters_stats[stock]):
                row = [f"{i + 1}",
                       f"{stats[FinancialMetricType.REVENUE_YOY_GROWTH.value]}",
                       f"{stats[FinancialMetricType.OPERATING_MARGIN]}",
                       f"{stats[FinancialMetricType.GROSS_MARGIN]}",
                       f"{stats[FinancialMetricType.FREE_CASH_FLOW_MARGIN]}"]
                rows.append(row)
            industry_to_stock_stats[stock.gics_sector].extend(rows)

        with pd.ExcelWriter(file_name) as writer:
            for industry, rows in industry_to_stock_stats.items():
                df = pd.DataFrame(rows, dtype=str)
                df.to_excel(writer, sheet_name=industry, header=False, index=False)
        return file_name

    # ---------------------------send email--------------------------------
    def _send_email(self, csv_files: List[str] = None, pdf_files: List[str] = None) -> None:
        """
        Send email

        :param csv_files: csv file names
        :param pdf_files: pdf file names
        """
        content = "Stock Screener 1: Growth Score Filter\n" \
                  "  - growth score = last two quarterly revenue yoy growth + avg (last two quarters) FCF margin\n" \
                  "  - growth score > 80%\n\n" \
                  "Stock Screener 2: Quarterly Revenue YoY Growth + Operating Margin Filter\n" \
                  "  - latest quarterly revenue yoy growth + operating margin > 40%\n\n" \
                  "Stock Screener 3: Quarterly Revenue YoY Growth + Revenue CAGR Filter\n" \
                  "  - latest quarterly revenue yoy growth > 30% and\n" \
                  "  - 3Y revenue CAGR > 30% or avg (last 6 quarterly revenue yoy growth) > 30%\n\n" \
                  "Stock Screener 4: Quarterly Revenue YoY Growth Filter\n" \
                  "  - latest quarterly revenue yoy growth > 30% and avg(last 3 quarterly revenue yoy growth) > 30%\n\n"
        self._email_api.send_email(self._alert_name, content, csv_files, pdf_files)

    # ---------------------------main--------------------------------
    def run(self) -> None:
        stocks = self._get_stocks()
        print(f"Total stocks: {len(stocks)}")

        pool = ThreadPool(processes=4)
        screener_1_res = pool.apply_async(self._growth_score_filter, (stocks,))
        screener_2_res = pool.apply_async(self._quarterly_revenue_yoy_growth_operating_margin_filter, (stocks,))
        screener_3_res = pool.apply_async(self._quarterly_revenue_yoy_growth_revenue_cagr_filter, (stocks,))
        screener_4_res = pool.apply_async(self._quarterly_revenue_yoy_growth_filter, (stocks,))

        csv_files = self._build_growth_filter_docs(*screener_1_res.get())
        xlsx_files = [self._build_standard_filter_xlsx(screener_2_res.get(),
                                                       "screener_2_quarter_rev_yoy_growth_operating_margin"),
                      self._build_standard_filter_xlsx(screener_3_res.get(),
                                                       "screener_3_quarter_rev_yoy_growth_revenue_cagr"),
                      self._build_standard_filter_xlsx(screener_4_res.get(),
                                                       "screener_4_quarter_rev_yoy_growth")]

        pool.close()
        pool.join()

        if self._email:
            self._send_email(csv_files, xlsx_files)

        for file in csv_files + xlsx_files:
            if os.path.exists(file):
                os.remove(file)


if __name__ == "__main__":
    start_time = time.time()
    alert = StockScreenerAlert("StockScreenerAlert")
    alert.run()

    print(f"Time taken: {time.time() - start_time}")
