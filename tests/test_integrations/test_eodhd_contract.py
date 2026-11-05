from unittest.mock import Mock, patch

from smrti_quant_alerts.stock_crypto_api import StockApi


def api():
    instance = object.__new__(StockApi)
    instance.EODHD_API_URL = "https://eodhd.example/api"
    instance.EODHD_API_KEY = "secret"
    return instance


def test_bulk_unauthorized_fails_once_without_historical_loop():
    with patch("requests.get", return_value=Mock(status_code=401)) as get:
        assert api().get_all_stock_price_volume_by_day_delta() == ({}, {})
    assert get.call_count == 1


def test_empty_bulk_history_has_finite_lookback():
    with patch("requests.get", return_value=Mock(status_code=200, json=lambda: [])) as get:
        assert api().get_all_stock_price_volume_by_day_delta() == ({}, {})
    assert get.call_count == 10


def test_malformed_bulk_and_history_arrays_fail_permanently():
    from smrti_quant_alerts.data_type import StockSymbol

    with patch("requests.get", return_value=Mock(status_code=200, json=lambda: {"unexpected": "object"})) as get:
        assert api().get_all_stock_price_volume_by_day_delta() == ({}, {})
        assert api().get_stock_close_prices_by_timeframe_num_of_ticks(StockSymbol("AAPL"), "1D", 5) == []
    assert get.call_count == 2
