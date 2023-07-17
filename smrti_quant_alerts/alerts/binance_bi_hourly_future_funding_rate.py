import time
from time import sleep
from decimal import Decimal
from datetime import datetime

import pytz

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot


class FutureFundingRate(GetExchangeList):
    def __init__(self, rate_threshold=Decimal(0.002), tg_type="FUNDING_RATE"):
        super().__init__("TEST")
        self.tg_bot = TelegramBot(tg_type)
        self.rate_threshold = rate_threshold

    def bi_hourly_alert_funding_rate_over_threshold(self):
        """
        This function is used to send bi-hourly alerts of funding rate over threshold
        """
        while True:
            # alerts every 2 hours
            # can easily change time and frequency here
            # if you want to change the frequency, remember to change the sleep time
            tz = pytz.timezone('Asia/Shanghai')
            shanghai_now = datetime.now(tz).strftime('%H:%M')
            if shanghai_now in {"00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
                                "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"}:
                exchange_list = self.get_all_binance_future_exchanges()
                res = []
                for exchange in exchange_list:
                    symbol, contract_type = exchange[0], exchange[1]
                    funding_rate = self.get_future_exchange_funding_rate(symbol)
                    if funding_rate > 0 and funding_rate > self.rate_threshold or \
                            funding_rate < 0 and funding_rate < -self.rate_threshold:
                        res.append([symbol, contract_type, funding_rate])
                    time.sleep(1)

                self.tg_bot.send_message(f"Bi-hourly Funding Rate Alert: \n{res}")
            sleep(60)


if __name__ == '__main__':
    test = FutureFundingRate(tg_type="TEST")
    test.bi_hourly_alert_funding_rate_over_threshold()
