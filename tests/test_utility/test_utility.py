import unittest
import datetime
from unittest.mock import patch


from smrti_quant_alerts.utility import run_task_at_daily_time, run_alert
from smrti_quant_alerts.settings import Config


class TestAlert:
    def __init__(self, **kwargs):
        pass

    def run(self) -> None:
        pass


class TestUtility(unittest.TestCase):
    def test_run_task_at_daily_time(self) -> None:
        times = ["00:00", ["00:00", "00:01"]]
        with patch('datetime.datetime', wraps=datetime.datetime) as dt:
            dt.now.return_value = \
                datetime.datetime(2023, 6, 14, 0, 0, 0).replace(tzinfo=datetime.timezone.utc)
            for time in times:
                with self.assertRaises(SystemExit) as cm:
                    run_task_at_daily_time(lambda: exit(1), time)
                    self.assertEqual(cm.exception.code, 1)

        with patch('datetime.datetime', wraps=datetime.datetime) as dt:
            dt.now.return_value = \
                datetime.datetime(2023, 6, 14, 0, 0, 0).replace(tzinfo=datetime.timezone.utc)
            with patch('time.sleep', side_effect=lambda x: exit(1) if x == 60 else print("")):
                with self.assertRaises(SystemExit) as cm:
                    run_task_at_daily_time(lambda: print(""), "00:00")
                    self.assertEqual(cm.exception.code, 1)

    def test_run_alert(self) -> None:
        Config()
        Config.SETTINGS = {"test": {"alert_input_args": {}, "run_time_input_args": {}}}
        with patch('smrti_quant_alerts.utility.run_task_at_daily_time', side_effect=lambda x: exit(1)):
            with self.assertRaises(SystemExit) as cm:
                run_alert("test", TestAlert)
                self.assertEqual(cm.exception.code, 1)
        with patch('smrti_quant_alerts.utility.run_task_at_daily_time', side_effect=lambda x: print("")):
            with patch("logging.info") as mock_info:
                run_alert("test", TestAlert)
            mock_info.assert_called()
