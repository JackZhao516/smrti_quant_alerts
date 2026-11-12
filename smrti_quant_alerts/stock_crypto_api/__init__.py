"""Compatibility imports for callers using the former market API package."""

import sys

from smrti_quant_alerts.db import share_history
from smrti_quant_alerts.gateway import (
    binance_client,
    binance_stream,
    crypto_binance_api,
    crypto_coingecko_api,
    crypto_comprehensive_api,
    fmp_client,
    stock_api,
)

from .utility import write_exclude_coins_to_file, get_datetime_now, get_stock_market_close_timestamp_from_date

BinanceApi = crypto_binance_api.BinanceApi
CoingeckoApi = crypto_coingecko_api.CoingeckoApi
CryptoComprehensiveApi = crypto_comprehensive_api.CryptoComprehensiveApi
StockApi = stock_api.StockApi

# Register the same modules so old and new paths share class identity and state.
for _module in (
    binance_client,
    binance_stream,
    crypto_binance_api,
    crypto_coingecko_api,
    crypto_comprehensive_api,
    fmp_client,
    share_history,
    stock_api,
):
    sys.modules[f"{__name__}.{_module.__name__.rsplit('.', 1)[-1]}"] = _module
