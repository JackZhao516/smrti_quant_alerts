import unittest

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


class TestCoingeckoCoin(unittest.TestCase):
    def test_coin_symbol(self) -> None:
        coin = CoingeckoCoin("bitcoin", "BTC")
        self.assertEqual(coin.coin_symbol, "BTC")
        self.assertNotEqual(coin, CoingeckoCoin("test", "BTC"))

    def test_get_symbol_object(self) -> None:
        CoingeckoCoin("bitcoin", "BTC")
        coin = CoingeckoCoin.get_symbol_object("BTC")
        self.assertEqual(coin, CoingeckoCoin("bitcoin", "BTC"))
        self.assertIsNone(CoingeckoCoin.get_symbol_object("ETH"))
