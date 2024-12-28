import logging
import uuid
import os
import threading
from typing import List

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.data_type import StockSymbol

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

    def _generate_floating_shares(self, symbols: List[StockSymbol]) -> str:
        """
        Generate outstanding shares for the list of symbols

        :param symbols: list of StockSymbol

        :return: outstanding shares formatted email content
        """
        floating_shares = self.get_floating_shares(symbols)
        shares_content = ""
        for symbol, shares in floating_shares.items():
            if shares and len(shares) == 4:
                has_increased = shares[1] > shares[3]
                shares_content += f"~ {symbol}: {shares[3]} ({shares[2]}) -> {shares[1]} ({shares[0]}) " \
                                  f"{'+' if has_increased else '-'}\n\n"
        return shares_content

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

    def run(self) -> None:
        """
        Run the alert
        """
        self._generate_file_8k_summary_csv()
        # email content
        content = f"Filter by symbols: {self._symbols}" if self._symbols else ""
        content += f"\n\n{self._generate_floating_shares([StockSymbol(symbol=s) for s in sorted(self._symbols)])}"

        # send email
        self._email_api.send_email(self._alert_name, content, [self._file_8k_summary_filename])

        # send telegram message
        self._tg_bot.send_message(f"{self._alert_name}\n{content}")
        self._tg_bot.send_file(self._file_8k_summary_filename, self._alert_name)
        os.remove(self._file_8k_summary_filename)


if __name__ == "__main__":
    alert = FloatingSharesAlert("FloatingSharesAlert", symbols_file="floating_shares_symbols.txt")
    alert.run()
