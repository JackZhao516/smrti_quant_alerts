"""Additional unit tests for the CoinGecko price increase alert."""

from unittest import mock

import pytest

from smrti_quant_alerts.alerts.crypto_alerts.coingecko_price_increase_alert import CoingeckoPriceIncreaseAlert
from smrti_quant_alerts.data_type import CoingeckoCoin
from smrti_quant_alerts.settings import Config


@pytest.fixture
def alert(runtime_database):
    Config.SETTINGS = {"price_increase_test": {"database_name": "price_increase_test"}}
    alert = CoingeckoPriceIncreaseAlert("price_increase_test", top_range=[(0, 10), (10, 20)], top_n=2, tg_type="TEST")
    alert._tg_bot = mock.Mock()
    return alert


def _coin(symbol: str) -> CoingeckoCoin:
    return CoingeckoCoin(symbol.lower(), symbol)


def test_constructor_normalizes_top_range(alert: CoingeckoPriceIncreaseAlert) -> None:
    assert alert._top_ranges == [(0, 10), (10, 20)]
    assert alert._timeframe == "14d"

    single_range = CoingeckoPriceIncreaseAlert("price_increase_test", top_range=(0, 10), tg_type="TEST")
    assert single_range._top_ranges == [(0, 10)]


def test_filter_top_n_coins_with_daily_volume_over_threshold(alert: CoingeckoPriceIncreaseAlert) -> None:
    coins = [_coin("AAA"), _coin("BBB"), _coin("CCC"), _coin("DDD")]
    volumes = {
        "AAA": None,
        "BBB": {"total_volumes": [[0, 999_999]]},
        "CCC": {"total_volumes": [[0, 1_500_000]]},
        "DDD": {"total_volumes": [[0, 2_000_000]]},
    }

    with mock.patch.object(
        alert,
        "get_coin_market_info",
        side_effect=lambda coin, *args, **kwargs: volumes[coin.coin_symbol],
    ):
        result = alert.filter_top_n_coins_with_daily_volume_over_threshold(coins)

    assert result == [_coin("CCC"), _coin("DDD")]


def test_filter_top_n_coins_stops_at_top_n(alert: CoingeckoPriceIncreaseAlert) -> None:
    coins = [_coin("AAA"), _coin("BBB")]

    with mock.patch.object(
        alert, "get_coin_market_info", return_value={"total_volumes": [[0, 1_500_000]]}
    ) as get_market_info:
        result = alert.filter_top_n_coins_with_daily_volume_over_threshold(coins)

    assert result == coins
    assert get_market_info.call_count == 2


def test_filter_top_n_coins_returns_when_fewer_than_top_n(alert: CoingeckoPriceIncreaseAlert) -> None:
    coins = [_coin("AAA"), _coin("BBB")]

    with mock.patch.object(
        alert,
        "get_coin_market_info",
        side_effect=[{"total_volumes": [[0, 1_500_000]]}, {"total_volumes": [[0, 1]]}],
    ):
        result = alert.filter_top_n_coins_with_daily_volume_over_threshold(coins)

    assert result == [_coin("AAA")]


def test_run_sends_message_and_coin_info(alert: CoingeckoPriceIncreaseAlert) -> None:
    coin_a, coin_b, coin_c = _coin("AAA"), _coin("BBB"), _coin("CCC")
    alert._coin_info = True

    with (
        mock.patch.object(
            alert, "get_top_n_market_cap_coins", side_effect=[[coin_a, coin_b, coin_c], []]
        ) as get_top_coins,
        mock.patch.object(
            alert,
            "get_coins_price_change_percentage",
            side_effect=[{coin_a: 5.123, coin_b: -1.0}, {}],
        ),
        mock.patch.object(
            alert,
            "filter_top_n_coins_with_daily_volume_over_threshold",
            side_effect=lambda coins, **_: coins,
        ),
        mock.patch(
            "smrti_quant_alerts.alerts.crypto_alerts.coingecko_price_increase_alert.send_coins_info_to_telegram"
        ) as send_info,
    ):
        alert.run()

    assert get_top_coins.call_count == 2
    alert._tg_bot.send_message.assert_called_once_with(
        "Top 2 coins in the top 0 - 10 Market Cap Coins with the biggest price increase "
        "in the last 14D timeframe: ['AAA: 5.12%']"
    )
    send_info.assert_called_once_with({coin_a}, alert._tg_bot, "price_increase_14d")


def test_run_skips_coin_info_when_disabled(alert: CoingeckoPriceIncreaseAlert) -> None:
    coin = _coin("AAA")
    alert._coin_info = False
    alert._top_ranges = [(0, 10)]

    with (
        mock.patch.object(alert, "get_top_n_market_cap_coins", return_value=[coin]),
        mock.patch.object(alert, "get_coins_price_change_percentage", return_value={coin: 10.0}),
        mock.patch.object(alert, "filter_top_n_coins_with_daily_volume_over_threshold", return_value=[coin]),
        mock.patch(
            "smrti_quant_alerts.alerts.crypto_alerts.coingecko_price_increase_alert.send_coins_info_to_telegram"
        ) as send_info,
    ):
        alert.run()

    send_info.assert_not_called()
    alert._tg_bot.send_message.assert_called_once()
