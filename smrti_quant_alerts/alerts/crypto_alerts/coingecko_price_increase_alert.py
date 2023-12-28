import time
from typing import Union, Sequence, List, Dict, Any

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import CoingeckoApi
from smrti_quant_alerts.data_type import CoingeckoCoin


class CoingeckoPriceIncreaseAlert(BaseAlert, CoingeckoApi):
    def __init__(self, top_range: Union[Sequence[int], Sequence[Sequence[int]]] = (0, 500),
                 top_n: int = 100, timeframe: str = "14d", tg_type: str = "CG_PRICE_INCREASE") -> None:
        """
        Alert for the list of <top_range> market cap coins with
        the biggest price increase in the last self._timeframe days

        :param top_range: range of top n coins to send alert for,
                          in the format of (start, end), or [(start, end), ...]
        :param top_n: top n coins to send alert for
        :param timeframe: timeframe string, e.g. "14d", "30d", "3m"
        :param tg_type: telegram type

        """
        BaseAlert.__init__(self, tg_type)
        CoingeckoApi.__init__(self)

        self._top_ranges = top_range if isinstance(top_range[0], Sequence) else [top_range]
        self._top_n = top_n
        self._timeframe = timeframe.lower()

    def get_coins_price_change_percentage(self, coins: List[CoingeckoCoin]) -> List[Dict[str, Any]]:
        """
        Get price change percentage for the list of coins

        :param coins: list of CoingeckoCoin

        :return: [{"coingecko_coin": CoingeckoCoin,
                 "price_change_percentage_<self._timeframe>_in_currency": value}]
        """
        price_change_attribute = f"price_change_percentage_{self._timeframe}_in_currency"
        if self._timeframe in ["1h", "24h", "7d", "14d", "30d", "200d", "1y"]:
            coin_list = self.get_coins_market_info(coins,
                                                   [price_change_attribute],
                                                   price_change_percentage=f"{self._timeframe}")
        else:
            if self._timeframe[-1] == "d":
                days = int(self._timeframe[:-1])
            elif self._timeframe[-1] == "m":
                days = int(self._timeframe[:-1]) * 30
            else:
                days = int(self._timeframe[:-1]) * 365
            coin_list = []
            for i, coin in enumerate(coins):
                coin_list.append({"coingecko_coin": coin})
                price = self.get_coin_history_hourly_close_price(coin, days=days)
                if price and price[-1]:
                    coin_list[i][price_change_attribute] = (price[0] - price[-1]) / price[-1] * 100
                else:
                    coin_list[i][price_change_attribute] = 0.0
            # time.sleep(0.01)
        if not coin_list:
            return []
        for i, coin in enumerate(coin_list):
            if not coin[price_change_attribute]:
                coin_list[i][price_change_attribute] = 0.0
        return coin_list

    def run(self) -> None:
        """
        Send alert for the list of <self._top_n> coins with
        the biggest price increase in the last self._timeframe days

        """
        for top_range in self._top_ranges:
            start, end = top_range
            top_n_list = self.get_top_n_market_cap_coins(n=end)
            if not top_n_list:
                continue
            top_n_list = top_n_list[start:]

            price_change_attribute = f"price_change_percentage_{self._timeframe}_in_currency"
            top_n_list = self.get_coins_price_change_percentage(top_n_list)

            top_n_list.sort(key=lambda x: x[price_change_attribute], reverse=True)
            top_n_list = top_n_list[:self._top_n]

            top_n_list = [f"{x['coingecko_coin']}: {round(x[price_change_attribute], 2)}%"
                          for x in top_n_list if x[price_change_attribute] > 0]
            self._tg_bot.send_message(f"Top {self._top_n} coins in the top {start} - {end} Market Cap Coins "
                                      f"with the biggest price increase in "
                                      f"the last {self._timeframe.upper()} timeframe: {top_n_list}")


if __name__ == '__main__':
    start = time.time()
    CoingeckoPriceIncreaseAlert(top_range=[(0, 50), (50, 100), (100, 300), (300, 1000)], top_n=10,
                                timeframe="3m", tg_type="TEST").run()
    print(time.time() - start)
