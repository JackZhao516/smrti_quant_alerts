import time
from typing import Union, Sequence, List, Dict, Any, Iterable

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import CoingeckoApi
from smrti_quant_alerts.data_type import CoingeckoCoin
from smrti_quant_alerts.alerts.crypto_alerts.utility import send_coins_info_to_telegram


class CoingeckoPriceIncreaseAlert(BaseAlert, CoingeckoApi):
    def __init__(self, alert_name: str, top_range: Union[Sequence[int], Sequence[Sequence[int]]] = (0, 500),
                 top_n: int = 100, timeframe: str = "14d", coin_info: bool = True,
                 tg_type: str = "CG_PRICE_INCREASE") -> None:
        """
        Alert for the list of <top_range> market cap coins with
        the biggest price increase in the last self._timeframe days

        :param top_range: range of top n coins to send alert for,
                          in the format of (start, end), or [(start, end), ...]
        :param top_n: top n coins to send alert for
        :param timeframe: timeframe string, e.g. "14d", "30d", "3m"
        :param  coin_info: whether send the coin info csv file to tg or not
        :param tg_type: telegram type

        """
        BaseAlert.__init__(self, alert_name, tg_type)
        CoingeckoApi.__init__(self)

        self._top_ranges = top_range if isinstance(top_range[0], Sequence) else [top_range]
        self._top_n = top_n
        self._timeframe = timeframe.lower()
        self._coin_info = coin_info

    def get_coins_price_change_percentage(self, coins: List[CoingeckoCoin]) -> Dict[CoingeckoCoin, float]:
        """
        Get price change percentage for the list of coins

        :param coins: list of CoingeckoCoin

        :return: {CoingeckoCoin: <price_change_percentage>}
        """
        price_change_attribute = f"price_change_percentage_{self._timeframe}_in_currency"
        if self._timeframe in ["1h", "24h", "7d", "14d", "30d", "200d", "1y"]:
            coin_list = self.get_coins_market_info(coins,
                                                   [price_change_attribute],
                                                   price_change_percentage=f"{self._timeframe}")
            coin_price_change_map = {coin["coingecko_coin"]: coin[price_change_attribute] for coin in coin_list
                                     if coin[price_change_attribute]} if coin_list else {}
        else:
            if self._timeframe[-1] == "d":
                days = int(self._timeframe[:-1])
            elif self._timeframe[-1] == "m":
                days = int(self._timeframe[:-1]) * 30
            else:
                days = int(self._timeframe[:-1]) * 365
            coin_price_change_map = {}
            for coin in coins:
                price = self.get_coin_history_hourly_close_price(coin, days=days)
                if price and price[-1]:
                    coin_price_change_map[coin] = (price[0] - price[-1]) / price[-1] * 100

        return coin_price_change_map

    def filter_top_n_coins_with_daily_volume_over_threshold(
            self, coins: Iterable[CoingeckoCoin], threshold: float = 1000000) -> List[CoingeckoCoin]:
        """
        Filter out coins with daily volume over the threshold

        :param coins: list of CoingeckoCoin
        :param threshold: threshold for daily volume

        :return: list of CoingeckoCoin, in the order of the input coins
        """
        res = []
        for coin in coins:
            data = self.get_coin_market_info(coin, ["total_volumes"], days=1)
            if data and data["total_volumes"][0][-1] >= threshold:
                res += [coin]
                if len(res) >= self._top_n:
                    return res
        return res

    def run(self) -> None:
        """
        Send alert for the list of <self._top_n> coins with
        the biggest price increase in the last self._timeframe days

        """
        top_n_set = set()
        for top_range in self._top_ranges:
            start, end = top_range
            top_n_list = self.get_top_n_market_cap_coins(n=end)
            if not top_n_list:
                continue
            top_n_list = top_n_list[start:]
            top_n_map = self.get_coins_price_change_percentage(top_n_list)
            top_n_list = self.filter_top_n_coins_with_daily_volume_over_threshold(
                [x[0] for x in sorted(top_n_map.items(), key=lambda x: x[1], reverse=True)], threshold=1000000)
            top_n_str = []

            for coin in top_n_list:
                if top_n_map[coin] <= 0:
                    break
                top_n_set.add(coin)
                top_n_str.append(f"{coin}: {round(top_n_map[coin], 2)}%")

            self._tg_bot.send_message(f"Top {self._top_n} coins in the top {start} - {end} Market Cap Coins "
                                      f"with the biggest price increase in "
                                      f"the last {self._timeframe.upper()} timeframe: {top_n_str}")
        if self._coin_info:
            send_coins_info_to_telegram(top_n_set, self._tg_bot, f"price_increase_{self._timeframe}")


if __name__ == '__main__':
    start = time.time()
    CoingeckoPriceIncreaseAlert(alert_name="price_increase_alert", top_range=[(0, 300), (300, 500), (500, 1000)],
                                top_n=40, timeframe="3m", tg_type="TEST").run()
    print(time.time() - start)
