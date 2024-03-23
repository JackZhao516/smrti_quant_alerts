import os
import unittest
from unittest import mock
from decimal import Decimal


from smrti_quant_alerts.stock_crypto_api import CoingeckoApi
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin


class TestCryptoCoingeckoApi(unittest.TestCase):
    def setUp(self) -> None:
        self.coingecko_api = CoingeckoApi()

    def test_get_exclude_coins(self) -> None:
        Config.PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
        CoingeckoCoin.symbol_id_map = {}
        with mock.patch.object(CoingeckoApi, 'get_all_coingecko_coins',
                               return_value=[CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("tether", "USDT"),
                                             CoingeckoCoin("test", "TEST"), CoingeckoCoin("alt", "ALT"),
                                             BinanceExchange("TEST", "TEST")]):
            exclude_coins = self.coingecko_api.get_exclude_coins([])
            self.assertEqual(exclude_coins, {CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("tether", "USDT"),
                                             CoingeckoCoin("test", "TEST")})

            exclude_coins = self.coingecko_api.get_exclude_coins([BinanceExchange("ALT", "USDT")])
            self.assertEqual(exclude_coins, {CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("tether", "USDT"),
                                             CoingeckoCoin("test", "TEST"), CoingeckoCoin("alt", "ALT")})

            exclude_coins = self.coingecko_api.get_exclude_coins([CoingeckoCoin("alt", "ALT")])
            self.assertEqual(exclude_coins, {CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("tether", "USDT"),
                                             CoingeckoCoin("test", "TEST"), CoingeckoCoin("alt", "ALT")})

    def test_get_all_coingecko_coins(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_list", return_value=[{
            "id": "bitcoin",
            "symbol": "BTC"
        }, {
            "id": "ethereum",
            "symbol": "ETH"
        }, {
            "id": "test",
            "symbol": "TEST"
        }]):
            self.assertEqual(self.coingecko_api.get_all_coingecko_coins(),
                             [CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("ethereum", "ETH"),
                              CoingeckoCoin("test", "TEST")])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_list", return_value=[]):
            self.assertEqual(self.coingecko_api.get_all_coingecko_coins(), [])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_list", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_all_coingecko_coins(), [])

    def test_get_top_n_market_cap_coins(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets", return_value=[{
            "id": "bitcoin",
            "symbol": "BTC",
        }, {
            "id": "ethereum",
            "symbol": "ETH",
        }, {
            "id": "test",
            "symbol": "TEST",
        }]):
            self.assertEqual(self.coingecko_api.get_top_n_market_cap_coins(),
                             [CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("ethereum", "ETH"),
                              CoingeckoCoin("test", "TEST")])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets", return_value=[]):
            self.assertEqual(self.coingecko_api.get_top_n_market_cap_coins(), [])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_top_n_market_cap_coins(), [])

    def test_get_coins_market_info(self) -> None:
        return_values = [{
            "id": "bitcoin",
            "symbol": "BTC",
            "current_price": 10000,
            "market_cap": 1000
        }, {
            "id": "ethereum",
            "symbol": "ETH",
            "current_price": 1000,
            "market_cap": 100
        }, {
            "id": "test",
            "symbol": "TEST",
            "current_price": 1,
            "market_cap": 10
        }]
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets",
                        return_value=return_values):
            self.assertEqual(
                self.coingecko_api.get_coins_market_info([CoingeckoCoin("bitcoin", "BTC"),
                                                          CoingeckoCoin("ethereum", "ETH"),
                                                          CoingeckoCoin("test", "TEST")],
                                                         ["current_price", "market_cap"]),
                [{"coingecko_coin": CoingeckoCoin("bitcoin", "BTC"), "current_price": 10000, "market_cap": 1000},
                 {"coingecko_coin": CoingeckoCoin("ethereum", "ETH"), "current_price": 1000, "market_cap": 100},
                 {"coingecko_coin": CoingeckoCoin("test", "TEST"), "current_price": 1, "market_cap": 10}])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_coins_market_info([CoingeckoCoin("test", "TEST")],
                                                                      ["current_price", "market_cap"]), [])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_markets", return_value=[]):
            self.assertEqual(self.coingecko_api.get_coins_market_info([CoingeckoCoin("test", "TEST")],
                                                                      ["current_price", "market_cap"]), [])

    def test_get_coin_info(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_by_id", return_value={
            "id": "bitcoin",
            "symbol": "BTC",
            "name": "Bitcoin",
            "links": {"homepage": ["https://bitcoin.org/"]},
            "description": {"en": "Bitcoin (BTC) is a cryptocurrency ."},
            "genesis_date": "2009-01-03",
            "market_cap_rank": 10
        }):
            self.assertEqual(self.coingecko_api.get_coin_info(CoingeckoCoin("bitcoin", "BTC")),
                             {"symbol": CoingeckoCoin("bitcoin", "BTC"), "name": "Bitcoin",
                              "description": "Bitcoin (BTC) is a cryptocurrency .",
                              "website": "https://bitcoin.org/", "genesis_date": "2009-01-03",
                              "market_cap_rank": 10})

            self.assertEqual(self.coingecko_api.get_coin_info(), {"symbol": "", "name": "", "description": "",
                                                                  "website": "", "genesis_date": "",
                                                                  "market_cap_rank": ""})

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_by_id", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_coin_info(CoingeckoCoin("bitcoin", "BTC")), {
                "symbol": "", "name": "", "description": "",
                "website": "", "genesis_date": "", "market_cap_rank": ""
            })

    def test_get_coins_chain_info(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coins_list", return_value=[
            {"id": "zyrri", "symbol": "zyr", "name": "Zyrri", "platforms": {}},
            {"id": "zyx", "symbol": "zyx", "name": "ZYX",
             "platforms": {
              "ethereum": "0xf974b5f9ac9c6632fee8b76c61b0242ce69c839d",
              "arbitrum-one": "0x377c6e37633e390aef9afb4f5e0b16689351eed4",
              "binance-smart-chain": "0x377c6e37633e390aef9afb4f5e0b16689351eed4"}}]):
            self.assertEqual(self.coingecko_api.get_coins_chain_info([]), {})
            self.assertEqual(self.coingecko_api.get_coins_chain_info([CoingeckoCoin("zyrri", "Zyrri")]),
                             {CoingeckoCoin("zyrri", "Zyrri"): ""})
            self.assertEqual(self.coingecko_api.get_coins_chain_info([CoingeckoCoin("zyx", "zyx")]),
                             {CoingeckoCoin("zyx", "zyx"): "ethereum, arbitrum-one, binance-smart-chain"})

    def test_get_coin_market_info(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value={
            "prices": [[1613846400000, 10000], [1613932800000, 20000], [1614019200000, 30000]],
            "market_caps": [[1613846400000, 1000], [1613932800000, 2000], [1614019200000, 3000]],
            "total_volumes": [[1613846400000, 100], [1613932800000, 200], [1614019200000, 300]]
        }):
            self.assertEqual(self.coingecko_api.get_coin_market_info(CoingeckoCoin("bitcoin", "BTC"),
                                                                     ["prices", "market_caps", "total_volumes"],
                                                                     3, "daily"),
                             {"prices": [[1613846400000, 10000], [1613932800000, 20000], [1614019200000, 30000]],
                              "market_caps": [[1613846400000, 1000], [1613932800000, 2000], [1614019200000, 3000]],
                              "total_volumes": [[1613846400000, 100], [1613932800000, 200], [1614019200000, 300]]})

            self.assertEqual(self.coingecko_api.get_coin_market_info(), {})

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_coin_market_info(CoingeckoCoin("bitcoin", "BTC"),
                                                                     ["prices", "market_caps", "total_volumes"],
                                                                     3, "daily"), {})

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value={}):
            self.assertEqual(self.coingecko_api.get_coin_market_info(CoingeckoCoin("bitcoin", "BTC"),
                                                                     ["prices", "market_caps", "total_volumes"],
                                                                     3, "daily"), {})

    def test_get_coin_history_hourly_close_price(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value={
            "prices": [[1613846400000, 10000], [1613932800000, 20000], [1614019200000, 30000]]
        }):
            self.assertEqual(self.coingecko_api.get_coin_history_hourly_close_price(CoingeckoCoin("bitcoin", "BTC"),
                                                                                    3),
                             [Decimal(30000), Decimal(20000), Decimal(10000)])

            self.assertEqual(self.coingecko_api.get_coin_history_hourly_close_price(), [])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_coin_history_hourly_close_price(CoingeckoCoin("bitcoin", "BTC"),
                                                                                    3), [])

        with mock.patch("pycoingecko.CoinGeckoAPI.get_coin_market_chart_by_id", return_value={}):
            self.assertEqual(self.coingecko_api.get_coin_history_hourly_close_price(CoingeckoCoin("bitcoin", "BTC"),
                                                                                    3), [])

    def test_get_coin_current_price(self) -> None:
        with mock.patch("pycoingecko.CoinGeckoAPI.get_price", return_value={
            "bitcoin": {"usd": 10000}
        }):
            self.assertEqual(self.coingecko_api.get_coin_current_price(CoingeckoCoin("bitcoin", "BTC")),
                             Decimal(10000))

            self.assertEqual(self.coingecko_api.get_coin_current_price(), Decimal(0))

        with mock.patch("pycoingecko.CoinGeckoAPI.get_price", return_value=Exception):
            self.assertEqual(self.coingecko_api.get_coin_current_price(CoingeckoCoin("bitcoin", "BTC")),
                             Decimal(0))

        with mock.patch("pycoingecko.CoinGeckoAPI.get_price", return_value={}):
            self.assertEqual(self.coingecko_api.get_coin_current_price(CoingeckoCoin("bitcoin", "BTC")),
                             Decimal(0))
