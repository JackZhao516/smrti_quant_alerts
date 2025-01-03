from time import sleep
from decimal import Decimal
from multiprocessing.pool import ThreadPool

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import BinanceApi
from smrti_quant_alerts.data_type import BinanceExchange


class FutureFundingRate(BaseAlert, BinanceApi):
    def __init__(self, alert_name: str, rate_threshold: float = 0.002, tg_type: str = "FUNDING_RATE") -> None:
        BaseAlert.__init__(self, alert_name, tg_type=tg_type)
        BinanceApi.__init__(self)

        self._rate_threshold = Decimal(rate_threshold)
        self._exchange_list = None
        self._pass_threshold_exchanges = []

    def _exchange_funding_rate_over_threshold(self, exchange: BinanceExchange) -> None:
        """
        Check whether the exchange funding rate pass threshold
        """
        funding_rate = self.get_future_exchange_funding_rate(exchange)
        if funding_rate and (funding_rate > 0 and funding_rate > self._rate_threshold or
                             funding_rate < 0 and funding_rate < -self._rate_threshold):
            funding_rate = f"{round(funding_rate * 100, 3)}%"
            self._pass_threshold_exchanges.append([exchange, funding_rate])
        sleep(0.5)

    def run(self) -> None:
        """
        This function is used to send bi-hourly alerts of funding rate over threshold
        """
        self._exchange_list = self.get_all_binance_exchanges("FUTURE")
        if not self._exchange_list:
            return
        pool = ThreadPool(8)
        pool.map(self._exchange_funding_rate_over_threshold, self._exchange_list)
        pool.close()

        if self._pass_threshold_exchanges:
            self._tg_bot.send_message(f"Bi-hourly Funding Rate Alert: \n"
                                      f"{self._pass_threshold_exchanges}")
            self._pass_threshold_exchanges = []


if __name__ == '__main__':
    FutureFundingRate(alert_name="funding_rate").run()
