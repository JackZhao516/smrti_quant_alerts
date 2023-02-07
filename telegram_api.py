import requests
import time
import threading


class TelegramBot:
    TOKEN = "5503993388:AAEhkd7Q_b7iYrAowBdC5QsMM35UJl0uknw"
    TELEGRAM_IDS = {
        "CG_ALERT": "-808085014",  # CG Alert
        "CG_SUM": "-804953236",  # CG Summary
        "TEST": "-814886566",  # TEST
        "VOLUME": "-859234465",  # Volume Alert
        "PRICE_15M": "-824512265",  # Price Alert 15m
        "PRICE_1H": "-824415540"  # Price Alert 1h
        }
    MAX_ERROR = 10

    def __init__(self, alert_type="CG_ALERT", daemon=False):
        """
        ::param alert_type: "CG_ALERT", "CG_SUM", "TEST", "VOLUME", "PRICE"
        ::param daemon: True if the thread is a daemon thread, False otherwise
                        need to call stop() explicitly if daemon is True
        """
        self.telegram_chat_id = self.TELEGRAM_IDS[alert_type]
        self.error = 0

        # message queue
        self.msg_queue_lock = threading.Lock()
        self.msg_queue = []
        self.msg_thread = threading.Thread(target=self._send_msg_from_queue)
        self.running = False
        if daemon:
            self.msg_thread.start()

    def send_message(self, message, blue_text=False):
        api_url = f'https://api.telegram.org/bot{self.TOKEN}/' \
                  f'sendMessage?chat_id={self.telegram_chat_id}&text={message}'
        if blue_text:
            api_url += '&parse_mode=MarkdownV2'
        print(api_url)
        requests.get(api_url, timeout=10).json()

    def safe_send_message(self, message, blue_text=False):
        try:
            self.send_message(message, blue_text)
        except Exception as e:
            self.error += 1
            if self.error > self.MAX_ERROR:
                raise e
            pass

    def add_msg_to_queue(self, msg):
        if not self.running:
            self.safe_send_message(msg)
            return
        self.msg_queue_lock.acquire()
        self.msg_queue.append(msg)
        self.msg_queue_lock.release()

    def _send_msg_from_queue(self):
        self.running = True
        while self.running:
            if self.msg_queue:
                self.msg_queue_lock.acquire()
                msg = self.msg_queue.pop(0)
                self.safe_send_message(msg)
                self.msg_queue_lock.release()
            time.sleep(0.11)

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.msg_thread.join()


if __name__ == "__main__":
    tg_bot = TelegramBot("TEST", daemon=False)
    a = ""
    for i in range(100):
        a += f"BTCUSDT monthly volume count: {i}\n"
    tg_bot.safe_send_message(f"[Daily volume alert ticker count: {a}](http://www.google.com/)", blue_text=True)
    print(tg_bot.running)
