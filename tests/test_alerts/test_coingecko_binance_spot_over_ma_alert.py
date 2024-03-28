import unittest
from unittest.mock import patch

from smrti_quant_alerts.alerts.crypto_alerts.coingecko_binance_spot_over_ma_alert \
    import SpotOverMABase, BinanceSpotOverMA, CoingeckoSpotOverMA, SpotOverMAAlert
from smrti_quant_alerts.data_type import CoingeckoCoin, BinanceExchange, TradingSymbol

# TODO: test alert_spot_over_ma


class TestSpotOverMABase(unittest.TestCase):
    pass
