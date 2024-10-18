import logging
import uuid
import os
from typing import List

import pandas as pd

from smrti_quant_alerts.email_api import EmailApi
from smrti_quant_alerts.stock_crypto_api import StockApi
from smrti_quant_alerts.alerts.base_alert import BaseAlert

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

        # send email
        self._email_api.send_email(self._alert_name, content, [self._file_name])

        # send telegram message
        self._tg_bot.send_message(f"{self._alert_name}\n{content}")
        self._tg_bot.send_file(self._file_name, self._alert_name)
        os.remove(self._file_name)


if __name__ == "__main__":
    alert = File8KAlert("File8KAlert")
    alert.run()
