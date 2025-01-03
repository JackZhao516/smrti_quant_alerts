import time
import math
import json
import logging
import threading
from typing import List, Any, Optional, Sequence, Iterable
from collections import defaultdict
from abc import ABC, abstractmethod

from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.stock_crypto_api import BinanceApi
from smrti_quant_alerts.data_type import BinanceExchange, ExchangeTick
from smrti_quant_alerts.db import PriceVolumeDBUtils
from smrti_quant_alerts.utility import run_task_at_daily_time


class BinancePriceVolumeBase(ABC, BaseAlert, BinanceApi):
    _db_utils = PriceVolumeDBUtils()

    def __init__(self, alert_name: str, alert_type: str = "binance_price_15m",
                 tg_type: str = "TEST", timeframe: str = "15m") -> None:
        BaseAlert.__init__(self, alert_name, tg_type)
        BinanceApi.__init__(self)

        # alert info and settings
        self._timeframe = timeframe
        self._alert_type = alert_type
        self._params = self.CONFIG.SETTINGS[alert_name]["alert_params"]
        self._alert_threshold = None

        # data
        self._exchanges = self.get_all_spot_exchanges_in_usdt_fdusd_btc()[:200]
        self._monthly_start_timestamp = 0.0
        self._current_timestamp = 0.0

        # dict for 15min/1h volume alert: exchange -> [volume1, ...]
        # dict for 15min/1h price alert: exchange -> <close_price_change_rate>
        self._exchange_bar_dict = {}

        # websocket client
        self._websocket_client = SpotWebsocketStreamClient(on_message=self._handle_tick_message,
                                                           is_combined=True, timeout=2000)

    # ------alert helper functions-------
    def _exchanges_to_subscription_stream_names(self, exchanges: Iterable[BinanceExchange]) -> List[str]:
        """
        Convert exchanges to subscription stream names
        """
        return [f"{e.lower()}@kline_{self._timeframe}" for e in exchanges]

    def _update_count_and_send_telegram_message(self, title: str, exchange: BinanceExchange,
                                                num_of_bars: int, amount: float) -> None:
        """
        Update count and send telegram message

        :param title: title of the message
        :param exchange: BinanceExchange object
        :param num_of_bars: number of bars in the alert
        :param amount: amount

        """
        self._db_utils.update_count(exchange, self._alert_type, 1850, "daily")
        monthly_count = self._db_utils.update_count(exchange, self._alert_type, 1850, "monthly")
        if num_of_bars == 2:
            bar_str = f"[{self._exchange_bar_dict[exchange][-2]} -> " \
                        f"{self._exchange_bar_dict[exchange][-1]}]"
        else:
            bar_str = f"[{self._exchange_bar_dict[exchange][-3]} -> " \
                        f"{self._exchange_bar_dict[exchange][-2]} -> " \
                        f"{self._exchange_bar_dict[exchange][-1]}]"
        self._tg_bot.send_message(
            f"{exchange} {self._alert_type} alert {title}:\n"
            f"{bar_str}\namount: ${math.ceil(amount)}\n"
            f"ticker volume alert monthly count:"
            f" {monthly_count}")

    def _handle_tick_message_pre_check(self, msg: str) -> Optional[ExchangeTick]:
        """
        Pre check for tick message

        :param msg: message parsed from websocket

        :return: message dict if pass pre check, otherwise empty dict
        """
        msg = json.loads(msg)
        if "stream" not in msg or "data" not in msg or "k" not in msg["data"] or \
                msg["data"]["k"]["x"] is False or msg["data"]["k"]["i"] != self._timeframe or \
                msg["data"]["k"]["s"] not in self._exchanges:
            return None
        return ExchangeTick(BinanceExchange.get_symbol_object(msg["data"]["k"]["s"]),
                            float(msg["data"]["k"]["v"]), float(msg["data"]["k"]["o"]), float(msg["data"]["k"]["c"]),
                            float(msg["data"]["k"]["h"]), float(msg["data"]["k"]["l"]), int(msg["data"]["k"]["t"]))

    def _alert_price_change(self) -> None:
        """
        Alert price change
        """
        # alert at the end of the bar
        if len(self._exchange_bar_dict[self._current_timestamp]) != len(self._exchanges):
            return

        price_lists = [[k, v] for k, v in self._exchange_bar_dict[self._current_timestamp].items()]
        largest, smallest = [], []
        del self._exchange_bar_dict[self._current_timestamp]

        # get the largest and smallest five
        price_lists.sort(key=lambda x: x[1], reverse=True)
        for i in range(5):
            if price_lists[i][1] >= self._alert_threshold:
                count = self._db_utils.update_count(price_lists[i][0], self._alert_type, 1850, "monthly")
                self._db_utils.update_count(price_lists[i][0], self._alert_type, 1850, "daily")
                largest.append(f"{price_lists[i][0]}: {round(price_lists[i][1], 2)}%, monthly count: {count}")

            if price_lists[-i - 1][1] <= -1 * self._alert_threshold:
                count = self._db_utils.update_count(price_lists[-i - 1][0], self._alert_type, 1850, "monthly")
                self._db_utils.update_count(price_lists[-i - 1][0], self._alert_type, 1850, "daily")
                smallest.append(
                    f"{price_lists[-i - 1][0]}: {round(price_lists[-i - 1][1], 2)}%, monthly count: {count}")

        price_type = "close/open" if self._timeframe == "15m" else "high/low"

        if len(largest) > 0:
            self._tg_bot.send_message(
                f"{self._timeframe} top {len(largest)} "
                f"positive price ({price_type}) change in % over {self._alert_threshold}%: {largest}")
        if len(smallest) > 0:
            self._tg_bot.send_message(
                f"{self._timeframe} top {len(smallest)} "
                f"negative price ({price_type}) change in % over {self._alert_threshold}%: {smallest}")

    @abstractmethod
    def _handle_tick_message(self, _, msg: str) -> Any:
        """
        Handle tick message parsed from websocket
        """
        raise NotImplementedError

    # --------service functions----------
    def _alert_count(self) -> None:
        """
        Alert daily count and monthly count
        """
        logging.info("daily alert daily count and monthly count")
        message_str = ""
        # alert and reset monthly count
        monthly_count = self._db_utils.get_count(alert_type=self._alert_type, count_type="monthly").items()
        message_list = sorted(monthly_count, key=lambda x: x[1][0], reverse=True)[:30]

        for exchange, count in message_list:
            message_str += f"{exchange} monthly count: {count[0]}\n"

        self._tg_bot.send_message(
            f"Daily {self._alert_type} ticker monthly count:\n"
            f"{message_str}", blue_text=True
        )
        if time.time() - self._monthly_start_timestamp > 30 * 86400 + 180:
            self._db_utils.reset_count(self._alert_type, "monthly")
            self._monthly_start_timestamp = time.time()

        daily_count = self._db_utils.get_count(alert_type=self._alert_type, count_type="daily").items()
        message_list = sorted(daily_count, key=lambda x: x[1][0], reverse=True)
        message_str = ""
        for exchange, count in message_list:
            message_str += f"{exchange}: {count[0]}\n"

        self._tg_bot.send_message(
            f"Daily {self._alert_type} new alerts daily count:\n"
            f"{message_str}", blue_text=True)
        self._db_utils.reset_count(self._alert_type, "daily")

    def _auto_subscribe_new_exchanges(self):
        """
        auto subscribe new exchanges, every ten minutes
        """
        logging.info("subscribe new exchange start every ten minutes")
        self.CONFIG.reload_settings()
        self._params = self.CONFIG.SETTINGS[self._alert_name]["alert_params"]

        new_exchanges_set = set(self.get_all_spot_exchanges_in_usdt_fdusd_btc())
        current_exchanges_set = set(self._exchanges)
        if current_exchanges_set != new_exchanges_set:
            exchange_diff = new_exchanges_set - current_exchanges_set

            if exchange_diff:
                new_exchanges = self._exchanges_to_subscription_stream_names(exchange_diff)
                self._websocket_client.subscribe(new_exchanges)

                logging.warning(f"adding new exchanges: {exchange_diff}")

            self._exchanges += list(exchange_diff)

    def _auto_restart_websocket(self):
        """
        auto restart websocket every 5 second when websocket is not alive
        """
        while True:
            if self._websocket_client.socket_manager.is_alive():
                time.sleep(5)
            else:
                self._websocket_client = SpotWebsocketStreamClient(on_message=self._handle_tick_message,
                                                                   is_combined=True, timeout=2000)
                exchange_strs = self._exchanges_to_subscription_stream_names(self._exchanges)
                self._websocket_client.subscribe(exchange_strs)
                logging.warning(f"Restarted websocket for {self._alert_type}")

    # ----------main functions-----------
    def run(self) -> None:
        """
        run the alert
        """
        self._monthly_start_timestamp = time.time()
        exchange_strs = self._exchanges_to_subscription_stream_names(self._exchanges)
        self._websocket_client.subscribe(exchange_strs)

        services = [
            threading.Thread(target=run_task_at_daily_time,
                             args=(self._alert_count,
                                   self.CONFIG.SETTINGS[self._alert_name]["run_time_input_args"]["daily_times"],
                                   None, self.CONFIG.SETTINGS[self._alert_name]["run_time_input_args"]["timezone"])),
            threading.Thread(target=run_task_at_daily_time,
                             args=(self._auto_subscribe_new_exchanges,
                                   [f"{str(h).zfill(2)}:05" for h in range(24)])),
            threading.Thread(target=self._auto_restart_websocket),
        ]
        for service in services:
            service.start()


class BinancePrice15mAlert(BinancePriceVolumeBase):
    def __init__(self, alert_name: str, tg_type: str = "TEST") -> None:
        BinancePriceVolumeBase.__init__(self, alert_name=alert_name, alert_type="binance_price_15m",
                                        tg_type=tg_type, timeframe="15m")
        self._alert_threshold = self._params["15m_price_change_percentage"]
        self._exchange_bar_dict = defaultdict(dict)

    def _handle_tick_message(self, _, msg: str) -> Any:
        tick = self._handle_tick_message_pre_check(msg)
        if not tick:
            return
        self._exchange_bar_dict[tick.timestamp][tick.exchange] = (tick.close / tick.open - 1) * 100
        self._current_timestamp = tick.timestamp
        self._alert_price_change()


class BinancePrice1hAlert(BinancePriceVolumeBase):
    def __init__(self, alert_name: str, tg_type: str = "TEST") -> None:
        BinancePriceVolumeBase.__init__(self, alert_name=alert_name, alert_type="binance_price_1h",
                                        tg_type=tg_type, timeframe="1h")
        self._alert_threshold = self._params["1h_price_change_percentage"]
        self._exchange_bar_dict = defaultdict(dict)

    def _handle_tick_message(self, _, msg: str) -> Any:
        tick = self._handle_tick_message_pre_check(msg)
        if not tick:
            return
        self._exchange_bar_dict[tick.timestamp][tick.exchange] = (tick.high / tick.low - 1) * 100
        self._current_timestamp = tick.timestamp
        self._alert_price_change()


class BinanceVolume15mAlert(BinancePriceVolumeBase):
    def __init__(self, alert_name: str, tg_type: str = "TEST") -> None:
        BinancePriceVolumeBase.__init__(self, alert_name=alert_name, alert_type="binance_volume_15m",
                                        tg_type=tg_type, timeframe="15m")
        self._alert_threshold = self._params["15m_volume_usd"]
        self._exchange_bar_dict = defaultdict(list)

    def _handle_tick_message(self, _, msg: str) -> Any:
        tick = self._handle_tick_message_pre_check(msg)
        if not tick:
            return

        # this is the first bar
        if len(self._exchange_bar_dict[tick.exchange]) == 0:
            self._exchange_bar_dict[tick.exchange] = [tick.volume]
            return

        self._exchange_bar_dict[tick.exchange].append(tick.volume)
        if tick.amount >= self._alert_threshold:
            # second bar is 50 times larger than first bar, amount is larger than threshold
            if tick.volume >= 50 * self._exchange_bar_dict[tick.exchange][-2]:
                self._update_count_and_send_telegram_message("2nd bar 50X", tick.exchange, 2, tick.amount)

            # third bar is 50 times larger than first bar, amount is larger than threshold
            if len(self._exchange_bar_dict[tick.exchange]) == 3 and \
                    tick.volume >= 50 * self._exchange_bar_dict[tick.exchange][-3]:
                self._update_count_and_send_telegram_message("3rd bar 50X", tick.exchange, 3, tick.amount)

            # second and third bar are 10 times larger than first bar, amount is larger than threshold
            if len(self._exchange_bar_dict[tick.exchange]) == 3 and \
                    tick.volume >= 10 * self._exchange_bar_dict[tick.exchange][-3] and \
                    self._exchange_bar_dict[tick.exchange][-2] >= 10 * self._exchange_bar_dict[tick.exchange][-3]:
                self._update_count_and_send_telegram_message("2nd, 3rd bar 10X", tick.exchange, 3, tick.amount)

        if len(self._exchange_bar_dict[tick.exchange]) == 3:
            self._exchange_bar_dict[tick.exchange].pop(0)


class BinanceVolume1hAlert(BinancePriceVolumeBase):
    def __init__(self, alert_name: str, tg_type: str = "TEST") -> None:
        BinancePriceVolumeBase.__init__(self, alert_name=alert_name, alert_type="binance_volume_1h",
                                        tg_type=tg_type, timeframe="1h")
        self._alert_threshold = self._params["1h_volume_usd"]
        self._exchange_bar_dict = defaultdict(list)

    def _handle_tick_message(self, _, msg: str) -> Any:
        tick = self._handle_tick_message_pre_check(msg)
        if not tick:
            return

        # this is the first bar
        if len(self._exchange_bar_dict[tick.exchange]) == 0:
            self._exchange_bar_dict[tick.exchange] = [tick.volume]
            return

        self._exchange_bar_dict[tick.exchange].append(tick.volume)
        # second bar is 10 times larger than first bar, amount is larger than threshold
        if tick.amount >= self._alert_threshold and \
                tick.volume >= 10 * self._exchange_bar_dict[tick.exchange][0]:
            self._update_count_and_send_telegram_message("2nd bar 10X", tick.exchange, 2, tick.amount)

        self._exchange_bar_dict[tick.exchange].pop(0)


class BinancePriceVolumeAlert(BaseAlert):
    def __init__(self, alert_name: str, alert_types: Sequence[str] = ("binance_price_15m", "binance_price_1h",
                                                                      "binance_volume_15m", "binance_volume_1h"),
                 tg_types: Sequence[str] = ("TEST", "TEST", "TEST", "TEST")) -> None:
        BaseAlert.__init__(self, alert_name, tg_types[0])
        self._alert_types = alert_types
        self._tg_types = tg_types

    def run(self) -> None:
        alert_type_to_class = {
            "binance_price_15m": BinancePrice15mAlert,
            "binance_price_1h": BinancePrice1hAlert,
            "binance_volume_15m": BinanceVolume15mAlert,
            "binance_volume_1h": BinanceVolume1hAlert,
        }

        for alert_type, tg_type in zip(self._alert_types, self._tg_types):
            alert = alert_type_to_class[alert_type](alert_name=self._alert_name, tg_type=tg_type)
            threading.Thread(target=alert.run).start()


if __name__ == "__main__":
    alert = BinancePriceVolumeAlert("price_volume", ["binance_price_1h"])
    alert.run()
