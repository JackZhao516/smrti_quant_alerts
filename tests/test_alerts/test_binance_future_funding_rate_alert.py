import unittest
from unittest.mock import patch

from smrti_quant_alerts.alerts import FutureFundingRate
from smrti_quant_alerts.data_type import BinanceExchange


class TestFutureFundingRate(unittest.TestCase):
    def setUp(self) -> None:
        self.alert = FutureFundingRate(rate_threshold=0.001, tg_type="TEST")

    def test_exchange_funding_rate_over_threshold(self) -> None:
        with patch.object(FutureFundingRate, 'get_future_exchange_funding_rate', return_value=0.0002):
            self.alert._exchange_funding_rate_over_threshold(BinanceExchange("BTC", "USDT"))
            self.assertEqual(self.alert._pass_threshold_exchanges, [])

        with patch.object(FutureFundingRate, 'get_future_exchange_funding_rate', return_value=0.002):
            self.alert._exchange_funding_rate_over_threshold(BinanceExchange("BTC", "USDT"))
            self.assertEqual(self.alert._pass_threshold_exchanges, [["BTCUSDT", "0.2%"]])

        with patch.object(FutureFundingRate, 'get_future_exchange_funding_rate', return_value=-0.002):
            self.alert._exchange_funding_rate_over_threshold(BinanceExchange("BTC", "USDT"))
            self.assertEqual(self.alert._pass_threshold_exchanges, [["BTCUSDT", "0.2%"], ["BTCUSDT", "-0.2%"]])

    def test_run(self) -> None:
        return_value = {BinanceExchange("BTC", "USDT"): 0.002, BinanceExchange("ETH", "USDT"): -0.0001}
        with patch.object(self.alert._tg_bot, "send_message") as mock_method:
            with patch.object(FutureFundingRate, 'get_all_binance_exchanges',
                              return_value=[BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")]):
                with patch.object(FutureFundingRate, 'get_future_exchange_funding_rate',
                                  side_effect=lambda x: return_value[x]):
                    self.alert.run()
                    mock_method.assert_called()
                    mock_method.assert_called_once_with(
                        "Bi-hourly Funding Rate Alert: \n"
                        f"[[{BinanceExchange('BTC', 'USDT')}, '0.2%']]")
                    self.assertEqual(self.alert._pass_threshold_exchanges, [])
            mock_method.reset_mock()
            with patch.object(FutureFundingRate, 'get_all_binance_exchanges',
                              return_value=[]):
                self.alert.run()
                mock_method.assert_not_called()
                self.assertEqual(self.alert._pass_threshold_exchanges, [])
