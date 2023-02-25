import time
import logging
from binance.lib.utils import config_logging
from binance.websocket.spot.websocket_client import SpotWebsocketClient as Client

config_logging(logging, logging.DEBUG)


def message_handler(message):
    print(f"ttt{message}")
def message_handler_0(message):
    print(f"0{message}")


my_client = Client()
my_client.start()

my_client.kline(symbol=["btcusdt", "btcbusd"], id=1, interval="1m", callback=message_handler)

time.sleep(1)

my_client.kline(
    symbol=["bnbusdt", "ethusdt"], id=2, interval="1m", callback=message_handler
)

time.sleep(10)

logging.debug("closing ws connection")
my_client.stop()

# from datetime import datetime
# import pytz
#
# tz = pytz.timezone('Asia/Shanghai')
# berlin_now = datetime.now(tz).strftime('%H:%M')
#
# print(berlin_now)