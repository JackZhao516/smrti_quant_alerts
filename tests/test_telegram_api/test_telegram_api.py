import unittest
import os
import time
from unittest.mock import patch

from smrti_quant_alerts.telegram_api import TelegramBot
from smrti_quant_alerts.settings import Config


class TestTelegramBot(unittest.TestCase):
    try:
        os.rmdir(os.path.join(Config.PROJECT_DIR, "runtime_data"))
    except OSError:
        pass

    def test_release_msg_from_queue(self) -> None:
        telegram_bot = TelegramBot(daemon=False)

        telegram_bot.msg_queue = [["test", True], ["test1", False], ["test2", True]]
        start = time.time()
        with patch('requests.get', side_effect=lambda x, timeout: {"ok": True}):
            telegram_bot._release_msg_from_queue()
            self.assertEqual(telegram_bot.msg_queue, [])
            self.assertFalse(telegram_bot.running)
            self.assertTrue(time.time() - start > 6)  # up to 20 msg/min

    def test_send_message(self) -> None:
        with patch('requests.get', side_effect=lambda x, timeout: {"ok": True}):
            with patch.object(TelegramBot, '_release_msg_from_queue') as mock_release_msg_from_queue:
                telegram_bot = TelegramBot(daemon=False)
                telegram_bot.send_message("test", blue_text=True)
                telegram_bot.send_message("test", blue_text=False)
            mock_release_msg_from_queue.assert_not_called()

        with patch('requests.get', side_effect=lambda x, timeout: {"ok": True}):
            with patch.object(TelegramBot, '_release_msg_from_queue') as mock_release_msg_from_queue:
                telegram_bot = TelegramBot(daemon=True)
                telegram_bot.send_message("test", blue_text=True)
                telegram_bot.send_message("test", blue_text=False)
            mock_release_msg_from_queue.assert_called()

    def test_send_file(self) -> None:
        path = os.path.dirname(os.path.abspath(__file__))
        mock_file_path = os.path.join(path, "mock_file.txt")

        with patch('requests.post',
                   side_effect=lambda x, data, files, stream, timeout: {"data": data, "files": files}):
            telegram_bot = TelegramBot(daemon=False)
            res = telegram_bot.send_file(mock_file_path, "test.csv")
            self.assertEqual(res["files"]["document"].read(), open(mock_file_path, "rb").read())

    def test_send_data_as_csv_file(self) -> None:
        with patch.object(TelegramBot, 'send_file',
                          side_effect=lambda x, y: open(x, "rb").read()):
            telegram_bot = TelegramBot(daemon=False)
            telegram_bot.PWD = os.path.dirname(os.path.abspath(__file__))
            res = telegram_bot.send_data_as_csv_file("test.csv", ["test1", "test2"], [["test3", "test4"]])
            self.assertEqual(res, b'test1,test2\r\ntest3,test4\r\n')
