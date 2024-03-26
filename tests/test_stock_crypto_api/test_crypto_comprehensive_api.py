import os
import unittest
from unittest import mock
from decimal import Decimal


from smrti_quant_alerts.stock_crypto_api import CryptoComprehensiveApi
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class TestCryptoComprehensiveApi(unittest.TestCase):
    def setUp(self) -> None:
        with mock.patch("smrti_quant_alerts.stock_crypto_api.CryptoComprehensiveApi."
                        "_match_binance_exchange_to_coingecko_coins",
                        side_effect=lambda: print("test")):
            self.crypto_comprehensive_api = CryptoComprehensiveApi()

    def test_get_exclude_coins(self) -> None:
        with mock.patch("smrti_quant_alerts.stock_crypto_api.BinanceApi.get_exclude_coins",
                        return_value={BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                      BinanceExchange("USDT", "BTC"), BinanceExchange("TEST", "TEST")}):
            with mock.patch("smrti_quant_alerts.stock_crypto_api.crypto_coingecko_api.CoingeckoApi.get_exclude_coins",
                            return_value={CoingeckoCoin("tether", "USDT")}):
                exclude_coins = self.crypto_comprehensive_api.get_exclude_coins([])
                self.assertEqual(exclude_coins, {BinanceExchange("BTC", "ETH"), BinanceExchange("BTC", "USDT"),
                                                 BinanceExchange("USDT", "BTC"), BinanceExchange("TEST", "TEST"),
                                                 CoingeckoCoin("tether", "USDT")})

    def test_match_binance_exchange_to_coingecko_coins(self) -> None:
        BinanceExchange.symbol_base_coingecko_id_map = {}
        with mock.patch("pycoingecko.CoinGeckoAPI.get_exchanges_tickers_by_id", return_value=[]):
            self.crypto_comprehensive_api._match_binance_exchange_to_coingecko_coins()
            self.assertEqual(BinanceExchange.symbol_base_coingecko_id_map, {})

        return_value = {0: {"tickers": [{"base": "BTC", "coin_id": "bitcoin"}]}, 1: {}}
        with mock.patch("pycoingecko.CoinGeckoAPI.get_exchanges_tickers_by_id",
                        side_effect=lambda id, coin_ids, page: return_value[page]):
            self.crypto_comprehensive_api._match_binance_exchange_to_coingecko_coins()
            self.assertEqual(BinanceExchange.symbol_base_coingecko_id_map, {"BTC": "bitcoin"})

    def test_get_coins_with_daily_volume_threshold_later_than_2023(self) -> None:
        with mock.patch.object(CryptoComprehensiveApi, 'get_all_coingecko_coins',
                               return_value=[CoingeckoCoin("alt", "ALT")]):
            with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets",
                            return_value=[{"id": "alt", "symbol": "ALT", "atl_date": "2023",
                                           "ath_date": "2023", "total_volume": 1000},
                                          {"id": "tether", "symbol": "USDT", "atl_date": "2023",
                                           "ath_date": "2021", "total_volume": 1000000},
                                          {"id": "test", "symbol": "TEST", "total_volume": 1000000,
                                           "atl_date": "2023", "ath_date": None}]):
                with mock.patch.object(CryptoComprehensiveApi, "get_coin_info",
                                       return_value={"genesis_date": "2023"}):
                    with mock.patch.object(CryptoComprehensiveApi, 'get_all_binance_exchanges',
                                           return_value=[BinanceExchange("ALT", "USDT"),
                                                         BinanceExchange("ALT", "TEST")]):

                        binance_exchanges, coingecko_coins = \
                            self.crypto_comprehensive_api.get_coins_with_daily_volume_threshold_later_than_2023(100)
                        self.assertEqual(binance_exchanges, [BinanceExchange("ALT", "USDT")])
                        self.assertEqual(coingecko_coins, [])

                    with mock.patch.object(CryptoComprehensiveApi, 'get_all_binance_exchanges',
                                           return_value=[BinanceExchange("TEST", "USDT")]):
                        self.crypto_comprehensive_api._reset_timestamp()
                        binance_exchanges, coingecko_coins = \
                            self.crypto_comprehensive_api.get_coins_with_daily_volume_threshold_later_than_2023(100)
                        self.assertEqual(binance_exchanges, [])
                        self.assertEqual(coingecko_coins, [CoingeckoCoin("alt", "ALT")])

                    with mock.patch.object(CryptoComprehensiveApi, 'get_all_binance_exchanges',
                                           return_value=Exception):
                        binance_exchanges, coingecko_coins = \
                            self.crypto_comprehensive_api.get_coins_with_daily_volume_threshold_later_than_2023(100)
                        self.assertEqual(binance_exchanges, [])
                        self.assertEqual(coingecko_coins, [CoingeckoCoin("alt", "ALT")])

    def test_get_top_market_cap_coins_with_volume_threshold(self):
        return_value = {"ALT": {"total_volumes": [[0, 100], [0, 200]]},
                        "BTC": {"total_volumes": [[0, 100], [0, 2]]},
                        "USDT": {"total_volumes": [[0, 100], [0, 200]]},
                        "TEST": {"total_volumes": [[0, 100], [0, 200]]}}
        with mock.patch.object(CryptoComprehensiveApi, 'get_top_n_market_cap_coins',
                               return_value=[CoingeckoCoin("alt", "ALT"), CoingeckoCoin("bitcoin", "BTC"),
                                             CoingeckoCoin("tether", "USDT"), CoingeckoCoin("test", "TEST")]):
            with mock.patch.object(CryptoComprehensiveApi, "get_all_binance_exchanges",
                                   return_value=[BinanceExchange("ALT", "FDUSD"), BinanceExchange("ALT", "BTC"),
                                                 BinanceExchange("ALT", "ETH"), BinanceExchange("TEST", "USDT")]):
                with mock.patch("smrti_quant_alerts.stock_crypto_api.CoingeckoApi.get_coin_market_info",
                                side_effect=lambda coin, _, **kwargs: return_value[coin.coin_symbol]):

                    binance_exchanges, coingecko_coins = \
                        self.crypto_comprehensive_api.get_top_market_cap_coins_with_volume_threshold(100, 50, 50)
                    self.assertEqual(set(binance_exchanges),
                                     {BinanceExchange("ALT", "FDUSD"), BinanceExchange("ALT", "BTC"),
                                      BinanceExchange("ALT", "ETH"), BinanceExchange("TEST", "USDT")})
                    self.assertEqual(coingecko_coins, [CoingeckoCoin("tether", "USDT")])

                with mock.patch("smrti_quant_alerts.stock_crypto_api.CoingeckoApi.get_coin_market_info",
                                side_effect=Exception):
                    binance_exchanges, coingecko_coins = \
                        self.crypto_comprehensive_api.get_top_market_cap_coins_with_volume_threshold(100, 50, 50)
                    self.assertEqual(binance_exchanges, [])
                    self.assertEqual(coingecko_coins, [])

    def test_get_coins_with_weekly_volume_increase(self) -> None:
        return_value = {"ALT": {"total_volumes": [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0],
                                                  [0, 0], [0, 0], [0, 100], [0, 200], [0, 300],
                                                  [0, 400], [0, 500], [0, 600], [0, 700]]},
                        "BTC": {"total_volumes": [[0, 1], [0, 0], [0, 0], [0, 0], [0, 0],
                                                  [0, 0], [0, 0], [0, 100], [0, 200], [0, 300],
                                                  [0, 400], [0, 500], [0, 600], [0, 700]]},
                        "USDT": {"total_volumes": [[0, 10000000000], [0, 0], [0, 0], [0, 0], [0, 0],
                                                   [0, 0], [0, 0], [0, 100], [0, 200], [0, 300],
                                                   [0, 400], [0, 500], [0, 600], [0, 700]]},
                        "TEST": {"total_volumes": [[0, 2], [0, 0], [0, 0], [0, 0], [0, 0],
                                                   [0, 0], [0, 0], [0, 100], [0, 200], [0, 300],
                                                   [0, 400], [0, 500], [0, 600], [0, 700]]}}
        with mock.patch.object(CryptoComprehensiveApi, 'get_top_n_market_cap_coins',
                               return_value=[CoingeckoCoin("alt", "ALT"), CoingeckoCoin("bitcoin", "BTC"),
                                             CoingeckoCoin("tether", "USDT"), CoingeckoCoin("test", "TEST")]):
            with mock.patch.object(CryptoComprehensiveApi, "get_all_binance_exchanges",
                                   return_value=[BinanceExchange("ALT", "FDUSD"), BinanceExchange("ALT", "BTC"),
                                                 BinanceExchange("ALT", "ETH"), BinanceExchange("TEST", "TEST"),
                                                 BinanceExchange("BTC", "USDT")]):
                with mock.patch("smrti_quant_alerts.stock_crypto_api.CoingeckoApi.get_coin_market_info",
                                side_effect=lambda coin, _, **kwargs: return_value[coin.coin_symbol]):
                    binance_exchanges, coingecko_coins = \
                        self.crypto_comprehensive_api.get_coins_with_weekly_volume_increase(1.1, 50)
                    self.assertEqual(set(binance_exchanges),
                                     {BinanceExchange("ALT", "FDUSD"), BinanceExchange("ALT", "BTC"),
                                      BinanceExchange("ALT", "ETH"), BinanceExchange("BTC", "USDT")})
                    self.assertEqual(coingecko_coins, [CoingeckoCoin("test", "TEST")])

                with mock.patch("smrti_quant_alerts.stock_crypto_api.CoingeckoApi.get_coin_market_info",
                                return_value=Exception):
                    binance_exchanges, coingecko_coins = \
                        self.crypto_comprehensive_api.get_coins_with_weekly_volume_increase(1.1, 50)
                    self.assertEqual(binance_exchanges, [])
                    self.assertEqual(coingecko_coins, [])
