"""
This script is used to send a weekly report of newly deleted and newly added
top n market cap coins
"""

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.alerts.utility import run_task_at_daily_time


class CoingeckoMarketCapAlert(GetExchangeList):
    def __init__(self, top_n=200, tg_type="CG_MAR_CAP"):
        super().__init__("TEST")
        self.tg_bot = TelegramBot(tg_type)
        if type(top_n) != list:
            top_n = [top_n]
        self.top_n = top_n
        self.top_n_list = dict()
        for n in self.top_n:
            try:
                self.top_n_list[n] = self.get_top_n_market_cap_coins(n=n)
            except:
                self.top_n_list[n] = []

    def run(self):
        """
        This function is used to send daily report of newly deleted and newly added
        """
        for n in self.top_n:
            cur_set = set(self.top_n_list[n])
            new_list = self.get_top_n_market_cap_coins(n=n)
            if not new_list:
                continue
            new_set = set(new_list)
            deleted_list, added_list = [], []

            if cur_set != new_set:
                deleted_list = list(cur_set - new_set)
                added = new_set - cur_set
                for i, a in enumerate(new_list):
                    if a in added:
                        added_list.append(a)
                self.top_n_list[n] = new_list
            self.tg_bot.send_message(f"Top {n} Market Cap Report: \n"
                                     f"Deleted: {deleted_list}\n"
                                     f"Added: {added_list}\n"
                                     f"(Added in market cap desc order)")


if __name__ == '__main__':
    nums = [100, 200, 300, 400, 500]
    cmc_alert = CoingeckoMarketCapAlert(top_n=nums, tg_type="TEST")
    run_task_at_daily_time(cmc_alert.run, "05:35", duration=60 * 60 * 24)
