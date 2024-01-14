import unittest

from smrti_quant_alerts.data_type import Tick, TradingSymbol


class TestTick(unittest.TestCase):
    def test_tick_amount(self) -> None:
        tick = Tick(symbol=TradingSymbol("TEST"), volume=1, open=1, close=1)
        self.assertEqual(tick.amount, 1)

        tick = Tick(symbol=TradingSymbol("TEST"))
        self.assertEqual(tick.amount, 0)


class TestTradingSymbol(unittest.TestCase):
    def test_equality(self) -> None:
        symbol = TradingSymbol("TEST")
        self.assertEqual(symbol, "TEST")
        self.assertEqual(symbol, "test")
        self.assertNotEqual(symbol, 1)

        self.assertEqual(symbol, TradingSymbol("TEST"))
        self.assertEqual(symbol, TradingSymbol("test"))

        self.assertLess(symbol, "TEST1")
        self.assertLess(symbol, TradingSymbol("TEST1"))
        self.assertLess(symbol, "test1")
        self.assertLess(symbol, TradingSymbol("test1"))
        self.assertFalse(symbol < 1)

        self.assertGreater(symbol, "TES")
        self.assertGreater(symbol, TradingSymbol("TES"))
        self.assertGreater(symbol, "tes")
        self.assertGreater(symbol, TradingSymbol("tes"))
        self.assertFalse(symbol > 1)

        self.assertLessEqual(symbol, "TEST")
        self.assertLessEqual(symbol, TradingSymbol("TEST"))
        self.assertLessEqual(symbol, "test")
        self.assertLessEqual(symbol, TradingSymbol("test"))
        self.assertFalse(symbol <= 1)

        self.assertGreaterEqual(symbol, "TEST")
        self.assertGreaterEqual(symbol, TradingSymbol("TEST"))
        self.assertGreaterEqual(symbol, "test")
        self.assertGreaterEqual(symbol, TradingSymbol("test"))
        self.assertFalse(symbol >= 1)

    def test_repr_str(self) -> None:
        for symbol in [TradingSymbol("tEsT"), TradingSymbol("TEST"), TradingSymbol("test")]:
            self.assertEqual(str(symbol), "TEST")
            self.assertEqual(repr(symbol), "TEST")
            self.assertEqual(symbol.str(), "TEST")
            self.assertEqual(symbol.upper(), "TEST")
            self.assertEqual(symbol.lower(), "test")

    def test_type(self) -> None:
        symbol = TradingSymbol("TEST")
        self.assertEqual(type(symbol), TradingSymbol)
        self.assertEqual(symbol.type(), "TradingSymbol")

    def test_hash(self) -> None:
        for symbol in [TradingSymbol("tEsT"), TradingSymbol("TEST"), TradingSymbol("test")]:
            self.assertEqual(hash(symbol), hash("TEST"))

    def test_get_symbol_object(self) -> None:
        with self.assertRaises(NotImplementedError) as e:
            TradingSymbol.get_symbol_object("TEST")
