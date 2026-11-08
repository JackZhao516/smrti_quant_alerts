from unittest.mock import Mock, patch

import pytest

from smrti_quant_alerts.http_client import PermanentAPIError
from smrti_quant_alerts.stock_crypto_api.fmp_client import FMPClient


def test_profiles_use_documented_single_symbol_query_not_legacy_batch_path():
    with patch("requests.get", return_value=Mock(status_code=200, json=lambda: [])) as get:
        FMPClient("https://financialmodelingprep.com/api", "secret").profiles(["AAPL", "MSFT"])
    assert get.call_count == 2
    assert get.call_args.args[0] == "https://financialmodelingprep.com/stable/profile"
    assert get.call_args.kwargs["params"] == {"symbol": "MSFT", "apikey": "secret"}


def test_permission_failure_never_falls_back_to_legacy():
    with patch("requests.get", return_value=Mock(status_code=403)) as get:
        with pytest.raises(PermanentAPIError):
            FMPClient("https://financialmodelingprep.com/api", "secret").get("quote", symbol="AAPL")
    assert get.call_count == 1


def test_stable_estimates_normalize_revenue_field_for_existing_scores():
    with patch(
        "requests.get", return_value=Mock(status_code=200, json=lambda: [{"date": "2026-12-31", "revenueAvg": 120}])
    ) as get:
        rows = FMPClient("https://financialmodelingprep.com/api", "secret").get(
            "analyst-estimates", symbol="AAPL", period="annual"
        )
    assert rows[0]["estimatedRevenueAvg"] == 120
    assert get.call_args.kwargs["params"]["period"] == "annual"


def test_zero_revenue_does_not_produce_nan_margins():
    from smrti_quant_alerts.stock_crypto_api import StockApi
    from smrti_quant_alerts.data_type import StockSymbol, FinancialMetricType

    instance = object.__new__(StockApi)
    instance._fmp = Mock()
    instance._fmp.get.side_effect = [[{"revenue": 0, "grossProfit": 0, "operatingIncome": 0}], [{"freeCashFlow": 0}]]
    result = instance.get_stocks_stats_by_num_of_timeframe([StockSymbol("ZERO")], "quarter", 1)
    assert result[StockSymbol("ZERO")][0][FinancialMetricType.GROSS_MARGIN] == 0
