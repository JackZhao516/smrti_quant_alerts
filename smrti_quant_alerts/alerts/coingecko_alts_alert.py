"""
Alert daily for top 500-3000 market cap coins.
"""

from smrti_quant_alerts.get_exchange_list import GetExchangeList


class CGAltsAlert(GetExchangeList):
    def __init__(self, tg_type: str = "ALTS") -> None:
        super().__init__(tg_type)

        # alts coins are from market cap 500 - 3000
        self._alts_coins = []

    def run(self) -> None:
        """
        Alert daily at noon, 12:00
        Alts coin: price change >= 50% in 24 hours
                   Volume change >= 50% in 24 hours, Volume >= 10k in USD
                   Market Cap >= 1M
        """
        # alts coins are from market cap 500 - 3000
        self._alts_coins = self.get_top_n_market_cap_coins(3000)[500:]
        market_info = self.get_coins_market_info(
            self._alts_coins, ["market_cap", "price_change_percentage_24h"])

        if not self._alts_coins or not market_info:
            return
        # first filter: price change >= 50% in 24 hours and market cap >= 1M
        market_info_filtered = []
        for coin_info in market_info:
            if (not coin_info["price_change_percentage_24h"] or
                coin_info["price_change_percentage_24h"] >= 50) \
                    and coin_info["market_cap"] and coin_info["market_cap"] >= 1000000:
                market_info_filtered.append(coin_info["coingecko_coin"])

        # second filter: volume change >= 50% in 24 hours, volume >= 10k in USD
        res = []
        for i, coin in enumerate(market_info_filtered):
            data = self.get_coin_market_info(coin, ["total_volumes"], days=1)
            if not data or len(data["total_volumes"]) < 2:
                continue
            volume_double = data["total_volumes"][-2][-1] == 0.0 or \
                            (data["total_volumes"][-1][-1] / data["total_volumes"][-2][-1]) >= 1.5
            volume_over_10k = data["total_volumes"][-1][-1] >= 10000

            if volume_double and volume_over_10k:
                res.append(coin)

        self._tg_bot.send_message(f"Alts coins bi-hourly alerts "
                                  f"(price increase by 50%, "
                                  f"volume increase by 50% and >= 10k, "
                                  f"market cap >= 100k), "
                                  f"in market cap desc order: {res}")


if __name__ == "__main__":
    alts_alert = CGAltsAlert(tg_type="TEST")
    alts_alert.run()
