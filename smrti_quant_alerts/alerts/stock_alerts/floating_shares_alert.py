import logging
import uuid
import os
import time
import threading
from typing import List, Tuple, Dict, Union
from collections import defaultdict

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.data_type import StockSymbol, FinancialMetricsData

logging.basicConfig(level=logging.INFO)


class FloatingSharesAlert(BaseAlert, StockApi):
    def __init__(self, alert_name: str, symbols_file: str = None, tg_type: str = "TEST") -> None:
        """
        :param alert_name: alert name
        :param symbols_file: stock symbols file
        :param tg_type: telegram type
        """
        super().__init__(tg_type)
        self._alert_name = alert_name
        self._email_api = EmailApi()
        self._symbols = []
        self._file_8k_summary_filename = f"file_8k_summary_{uuid.uuid4()}.csv"
        self._floating_shares_summary_filename = f"floating_shares_{uuid.uuid4()}.xlsx"
        self._load_symbols(symbols_file)
        self._load_stocks_info_thread = threading.Thread(target=self._load_stocks_info)
        self._load_stocks_info_thread.start()

    def _load_symbols(self, symbols_file: str) -> None:
        """
        Load symbols from file

        :param symbols_file: symbols file
        """
        if not symbols_file:
            return
        with open(symbols_file, "r") as f:
            self._symbols = [line.strip() for line in f.readlines()]

    def _load_stocks_info(self) -> None:
        """
        Pre-load the stocks info
        """
        stocks = self.get_nasdaq_list() + self.get_nyse_list()
        self.get_stock_info(stocks)

    def _generate_floating_shares(self, symbols: List[StockSymbol]) \
            -> Tuple[str, Dict[StockSymbol, Dict[str, FinancialMetricsData]]]:
        """
        Generate outstanding shares for the list of symbols

        :param symbols: list of StockSymbol

        :return: outstanding shares formatted email content
        """
        floating_shares = self.get_floating_shares_change(symbols)
        shares_content = ""

        for symbol, shares in floating_shares.items():
            if shares:
                shares_content += f"~ {symbol}:\n"
                for metric, data in shares.items():
                    shares_content += f"    · {metric}: {data}\n"
                shares_content += "\n"

        return shares_content, floating_shares

    def _generate_file_8k_summary_csv(self) -> None:
        """
        Generate the file 8k summary csv
        """
        filings = self.get_all_8k_filings_for_today()
        headers = ["title", "symbol", "cik", "link", "process", "hasFinancials", "date"]
        data = [[filing.get(header, "") for header in headers] for filing in filings]
        if self._symbols:
            data = [d for d in data if d[1] in self._symbols]
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(self._file_8k_summary_filename, index=False)

    def _generate_floating_shares_summary_xlsx(
            self, floating_shares: Dict[StockSymbol, Dict[str, FinancialMetricsData]]) -> None:
        """
        Generate the floating shares summary xlsx
        """
        self._load_stocks_info_thread.join()
        industry_stock_floating_shares_mapping = defaultdict(list)
        headers = ["stock", "7d change %", "90d change %"]
        for stock, floating_share in floating_shares.items():
            industry_stock_floating_shares_mapping[stock.gics_sector].append(
                [stock.ticker] + [str(floating_share["7d"]), str(floating_share["90d"])]
            )
        with pd.ExcelWriter(self._floating_shares_summary_filename) as writer:
            for industry, rows in industry_stock_floating_shares_mapping.items():
                if industry == "":
                    industry = "Others"
                df = pd.DataFrame(rows, dtype=str)
                df.to_excel(writer, sheet_name=industry, header=headers, index=False)

    def run(self) -> None:
        """
        Run the alert
        """
        self._generate_file_8k_summary_csv()
        # email content
        content = f"Filter by symbols: {self._symbols}" if self._symbols else ""
        content_str, floating_shares = \
            self._generate_floating_shares([StockSymbol(symbol=s) for s in sorted(self._symbols)])
        content += f"\n\n{content_str}"
        self._generate_floating_shares_summary_xlsx(floating_shares)

        # send email
        self._email_api.send_email(self._alert_name, content,
                                   [self._file_8k_summary_filename], [self._floating_shares_summary_filename])

        # send telegram message
        self._tg_bot.send_message(f"{self._alert_name}\n{content}")
        for file in [self._file_8k_summary_filename, self._floating_shares_summary_filename]:
            if os.path.exists(file):
                self._tg_bot.send_file(file, self._alert_name)
                os.remove(file)


if __name__ == "__main__":
    start = time.time()
    alert = FloatingSharesAlert("FloatingSharesAlert", symbols_file="floating_shares_symbols.txt")
    alert.run()

    print(f"time taken: {time.time() - start} seconds")
