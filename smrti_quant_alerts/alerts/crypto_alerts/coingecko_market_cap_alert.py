"""
This script is used to send a weekly report of newly deleted and newly added
top n market cap coins
"""
import time
import logging
from collections import defaultdict
from typing import Union, Iterable

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import CoingeckoApi


class CoingeckoMarketCapAlert(BaseAlert, CoingeckoApi):
    def __init__(self, alert_name: str, top_n: Union[Iterable[int], int] = 200, tg_type: str = "CG_MAR_CAP") -> None:
        BaseAlert.__init__(self, alert_name, tg_type)
        CoingeckoApi.__init__(self)
        if isinstance(top_n, int):
            top_n = [top_n]
        self._top_n = top_n
        self._top_n_list = defaultdict(list)
        for n in self._top_n:
            self._top_n_list[n] = self.get_top_n_market_cap_coins(n=n)

    def run(self) -> None:
        """
        This function is used to send daily report of newly deleted and newly added
        """
        for n in self._top_n:
            cur_set = set(self._top_n_list[n])
            new_list = self.get_top_n_market_cap_coins(n=n)
            if not new_list:
                logging.error(f"get_top_n_market_cap_coins({n}) failed")
                continue
            new_set = set(new_list)
            deleted_list, added_list = [], []

            if cur_set != new_set:
                deleted_list = list(cur_set - new_set)
                for i, coin in enumerate(new_list):
                    if coin not in cur_set:
                        added_list.append(coin)
                self._top_n_list[n] = new_list
            self._tg_bot.send_message(f"Top {n} Market Cap Report: \n"
                                      f"Deleted: {deleted_list}\n"
                                      f"Added: {added_list}\n"
                                      f"(Added in market cap desc order)")
            time.sleep(5)


if __name__ == '__main__':
    nums = [100, 200, 300, 400, 500]
    cmc_alert = CoingeckoMarketCapAlert(alert_name="market_cap", top_n=nums, tg_type="TEST")
    cmc_alert.run()
