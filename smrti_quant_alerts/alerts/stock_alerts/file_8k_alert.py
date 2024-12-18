import logging
import uuid
import os
from typing import List

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.data_type import StockSymbol

logging.basicConfig(level=logging.INFO)


class File8KAlert(BaseAlert):
    def __init__(self, alert_name: str, symbols: List[str] = None, tg_type: str = "TEST") -> None:
        """
        :param alert_name: alert name
        :param symbols: stock symbols
        :param tg_type: telegram type
        """
        super().__init__(tg_type)
        self._alert_name = alert_name
        self._email_api = EmailApi()
        self._stock_api = StockApi()
        self._symbols = set(symbols) if symbols else None
        self._file_name = f"{self._alert_name}_{uuid.uuid4()}.csv"

    def _generate_outstanding_shares(self, symbols: List[StockSymbol]) -> str:
        """
        Generate outstanding shares for the list of symbols

        :param symbols: list of StockSymbol

        :return: outstanding shares formatted email content
        """
        outstanding_shares = self._stock_api.get_outstanding_shares(symbols)
        shares_content = ""
        for symbol, shares in outstanding_shares.items():
            if shares and len(shares) == 4:
                has_increased = shares[1] > shares[3]
                shares_content += f"~ {symbol}: {shares[3]} ({shares[2]}) -> {shares[1]} ({shares[0]}) " \
                                  f"{'+' if has_increased else '-'}\n\n"
        return shares_content

    def run(self) -> None:
        """
        Run the alert
        """
        filings = self._stock_api.get_all_8k_filings_for_today()
        headers = ["title", "symbol", "cik", "link", "process", "hasFinancials", "date"]
        data = [[filing.get(header, "") for header in headers] for filing in filings]
        if self._symbols:
            data = [d for d in data if d[1] in self._symbols]
        df = pd.DataFrame(data, columns=headers)
        df.to_csv(self._file_name, index=False)
        # email content
        content = f"Filter by symbols: {self._symbols}" if self._symbols else ""
        content += f"\n\n{self._generate_outstanding_shares([StockSymbol(symbol=s) for s in sorted(self._symbols)])}"

        # send email
        self._email_api.send_email(self._alert_name, content, [self._file_name])

        # send telegram message
        self._tg_bot.send_message(f"{self._alert_name}\n{content}")
        self._tg_bot.send_file(self._file_name, self._alert_name)
        os.remove(self._file_name)


if __name__ == "__main__":
    alert = File8KAlert("File8KAlert", symbols=["TSLA", "ALAB", "TEM", "CRM", "RKLB", "SHOP"])
    alert.run()
