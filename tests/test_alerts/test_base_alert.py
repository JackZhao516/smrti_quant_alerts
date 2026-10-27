import unittest
import os
from unittest import mock

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.settings import Config


class TestBaseAlert(unittest.TestCase):
    def setUp(self) -> None:
        # Set project directory to test settings like other tests do
        Config.PROJECT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_settings")
        Config.IS_SETUP = False  # Force re-initialization
        self.alert = BaseAlert("<price_volume_alert_example_name>", tg_type="TEST")

    def test_str(self) -> None:
        self.assertEqual(str(self.alert), "BaseAlert")

    def test_repr(self) -> None:
        self.assertEqual(repr(self.alert), "BaseAlert")

    def test_run(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.alert.run()

    def test_injected_dependencies(self) -> None:
        tg_bot = mock.MagicMock()
        config = mock.MagicMock()
        config.SETTINGS = {"alert": {"database_name": "custom_db"}}
        init_db = mock.MagicMock()

        alert = BaseAlert("alert", tg_bot=tg_bot, config=config, init_db=init_db)

        self.assertIs(alert._tg_bot, tg_bot)
        self.assertIs(alert._config, config)
        init_db.assert_called_once_with("custom_db.db")

    def test_database_name_falls_back_to_alert_name(self) -> None:
        config = mock.MagicMock()
        config.SETTINGS = {"alert": {}}
        init_db = mock.MagicMock()

        BaseAlert("alert", tg_bot=mock.MagicMock(), config=config, init_db=init_db)

        init_db.assert_called_once_with("alert.db")
