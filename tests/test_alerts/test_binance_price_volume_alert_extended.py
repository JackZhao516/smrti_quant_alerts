"""Tests for the Binance price/volume alerts.

All external boundaries (websocket clients, exchange APIs, Telegram, database
utilities) are mocked or backed by the temporary SQLite database provided by the
``runtime_database`` fixture.
"""

import copy
import json
from unittest.mock import MagicMock, call, patch

import pytest

from smrti_quant_alerts.alerts.crypto_alerts import binance_price_volume_alert as price_volume_module
from smrti_quant_alerts.alerts.crypto_alerts.binance_price_volume_alert import (
    BinancePrice15mAlert,
    BinancePrice1hAlert,
    BinancePriceVolumeAlert,
    BinancePriceVolumeBase,
    BinanceVolume15mAlert,
    BinanceVolume1hAlert,
)
from smrti_quant_alerts.data_type import BinanceExchange, ExchangeTick
from smrti_quant_alerts.settings import Config

PRICE_VOLUME_ALERT_NAME = "price_volume"

SETTINGS = {
    PRICE_VOLUME_ALERT_NAME: {
        "alert_type": "price_volume",
        "alert_input_args": {
            "alert_name": PRICE_VOLUME_ALERT_NAME,
            "tg_types": ["PRICE_15M", "PRICE_1H", "VOLUME_15M", "VOLUME_1H"],
            "alert_types": [
                "binance_price_15m",
                "binance_price_1h",
                "binance_volume_15m",
                "binance_volume_1h",
            ],
        },
        "alert_params": {
            "15m_volume_usd": 5.0,
            "1h_volume_usd": 5.0,
            "15m_price_change_percentage": 5.0,
            "1h_price_change_percentage": 10.0,
        },
        "run_time_input_args": {"daily_times": "11:59", "timezone": "Asia/Shanghai"},
        "database_name": PRICE_VOLUME_ALERT_NAME,
    },
}


class _StopAutoRestart(Exception):
    """Sentinel used to break out of the websocket restart loop."""


@pytest.fixture(autouse=True)
def alert_settings():
    """Install deterministic alert settings for every test."""
    Config.SETTINGS = copy.deepcopy(SETTINGS)
    yield Config.SETTINGS


@pytest.fixture
def make_price_volume_alert(runtime_database):
    """Build a price/volume alert with websocket and exchange discovery mocked."""

    def factory(
        alert_cls=BinancePrice15mAlert,
        exchanges=None,
        client=None,
        tg_type="TEST",
    ):
        if exchanges is None:
            exchanges = [BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")]
        if client is None:
            client = MagicMock()
        with (
            patch.object(price_volume_module, "SpotWebsocketStreamClient", return_value=client),
            patch.object(
                BinancePriceVolumeBase,
                "get_all_spot_exchanges_in_usdt_fdusd_btc",
                return_value=exchanges,
            ),
        ):
            alert = alert_cls(PRICE_VOLUME_ALERT_NAME, tg_type=tg_type)
        alert._test_websocket_client = client
        return alert

    return factory


def _tick_message(
    symbol="BTCUSDT",
    interval="15m",
    closed=True,
    volume=10.0,
    open_price=100.0,
    close_price=1.0,
    high_price=120.0,
    low_price=90.0,
    timestamp=1000,
):
    return json.dumps(
        {
            "stream": f"{symbol.lower()}@kline_{interval}",
            "data": {
                "k": {
                    "x": closed,
                    "i": interval,
                    "s": symbol,
                    "v": volume,
                    "o": open_price,
                    "c": close_price,
                    "h": high_price,
                    "l": low_price,
                    "t": timestamp,
                }
            },
        }
    )


def test_exchanges_to_subscription_stream_names(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    assert alert._exchanges_to_subscription_stream_names(
        [BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "BTC")]
    ) == ["btcusdt@kline_15m", "ethbtc@kline_15m"]

    hourly = make_price_volume_alert(BinancePrice1hAlert)
    assert hourly._exchanges_to_subscription_stream_names([BinanceExchange("BTC", "USDT")]) == ["btcusdt@kline_1h"]


@pytest.mark.parametrize(
    ("alert_cls", "alert_type", "timeframe", "threshold_key", "threshold"),
    [
        (BinancePrice15mAlert, "binance_price_15m", "15m", "15m_price_change_percentage", 5.0),
        (BinancePrice1hAlert, "binance_price_1h", "1h", "1h_price_change_percentage", 10.0),
        (BinanceVolume15mAlert, "binance_volume_15m", "15m", "15m_volume_usd", 5.0),
        (BinanceVolume1hAlert, "binance_volume_1h", "1h", "1h_volume_usd", 5.0),
    ],
)
def test_concrete_alert_constructor_reads_thresholds(
    make_price_volume_alert, alert_cls, alert_type, timeframe, threshold_key, threshold
):
    alert = make_price_volume_alert(alert_cls)

    assert alert._alert_type == alert_type
    assert alert._timeframe == timeframe
    assert alert._alert_threshold == Config.SETTINGS[PRICE_VOLUME_ALERT_NAME]["alert_params"][threshold_key]
    assert alert._alert_threshold == threshold
    assert len(alert._exchanges) == 2
    if alert_cls in (BinancePrice15mAlert, BinancePrice1hAlert):
        assert alert._exchange_bar_dict.default_factory is dict
    else:
        assert alert._exchange_bar_dict.default_factory is list


def test_handle_tick_message_pre_check_accepts_valid_message(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    msg = _tick_message(volume=12.5, open_price=100.0, close_price=110.0, high_price=120.0, low_price=90.0)

    tick = alert._handle_tick_message_pre_check(msg)

    assert isinstance(tick, ExchangeTick)
    assert tick.exchange == BinanceExchange("BTC", "USDT")
    assert tick.volume == 12.5
    assert tick.open == 100.0
    assert tick.close == 110.0
    assert tick.high == 120.0
    assert tick.low == 90.0
    assert tick.timestamp == 1000


def test_handle_tick_message_pre_check_rejects_missing_stream(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    payload = json.loads(_tick_message())
    del payload["stream"]
    assert alert._handle_tick_message_pre_check(json.dumps(payload)) is None


def test_handle_tick_message_pre_check_rejects_missing_data(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    payload = json.loads(_tick_message())
    del payload["data"]
    assert alert._handle_tick_message_pre_check(json.dumps(payload)) is None


def test_handle_tick_message_pre_check_rejects_missing_kline(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    payload = json.loads(_tick_message())
    del payload["data"]["k"]
    assert alert._handle_tick_message_pre_check(json.dumps(payload)) is None


def test_handle_tick_message_pre_check_rejects_open_kline(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    assert alert._handle_tick_message_pre_check(_tick_message(closed=False)) is None


def test_handle_tick_message_pre_check_rejects_wrong_interval(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    assert alert._handle_tick_message_pre_check(_tick_message(interval="1h")) is None


def test_handle_tick_message_pre_check_rejects_unknown_symbol(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    assert alert._handle_tick_message_pre_check(_tick_message(symbol="DOGEUSDT")) is None


def test_price_15m_handle_tick_message_uses_close_over_open(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    alert._alert_price_change = MagicMock()

    alert._handle_tick_message(
        None,
        _tick_message(open_price=100.0, close_price=110.0, timestamp=1234),
    )

    btc = BinanceExchange("BTC", "USDT")
    assert alert._exchange_bar_dict[1234][btc] == pytest.approx(10.0)
    assert alert._current_timestamp == 1234
    alert._alert_price_change.assert_called_once_with()


def test_price_1h_handle_tick_message_uses_high_over_low(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice1hAlert)
    alert._alert_price_change = MagicMock()

    alert._handle_tick_message(
        None,
        _tick_message(interval="1h", high_price=110.0, low_price=100.0, timestamp=4321),
    )

    btc = BinanceExchange("BTC", "USDT")
    assert alert._exchange_bar_dict[4321][btc] == pytest.approx(10.0)
    alert._alert_price_change.assert_called_once_with()


@pytest.mark.parametrize(
    ("alert_cls", "interval"),
    [(BinancePrice15mAlert, "15m"), (BinancePrice1hAlert, "1h")],
)
def test_price_handle_tick_message_ignores_invalid_tick(make_price_volume_alert, alert_cls, interval):
    alert = make_price_volume_alert(alert_cls)
    alert._alert_price_change = MagicMock()

    alert._handle_tick_message(None, _tick_message(interval=interval, closed=False))

    assert alert._exchange_bar_dict == {}
    alert._alert_price_change.assert_not_called()


def test_volume_15m_handle_tick_message_stores_first_bar(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume15mAlert)
    alert._update_count_and_send_telegram_message = MagicMock()

    alert._handle_tick_message(None, _tick_message(volume=10.0))

    btc = BinanceExchange("BTC", "USDT")
    assert alert._exchange_bar_dict[btc] == [10.0]
    alert._update_count_and_send_telegram_message.assert_not_called()


def test_volume_15m_handle_tick_message_alerts_on_large_bars(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume15mAlert)
    alert._update_count_and_send_telegram_message = MagicMock()
    btc = BinanceExchange("BTC", "USDT")

    alert._handle_tick_message(None, _tick_message(volume=10.0))
    alert._handle_tick_message(None, _tick_message(volume=500.0))
    alert._update_count_and_send_telegram_message.assert_called_once_with("2nd bar 50X", btc, 2, 500.0)

    alert._update_count_and_send_telegram_message.reset_mock()
    alert._handle_tick_message(None, _tick_message(volume=500.0))

    assert alert._update_count_and_send_telegram_message.call_args_list == [
        call("3rd bar 50X", btc, 3, 500.0),
        call("2nd, 3rd bar 10X", btc, 3, 500.0),
    ]
    assert alert._exchange_bar_dict[btc] == [500.0, 500.0]


def test_volume_15m_handle_tick_message_skips_small_bars(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume15mAlert)
    alert._update_count_and_send_telegram_message = MagicMock()

    alert._handle_tick_message(None, _tick_message(volume=10.0))
    alert._handle_tick_message(None, _tick_message(volume=20.0))
    alert._handle_tick_message(None, _tick_message(volume=20.0))

    alert._update_count_and_send_telegram_message.assert_not_called()
    btc = BinanceExchange("BTC", "USDT")
    assert alert._exchange_bar_dict[btc] == [20.0, 20.0]


def test_volume_1h_handle_tick_message_stores_first_and_alerts_on_second(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume1hAlert)
    alert._update_count_and_send_telegram_message = MagicMock()
    btc = BinanceExchange("BTC", "USDT")

    alert._handle_tick_message(None, _tick_message(interval="1h", volume=10.0))
    assert alert._exchange_bar_dict[btc] == [10.0]
    alert._update_count_and_send_telegram_message.assert_not_called()

    alert._handle_tick_message(None, _tick_message(interval="1h", volume=100.0))
    alert._update_count_and_send_telegram_message.assert_called_once_with("2nd bar 10X", btc, 2, 100.0)
    assert alert._exchange_bar_dict[btc] == [100.0]


def test_volume_1h_handle_tick_message_skips_small_second_bar(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume1hAlert)
    alert._update_count_and_send_telegram_message = MagicMock()

    alert._handle_tick_message(None, _tick_message(interval="1h", volume=10.0))
    alert._handle_tick_message(None, _tick_message(interval="1h", volume=20.0))

    alert._update_count_and_send_telegram_message.assert_not_called()


@pytest.mark.parametrize(
    ("alert_cls", "interval"),
    [(BinanceVolume15mAlert, "15m"), (BinanceVolume1hAlert, "1h")],
)
def test_volume_handle_tick_message_ignores_invalid_tick(make_price_volume_alert, alert_cls, interval):
    alert = make_price_volume_alert(alert_cls)
    alert._update_count_and_send_telegram_message = MagicMock()

    alert._handle_tick_message(None, _tick_message(interval=interval, closed=False))

    assert alert._exchange_bar_dict == {}
    alert._update_count_and_send_telegram_message.assert_not_called()


def test_update_count_and_send_telegram_message_two_bars(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume15mAlert)
    btc = BinanceExchange("BTC", "USDT")
    alert._exchange_bar_dict[btc] = [100.0, 500.0]
    alert._db_utils = MagicMock()
    alert._db_utils.update_count.side_effect = [1, 6]
    alert._tg_bot = MagicMock()

    alert._update_count_and_send_telegram_message("2nd bar 50X", btc, 2, 500.2)

    assert alert._db_utils.update_count.call_args_list == [
        call(btc, "binance_volume_15m", 1850, "daily"),
        call(btc, "binance_volume_15m", 1850, "monthly"),
    ]
    alert._tg_bot.send_message.assert_called_once_with(
        "BTCUSDT binance_volume_15m alert 2nd bar 50X:\n"
        "[100.0 -> 500.0]\namount: $501\n"
        "ticker volume alert monthly count: 6"
    )


def test_update_count_and_send_telegram_message_three_bars(make_price_volume_alert):
    alert = make_price_volume_alert(BinanceVolume15mAlert)
    btc = BinanceExchange("BTC", "USDT")
    alert._exchange_bar_dict[btc] = [1.0, 2.0, 3.0]
    alert._db_utils = MagicMock()
    alert._db_utils.update_count.side_effect = [2, 7]
    alert._tg_bot = MagicMock()

    alert._update_count_and_send_telegram_message("2nd, 3rd bar 10X", btc, 3, 12.3)

    alert._tg_bot.send_message.assert_called_once_with(
        "BTCUSDT binance_volume_15m alert 2nd, 3rd bar 10X:\n"
        "[1.0 -> 2.0 -> 3.0]\namount: $13\n"
        "ticker volume alert monthly count: 7"
    )


def test_alert_price_change_ignores_incomplete_exchange_set(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    alert._current_timestamp = 100
    alert._exchange_bar_dict[100] = {BinanceExchange("BTC", "USDT"): 10.0}
    alert._tg_bot = MagicMock()

    alert._alert_price_change()

    alert._tg_bot.send_message.assert_not_called()
    assert alert._exchange_bar_dict[100]


def test_alert_price_change_sends_largest_and_smallest(make_price_volume_alert):
    bases = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ"]
    exchanges = [BinanceExchange(base, "USDT") for base in bases]
    alert = make_price_volume_alert(BinancePrice15mAlert, exchanges=exchanges)
    changes = [10.0, 9.0, 8.0, 7.0, 6.0, -6.0, -7.0, -8.0, -9.0, -10.0]
    alert._exchange_bar_dict[100] = dict(zip(exchanges, changes, strict=True))
    alert._current_timestamp = 100
    alert._db_utils = MagicMock()
    alert._db_utils.update_count.return_value = 3
    alert._tg_bot = MagicMock()

    alert._alert_price_change()

    assert alert._db_utils.update_count.call_count == 20
    alert._tg_bot.send_message.assert_has_calls(
        [
            call(
                "15m top 5 positive price (close/open) change in % over 5.0%: "
                "['AAAUSDT: 10.0%, monthly count: 3', 'BBBUSDT: 9.0%, monthly count: 3', "
                "'CCCUSDT: 8.0%, monthly count: 3', 'DDDUSDT: 7.0%, monthly count: 3', "
                "'EEEUSDT: 6.0%, monthly count: 3']"
            ),
            call(
                "15m top 5 negative price (close/open) change in % over 5.0%: "
                "['JJJUSDT: -10.0%, monthly count: 3', 'IIIUSDT: -9.0%, monthly count: 3', "
                "'HHHUSDT: -8.0%, monthly count: 3', 'GGGUSDT: -7.0%, monthly count: 3', "
                "'FFFUSDT: -6.0%, monthly count: 3']"
            ),
        ]
    )
    assert 100 not in alert._exchange_bar_dict


def test_alert_price_change_uses_high_low_for_hourly(make_price_volume_alert):
    bases = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF", "GGG", "HHH", "III", "JJJ"]
    exchanges = [BinanceExchange(base, "USDT") for base in bases]
    alert = make_price_volume_alert(BinancePrice1hAlert, exchanges=exchanges)
    changes = [20.0, 18.0, 16.0, 14.0, 12.0, -12.0, -14.0, -16.0, -18.0, -20.0]
    alert._exchange_bar_dict[100] = dict(zip(exchanges, changes, strict=True))
    alert._current_timestamp = 100
    alert._db_utils = MagicMock()
    alert._db_utils.update_count.return_value = 1
    alert._tg_bot = MagicMock()

    alert._alert_price_change()

    messages = [call_args.args[0] for call_args in alert._tg_bot.send_message.call_args_list]
    assert len(messages) == 2
    assert "(high/low)" in messages[0]
    assert "(high/low)" in messages[1]
    assert "over 10.0%" in messages[0]


def test_abstract_handle_tick_message_raises(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    with pytest.raises(NotImplementedError):
        BinancePriceVolumeBase._handle_tick_message(alert, None, "{}")


def test_alert_count_sends_counts_and_resets_monthly(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    btc, eth, ada = BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT"), BinanceExchange("ADA", "USDT")
    monthly = {eth: (5, 0.0), btc: (2, 0.0), ada: (1, 0.0)}
    daily = {ada: (9, 0.0), eth: (4, 0.0), btc: (2, 0.0)}
    alert._db_utils = MagicMock()
    alert._db_utils.get_count.side_effect = [monthly, daily]
    alert._tg_bot = MagicMock()
    alert._monthly_start_timestamp = 0.0

    with patch.object(price_volume_module.time, "time", return_value=3_000_000.0):
        alert._alert_count()

    alert._tg_bot.send_message.assert_has_calls(
        [
            call(
                "Daily binance_price_15m ticker monthly count:\n"
                "ETHUSDT monthly count: 5\n"
                "BTCUSDT monthly count: 2\n"
                "ADAUSDT monthly count: 1\n",
                blue_text=True,
            ),
            call(
                "Daily binance_price_15m new alerts daily count:\nADAUSDT: 9\nETHUSDT: 4\nBTCUSDT: 2\n",
                blue_text=True,
            ),
        ]
    )
    alert._db_utils.reset_count.assert_has_calls(
        [
            call("binance_price_15m", "monthly"),
            call("binance_price_15m", "daily"),
        ]
    )
    assert alert._monthly_start_timestamp == 3_000_000.0


def test_alert_count_does_not_reset_recent_monthly_count(make_price_volume_alert):
    alert = make_price_volume_alert(BinancePrice15mAlert)
    btc = BinanceExchange("BTC", "USDT")
    alert._db_utils = MagicMock()
    alert._db_utils.get_count.side_effect = [{btc: (1, 0.0)}, {btc: (1, 0.0)}]
    alert._tg_bot = MagicMock()
    alert._monthly_start_timestamp = 1_000_000.0 - 100

    with patch.object(price_volume_module.time, "time", return_value=1_000_000.0):
        alert._alert_count()

    alert._db_utils.reset_count.assert_called_once_with("binance_price_15m", "daily")
    assert alert._monthly_start_timestamp == 1_000_000.0 - 100


def test_auto_subscribe_new_exchanges_no_change(make_price_volume_alert):
    btc = BinanceExchange("BTC", "USDT")
    alert = make_price_volume_alert(BinancePrice15mAlert, exchanges=[btc])
    alert._websocket_client = MagicMock()
    Config.SETTINGS[PRICE_VOLUME_ALERT_NAME]["alert_params"]["15m_price_change_percentage"] = 99.0

    with (
        patch.object(alert.CONFIG, "reload_settings") as reload_mock,
        patch.object(alert, "get_all_spot_exchanges_in_usdt_fdusd_btc", return_value=[BinanceExchange("BTC", "USDT")]),
    ):
        alert._auto_subscribe_new_exchanges()

    reload_mock.assert_called_once_with()
    alert._websocket_client.subscribe.assert_not_called()
    assert alert._exchanges == [btc]
    assert alert._params["15m_price_change_percentage"] == 99.0


def test_auto_subscribe_new_exchanges_subscribes_diff(make_price_volume_alert):
    btc, eth = BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")
    alert = make_price_volume_alert(BinancePrice15mAlert, exchanges=[btc])
    alert._websocket_client = MagicMock()

    with (
        patch.object(alert.CONFIG, "reload_settings"),
        patch.object(alert, "get_all_spot_exchanges_in_usdt_fdusd_btc", return_value=[btc, eth]),
    ):
        alert._auto_subscribe_new_exchanges()

    alert._websocket_client.subscribe.assert_called_once_with(["ethusdt@kline_15m"])
    assert alert._exchanges == [btc, eth]


def test_auto_restart_websocket_restarts_dead_client(make_price_volume_alert):
    btc = BinanceExchange("BTC", "USDT")
    old_client = MagicMock()
    new_client = MagicMock()
    alert = make_price_volume_alert(BinancePrice15mAlert, exchanges=[btc], client=old_client)
    old_client.socket_manager.is_alive.side_effect = [True, False]
    new_client.socket_manager.is_alive.side_effect = [_StopAutoRestart()]

    with patch.object(price_volume_module, "SpotWebsocketStreamClient", return_value=new_client):
        with pytest.raises(_StopAutoRestart):
            alert._auto_restart_websocket()

    assert alert._websocket_client is new_client
    new_client.subscribe.assert_called_once_with(["btcusdt@kline_15m"])


def test_run_subscribes_and_starts_three_services(make_price_volume_alert):
    btc, eth = BinanceExchange("BTC", "USDT"), BinanceExchange("ETH", "USDT")
    alert = make_price_volume_alert(BinancePrice15mAlert, exchanges=[btc, eth])

    with patch.object(price_volume_module.threading, "Thread") as thread_cls:
        alert.run()

    alert._websocket_client.subscribe.assert_called_once_with(["btcusdt@kline_15m", "ethusdt@kline_15m"])
    assert alert._monthly_start_timestamp > 0
    assert thread_cls.call_count == 3
    assert thread_cls.return_value.start.call_count == 3

    first, second, third = thread_cls.call_args_list
    assert first.kwargs["target"] == price_volume_module.run_task_at_daily_time
    assert first.kwargs["args"] == (alert._alert_count, "11:59", None, "Asia/Shanghai")
    assert second.kwargs["target"] == price_volume_module.run_task_at_daily_time
    assert second.kwargs["args"] == (
        alert._auto_subscribe_new_exchanges,
        [f"{str(hour).zfill(2)}:05" for hour in range(24)],
    )
    assert third.kwargs["target"] == alert._auto_restart_websocket


def test_price_volume_alert_run_constructs_and_starts_each_alert(runtime_database):
    alert = BinancePriceVolumeAlert(PRICE_VOLUME_ALERT_NAME)

    with (
        patch.object(price_volume_module, "BinancePrice15mAlert") as price_15m,
        patch.object(price_volume_module, "BinancePrice1hAlert") as price_1h,
        patch.object(price_volume_module, "BinanceVolume15mAlert") as volume_15m,
        patch.object(price_volume_module, "BinanceVolume1hAlert") as volume_1h,
        patch.object(price_volume_module.threading, "Thread") as thread_cls,
    ):
        alert.run()

    for alert_cls in (price_15m, price_1h, volume_15m, volume_1h):
        alert_cls.assert_called_once_with(alert_name=PRICE_VOLUME_ALERT_NAME, tg_type="TEST")

    assert thread_cls.call_count == 4
    assert thread_cls.return_value.start.call_count == 4
    started_targets = [call_args.kwargs["target"] for call_args in thread_cls.call_args_list]
    assert started_targets == [
        price_15m.return_value.run,
        price_1h.return_value.run,
        volume_15m.return_value.run,
        volume_1h.return_value.run,
    ]
