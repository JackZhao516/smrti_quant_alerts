import unittest
import os
from unittest.mock import patch

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
