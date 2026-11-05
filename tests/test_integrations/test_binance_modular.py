from unittest.mock import Mock

from binance_common.models import ApiResponse
from binance_sdk_spot.rest_api.models.exchange_info_response import ExchangeInfoResponse

from smrti_quant_alerts.stock_crypto_api.binance_client import Spot, UMFutures


def test_actual_sdk_models_normalize_to_legacy_dictionary():
    sdk = Mock()
    sdk.rest_api.exchange_info.return_value = ApiResponse(
        lambda: ExchangeInfoResponse(timezone="UTC", symbols=[]), 200, {}
    )
    assert Spot(sdk).exchange_info(permissions=["SPOT"])["symbols"] == []
    sdk.rest_api.exchange_info.assert_called_once_with(permissions="SPOT")


def test_klines_maps_camelcase_and_retains_raw_arrays():
    sdk = Mock()
    sdk.rest_api.klines.return_value = ApiResponse(lambda: [[1, "2", "3", "4", "5"]], 200, {})
    assert Spot(sdk).klines("BTCUSDT", "1h", startTime=1)[0][4] == "5"
    sdk.rest_api.klines.assert_called_once_with(symbol="BTCUSDT", interval="1h", start_time=1)


def test_futures_uses_modular_exchange_information():
    sdk = Mock()
    sdk.rest_api.exchange_information.return_value = ApiResponse(lambda: {"symbols": []}, 200, {})
    assert UMFutures(sdk).exchange_info() == {"symbols": []}
    sdk.rest_api.exchange_information.assert_called_once_with()


def test_permissions_failure_is_permanent_and_single_symbol_ticker():
    from binance_common.errors import ForbiddenError
    from smrti_quant_alerts.http_client import PermanentAPIError
    import pytest

    sdk = Mock()
    sdk.rest_api.ticker_price.return_value.data.return_value = {"price": "2"}
    assert Spot(sdk).ticker_price(symbol="BTCUSDT") == {"price": "2"}
    sdk.rest_api.exchange_info.side_effect = ForbiddenError("private provider detail")
    with pytest.raises(PermanentAPIError) as caught:
        Spot(sdk).exchange_info()
    assert "private" not in str(caught.value)
    futures = UMFutures(sdk)
    sdk.rest_api.exchange_information.return_value.data.return_value = {"symbols": []}
    assert futures.exchange_info() == {"symbols": []}
