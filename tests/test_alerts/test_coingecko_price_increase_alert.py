import unittest
from unittest.mock import patch

from smrti_quant_alerts.alerts import CoingeckoPriceIncreaseAlert
from smrti_quant_alerts.data_type import CoingeckoCoin


class TestPriceIncreaseAlert(unittest.TestCase):
    def test_get_coins_price_change_percentage(self) -> None:
        test_coin = CoingeckoCoin("test", "TEST")
        alert = CoingeckoPriceIncreaseAlert([0, 2], 2, "14d", "TEST")

        return_value = [{"coingecko_coin": test_coin,
                         "price_change_percentage_14d_in_currency": 10}]
        with patch.object(CoingeckoPriceIncreaseAlert, "get_coins_market_info",
                          return_value=return_value):
            res = alert.get_coins_price_change_percentage([test_coin])
            self.assertEqual(res, return_value)

            return_value[0]["price_change_percentage_14d_in_currency"] = None
            res = alert.get_coins_price_change_percentage([test_coin])
            return_value[0]["price_change_percentage_14d_in_currency"] = 0.0
            self.assertEqual(res, return_value)

            del return_value[0]
            res = alert.get_coins_price_change_percentage([test_coin])
            self.assertEqual(res, [])

        return_value = [100, 50]
        with patch.object(CoingeckoPriceIncreaseAlert, "get_coin_history_hourly_close_price",
                          return_value=return_value) as mock_get_price:
            for timeframe, days in zip(["5d", "3m", "2y"], [5, 90, 730]):
                alert = CoingeckoPriceIncreaseAlert([0, 1], 1, timeframe, "TEST")
                res = alert.get_coins_price_change_percentage([test_coin])
                mock_get_price.assert_called_once_with(test_coin, days=days)
                mock_get_price.reset_mock()
                self.assertEqual(res, [{"coingecko_coin": test_coin,
                                        f"price_change_percentage_{timeframe}_in_currency": 100}])

        with patch.object(CoingeckoPriceIncreaseAlert, "get_coin_history_hourly_close_price",
                          return_value=[100, 0]):
            alert = CoingeckoPriceIncreaseAlert([0, 1], 1, "4d", "TEST")
            res = alert.get_coins_price_change_percentage([test_coin])
            self.assertEqual(res, [{"coingecko_coin": test_coin,
                                    "price_change_percentage_4d_in_currency": 0}])

    def test_run(self) -> None:
        coin1, coin2, coin3 = CoingeckoCoin("test1", "TEST1"), CoingeckoCoin("test2", "TEST2"), \
            CoingeckoCoin("test3", "TEST3")
        alert = CoingeckoPriceIncreaseAlert((0, 3), 3, "14d", "TEST")
        with patch.object(alert._tg_bot, "send_message") as mock_send_message:
            with patch.object(CoingeckoPriceIncreaseAlert, "get_top_n_market_cap_coins", return_value=[]):
                alert.run()
                mock_send_message.assert_not_called()

            with patch.object(CoingeckoPriceIncreaseAlert, "get_top_n_market_cap_coins",
                              return_value=[coin1, coin2, coin3]):
                with patch.object(CoingeckoPriceIncreaseAlert, "get_coins_price_change_percentage",
                                  return_value=[{"coingecko_coin": coin1,
                                                 "price_change_percentage_14d_in_currency": 23.873},
                                                {"coingecko_coin": coin2,
                                                 "price_change_percentage_14d_in_currency": 12.098},
                                                {"coingecko_coin": coin3,
                                                 "price_change_percentage_14d_in_currency": -10.013}]):
                    alert.run()
                    mock_send_message.assert_called_once_with("Top 3 coins in the top 0 - 3 Market Cap Coins "
                                                              "with the biggest price increase in the last 14D "
                                                              "timeframe: ['TEST1: 23.87%', 'TEST2: 12.1%']")
