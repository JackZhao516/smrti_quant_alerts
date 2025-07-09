import unittest
from unittest.mock import patch

from smrti_quant_alerts.alerts import CoingeckoMarketCapAlert
from smrti_quant_alerts.data_type import CoingeckoCoin


class TestMarketCapAlert(unittest.TestCase):
    def test_run(self) -> None:
        coin1, coin2, coin3, coin4 = CoingeckoCoin("test1", "TEST1"), CoingeckoCoin("test2", "TEST2"), \
            CoingeckoCoin("test3", "TEST3"), CoingeckoCoin("test4", "TEST4")

        with patch.object(CoingeckoMarketCapAlert, "get_top_n_market_cap_coins") as mock_get_coins:
            top_coins = [coin1, coin2, coin4]
            mock_get_coins.return_value = top_coins
            alert = CoingeckoMarketCapAlert("<market_cap_example_name>", 3)
            self.assertEqual(alert._top_n_list[3], top_coins)

            with patch.object(alert._tg_bot, "send_message") as mock_send_message:
                mock_get_coins.return_value = [coin1, coin3, coin4]
                alert.run()
                mock_send_message.assert_called()
                mock_send_message.assert_called_once_with(f"Top 3 Market Cap Report: \n"
                                                          f"Deleted: {[coin2]}\n"
                                                          f"Added: {[coin3]}\n"
                                                          f"(Added in market cap desc order)")
                mock_send_message.reset_mock()
                mock_get_coins.return_value = []
                alert.run()
                mock_send_message.assert_not_called()
