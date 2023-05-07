import time
import logging
from binance.lib.utils import config_logging
from binance.websocket.spot.websocket_client import SpotWebsocketClient as Client




def message_handler(message):
    pass
def message_handler_0(message):
    print(f"0{message}")


# logging.info("test")
# my_client = Client()
# config_logging(my_client._logger, logging.WARNING)
# my_client.start()
#
# my_client.kline(symbol=["btcusdt", "btcbusd"], id=1, interval="1m", callback=message_handler)
#
# time.sleep(1200)
#
# my_client.kline(
#     symbol=["bnbusdt", "ethusdt"], id=2, interval="1m", callback=message_handler
# )
#
# time.sleep(10)
#
# logging.debug("closing ws connection")
# my_client.stop()

# from datetime import datetime
# import pytz
#
# tz = pytz.timezone('Asia/Shanghai')
# print(datetime.now(tz).weekday())
# berlin_now = datetime.now(tz).strftime('%H:%M')
#
# print(berlin_now)

import requests
# print(int(time.time()))
# # url = f"https://api.binance.com/api/v3/klines?symbol=SUBETH&interval=1m&startTime={(int(time.time())-70)*1000}&limit=500"
# # response = requests.get(url)
# exchange = "AMBUSDT"
# time_delta = 34 * 24 * 60 * 60 * 1000
# time_now = int(time.time()) * 1000
# print(time_now - time_delta)
# url = f"https://api.binance.com/api/v3/historicalTrades?symbol={exchange}"
# # url = f"https://api.binance.com/api/v3/klines?symbol={exchange}&interval=4h&startTime={time_now - time_delta}&limit=1000"
# response = requests.get(url, timeout=2).json()
# # print(response)
#
# import logging
# from binance.spot import Spot as Client
# from binance.lib.utils import config_logging
# import json
#
#
# config_logging(logging, logging.DEBUG)
#
# f = open("token.json", "r")
# api_key = json.load(f)["BINANCE"]
#
# # historical_trades requires api key in request header
# spot_client = Client(api_key=api_key)


from error import error_handling


# print(response.json())


