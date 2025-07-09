import unittest
from unittest.mock import patch

from smrti_quant_alerts.alerts import CGAltsAlert
from smrti_quant_alerts.data_type import CoingeckoCoin


class TestCGAltsAlert(unittest.TestCase):
    def setUp(self) -> None:
        self.alert = CGAltsAlert("<alts_alert_example_name>", tg_type="TEST")

    def test_run(self) -> None:
        with patch.object(self.alert._tg_bot, "send_message") as mock_send_message:
            coin1, coin2, coin3, coin4 = CoingeckoCoin("test1", "TEST1"), CoingeckoCoin("test2", "TEST2"), \
                CoingeckoCoin("test3", "TEST3"), CoingeckoCoin("test4", "TEST4")
            return_value = {
                coin1: {"total_volumes": [[0, 500], [0, 10000]]},
                coin4: {"total_volumes": [[0, 1]]}
            }
            with patch.object(CGAltsAlert, "get_top_n_market_cap_coins") as mock_get_coins, \
                    patch.object(CGAltsAlert, "get_coins_market_info") as mock_get_coins_market_info, \
                    patch.object(CGAltsAlert, "get_coin_market_info") as mock_get_coin_market_info:
                mock_get_coins.return_value = [CoingeckoCoin("", "") for _ in range(500)] + \
                                              [coin1, coin2, coin3, coin4]
                mock_get_coins_market_info.return_value = [
                    {"coingecko_coin": coin1, "market_cap": 10000000, "price_change_percentage_24h": 50},
                    {"coingecko_coin": coin2, "market_cap": 10000000, "price_change_percentage_24h": 49},
                    {"coingecko_coin": coin3, "market_cap": 10000, "price_change_percentage_24h": 51},
                    {"coingecko_coin": coin4, "market_cap": 10000000, "price_change_percentage_24h": 60}]
                mock_get_coin_market_info.side_effect = lambda coin, _, **kwargs: return_value[coin]

                self.alert.run()
                mock_send_message.assert_called()
                mock_send_message.assert_called_once_with(f"Alts coins bi-hourly alerts "
                                                          f"(price increase by 50%, "
                                                          f"volume increase by 50% and >= 10k, "
                                                          f"market cap >= 100k), "
                                                          f"in market cap desc order: {[coin1]}")
                mock_send_message.reset_mock()

            with patch.object(self.alert, "get_top_n_market_cap_coins", return_value=[]):
                self.alert.run()
                mock_send_message.assert_not_called()
