"""
This script is used to send a weekly report of newly deleted and newly added
top n market cap coins
"""

from time import sleep, time
from datetime import datetime

import pytz

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot


class CoingeckoMarketCapReport(GetExchangeList):
    def __init__(self, top_n=200, tg_type="CG_MAR_CAP"):
        super().__init__("TEST")
        self.tg_bot = TelegramBot(tg_type)
        if type(top_n) != list:
            top_n = [top_n]
        self.top_n = top_n
        self.top_n_list = dict()
        self.run()

    def run(self):
        for n in self.top_n:
            self.top_n_list[n] = self.get_top_n_market_cap_coins(n=n)
        while True:
            # alerts every day 00:00 in Shanghai Time
            # can easily change time and frequency here
            # if you want to change the frequency, remember to change the sleep time
            tz = pytz.timezone('Asia/Shanghai')
            if datetime.now(tz).strftime('%H:%M') == "00:00":
                start = time()
                try:
                    for n in self.top_n:
                        cur_set = set(self.top_n_list[n])
                        new_list = self.get_top_n_market_cap_coins(n=n)
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
                except Exception:
                    continue
                sleep(60 * 60 * 24 - 3 * (time() - start))
            sleep(60)


if __name__ == '__main__':
    test = CoingeckoMarketCapReport()
    test.run()
