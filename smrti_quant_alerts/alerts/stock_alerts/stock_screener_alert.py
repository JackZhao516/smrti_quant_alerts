import logging
import time
import os
import uuid
import threading
from typing import List, Dict, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.data_type import StockSymbol, FinancialMetricType, FinancialMetricsData
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.db import StockAlertDBUtils


class StockScreenerAlert(BaseAlert, StockApi):
    def __init__(self, alert_name: str, price_top_percent: 20, top_performer_exclude_sectors: List[str] = None,
                 email: bool = True, market_cap_threshold: int = 10 ** 8) -> None:
        BaseAlert.__init__(self, alert_name)
        StockApi.__init__(self)

        self._email_api = EmailApi()
        self._email = email
        self._price_top_percent = price_top_percent
        self._top_performer_exclude_sectors = top_performer_exclude_sectors
        self._market_cap_threshold = market_cap_threshold
        self._stocks_ev_over_gross_profit = defaultdict(float)
        self._stocks_valuation_score = defaultdict(FinancialMetricsData)
        self._stocks_eight_quarters_stats = defaultdict(list)
        self._screener_name_to_stocks = defaultdict(list)
        self._stock_price_top_performer_by_gics_sector_timeframe = {}

        self._get_stock_info_thread = threading.Thread(target=self._get_all_stock_info)
        self._get_stock_info_thread.start()

        self._get_price_top_performer_thread = \
            threading.Thread(target=self.get_top_percent_stock_price_top_performer_by_gics_sector_timeframe)
        self._get_price_top_performer_thread.start()

    def _get_stocks(self) -> List[StockSymbol]:
        """
        Get stocks from the initial filter
        """
        return self.get_top_market_cap_stocks_by_market_cap_threshold(self._market_cap_threshold)

    def _get_all_stock_info(self) -> None:
        """
        Get stock info
        """
        stocks = self.get_nyse_list() + self.get_nasdaq_list()
        self.get_stock_info(stocks)

    def _get_enterprise_value_over_gross_profit(self, stocks: List[StockSymbol]) -> None:
        """
        Get enterprise value over revenue
        """
        # filter out already calculated stocks
        stocks = [stock for stock in stocks if stock not in self._stocks_ev_over_gross_profit]

        with ThreadPoolExecutor(max_workers=8) as executor:
            enterprise_values = executor.submit(self.get_stocks_enterprise_value, stocks)
            stocks_stats = executor.submit(self.get_stocks_stats_by_num_of_timeframe, stocks, "annual", 1)
            enterprise_values = enterprise_values.result()
            stocks_stats = stocks_stats.result()

        self._stocks_ev_over_gross_profit.update(
            {stock: (enterprise_values[stock] / stocks_stats[stock][0][FinancialMetricType.GROSS_PROFIT])
             for stock in stocks if len(stocks_stats[stock]) > 0})

    def _parallel_get_stocks_valuation_score(self, stocks: List[StockSymbol]) -> None:
        """
        Get stocks valuation score

        :param stocks: list of stocks
        """
        stocks = [stock for stock in stocks if stock not in self._stocks_valuation_score]
        valuation_scores_res = []
        step = len(stocks) // 8
        with ThreadPoolExecutor(max_workers=8) as executor:
            for i in range(8):
                valuation_scores_res.append(executor.submit(self.get_stocks_valuation_score, stocks[i*step:(i+1)*step]))
            valuation_scores_res = [res.result() for res in valuation_scores_res]
        for res in valuation_scores_res:
            self._stocks_valuation_score.update(res)

    def _get_stocks_eight_quarters_stats(self, stocks: List[StockSymbol]) -> None:
        """
        Get eight quarters stats: quarterly revenue yoy growth, operating margin, gross margin, FCF margin

        :param stocks: list of stocks
        """
        # filter out already calculated stocks
        stocks = [stock for stock in stocks if stock not in self._stocks_eight_quarters_stats]

        with ThreadPoolExecutor(max_workers=8) as executor:
            quarterly_revenue_yoy_growth = executor.submit(self.get_stocks_quarterly_revenue_yoy_growth, stocks, 8)
            stock_stats = executor.submit(self.get_stocks_stats_by_num_of_timeframe, stocks, "quarter", 8)
            quarterly_revenue_yoy_growth = quarterly_revenue_yoy_growth.result()
            stock_stats = stock_stats.result()

        for stock in stocks:
            stats = [{FinancialMetricType.REVENUE_YOY_GROWTH: quarterly_revenue_yoy_growth[stock][i],
                      FinancialMetricType.GROSS_MARGIN: stock_stats[stock][i][FinancialMetricType.GROSS_MARGIN],
                      FinancialMetricType.OPERATING_MARGIN: stock_stats[stock][i][FinancialMetricType.OPERATING_MARGIN],
                      FinancialMetricType.FREE_CASH_FLOW_MARGIN:
                          stock_stats[stock][i][FinancialMetricType.FREE_CASH_FLOW_MARGIN]} for i in range(8)]
            self._stocks_eight_quarters_stats[stock] = stats

    def get_top_percent_stock_price_top_performer_by_gics_sector_timeframe(self) -> None:
        """
        Get top percent stock price top performer by gics sector timeframe
        """
        all_non_etf_stocks = self.get_all_non_etf_stocks_by_gics_sector()
        self._stock_price_top_performer_by_gics_sector_timeframe = \
            self.get_all_non_etf_stocks_price_change_percentage_by_gics_sector_timeframes(["5D", "1M"])
        if self._top_performer_exclude_sectors:
            for sector in self._top_performer_exclude_sectors:
                for key in self._stock_price_top_performer_by_gics_sector_timeframe.keys():
                    if sector in self._stock_price_top_performer_by_gics_sector_timeframe[key]:
                        del self._stock_price_top_performer_by_gics_sector_timeframe[key][sector]
        for timeframe, value in self._stock_price_top_performer_by_gics_sector_timeframe.items():
            for key, _ in value.items():
                num_kept = int(len(all_non_etf_stocks[key]) * self._price_top_percent / 100)
                self._stock_price_top_performer_by_gics_sector_timeframe[timeframe][key] = \
                    self._stock_price_top_performer_by_gics_sector_timeframe[timeframe][key][:num_kept]

    # ---------------------------screener rules--------------------------------
    def _growth_score_filter(self, stocks: List[StockSymbol]) \
            -> Tuple[List[StockSymbol], Dict[StockSymbol, Dict[str, FinancialMetricsData]]]:
        """
        last two quarterly revenue yoy growth + avg (last two quarters) FCF margin > 80%
        """
        logging.info("growth_score_filter started")
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
        logging.info("quarterly_revenue_yoy_growth_operating_margin_filter started")
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
        logging.info("quarterly_revenue_yoy_growth_revenue_cagr_filter started")
        filtered_stocks = []
        revenue_yoy_growth = self.get_stocks_quarterly_revenue_yoy_growth(stocks, 6)
        revenue_cagr = self.get_stocks_revenue_cagr(stocks)
        for stock in stocks:
            if revenue_yoy_growth[stock][0] > 0.3 and \
                    (revenue_cagr[stock][FinancialMetricType.REVENUE_3Y_CAGR] > 0.3 or
                     sum(revenue_yoy_growth[stock]) / 6 > 0.3):
                filtered_stocks.append(stock)

        return filtered_stocks

    def _quarterly_revenue_yoy_growth_filter(self, stocks: List[StockSymbol]) -> List[StockSymbol]:
        """
        latest quarterly revenue yoy growth > 30% and avg(last 3 quarterly revenue yoy growth) > 30%
        """
        logging.info("quarterly_revenue_yoy_growth_filter started")
        filtered_stocks = []
        revenue_yoy_growth = self.get_stocks_quarterly_revenue_yoy_growth(stocks, 3)
        for stock in stocks:
            if revenue_yoy_growth[stock][0] > 0.3 and \
                    sum(revenue_yoy_growth[stock]) / 3 > 0.3:
                filtered_stocks.append(stock)
        return filtered_stocks

    # -------------------enrich email content----------------------
    def _get_newly_added_stocks_str(self) -> str:
        """
        Find newly added stocks

        :return: enriched email content
        """
        sector_to_stocks = self.get_all_non_etf_stocks_by_gics_sector()
        content = "~Newly added stocks:\n"
        for screener_name, stocks in self._screener_name_to_stocks.items():
            last_stocks = StockAlertDBUtils.get_stocks(screener_name)
            new_stocks = set(stocks) - set(last_stocks)
            StockAlertDBUtils.reset_stocks(screener_name)
            StockAlertDBUtils.add_stocks(stocks, screener_name)
            if not new_stocks:
                content += f"  ·{screener_name} no newly added stocks\n"
            else:
                content += f"   ·{screener_name} newly added stocks:\n"
                for sector, sector_stocks in sector_to_stocks.items():
                    sector_stocks_set = set(sector_stocks)
                    chosen_stocks = [stock.ticker for stock in new_stocks if stock in sector_stocks_set]
                    if chosen_stocks:
                        if sector == "":
                            sector = "Others"
                        content += f"       ·{sector}: {chosen_stocks}\n"

        return content + "\n"

    def _get_screener_stocks_in_top_performer(self) -> str:
        """
        Get screener stocks in top performer

        :return: enriched email content
        """
        self._get_price_top_performer_thread.join()
        content = ""
        for timeframe, value in self._stock_price_top_performer_by_gics_sector_timeframe.items():
            content += f"~Top {self._price_top_percent}% price performer in {timeframe}:\n"
            for screener_name, screener_stocks in self._screener_name_to_stocks.items():
                screener_stocks = set(screener_stocks)
                content += f"   ·{screener_name} top performer: \n"
                for sector, top_performers in value.items():
                    chosen_stocks = [stock[0] for stock in top_performers if stock[0] in screener_stocks]
                    if chosen_stocks:
                        content += f"       ·{sector}: {chosen_stocks}\n"

        return content + "\n"

    # ---------------------------build csv/xlsx-----------------------
    def _build_growth_filter_docs(self, stocks: List[StockSymbol],
                                  growth_scores: Dict[StockSymbol, Dict[str, FinancialMetricsData]],
                                  growth_score_file_break_threshold: int = 1) -> List[str]:
        """
        Build growth filter xlsx files

        :param stocks: list of stocks
        :param growth_scores: growth scores
        :param growth_score_file_break_threshold: growth score file break threshold

        :return: list of file names
        """
        filenames = [f"screener_1_growth_score_filter_lt_{growth_score_file_break_threshold}_"
                     f"{self._alert_name}_{uuid.uuid4()}.xlsx",
                     f"screener_1_growth_score_filter_gt_{growth_score_file_break_threshold}"
                     f"_{self._alert_name}_{uuid.uuid4()}.xlsx"]
        headers = ["symbol", FinancialMetricType.REVENUE_YOY_GROWTH_LATEST,
                   FinancialMetricType.REVENUE_YOY_GROWTH_SECOND_LATEST,
                   FinancialMetricType.REVENUE_YOY_GROWTH_SUM,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_LATEST,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_SECOND_LATEST,
                   FinancialMetricType.FREE_CASH_FLOW_MARGIN_AVG,
                   FinancialMetricType.GROWTH_SCORE]

        writer_industry_maps = [defaultdict(list), defaultdict(list)]

        for stock in stocks:
            index = 1 if growth_scores[stock][FinancialMetricType.GROWTH_SCORE] > \
                         growth_score_file_break_threshold else 0
            writer_industry_maps[index][stock.gics_sector].append(
                [stock.ticker] + [str(growth_scores[stock][header]) for header in headers[1:]])

        for filename, writer_industry_map in zip(filenames, writer_industry_maps):
            with pd.ExcelWriter(filename) as writer:
                for industry, rows in writer_industry_map.items():
                    rows.insert(0, headers)
                    if industry == "":
                        industry = "Others"
                    df = pd.DataFrame(rows, dtype=str)
                    df.to_excel(writer, sheet_name=industry, header=False, index=False)

        return filenames

    def _build_standard_filter_xlsx(self, stocks: List[StockSymbol], screener_name: str) -> str:
        """
        Build csv file

        :param stocks: list of stocks
        :param screener_name: screener name

        :return: file name, email content add on
        """
        self._screener_name_to_stocks[screener_name] = stocks
        file_name = f"{screener_name}_{self._alert_name}_{uuid.uuid4()}.xlsx"
        self._get_enterprise_value_over_gross_profit(stocks)
        self._get_stocks_eight_quarters_stats(stocks)
        self._parallel_get_stocks_valuation_score(stocks)

        industry_to_stock_stats = defaultdict(list)
        for stock in stocks:
            rows = [[], [], [stock.ticker, f"EV/Gross Profit: {self._stocks_ev_over_gross_profit[stock]}", "",
                             f"Stock Valuation Score: {self._stocks_valuation_score[stock]}"],
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
                if industry == "":
                    industry = "Others"
                df = pd.DataFrame(rows, dtype=str)
                df.to_excel(writer, sheet_name=industry, header=False, index=False)
        return file_name

    # ---------------------------send email--------------------------------
    def _send_email(self, csv_files: List[str] = None,
                    pdf_xlsx_files: List[str] = None, email_content_add_on: str = "") -> None:
        """
        Send email

        :param csv_files: csv file names
        :param pdf_xlsx_files: pdf file names
        :param email_content_add_on: email content add on
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
        content += email_content_add_on
        self._email_api.send_email(self._alert_name, content, csv_files, pdf_xlsx_files)

    # ---------------------------main--------------------------------
    def run(self) -> None:
        stocks = self._get_stocks()
        logging.warning(f"Total stocks: {len(stocks)}")

        with ThreadPoolExecutor(max_workers=8) as executor:
            screener_1_res = executor.submit(self._growth_score_filter, stocks)
            screener_2_res = executor.submit(self._quarterly_revenue_yoy_growth_operating_margin_filter, stocks)
            screener_3_res = executor.submit(self._quarterly_revenue_yoy_growth_revenue_cagr_filter, stocks)
            screener_4_res = executor.submit(self._quarterly_revenue_yoy_growth_filter, stocks)
            self._get_stock_info_thread.join()

            screener_1_res_stocks, growth_scores = screener_1_res.result()
            xlsx_files = self._build_growth_filter_docs(screener_1_res_stocks, growth_scores) + \
                [self._build_standard_filter_xlsx(screener_1_res_stocks,
                                                  "screener_1_8-quarters_stats"),
                 self._build_standard_filter_xlsx(screener_2_res.result(),
                                                  "screener_2_quarter_rev_yoy_growth_operating_margin"),
                 self._build_standard_filter_xlsx(screener_3_res.result(),
                                                  "screener_3_quarter_rev_yoy_growth_revenue_cagr"),
                 self._build_standard_filter_xlsx(screener_4_res.result(),
                                                  "screener_4_quarter_rev_yoy_growth")]

        # after this point, all stocks are already calculated
        email_content_add_on = self._get_newly_added_stocks_str()
        email_content_add_on += self._get_screener_stocks_in_top_performer()

        if self._email:
            self._send_email(pdf_xlsx_files=xlsx_files, email_content_add_on=email_content_add_on)

        for file in xlsx_files:
            if os.path.exists(file):
                os.remove(file)


if __name__ == "__main__":
    start_time = time.time()
    alert = StockScreenerAlert("stock_screener", 20,
                               ["Energy", "Basic Materials"], email=True, market_cap_threshold=10 ** 9)
    alert.run()

    print(f"Time taken: {time.time() - start_time}")
