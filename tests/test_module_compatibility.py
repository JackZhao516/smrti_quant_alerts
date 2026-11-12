from importlib import import_module

import pytest


@pytest.mark.parametrize(
    ("legacy", "canonical"),
    [
        ("http_client", "gateway.http_client"),
        ("stock_crypto_api.stock_api", "gateway.stock_api"),
        ("stock_crypto_api.binance_stream", "gateway.binance_stream"),
        ("stock_crypto_api.share_history", "db.share_history"),
        ("email_api.email_api", "gateway.email_api"),
        ("telegram_api.telegram_api", "gateway.telegram_api"),
        ("llm_api.llm_api", "gateway.llm_api"),
    ],
)
def test_legacy_paths_share_the_same_module(legacy, canonical):
    assert import_module(f"smrti_quant_alerts.{legacy}") is import_module(f"smrti_quant_alerts.{canonical}")
