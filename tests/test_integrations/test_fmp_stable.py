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
