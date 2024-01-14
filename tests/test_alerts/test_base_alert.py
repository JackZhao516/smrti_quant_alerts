import unittest

from smrti_quant_alerts.alerts.base_alert import BaseAlert


class TestBaseAlert(unittest.TestCase):
    def setUp(self) -> None:
        self.alert = BaseAlert(tg_type="TEST")

    def test_str(self) -> None:
        self.assertEqual(str(self.alert), "BaseAlert")

    def test_repr(self) -> None:
        self.assertEqual(repr(self.alert), "BaseAlert")

    def test_run(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.alert.run()
