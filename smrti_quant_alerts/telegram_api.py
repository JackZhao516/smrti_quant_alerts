import time
import threading
import requests

from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config


class TelegramBot:
    tokens = Config.TOKENS["TelegramBot"]
    TOKEN = tokens["TOKEN"]
    TELEGRAM_IDS = tokens["TELEGRAM_IDS"]

    def __init__(self, alert_type="CG_ALERT", daemon=True):
        """
        TelegramBot class for sending message to telegram group via bot

        send_message(msg, blue_text=False) is the main method for sending message
        stop() should be called explicitly to stop TelegramBot


        ::param alert_type: "CG_ALERT", "CG_SUM", "TEST", "VOLUME", "PRICE", etc.
        ::param daemon: True if letting the TelegramBot handle the 20 msg/min limit,
                        False if you want to handle the limit yourself

        """
        self.telegram_chat_id = self.TELEGRAM_IDS[alert_type]

        # message queue
        self.msg_queue_lock = threading.Lock()
        self.msg_queue = []
        self.daemon = daemon
        self.running = False

    @error_handling("telegram", default_val=None)
    def _send_message(self, message, blue_text=False):
        """
        helper method for sending message to telegram
        """
        if blue_text:
            message = message.replace("[", "(")
            message = message.replace("]", ")")
            message = f"[{message}](https://api.telegram.org/bot{self.TOKEN}/getMe)"
        api_url = f'https://api.telegram.org/bot{self.TOKEN}/' \
                  f'sendMessage?chat_id={self.telegram_chat_id}&text={message}'
        if blue_text:
            api_url += '&parse_mode=Markdown'
        requests.get(api_url, timeout=5)

    def _release_msg_from_queue(self):
        """
        helper method for releasing message from queue
        """
        self.msg_queue_lock.acquire()
        while self.msg_queue:
            msg = self.msg_queue.pop(0)
            blue_text = msg[1]
            msg = msg[0]
            self._send_message(msg, blue_text)
            self.msg_queue_lock.release()
            time.sleep(3.1)  # 20 msg/min
            self.msg_queue_lock.acquire()
        self.running = False
        self.msg_queue_lock.release()

    def send_message(self, message, blue_text=False):
        """
        send message to telegram group

        :param message: message to send
        :param blue_text: True if you want to send message in blue text

        """
        # split message if it's too long, 4000 is the limit
        messages = [[message[i:i + 4000], blue_text] for i in range(0, len(message), 4000)]

        if not self.daemon:
            for message in messages:
                self._send_message(message[0], blue_text)
            return

        self.msg_queue_lock.acquire()
        self.msg_queue += messages
        if not self.running and len(self.msg_queue) == len(messages):
            msg_thread = threading.Thread(target=self._release_msg_from_queue)
            self.running = True
            self.msg_queue_lock.release()
            msg_thread.start()
        else:
            self.msg_queue_lock.release()
        time.sleep(0.1)

    @error_handling("telegram", default_val=None)
    def send_file(self, file_path, file_name):
        """
        send file to telegram group

        :param file_path: path of the file to send
        :param file_name: name of the file to send
        """
        api_url = f'https://api.telegram.org/bot{self.TOKEN}/' \
                  f'sendDocument?'
        files = {'document': open(file_path, 'rb')}
        data = {'chat_id': self.telegram_chat_id, 'caption': file_name, 'parse_mode': 'HTML'}
        requests.post(api_url, data=data, files=files, stream=True, timeout=5)


if __name__ == "__main__":
    tg_bot = TelegramBot("TEST", daemon=True)
    tg_bot.send_message("test", blue_text=True)
