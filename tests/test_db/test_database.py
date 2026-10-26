import unittest
import os
from unittest.mock import patch

from smrti_quant_alerts.db import init_database_runtime
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
        with patch('playhouse.pool.PooledSqliteDatabase', side_effect=lambda x, **kwargs: exit(1)):
            with self.assertRaises(SystemExit) as cm:
                init_database_runtime("test.db")
                self.assertEqual(cm.exception.code, 1)

        self.delete_dir()
        Config.PROJECT_DIR = tmp
