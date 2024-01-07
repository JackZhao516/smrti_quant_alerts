import os
import unittest
from unittest import mock
from decimal import Decimal

from binance.spot import Spot
from binance.um_futures import UMFutures

from smrti_quant_alerts.stock_crypto_api import BinanceApi
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class TestCryptoBinanceApi(unittest.TestCase):
    def setUp(self) -> None:
        self.binance_api = BinanceApi()

    def test_update_active_binance_spot_exchanges(self) -> None:
        self.binance_api._reset_timestamp()
        with mock.patch.object(BinanceApi, 'get_all_binance_exchanges', return_value=["test", "test1"]):
            self.binance_api._update_active_binance_spot_exchanges()
            self.assertEqual(self.binance_api.active_binance_spot_exchanges, ["test", "test1"])
            self.assertEqual(self.binance_api.active_binance_spot_exchanges_set, {"test", "test1"})

    def test_get_exclude_coins(self) -> None:
        Config.PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
        with mock.patch.object(BinanceApi, 'get_all_binance_exchanges',
                               return_value=[BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                             BinanceExchange("TEST", "TEST"), CoingeckoCoin("tether", "USDT"),
                                             BinanceExchange("USDT", "BTC"), BinanceExchange("ALT", "USDT")]):
            exclude_coins = self.binance_api.get_exclude_coins([])
            self.assertEqual(exclude_coins, {BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                             BinanceExchange("USDT", "BTC"), BinanceExchange("TEST", "TEST")})

            exclude_coins = self.binance_api.get_exclude_coins([BinanceExchange("ALT", "USDT")])
            self.assertEqual(exclude_coins, {BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                             BinanceExchange("USDT", "BTC"), BinanceExchange("TEST", "TEST"),
                                             BinanceExchange("ALT", "USDT")})

            exclude_coins = self.binance_api.get_exclude_coins([CoingeckoCoin("alt", "ALT")])
            self.assertEqual(exclude_coins, {BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                             BinanceExchange("USDT", "BTC"), BinanceExchange("TEST", "TEST"),
                                             BinanceExchange("ALT", "USDT")})

    def test_get_all_binance_exchanges(self) -> None:
        return_value = {
            "symbols": [{
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDT"
            }, {
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "USDT"
            }, {
                "status": "NOT TRADING",
                "baseAsset": "TEST",
                "quoteAsset": "TEST"
            }]
        }
        with mock.patch.object(Spot, 'exchange_info', return_value=return_value):
            self.assertEqual(set(self.binance_api.get_all_binance_exchanges()),
                             {BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")})

        with mock.patch.object(Spot, 'exchange_info', side_effect=Exception):
            self.assertEqual(self.binance_api.get_all_binance_exchanges(), [])

    def test_get_all_spot_exchanges_in_usdt_fdusd_btc(self) -> None:
        return_value = {
            "symbols": [{
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDT"
            }, {
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "FDUSD"
            }, {
                "status": "TRADING",
                "baseAsset": "TEST",
                "quoteAsset": "TEST"
            }]
        }
        with mock.patch.object(Spot, 'exchange_info', return_value=return_value):
            self.assertEqual(set(self.binance_api.get_all_spot_exchanges_in_usdt_fdusd_btc()),
                             {BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "FDUSD")})

        self.binance_api._reset_timestamp()

        with mock.patch.object(Spot, 'exchange_info', side_effect=Exception):
            self.assertEqual(self.binance_api.get_all_spot_exchanges_in_usdt_fdusd_btc(), [])

    def test_get_future_exchange_funding_rate(self) -> None:
        self.assertEqual(self.binance_api.get_future_exchange_funding_rate(None), Decimal(0))

        with mock.patch.object(UMFutures, 'mark_price', return_value={"lastFundingRate": "-0.002"}):
            self.assertEqual(self.binance_api.get_future_exchange_funding_rate(BinanceExchange("BTC", "USDT")),
                             Decimal("-0.002"))

        with mock.patch.object(UMFutures, 'mark_price', side_effect=Exception):
            self.assertEqual(self.binance_api.get_future_exchange_funding_rate(BinanceExchange("BTC", "USDT")),
                             Decimal(0))

        with mock.patch.object(UMFutures, 'mark_price', return_value={"lastFundingRate": None}):
            self.assertEqual(self.binance_api.get_future_exchange_funding_rate(BinanceExchange("BTC", "USDT")),
                             Decimal(0))

    def test_get_exchange_current_price(self) -> None:
        self.assertEqual(self.binance_api.get_exchange_current_price(None), Decimal(0))

        with mock.patch.object(Spot, 'ticker_price', return_value={"price": "100"}):
            self.assertEqual(self.binance_api.get_exchange_current_price(BinanceExchange("BTC", "USDT")),
                             Decimal("100"))

        with mock.patch.object(Spot, 'ticker_price', side_effect=Exception):
            self.assertEqual(self.binance_api.get_exchange_current_price(BinanceExchange("BTC", "USDT")),
                             Decimal(0))

        with mock.patch.object(Spot, 'ticker_price', return_value=[{"price": "100"}]):
            self.assertEqual(self.binance_api.get_exchange_current_price(BinanceExchange("BTC", "USDT")),
                             Decimal("100"))

    def test_get_exchange_history_hourly_close_price(self) -> None:
        self.assertEqual(self.binance_api.get_exchange_history_hourly_close_price(None), [])

        price = [[i] * 5 for i in range(24)]
        return_value = [Decimal(i) for i in range(23, -1, -1)]

        with mock.patch.object(Spot, 'klines', return_value=price):
            self.assertEqual(self.binance_api.get_exchange_history_hourly_close_price(BinanceExchange("T", "T"), 1),
                             return_value)

        with mock.patch.object(Spot, 'klines', side_effect=Exception):
            self.assertEqual(self.binance_api.get_exchange_history_hourly_close_price(BinanceExchange("T", "T")),
                             [])
