import unittest
from collections import defaultdict

from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, ExchangeTick, TradingSymbol


class TestExchangeTick(unittest.TestCase):
    def test_exchange_tick(self) -> None:
        tick = ExchangeTick(BinanceExchange("BTC", "USDT"))
        self.assertEqual(tick.exchange, BinanceExchange("BTC", "USDT"))

        tick = ExchangeTick(TradingSymbol("BTCUSDT"))
        self.assertEqual(tick.exchange, BinanceExchange("BTC", "USDT"))


class TestBinanceExchange(unittest.TestCase):
    def test_exchange(self) -> None:
        exchange = BinanceExchange("BTC", "USDT")
        self.assertEqual(exchange.exchange, "BTCUSDT")

    def test_get_symbol_object(self) -> None:
        exchange = BinanceExchange.get_symbol_object("BTCUSDT")
        self.assertEqual(exchange, BinanceExchange("BTC", "USDT"))
        self.assertIsNone(BinanceExchange.get_symbol_object("BTCUSD"))

    def test_add_base_coin_id_pair_to_dict(self) -> None:
        BinanceExchange.add_base_coin_id_pair_to_dict("BTC", "bitcoin")
        self.assertEqual(BinanceExchange.symbol_base_coingecko_id_map["BTC"], "bitcoin")


class TestCoingeckoCoin(unittest.TestCase):
    def test_coin_symbol(self) -> None:
        CoingeckoCoin.symbol_id_map = defaultdict(set)
        coin = CoingeckoCoin("bitcoin", "BTC")
        self.assertEqual(coin.coin_symbol, "BTC")
        self.assertNotEqual(coin, CoingeckoCoin("test", "BTC"))

    def test_get_symbol_object(self) -> None:
        CoingeckoCoin.symbol_id_map = defaultdict(set)
        CoingeckoCoin("bitcoin", "BTC")
        coin = CoingeckoCoin.get_symbol_object("BTC", "other")
        self.assertEqual(coin, CoingeckoCoin("bitcoin", "BTC"))
        self.assertIsNone(CoingeckoCoin.get_symbol_object("ETH", "other"))

        CoingeckoCoin("bitcoin1", "BTC")
        coin = CoingeckoCoin.get_symbol_object("BTC", "other")
        self.assertEqual(set(coin), {CoingeckoCoin("bitcoin1", "BTC"), CoingeckoCoin("bitcoin", "BTC")})

    def test_equal(self) -> None:
        self.assertTrue(CoingeckoCoin("bitcoin", "BTC") == "BTC")
        self.assertFalse(CoingeckoCoin("bitcoin", "BTC") == "BTC1")
        self.assertFalse(CoingeckoCoin("bitcoin", "BTC") == 0)
