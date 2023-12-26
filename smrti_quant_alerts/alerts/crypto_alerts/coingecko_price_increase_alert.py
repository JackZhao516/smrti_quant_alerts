from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import CoingeckoApi


class CoingeckoPriceIncreaseAlert(BaseAlert, CoingeckoApi):
    def __init__(self, top_n: int = 500, timeframe_in_days: int = 14, tg_type: str = "CG_PRICE_INCREASE") -> None:
        BaseAlert.__init__(self, tg_type)
        CoingeckoApi.__init__(self)
        self._top_n = top_n
        self._timeframe = timeframe_in_days

    def run(self) -> None:
        """
        Send alert for the list of 100 coins with the biggest price increase in the last self._timeframe days
        """
        top_n_list = self.get_top_n_market_cap_coins(n=self._top_n)
        if not top_n_list:
            return

        price_change_attribute = f"price_change_percentage_{self._timeframe}d_in_currency"
        top_n_list = self.get_coins_market_info(top_n_list,
                                                [price_change_attribute],
                                                price_change_percentage=f"{self._timeframe}d")
        if not top_n_list:
            return
        for i, coin in enumerate(top_n_list):
            if not coin[price_change_attribute]:
                top_n_list[i][price_change_attribute] = 0.0

        top_n_list.sort(key=lambda x: x[price_change_attribute], reverse=True)
        top_n_list = [f"{x['coingecko_coin']}: {round(x[price_change_attribute], 2)}%"
                      for x in top_n_list if x[price_change_attribute] > 0]
        self._tg_bot.send_message(f"Top 100 coins in the top {self._top_n} Market Cap Coins "
                                  f"with the biggest price increase in "
                                  f"the last {self._timeframe} days: {top_n_list[:100]}")


if __name__ == '__main__':
    CoingeckoPriceIncreaseAlert(top_n=500, timeframe_in_days=30, tg_type="TEST").run()
