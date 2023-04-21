import time
import logging
from binance.lib.utils import config_logging
from binance.websocket.spot.websocket_client import SpotWebsocketClient as Client

config_logging(logging, logging.DEBUG)


def message_handler(message):
    print(f"ttt{message}")
def message_handler_0(message):
    print(f"0{message}")

#
# my_client = Client()
# my_client.start()
#
# my_client.kline(symbol=["btcusdt", "btcbusd"], id=1, interval="1m", callback=message_handler)
#
# time.sleep(1)
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
#
# # logging.info(spot_client.historical_trades("BTCUSDT"))
# logging.info(len(spot_client.historical_trades("BTCUSDT", limit=1000)))
import os
import json
from collections import defaultdict
from telegram_api import TelegramBot
exchange_alert_monthly_count = {
                "15m_price": defaultdict(lambda : 0),

            }

exchange_alert_monthly_count["15m_price"]["BTCUSDT"] = 1
exchange_alert_monthly_count["15m_price"]["ETHUSDT"] = 2
exchange_alert_monthly_count["15m_price"]["BNBUSDT"] = 3
a = exchange_alert_monthly_count["15m_price"]

print(a)
a = sorted(a.items(), key=lambda x: x[1], reverse=True)
a = [f"{i[0]}: {i[1]}" for i in a]
a = ", ".join(a)
tg = TelegramBot("TEST", daemon=False)
tg.safe_send_message(a, True)

f = open("test.json", "w")

