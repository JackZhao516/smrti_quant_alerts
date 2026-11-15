import unittest
import os
from unittest.mock import patch

from smrti_quant_alerts.db import close_database, init_database_runtime, is_database_runtime_initialized
from smrti_quant_alerts.settings import Config
import contextlib


class TestDatabase(unittest.TestCase):
    PWD = os.path.dirname(os.path.abspath(__file__))

    def delete_dir(self) -> None:
        with contextlib.suppress(OSError):
            os.rmdir(os.path.join(self.PWD, "runtime_database"))

    def test_init_database(self) -> None:
        tmp, Config.PROJECT_DIR = Config.PROJECT_DIR, self.PWD
        self.delete_dir()
        with patch("playhouse.pool.PooledSqliteDatabase", side_effect=lambda x, **kwargs: exit(1)):
            with self.assertRaises(SystemExit) as cm:
                init_database_runtime("test.db")
                self.assertEqual(cm.exception.code, 1)

        self.delete_dir()
        Config.PROJECT_DIR = tmp


def test_close_database_resets_proxy(runtime_database) -> None:
    assert is_database_runtime_initialized()

    close_database()

    assert not is_database_runtime_initialized()


def test_screener_read_uses_separate_connection_and_existing_data(runtime_database):
    from peewee import SqliteDatabase

    from smrti_quant_alerts.data_type import StockSymbol
    from smrti_quant_alerts.db import StockAlertDBUtils
    from smrti_quant_alerts.db.database import database_runtime, runtime_database_path
    from smrti_quant_alerts.db.models import StockAlertCount

    active = database_runtime.obj
    StockAlertDBUtils.add_stocks([StockSymbol("AAPL")])
    name = "screener #1.db"
    screener = SqliteDatabase(str(runtime_database_path(name)))
    with screener.bind_ctx([StockAlertCount]), screener.connection_context():
        screener.create_tables([StockAlertCount])
        StockAlertCount.insert(stock_symbol="MSFT", alert_type="screen").execute(screener)

    assert StockAlertDBUtils.get_all_stocks(name) == {StockSymbol("MSFT")}
    assert database_runtime.obj is active
    assert StockAlertDBUtils.get_all_stocks() == {StockSymbol("AAPL")}


def test_screener_read_does_not_create_missing_files_or_tables(runtime_database):
    from peewee import SqliteDatabase

    from smrti_quant_alerts.db import StockAlertDBUtils
    from smrti_quant_alerts.db.database import runtime_database_path

    name = "missing.db"
    path = runtime_database_path(name)
    assert StockAlertDBUtils.get_all_stocks(name) == set()
    assert not path.exists()

    database = SqliteDatabase(str(path))
    with database.connection_context():
        assert StockAlertDBUtils.get_all_stocks(name) == set()
        assert not database.get_tables()
