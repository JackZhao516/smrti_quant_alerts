from time import sleep
from decimal import Decimal
from multiprocessing.pool import ThreadPool

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.alerts.utility import run_task_at_daily_time


class FutureFundingRate(GetExchangeList):
    def __init__(self, rate_threshold=Decimal(0.002), tg_type="FUNDING_RATE"):
        super().__init__("TEST")
        self.tg_bot = TelegramBot(tg_type)
        self.rate_threshold = rate_threshold
        self.exchange_list = None
        self.pass_threshold_exchanges = []

    def _exchange_funding_rate_over_threshold(self, exchange):
        """
        Check whether the exchange funding rate pass threshold
        """
        funding_rate = self.get_future_exchange_funding_rate(exchange)
        if funding_rate and (funding_rate > 0 and funding_rate > self.rate_threshold or
                             funding_rate < 0 and funding_rate < -self.rate_threshold):
            funding_rate = f"{round(funding_rate * 100, 3)}%"
            self.pass_threshold_exchanges.append([exchange, funding_rate])
        sleep(0.5)

    def run(self):
        """
        This function is used to send bi-hourly alerts of funding rate over threshold
        """
        self.exchange_list = self.get_all_binance_exchanges("FUTURE")
        if not self.exchange_list:
            return
        pool = ThreadPool(8)
        pool.map(self._exchange_funding_rate_over_threshold, self.exchange_list)
        pool.close()

        if self.pass_threshold_exchanges:
            self.tg_bot.send_message(f"Bi-hourly Funding Rate Alert: \n"
                                     f"{self.pass_threshold_exchanges}")
            self.pass_threshold_exchanges = []


if __name__ == '__main__':
    t = FutureFundingRate(tg_type="TEST")
    run_task_at_daily_time(t.run, "03:53", duration=60 * 60 * 24)
