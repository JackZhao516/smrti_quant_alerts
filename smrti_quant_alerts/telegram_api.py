import time
import threading
import requests

from smrti_quant_alerts.error import error_handling
from smrti_quant_alerts.settings import Config


class TelegramBot:
    tokens = Config.TOKENS["TelegramBot"]
    TOKEN = tokens["TOKEN"]
    TELEGRAM_IDS = tokens["TELEGRAM_IDS"]

    def __init__(self, alert_type="CG_ALERT", daemon=False):
        """
        TelegramBot class for sending message to telegram group via bot

        send_message(msg, blue_text=False) is the main method for sending message
        stop() should be called explicitly to stop TelegramBot


        ::param alert_type: "CG_ALERT", "CG_SUM", "TEST", "VOLUME", "PRICE", etc.
        ::param daemon: True if letting the TelegramBot handle the 10 msg/s limit,
                        False if you want to handle the limit yourself

        """
        self.telegram_chat_id = self.TELEGRAM_IDS[alert_type]

        # message queue
        self.msg_queue_lock = threading.Lock()
        self.msg_queue = []
        self.msg_thread = threading.Thread(target=self._release_msg_from_queue)
        self.running = False
        if daemon:
            self.msg_thread.start()

    @error_handling("telegram", "send_message")
    def _send_message(self, message, blue_text=False):
        """
        helper method for sending message to telegram
        """
        if blue_text:
            message = message.replace("[", "(")
            message = message.replace("]", ")")
            message = f"[{message}](https://www.google.com/)"
        api_url = f'https://api.telegram.org/bot{self.TOKEN}/' \
                  f'sendMessage?chat_id={self.telegram_chat_id}&text={message}'
        if blue_text:
            api_url += '&parse_mode=Markdown'
        requests.get(api_url, timeout=2)

    def _release_msg_from_queue(self):
        """
        helper method for releasing message from queue
        """
        self.running = True
        while self.running:
            while self.msg_queue:
                self.msg_queue_lock.acquire()
                msg = self.msg_queue.pop(0)
                self._send_message(msg)
                self.msg_queue_lock.release()
                time.sleep(0.11)  # 10 msg/s
            time.sleep(1)

    def send_message(self, message, blue_text=False):
        """
        send message to telegram group

        :param message: message to send
        :param blue_text: True if you want to send message in blue text

        """
        # split message if it's too long, 4000 is the limit
        messages = [message[i:i + 4000] for i in range(0, len(message), 4000)]

        if not self.running:
            for message in messages:
                self._send_message(message, blue_text)
            return
        self.msg_queue_lock.acquire()
        for message in messages:
            self.msg_queue.append(message)
        self.msg_queue_lock.release()

    def stop(self):
        """
        stop TelegramBot
        """
        if not self.running:
            return
        self.running = False
        self.msg_thread.join()


if __name__ == "__main__":
    tg_bot = TelegramBot("TEST", daemon=False)
    a = "test"
    tg_bot.send_message(a, blue_text=True)
