"""Replay real calculations against fixed data; never sends notifications."""

import argparse
import json
import tempfile
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from smrti_quant_alerts.data_type import CoingeckoCoin, StockSymbol
from smrti_quant_alerts.db import close_database, init_database_runtime
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.stock_crypto_api import CryptoComprehensiveApi, StockApi
from smrti_quant_alerts.alerts.crypto_alerts.coingecko_binance_spot_over_ma_alert import CoingeckoSpotOverMA


class CoinData:
    def get_price(self, **kwargs):
        return {"bitcoin": {"usd": "10"}}

    def get_coin_market_chart_by_id(self, **kwargs):
        return {"prices": [[i, "1"] for i in range(250)]}


def crypto():
    """A second run increments the persisted counter without marking BTC new."""
    coin = CoingeckoCoin("bitcoin", "BTC")
    with (
        patch.object(CryptoComprehensiveApi, "__init__", return_value=None),
        patch.object(CryptoComprehensiveApi, "get_exclude_coins", return_value=set()),
        patch("smrti_quant_alerts.alerts.crypto_alerts.coingecko_binance_spot_over_ma_alert.sleep"),
    ):
        alert = CoingeckoSpotOverMA(set(), [coin], window=200)
        alert._cg = CoinData()
        first, second = alert.run(), alert.run()
    return {
        "symbol": "BTC",
        "first_count": first[0][0][1],
        "second_count": second[0][0][1],
        "new_on_second_run": bool(second[2]),
    }


def stock():
    """Feed historical snapshots into the real percentage-change calculation."""
    config = SimpleNamespace(
        TOKENS={"FMP_API_KEY": "offline", "EODHD_API_KEY": "offline"},
        API_ENDPOINTS=Config.API_ENDPOINTS,
        PROJECT_DIR=Config.PROJECT_DIR,
    )
    api = StockApi(config=config)
    symbol = StockSymbol("AAPL")

    def prices(day):
        return {symbol: Decimal(110 if day == 1 else 100)}, {}

    with patch.object(api, "get_all_stock_price_volume_by_day_delta", side_effect=prices):
        result = api.get_all_stock_price_change_percentage(["1D"])
    return {"symbol": "AAPL", "timeframe": "1D", "change_percent": float(result[symbol]["1D"])}


def replay(scenario):
    original = Config.PROJECT_DIR
    with tempfile.TemporaryDirectory() as directory:
        try:
            Config.PROJECT_DIR = directory
            init_database_runtime("offline.db")

            # An unexpected request is a failing example, including retry paths.
            def no_network(*args, **kwargs):
                raise SystemExit("Offline examples must not contact external services")

            with patch("requests.sessions.Session.request", no_network):
                return {"crypto": crypto, "stock": stock}[scenario]()
        finally:
            close_database()
            Config.PROJECT_DIR = original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=["crypto", "stock"])
    args = parser.parse_args()
    print(json.dumps(replay(args.scenario), sort_keys=True))


if __name__ == "__main__":
    main()
