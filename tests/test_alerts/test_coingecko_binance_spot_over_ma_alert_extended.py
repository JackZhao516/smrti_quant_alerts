"""Tests for the CoinGecko/Binance spot-over-MA alerts.

All external boundaries (exchange APIs, Telegram, database utilities) are mocked
or backed by the temporary SQLite database provided by the ``runtime_database``
fixture.
"""

import copy
from unittest.mock import MagicMock, call, patch

import pytest

from smrti_quant_alerts.alerts.crypto_alerts import coingecko_binance_spot_over_ma_alert as spot_over_ma_module
from smrti_quant_alerts.alerts.crypto_alerts.coingecko_binance_spot_over_ma_alert import (
    BinanceSpotOverMA,
    CoingeckoSpotOverMA,
    SpotOverMAAlert,
    SpotOverMABase,
)
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.stock_crypto_api import CryptoComprehensiveApi

SPOT_OVER_MA_ALERT_NAME = "spot_ma"

SETTINGS = {
    SPOT_OVER_MA_ALERT_NAME: {
        "alert_type": "spot_over_ma",
        "alert_input_args": {},
        "alert_params": {},
        "run_time_input_args": {"daily_times": "09:30", "timezone": "Asia/Shanghai"},
        "database_name": SPOT_OVER_MA_ALERT_NAME,
    },
}


@pytest.fixture(autouse=True)
def alert_settings():
    """Install deterministic alert settings for every test."""
    Config.SETTINGS = copy.deepcopy(SETTINGS)
    yield Config.SETTINGS


@pytest.fixture
def make_coingecko_spot_over_ma(runtime_database, monkeypatch):
    """Build CoingeckoSpotOverMA without touching network-backed discovery."""
    monkeypatch.setattr(
        CryptoComprehensiveApi,
        "_match_binance_exchange_to_coingecko_coins",
        lambda self: None,
    )

    def factory(coins=None, exclude=None, timeframe=1, window=200, alert_type="alert_300"):
        coins = [] if coins is None else list(coins)
        exclude = set() if exclude is None else set(exclude)
        monkeypatch.setattr(
            CryptoComprehensiveApi,
            "get_exclude_coins",
            lambda self, _input_exclude_coins: exclude,
        )
        return CoingeckoSpotOverMA(exclude, coins, timeframe, window, alert_type)

    return factory


@pytest.fixture
def make_binance_spot_over_ma(runtime_database, monkeypatch):
    """Build BinanceSpotOverMA without touching network-backed discovery."""
    monkeypatch.setattr(
        CryptoComprehensiveApi,
        "_match_binance_exchange_to_coingecko_coins",
        lambda self: None,
    )

    def factory(exchanges=None, exclude=None, timeframe=1, window=200, alert_type="alert_300"):
        exchanges = [] if exchanges is None else list(exchanges)
        exclude = set() if exclude is None else set(exclude)
        monkeypatch.setattr(
            CryptoComprehensiveApi,
            "get_exclude_coins",
            lambda self, _input_exclude_coins: exclude,
        )
        return BinanceSpotOverMA(exclude, exchanges, timeframe, window, alert_type)

    return factory


@pytest.fixture
def make_spot_over_ma_alert(runtime_database, monkeypatch):
    """Build SpotOverMAAlert without its network-backed initializer."""
    monkeypatch.setattr(
        CryptoComprehensiveApi,
        "_match_binance_exchange_to_coingecko_coins",
        lambda self: None,
    )

    def factory(alert_type="alert_300", alert_coins_info=True):
        return SpotOverMAAlert(
            SPOT_OVER_MA_ALERT_NAME,
            alert_type,
            4,
            200,
            alert_coins_info,
            "TEST",
        )

    return factory


def test_coingecko_coin_spot_over_ma_excluded_coin(make_coingecko_spot_over_ma):
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert = make_coingecko_spot_over_ma([coin], exclude=[coin])
    alert.get_coin_current_price = MagicMock()
    alert.get_coin_history_hourly_close_price = MagicMock()

    with patch.object(spot_over_ma_module, "sleep") as sleep_mock:
        assert alert._coin_spot_over_ma(coin) is False

    sleep_mock.assert_not_called()
    alert.get_coin_current_price.assert_not_called()
    alert.get_coin_history_hourly_close_price.assert_not_called()
    assert alert._spot_over_ma == {}


def test_coingecko_coin_spot_over_ma_above_ma(make_coingecko_spot_over_ma):
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert = make_coingecko_spot_over_ma([coin])
    alert.get_coin_current_price = MagicMock(return_value=10)
    alert.get_coin_history_hourly_close_price = MagicMock(return_value=[1.0] * 200)

    with patch.object(spot_over_ma_module, "sleep") as sleep_mock:
        assert alert._coin_spot_over_ma(coin) is True

    sleep_mock.assert_called_once_with(2)
    alert.get_coin_history_hourly_close_price.assert_called_once_with(coin, 9)
    assert alert._spot_over_ma == {coin: 1}


def test_coingecko_coin_spot_over_ma_at_or_below_ma(make_coingecko_spot_over_ma):
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert = make_coingecko_spot_over_ma([coin])
    alert.get_coin_current_price = MagicMock(return_value=1)
    alert.get_coin_history_hourly_close_price = MagicMock(return_value=[1.0] * 200)

    with patch.object(spot_over_ma_module, "sleep"):
        assert alert._coin_spot_over_ma(coin) is False

    assert alert._spot_over_ma == {}


def test_coingecko_coin_spot_over_ma_exception_returns_false(make_coingecko_spot_over_ma):
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert = make_coingecko_spot_over_ma([coin])
    alert.get_coin_current_price = MagicMock(side_effect=RuntimeError("api failure"))
    alert.get_coin_history_hourly_close_price = MagicMock()

    with patch.object(spot_over_ma_module, "sleep"):
        assert alert._coin_spot_over_ma(coin) is False

    assert alert._spot_over_ma == {}


def test_binance_coin_spot_over_ma_excluded_coin(make_binance_spot_over_ma):
    exchange = BinanceExchange("BTC", "USDT")
    alert = make_binance_spot_over_ma([exchange], exclude=[exchange])
    alert.get_exchange_current_price = MagicMock()
    alert.get_exchange_history_hourly_close_price = MagicMock()

    assert alert._coin_spot_over_ma(exchange) is False

    alert.get_exchange_current_price.assert_not_called()
    alert.get_exchange_history_hourly_close_price.assert_not_called()
    assert alert._spot_over_ma == {}


def test_binance_coin_spot_over_ma_above_ma(make_binance_spot_over_ma):
    exchange = BinanceExchange("BTC", "USDT")
    alert = make_binance_spot_over_ma([exchange])
    alert.get_exchange_current_price = MagicMock(return_value=10)
    alert.get_exchange_history_hourly_close_price = MagicMock(return_value=[1.0] * 200)

    assert alert._coin_spot_over_ma(exchange) is True

    alert.get_exchange_history_hourly_close_price.assert_called_once_with(exchange, 9)
    assert alert._spot_over_ma == {exchange: 1}


def test_binance_coin_spot_over_ma_at_or_below_ma(make_binance_spot_over_ma):
    exchange = BinanceExchange("BTC", "USDT")
    alert = make_binance_spot_over_ma([exchange])
    alert.get_exchange_current_price = MagicMock(return_value=1)
    alert.get_exchange_history_hourly_close_price = MagicMock(return_value=[1.0] * 200)

    assert alert._coin_spot_over_ma(exchange) is False

    assert alert._spot_over_ma == {}


def test_binance_coin_spot_over_ma_exception_returns_false(make_binance_spot_over_ma):
    exchange = BinanceExchange("BTC", "USDT")
    alert = make_binance_spot_over_ma([exchange])
    alert.get_exchange_current_price = MagicMock(return_value=10)
    alert.get_exchange_history_hourly_close_price = MagicMock(side_effect=RuntimeError("api failure"))

    assert alert._coin_spot_over_ma(exchange) is False

    assert alert._spot_over_ma == {}


def test_coins_spot_over_ma_uses_thread_pool(make_coingecko_spot_over_ma):
    coins = [CoingeckoCoin("bitcoin", "BTC"), CoingeckoCoin("ethereum", "ETH")]
    alert = make_coingecko_spot_over_ma(coins)
    alert._coin_spot_over_ma = MagicMock(return_value=False)

    alert._coins_spot_over_ma(threads=2)

    assert alert._coin_spot_over_ma.call_count == 2
    assert alert._spot_over_ma == {}


def test_binance_coins_spot_over_ma_keeps_preferred_quotes(make_binance_spot_over_ma):
    alert = make_binance_spot_over_ma()

    def fake_coins_spot_over_ma(_self, threads=4):
        _self._spot_over_ma = {
            BinanceExchange("BTC", "ETH"): 1,
            BinanceExchange("BTC", "USDT"): 1,
            BinanceExchange("ETH", "ETH"): 1,
            BinanceExchange("ETH", "USDT"): 1,
            BinanceExchange("ADA", "BUSD"): 1,
            BinanceExchange("XRP", "BTC"): 1,
            BinanceExchange("DOGE", "ETH"): 1,
        }

    with patch.object(SpotOverMABase, "_coins_spot_over_ma", fake_coins_spot_over_ma):
        alert._coins_spot_over_ma(threads=6)

    assert alert._spot_over_ma == {
        BinanceExchange("BTC", "USDT"): 1,
        BinanceExchange("BTC", "ETH"): 1,
        BinanceExchange("ETH", "USDT"): 1,
        BinanceExchange("ADA", "BUSD"): 1,
        BinanceExchange("XRP", "BTC"): 1,
        BinanceExchange("DOGE", "ETH"): 1,
    }


def test_compare_last_time_tracks_deleted_added_and_incremented(make_coingecko_spot_over_ma, monkeypatch):
    alert_coin = CoingeckoCoin("alert-coin", "ALERT")
    deleted_coin = CoingeckoCoin("deleted-coin", "DEL")
    excluded_coin = CoingeckoCoin("excluded-coin", "EXCL")
    added_coin = CoingeckoCoin("added-coin", "ADD")
    alert = make_coingecko_spot_over_ma([alert_coin, excluded_coin, added_coin], exclude=[excluded_coin])
    alert._spot_over_ma = {alert_coin: 1, excluded_coin: 1, added_coin: 1}

    fake_db_utils = MagicMock()
    fake_db_utils.get_last_count.side_effect = [
        {alert_coin: 3, deleted_coin: 1},
        {alert_coin: 5, deleted_coin: 5, excluded_coin: 5},
    ]
    monkeypatch.setattr(spot_over_ma_module, "db_utils", fake_db_utils)

    newly_deleted, newly_added = alert._compare_last_time()

    assert newly_deleted == [deleted_coin]
    assert newly_added == [added_coin]
    assert alert._spot_over_ma[alert_coin] == 4
    assert alert._spot_over_ma[added_coin] == 1
    fake_db_utils.get_last_count.assert_has_calls(
        [
            call(CoingeckoCoin),
            call(CoingeckoCoin, "alert_300"),
        ]
    )
    fake_db_utils.update_last_count.assert_called_once_with([alert_coin, excluded_coin, added_coin], "alert_300")


def test_spot_over_ma_run_returns_sorted_counts(make_coingecko_spot_over_ma):
    coin_a = CoingeckoCoin("coin-a", "AAA")
    coin_b = CoingeckoCoin("coin-b", "BBB")
    coin_c = CoingeckoCoin("coin-c", "CCC")
    alert = make_coingecko_spot_over_ma([coin_a, coin_b, coin_c])

    def fake_coins_spot_over_ma():
        alert._spot_over_ma = {coin_a: 2, coin_b: 5, coin_c: 2}

    alert._coins_spot_over_ma = fake_coins_spot_over_ma
    alert._compare_last_time = MagicMock(return_value=([coin_c], [coin_a]))

    result = alert.run()

    assert result == ([(coin_b, 5), (coin_a, 2), (coin_c, 2)], [coin_c], [coin_a])


def test_get_target_coins_by_alert_type_alert_100(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert()
    exchange = BinanceExchange("BTC", "USDT")
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert.get_top_market_cap_coins_with_volume_threshold = MagicMock(return_value=([exchange], [coin]))

    alert._get_target_coins_by_alert_type("alert_100")

    alert.get_top_market_cap_coins_with_volume_threshold.assert_called_once_with(num=100)
    assert alert._binance_exchanges == [exchange]
    assert alert._coingecko_coins == [coin]


@pytest.mark.parametrize("alert_type", ["alert_300", "alert_500"])
def test_get_target_coins_by_alert_type_volume_filtered(make_spot_over_ma_alert, alert_type):
    alert = make_spot_over_ma_alert()
    exchange = BinanceExchange("ETH", "USDT")
    coin = CoingeckoCoin("ethereum", "ETH")
    alert.get_top_market_cap_coins_with_volume_threshold = MagicMock(return_value=([exchange], [coin]))

    alert._get_target_coins_by_alert_type(alert_type)

    alert.get_top_market_cap_coins_with_volume_threshold.assert_called_once_with(
        num=int(alert_type.split("_")[1]),
        daily_volume_threshold=1_000_000,
        weekly_volume_threshold=7_000_000,
    )
    assert alert._binance_exchanges == [exchange]
    assert alert._coingecko_coins == [coin]


def test_get_target_coins_by_alert_type_meme(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert()
    exchange = BinanceExchange("DOGE", "USDT")
    coin = CoingeckoCoin("doge", "DOGE")
    alert.get_coins_with_daily_volume_threshold_later_than_2023 = MagicMock(return_value=([exchange], [coin]))

    alert._get_target_coins_by_alert_type("meme_alert")

    alert.get_coins_with_daily_volume_threshold_later_than_2023.assert_called_once_with(threshold=3_000_000)
    assert alert._binance_exchanges == [exchange]
    assert alert._coingecko_coins == [coin]


def _spot_over_ma_fakes(cg_result, binance_result):
    cg_cls = MagicMock()
    cg_cls.return_value.run.return_value = cg_result
    binance_cls = MagicMock()
    binance_cls.return_value.run.return_value = binance_result
    return cg_cls, binance_cls


def test_alert_spot_cross_ma_by_alert_type_alert_100(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert()
    alert._tg_bot = MagicMock()
    cg_coin = CoingeckoCoin("coin-cg", "CG")
    binance_coin = BinanceExchange("BNB", "USDT")
    cg_deleted, cg_added = CoingeckoCoin("del-cg", "DELCG"), CoingeckoCoin("add-cg", "ADDCG")
    binance_deleted, binance_added = BinanceExchange("DELB", "USDT"), BinanceExchange("ADDB", "USDT")
    cg_cls, binance_cls = _spot_over_ma_fakes(
        ([(cg_coin, 10)], [cg_deleted], [cg_added]),
        ([(binance_coin, 7)], [binance_deleted], [binance_added]),
    )

    with (
        patch.object(spot_over_ma_module, "CoingeckoSpotOverMA", cg_cls),
        patch.object(spot_over_ma_module, "BinanceSpotOverMA", binance_cls),
        patch.object(alert, "_get_target_coins_by_alert_type"),
    ):
        exclude_coins, coins = alert._alert_spot_cross_ma_by_alert_type(alert_type="alert_100")

    cg_cls.assert_called_once_with(set(), alert._coingecko_coins, 4, 200, "alert_100")
    binance_cls.assert_called_once_with(set(), alert._binance_exchanges, 4, 200, "alert_100")
    assert coins == [cg_coin, binance_coin]
    assert exclude_coins == {cg_coin, binance_coin, cg_added, binance_added}
    alert._tg_bot.send_message.assert_has_calls(
        [
            call("alert_100: market cap top 100"),
            call(
                "Top 100 coins/coin exchanges spot over H4 MA200:\n"
                f"{[(cg_coin, 10), (binance_coin, 7)]}\n\n"
                "Top 100 coins/coin exchanges exchanges spot over H4 MA200 newly added:\n"
                f"{[cg_added, binance_added]}\n\n"
                "Top 100 coins/coin exchanges exchanges spot over H4 MA200 newly deleted:\n"
                f"{[cg_deleted, binance_deleted]}\n"
            ),
        ]
    )


@pytest.mark.parametrize("alert_type", ["alert_300", "alert_500"])
def test_alert_spot_cross_ma_by_alert_type_volume_headers(make_spot_over_ma_alert, alert_type):
    alert = make_spot_over_ma_alert()
    alert._tg_bot = MagicMock()
    cg_coin = CoingeckoCoin("coin-cg", "CG")
    exclude_coin = CoingeckoCoin("excluded", "EXCL")
    cg_cls, binance_cls = _spot_over_ma_fakes(([(cg_coin, 3)], [], []), ([], [], []))

    with (
        patch.object(spot_over_ma_module, "CoingeckoSpotOverMA", cg_cls),
        patch.object(spot_over_ma_module, "BinanceSpotOverMA", binance_cls),
        patch.object(alert, "_get_target_coins_by_alert_type"),
    ):
        exclude_coins, coins = alert._alert_spot_cross_ma_by_alert_type(
            exclude_coins={exclude_coin}, alert_type=alert_type
        )

    count = int(alert_type.split("_")[1])
    assert coins == [cg_coin]
    assert exclude_coins == {exclude_coin, cg_coin}
    assert alert._tg_bot.send_message.call_count == 3
    assert alert._tg_bot.send_message.call_args_list[0] == call(f"{alert_type}: market cap top {count}")
    assert alert._tg_bot.send_message.call_args_list[1] == call(
        "and daily volume >= 1M USDT "
        "for alt/busd, alt/usdt pairs\n"
        "and weekly volume >= 7M USDT  "
        "for alt/busd, alt/usdt pairs\n"
    )
    assert (
        f"Top {count} coins/coin exchanges spot over H4 MA200" in alert._tg_bot.send_message.call_args_list[2].args[0]
    )


def test_alert_spot_cross_ma_by_alert_type_meme(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert()
    alert._tg_bot = MagicMock()
    cg_coin = CoingeckoCoin("coin-cg", "CG")
    binance_coin = BinanceExchange("BNB", "USDT")
    cg_added = CoingeckoCoin("add-cg", "ADDCG")
    binance_deleted = BinanceExchange("DELB", "USDT")
    cg_cls, binance_cls = _spot_over_ma_fakes(
        ([(cg_coin, 1)], [], [cg_added]),
        ([(binance_coin, 1)], [binance_deleted], []),
    )

    with (
        patch.object(spot_over_ma_module, "CoingeckoSpotOverMA", cg_cls),
        patch.object(spot_over_ma_module, "BinanceSpotOverMA", binance_cls),
        patch.object(alert, "_get_target_coins_by_alert_type"),
    ):
        exclude_coins, coins = alert._alert_spot_cross_ma_by_alert_type(set(), "meme_alert")

    assert coins == [cg_coin, binance_coin]
    assert exclude_coins == {cg_coin, binance_coin, cg_added}
    assert alert._tg_bot.send_message.call_args_list == [
        call("For 2023 listed coins/exchanges with 24H volume larger than 3000000 USD"),
        call(
            "coins/coin exchanges spot over H4 MA200:\n"
            f"{[(cg_coin, 1), (binance_coin, 1)]}\n\n"
            "coins/coin exchanges exchanges spot over H4 MA200 newly added:\n"
            f"{[cg_added]}\n\n"
            "coins/coin exchanges exchanges spot over H4 MA200 newly deleted:\n"
            f"{[binance_deleted]}\n"
        ),
    ]


def test_sequential_alert_unions_exclusions_and_coins(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert()
    coin_100 = CoingeckoCoin("coin-100", "C100")
    coin_300 = CoingeckoCoin("coin-300", "C300")
    coin_500 = CoingeckoCoin("coin-500", "C500")
    excluded_100 = CoingeckoCoin("excluded-100", "E100")
    excluded_300 = CoingeckoCoin("excluded-300", "E300")
    excluded_500 = CoingeckoCoin("excluded-500", "E500")
    results = [
        ({excluded_100}, [coin_100]),
        ({excluded_300}, [coin_300]),
        ({excluded_500}, [coin_500]),
    ]
    calls = []

    def fake_alert_cross_ma(exclude_coins, alert_type):
        calls.append((set(exclude_coins), alert_type))
        return results[len(calls) - 1]

    alert._alert_spot_cross_ma_by_alert_type = fake_alert_cross_ma

    exclude_coins, alert_coins = alert._sequential_alert()

    assert exclude_coins == {excluded_100, excluded_300, excluded_500}
    assert alert_coins == {coin_100, coin_300, coin_500}
    assert calls == [
        (set(), "alert_100"),
        ({excluded_100}, "alert_300"),
        ({excluded_100, excluded_300}, "alert_500"),
    ]


def test_run_sequential_alert_sends_coins_info(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert(alert_type="sequential", alert_coins_info=True)
    alert.get_all_coingecko_coins = MagicMock()
    alert.get_all_binance_exchanges = MagicMock()
    coin = CoingeckoCoin("coin", "COIN")
    alert._sequential_alert = MagicMock(return_value=({"EXCL"}, [coin]))
    alert._alert_spot_cross_ma_by_alert_type = MagicMock()
    fake_db_utils = MagicMock()

    with (
        patch.object(spot_over_ma_module, "db_utils", fake_db_utils),
        patch.object(spot_over_ma_module, "close_database") as close_database_mock,
        patch.object(spot_over_ma_module, "send_coins_info_to_telegram") as send_info_mock,
        patch.object(spot_over_ma_module, "time", return_value=1_234.5),
    ):
        alert.run()

    alert.get_all_coingecko_coins.assert_called_once_with()
    alert.get_all_binance_exchanges.assert_called_once_with()
    alert._sequential_alert.assert_called_once_with()
    alert._alert_spot_cross_ma_by_alert_type.assert_not_called()
    fake_db_utils.remove_older_count.assert_called_once_with(1_234.5)
    close_database_mock.assert_called_once_with()
    send_info_mock.assert_called_once_with([coin], alert._tg_bot, "sequential")


def test_run_single_alert_without_coins_info(make_spot_over_ma_alert):
    alert = make_spot_over_ma_alert(alert_type="alert_100", alert_coins_info=False)
    alert.get_all_coingecko_coins = MagicMock()
    alert.get_all_binance_exchanges = MagicMock()
    coin = CoingeckoCoin("coin", "COIN")
    alert._alert_spot_cross_ma_by_alert_type = MagicMock(return_value=({coin}, [coin]))
    alert._sequential_alert = MagicMock()
    fake_db_utils = MagicMock()

    with (
        patch.object(spot_over_ma_module, "db_utils", fake_db_utils),
        patch.object(spot_over_ma_module, "close_database") as close_database_mock,
        patch.object(spot_over_ma_module, "send_coins_info_to_telegram") as send_info_mock,
        patch.object(spot_over_ma_module, "time", return_value=987.0),
    ):
        alert.run()

    alert._alert_spot_cross_ma_by_alert_type.assert_called_once_with(alert_type="alert_100")
    alert._sequential_alert.assert_not_called()
    fake_db_utils.remove_older_count.assert_called_once_with(987.0)
    close_database_mock.assert_called_once_with()
    send_info_mock.assert_not_called()


def test_abstract_coin_spot_over_ma_raises(make_binance_spot_over_ma):
    alert = make_binance_spot_over_ma()
    with pytest.raises(NotImplementedError):
        SpotOverMABase._coin_spot_over_ma(alert, BinanceExchange("BTC", "USDT"))


def test_spot_over_ma_alert_constructor_defaults(runtime_database, monkeypatch):
    monkeypatch.setattr(
        CryptoComprehensiveApi,
        "_match_binance_exchange_to_coingecko_coins",
        lambda self: None,
    )
    alert = SpotOverMAAlert(SPOT_OVER_MA_ALERT_NAME, "alert_300", 1, 200)

    assert alert._alert_type == "alert_300"
    assert alert._timeframe == 1
    assert alert._window == 200
    assert alert._alert_coins_info is True
    assert alert._coingecko_coins == []
    assert alert._binance_exchanges == []
