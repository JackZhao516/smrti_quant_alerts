"""Read-only compatibility facade over Binance's official modular REST SDKs."""

from binance_common.configuration import ConfigurationRestAPI
from binance_common.errors import ForbiddenError, UnauthorizedError
from binance_sdk_spot.spot import Spot as SpotSDK
from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import DerivativesTradingUsdsFutures

from smrti_quant_alerts.http_client import PermanentAPIError


def plain(value):
    if isinstance(value, list):
        return [plain(item) for item in value]
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if hasattr(value, "to_dict"):
        return plain(value.to_dict())
    return value


class Spot:
    def __init__(self, sdk=None):
        self.sdk = sdk or SpotSDK(config_rest_api=ConfigurationRestAPI(timeout=30000, retries=2))

    def _call(self, method, **kwargs):
        try:
            return plain(getattr(self.sdk.rest_api, method)(**kwargs).data())
        except (UnauthorizedError, ForbiddenError):
            raise PermanentAPIError(403, "Binance permissions rejected") from None

    def exchange_info(self, **kwargs):
        if isinstance(kwargs.get("permissions"), list):
            kwargs["permissions"] = kwargs["permissions"][0]
        return self._call("exchange_info", **kwargs)

    def ticker_price(self, **kwargs):
        return self._call("ticker_price", **kwargs)

    def klines(self, symbol, interval, **kwargs):
        kwargs = {{"startTime": "start_time", "endTime": "end_time"}.get(k, k): v for k, v in kwargs.items()}
        return self._call("klines", symbol=str(symbol), interval=interval, **kwargs)


class UMFutures(Spot):
    def __init__(self, sdk=None):
        self.sdk = sdk or DerivativesTradingUsdsFutures(config_rest_api=ConfigurationRestAPI(timeout=30000, retries=2))

    def exchange_info(self, **kwargs):
        return self._call("exchange_information")

    def mark_price(self, symbol):
        return self._call("mark_price", symbol=str(symbol))
