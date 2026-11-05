"""End-to-end tests for alert workflows.

These tests wire the real alert, settings, database, and data-source layers
together. Only external boundaries (exchange HTTP clients and Telegram) are
faked, and every database is a temporary SQLite file.
"""

import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from smrti_quant_alerts.alerts.base_alert import BaseAlert
from smrti_quant_alerts.alerts.crypto_alerts.coingecko_binance_spot_over_ma_alert import (
    BinanceSpotOverMA,
    CoingeckoSpotOverMA,
)
from smrti_quant_alerts.data_type import BinanceExchange, CoingeckoCoin
from smrti_quant_alerts.db import SpotOverMaDBUtils, close_database
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.stock_crypto_api import CryptoComprehensiveApi

TEST_SETTINGS_DIR = Path(__file__).resolve().parents[1] / "test_settings"


@pytest.fixture
def app_config(restore_config):
    """Load deterministic tokens and settings without reading project files."""
    Config.TOKENS = json.loads((TEST_SETTINGS_DIR / "dummy_token.json").read_text())
    Config.SETTINGS = json.loads((TEST_SETTINGS_DIR / "dummy_configs.json").read_text())
    Config.IS_SETUP = True
    yield Config


@pytest.fixture
def offline_discovery(monkeypatch):
    """Keep alert construction away from exchange discovery endpoints."""
    monkeypatch.setattr(CryptoComprehensiveApi, "_match_binance_exchange_to_coingecko_coins", lambda self: None)
    monkeypatch.setattr(CryptoComprehensiveApi, "get_exclude_coins", lambda self, _coins: set())


def test_config_files_drive_alert_database_initialization(tmp_path):
    shutil.copy(TEST_SETTINGS_DIR / "dummy_token.json", tmp_path / "token.json")
    shutil.copy(TEST_SETTINGS_DIR / "dummy_configs.json", tmp_path / "configs.json")
    Config.PROJECT_DIR = str(tmp_path)
    Config.IS_SETUP = False

    try:
        config = Config()
        alert = BaseAlert("price_volume", tg_type="TEST", config=config)

        assert alert._alert_name == "price_volume"
        assert config.SETTINGS["price_volume"]["database_name"] == "price_volume"
        assert (tmp_path / "runtime_database" / "price_volume.db").is_file()
    finally:
        close_database()


def test_coingecko_spot_over_ma_persists_counts_across_runs(runtime_database, app_config, offline_discovery):
    coin = CoingeckoCoin("bitcoin", "BTC")
    alert = CoingeckoSpotOverMA(set(), [coin], timeframe=1, window=200, alert_type="alert_100")
    client = MagicMock()
    client.get_price.return_value = {"bitcoin": {"usd": "10"}}
    client.get_coin_market_chart_by_id.return_value = {"prices": [[i, "1.0"] for i in range(250)]}
    alert._cg = client

    first_result = alert.run()

    assert first_result == ([(coin, 1)], [], [coin])
    assert SpotOverMaDBUtils.get_last_count(CoingeckoCoin) == {coin: 1}
    assert client.get_price.call_args.kwargs == {"ids": "bitcoin", "vs_currencies": "usd", "precision": "full"}
    assert client.get_coin_market_chart_by_id.call_args.kwargs == {
        "id": "bitcoin",
        "vs_currency": "usd",
        "days": 9,
        "precision": "full",
    }

    second_result = alert.run()

    assert second_result == ([(coin, 2)], [], [])
    assert SpotOverMaDBUtils.get_last_count(CoingeckoCoin) == {coin: 2}


def test_binance_spot_over_ma_persists_counts_across_runs(runtime_database, app_config, offline_discovery):
    exchange = BinanceExchange("BTC", "USDT")
    alert = BinanceSpotOverMA(set(), [exchange], timeframe=1, window=200, alert_type="alert_100")
    client = MagicMock()
    client.ticker_price.return_value = {"price": "10"}
    client.klines.return_value = [["0", "0", "0", "0", "1.0"] for _ in range(250)]
    alert._binance_spot_client = client

    first_result = alert.run()

    assert first_result == ([(exchange, 1)], [], [exchange])
    assert SpotOverMaDBUtils.get_last_count(BinanceExchange) == {exchange: 1}
    assert client.ticker_price.call_args.kwargs == {"symbol": "BTCUSDT"}
    assert client.klines.call_args.kwargs["interval"] == "1h"
    assert client.klines.call_args.kwargs["limit"] == 1000

    second_result = alert.run()

    assert second_result == ([(exchange, 2)], [], [])
    assert SpotOverMaDBUtils.get_last_count(BinanceExchange) == {exchange: 2}
