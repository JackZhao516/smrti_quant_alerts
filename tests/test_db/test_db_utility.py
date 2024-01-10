import unittest
import os
import threading
import time
from unittest.mock import patch
from typing import Dict, Tuple

from smrti_quant_alerts.db import init_database_runtime, PriceVolumeDBUtils, SpotOverMaDBUtils, close_database
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin, TradingSymbol
from smrti_quant_alerts.settings import Config


def remove_database() -> None:
    """
    remove database
    """
    try:
        os.remove(os.path.join(Config.PROJECT_DIR, "runtime_database", "test.db"))
        os.remove(os.path.join(Config.PROJECT_DIR, "runtime_database", "test.db-shm"))
        os.remove(os.path.join(Config.PROJECT_DIR, "runtime_database", "test.db-wal"))
    except OSError:
        pass


class TestConfig:
    """
    Test config for database; context manager
    """
    def __enter__(self):
        remove_database()
        init_database_runtime("test.db")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        close_database()
        remove_database()
        return False


class TestDBUtility(unittest.TestCase):
    def test_init_database_runtime(self) -> None:
        with patch('playhouse.pool.PooledSqliteDatabase', side_effect=lambda x, **kwargs: exit(1)):
            with self.assertRaises(SystemExit) as cm:
                init_database_runtime("test.db")
                self.assertEqual(cm.exception.code, 1)
        remove_database()


class TestPriceVolumeDBUtils(unittest.TestCase):
    @staticmethod
    def convert_timestamp_to_zero(count_dict: Dict[BinanceExchange, Tuple[int, float]]) \
            -> Dict[BinanceExchange, Tuple[int, float]]:
        """
        convert timestamp to 0
        """
        return {exchange: (count, 0) for exchange, (count, _) in count_dict.items()}

    def test_update_count(self) -> None:
        with TestConfig() as _:
            count = PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
            self.assertEqual(count, 1)
            count = PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
            self.assertEqual(count, 2)
            count = PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 1000, "daily")
            self.assertEqual(count, 2)

    def test_get_count(self) -> None:
        with TestConfig() as _:
            count = PriceVolumeDBUtils.get_count("test_alert", BinanceExchange("test", "test"), "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {})

            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
            count = PriceVolumeDBUtils.get_count("test_alert", BinanceExchange("test", "test"), "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (1, 0)})

            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
            count = PriceVolumeDBUtils.get_count("test_alert", BinanceExchange("test", "test"), "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (2, 0)})

            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 1000, "daily")
            count = PriceVolumeDBUtils.get_count("test_alert", BinanceExchange("test", "test"), "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (2, 0)})

            count = PriceVolumeDBUtils.get_count("test_alert", None, "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (2, 0)})

    def test_reset_count(self):
        with TestConfig() as _:
            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
            PriceVolumeDBUtils.update_count(BinanceExchange("test1", "test"), "test_alert", 0, "daily")
            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test2"), "test_alert", 1000, "daily")
            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "monthly")
            PriceVolumeDBUtils.update_count(BinanceExchange("test3", "test"), "test_alert", 0, "monthly")
            PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 1000, "monthly")

            PriceVolumeDBUtils.reset_count("test_alert", "daily")
            count = PriceVolumeDBUtils.get_count("test_alert", None, "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {})
            count = PriceVolumeDBUtils.get_count("test_alert", None, "monthly")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (1, 0),
                                                                     BinanceExchange("test3", "test"): (1, 0)})
            try:
                PriceVolumeDBUtils.reset_count("test_alert", "daily")
            except Exception:
                self.fail("reset_count() raised Exception unexpectedly for repeated reset")

            PriceVolumeDBUtils.reset_count("test_alert", "monthly")
            count = PriceVolumeDBUtils.get_count("test_alert", None, "monthly")
            self.assertEqual(self.convert_timestamp_to_zero(count), {})

    def test_multithreading_access(self) -> None:
        with TestConfig() as _:
            def update_count() -> None:
                for _ in range(100):
                    PriceVolumeDBUtils.update_count(BinanceExchange("test", "test"), "test_alert", 0, "daily")
                    PriceVolumeDBUtils.update_count(BinanceExchange("test1", "test"), "test_alert", 10000, "monthly")
                    PriceVolumeDBUtils.update_count(BinanceExchange("test1", "test"), "test_alert", 0, "monthly")
                    PriceVolumeDBUtils.update_count(BinanceExchange("test3", "test"), "test_alert", 10000, "monthly")

            threads = []
            for _ in range(10):
                threads.append(threading.Thread(target=update_count))
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            count = PriceVolumeDBUtils.get_count("test_alert", None, "daily")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test", "test"): (1000, 0)})
            count = PriceVolumeDBUtils.get_count("test_alert", None, "monthly")
            self.assertEqual(self.convert_timestamp_to_zero(count), {BinanceExchange("test1", "test"): (1001, 0),
                                                                     BinanceExchange("test3", "test"): (1, 0)})


class TestSpotOverMaDBUtils(unittest.TestCase):
    def test_get_last_count(self) -> None:
        with TestConfig() as _:
            SpotOverMaDBUtils.update_last_count([BinanceExchange("test", "test"),
                                                 BinanceExchange("test1", "test")], "test")
            SpotOverMaDBUtils.update_last_count([BinanceExchange("test", "test1")], "test1")
            SpotOverMaDBUtils.update_last_count([CoingeckoCoin("test", "test")], "test")

            count = SpotOverMaDBUtils.get_last_count(BinanceExchange)
            self.assertEqual(count, {BinanceExchange("test", "test"): 1, BinanceExchange("test1", "test"): 1,
                                     BinanceExchange("test", "test1"): 1})

            count = SpotOverMaDBUtils.get_last_count()
            self.assertEqual(count, {BinanceExchange("test", "test"): 1, BinanceExchange("test1", "test"): 1,
                                     BinanceExchange("test", "test1"): 1, CoingeckoCoin("test", "test"): 1})

            count = SpotOverMaDBUtils.get_last_count(alert_type="test")
            self.assertEqual(count, {BinanceExchange("test", "test"): 1, BinanceExchange("test1", "test"): 1,
                                     CoingeckoCoin("test", "test"): 1})

            count = SpotOverMaDBUtils.get_last_count(BinanceExchange, "test1")
            self.assertEqual(count, {BinanceExchange("test", "test1"): 1})

            count = SpotOverMaDBUtils.get_last_count(TradingSymbol)
            self.assertEqual(count, {})

    def test_update_last_count(self) -> None:
        with TestConfig() as _:
            SpotOverMaDBUtils.update_last_count([BinanceExchange("test", "test")], "test")
            SpotOverMaDBUtils.update_last_count([BinanceExchange("test", "test")], "test1")

            count = SpotOverMaDBUtils.get_last_count(BinanceExchange)
            self.assertEqual(count, {BinanceExchange("test", "test"): 2})

            count = SpotOverMaDBUtils.get_last_count(BinanceExchange, "test")
            self.assertEqual(count, {})

            count = SpotOverMaDBUtils.get_last_count(BinanceExchange, "test1")
            self.assertEqual(count, {BinanceExchange("test", "test"): 2})

            SpotOverMaDBUtils.update_last_count([CoingeckoCoin("test", "test")], "test")
            count = SpotOverMaDBUtils.get_last_count()
            self.assertEqual(count, {BinanceExchange("test", "test"): 2, CoingeckoCoin("test", "test"): 1})

            SpotOverMaDBUtils.update_last_count([CoingeckoCoin("test1", "test1")], "test2")
            count = SpotOverMaDBUtils.get_last_count(CoingeckoCoin)
            self.assertEqual(count, {CoingeckoCoin("test", "test"): 1, CoingeckoCoin("test1", "test1"): 1})

    def test_remove_older_count(self) -> None:
        start = time.time()
        with TestConfig() as _:
            SpotOverMaDBUtils.update_last_count([BinanceExchange("test", "test")], "test")
            count = SpotOverMaDBUtils.get_last_count(BinanceExchange)
            self.assertEqual(count, {BinanceExchange("test", "test"): 1})

            SpotOverMaDBUtils.remove_older_count(start)
            count = SpotOverMaDBUtils.get_last_count(BinanceExchange)
            self.assertEqual(count, {BinanceExchange("test", "test"): 1})

            SpotOverMaDBUtils.remove_older_count(time.time())
            count = SpotOverMaDBUtils.get_last_count()
            self.assertEqual(count, {})
