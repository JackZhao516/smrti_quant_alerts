import time
import threading
from datetime import datetime
import pytz

from crawl_exchange_list import CrawlExchangeList
from telegram_api import TelegramBot
from error import error_handling


class CGAltsAlert:
    def __init__(self):
        self.cel = CrawlExchangeList("TEST")
        self.tg_bot = TelegramBot("TEST")

        # alts coins are from market cap 500 - 3000
        self.alts_coins = []
        self.running = True
        self.thread = threading.Thread(target=self.daily_report)
        self.thread.start()

    @error_handling("coingecko", "daily_report")
    def daily_report(self):
        """
        Alert daily at noon, 12:00
        Alts coin: price change >= 100% in 24 hours
                   Volume change >= 100% in 24 hours, Volume >= 10k in USD
                   Market Cap >= 1M
        """

        while self.running:
            tz = pytz.timezone('Asia/Shanghai')
            shanghai_now = datetime.now(tz).strftime('%H:%M')
            # coingecko update daily price and volume at 8:00
            if shanghai_now == "8:00":
                start = time.time()
                # alts coins are from market cap 500 - 3000
                self.alts_coins = self.cel.get_top_n_market_cap_coins(3000)[500:]

                res = []
                for coin_id, coin_symbol in self.alts_coins:
                    data = self.cel.cg.get_coin_market_chart_by_id(
                        id=coin_id, vs_currency="usd", days=1, interval="daily")
                    if len(data["prices"]) < 2:
                        continue
                    price_double = data["prices"][-2][-1] == 0.0 or \
                                   (data["prices"][-1][-1] / data["prices"][-2][-1]) >= 2.0
                    volume_double = data["total_volumes"][-2][-1] == 0.0 or \
                                    (data["total_volumes"][-1][-1] / data["total_volumes"][-2][-1]) >= 2.0
                    volume_over_10k = data["total_volumes"][-1][-1] >= 10000
                    market_cap_over_1m = data["market_caps"][-1][-1] >= 1000000
                    if price_double and volume_double and volume_over_10k and market_cap_over_1m:
                        res.append(coin_symbol)

                self.tg_bot.send_message(f"Alts coins daily alerts "
                                         f"(price doubled, volume doubled and >= 10k, "
                                         f"market cap >= 100k), "
                                         f"in market cap desc order: {res}")
                end = time.time()
                print(f"Time used: {end - start}")
                time.sleep(60 * 60 * 24 - 100)
            time.sleep(1)


if __name__ == "__main__":
    cgaa = CGAltsAlert()

