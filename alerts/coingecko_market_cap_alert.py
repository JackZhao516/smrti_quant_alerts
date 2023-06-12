"""
This script is used to send a weekly report of newly deleted and newly added
top n market cap coins
"""

from time import sleep
from datetime import datetime

import pytz

from coin_list.crawl_exchange_list import CrawlExchangeList
from telegram.telegram_api import TelegramBot


class CoingeckoMarketCapReport(CrawlExchangeList):
    def __init__(self, top_n=200, tg_type="CG_MAR_CAP"):
        super().__init__("TEST")
        self.tg_bot = TelegramBot(tg_type)
        self.top_n = top_n
        self.top_n_list = None
        self.run()

    def run(self):
        market_list = self.get_top_n_market_cap_coins(n=self.top_n)
        self.top_n_list = [coin[1] for coin in market_list]
        while True:
            # alerts every Monday 00:00 in Shanghai Time
            # can easily change time and frequency here
            # if you want to change the frequency, remember to change the sleep time
            tz = pytz.timezone('Asia/Shanghai')
            shanghai_now = datetime.now(tz).strftime('%H:%M')
            weekday = datetime.now(tz).weekday()
            if shanghai_now == "00:00" and weekday == 0:
                cur_set = set(self.top_n_list)
                new_list = [coin[1] for coin in self.get_top_n_market_cap_coins(n=self.top_n)]
                new_set = set(new_list)
                deleted_list = []
                added_list = []
                if cur_set != new_set:
                    deleted_list = list(cur_set - new_set)
                    added = new_set - cur_set
                    for i, a in enumerate(new_list):
                        if a in added:
                            added_list.append(a)
                    self.top_n_list = new_list
                self.tg_bot.send_message(f"Top {self.top_n} Market Cap Report: \n"
                                         f"Deleted: {deleted_list}\n"
                                         f"Added: {added_list}\n"
                                         f"(Added in market cap desc order)")
                sleep(60 * 60 * 24 * 7 - 70)
            sleep(60)


if __name__ == '__main__':
    test = CoingeckoMarketCapReport()
    test.run()
