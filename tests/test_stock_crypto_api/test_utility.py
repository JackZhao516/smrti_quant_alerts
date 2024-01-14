import os
import unittest
import datetime
from unittest import mock

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.stock_crypto_api.utility import get_datetime_now, write_exclude_coins_to_file, \
    read_exclude_coins_from_file


class TestUtility(unittest.TestCase):
    def test_get_datetime_now(self) -> None:
        with mock.patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime.datetime(2021, 1, 1, 0, 0, 0)
            self.assertEqual(get_datetime_now(), datetime.datetime(2021, 1, 1, 0, 0, 0))

    def test_write_exclude_coins_to_file(self) -> None:
        Config.PROJECT_DIR = os.path.dirname(__file__)
        with mock.patch("json.dump") as mock_json_dump:
            write_exclude_coins_to_file("BTC, ETH")
            mock_json_dump.assert_called_once_with(["TESTTEST", "BTC", "TEST1", "ETH"], mock.ANY)

    def test_read_exclude_coins_from_file(self) -> None:
        Config.PROJECT_DIR = os.path.dirname(__file__)
        exclude_coins = read_exclude_coins_from_file()
        self.assertEqual(exclude_coins, {"TESTTEST", "TEST1", "BTC", "USDT"})
