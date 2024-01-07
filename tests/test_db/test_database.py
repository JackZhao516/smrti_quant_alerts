import unittest
import os
from unittest.mock import patch

from smrti_quant_alerts.db import init_database_runtime
from smrti_quant_alerts.settings import Config


class TestDatabase(unittest.TestCase):
    PWD = os.path.dirname(os.path.abspath(__file__))

    def delete_dir(self) -> None:
        try:
            os.rmdir(os.path.join(self.PWD, "runtime_database"))
        except OSError:
            pass

    def test_init_database(self) -> None:
        self.delete_dir()
        tmp, Config.PROJECT_DIR = Config.PROJECT_DIR, self.PWD
        with patch('peewee.SqliteDatabase', side_effect=lambda x, **kwargs: exit(1)):
            with self.assertRaises(SystemExit) as cm:
                init_database_runtime("test.db")
                self.assertEqual(cm.exception.code, 1)

        self.delete_dir()
        Config.PROJECT_DIR = tmp
