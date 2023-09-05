"""
Alert daily for top 500-3000 market cap coins.
"""

import time
import threading
import logging
from datetime import datetime
import pytz

from smrti_quant_alerts.get_exchange_list import GetExchangeList
from smrti_quant_alerts.telegram_api import TelegramBot


class CGAltsAlert:
    def __init__(self):
        self.cel = GetExchangeList("TEST")
        self.tg_bot = TelegramBot("ALTS")

        # alts coins are from market cap 500 - 3000
        self.alts_coins = []
        self.running = True
        self.daily_report()

    def daily_report(self):
        """
        Alert daily at noon, 12:00
        Alts coin: price change >= 50% in 24 hours
                   Volume change >= 50% in 24 hours, Volume >= 10k in USD
                   Market Cap >= 1M
        """
        logging.info("alts_alert start")
        while self.running:
            tz = pytz.timezone('Asia/Shanghai')
            # coingecko update daily price and volume at 8:00
            if datetime.now(tz).strftime('%H:%M') == "08:00":
                start = time.time()
                try:
                    # alts coins are from market cap 500 - 3000
                    self.alts_coins = self.cel.get_top_n_market_cap_coins(3000)[500:]
                    market_info = self.cel.get_coins_market_info(
                        self.alts_coins, ["market_cap", "price_change_percentage_24h"])
                    res = []

                    # first filter: price change >= 50% in 24 hours and market cap >= 1M
                    market_info_filtered = []
                    for coin_info in market_info:
                        if (not coin_info["price_change_percentage_24h"] or
                            coin_info["price_change_percentage_24h"] >= 50) \
                                and coin_info["market_cap"] and coin_info["market_cap"] >= 1000000:
                            market_info_filtered.append(coin_info["coingecko_coin"])

                    # second filter: volume change >= 50% in 24 hours, volume >= 10k in USD
                    for i, coin in enumerate(market_info_filtered):
                        data = self.cel.get_coin_market_info(coin, ["total_volumes"], days=1)
                        if len(data["total_volumes"]) < 2:
                            continue
                        volume_double = data["total_volumes"][-2][-1] == 0.0 or \
                                        (data["total_volumes"][-1][-1] / data["total_volumes"][-2][-1]) >= 1.5
                        volume_over_10k = data["total_volumes"][-1][-1] >= 10000

                        if volume_double and volume_over_10k:
                            res.append(coin)

                    logging.info(res)
                    self.tg_bot.send_message(f"Alts coins daily alerts "
                                             f"(price increase by 50%, "
                                             f"volume increase by 50% and >= 10k, "
                                             f"market cap >= 100k), "
                                             f"in market cap desc order: {res}")

                    time_used = time.time() - start
                    logging.info(f"Time used: {time_used}")
                except Exception:
                    continue
                time.sleep(60 * 60 * 24 - time_used * 3)
            time.sleep(60)


if __name__ == "__main__":
    cgaa = CGAltsAlert()
