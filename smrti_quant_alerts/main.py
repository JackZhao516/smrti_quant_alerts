import sys
import logging

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.alerts import CoingeckoMarketCapAlert, BinancePriceVolumeAlert, \
    CGAltsAlert, SpotOverMAAlert, FutureFundingRate, StockPriceTopPerformerAlert, CoingeckoPriceIncreaseAlert, \
    MACDAlert, FloatingSharesAlert
from smrti_quant_alerts.utility import run_alert

logging.warning("alert system started")
configs = Config(True)

alert_type_to_alert_class = {
    "market_cap": CoingeckoMarketCapAlert,
    "price_volume": BinancePriceVolumeAlert,
    "alts_alert": CGAltsAlert,
    "alert_100": SpotOverMAAlert,
    "alert_300": SpotOverMAAlert,
    "alert_500": SpotOverMAAlert,
    "meme_alert": SpotOverMAAlert,
    "sequential": SpotOverMAAlert,
    "funding_rate": FutureFundingRate,
    "stock_price_outperformer": StockPriceTopPerformerAlert,
    "price_increase_alert": CoingeckoPriceIncreaseAlert,
    "macd_alert": MACDAlert,
    "floating_shares": FloatingSharesAlert
}


def main():
    if len(sys.argv) == 1:
        raise ValueError("Please specify the alert name; Alert names are defined in configs.json")
    alert_name = sys.argv[1]
    if alert_name not in configs.SETTINGS:
        raise ValueError(f"Alert name {alert_name} is not defined in configs.json")

    alert_type = configs.SETTINGS[alert_name]["alert_type"]
    alert_class = alert_type_to_alert_class[alert_type]
    if alert_type == "price_volume":
        alert = alert_class(**configs.SETTINGS[alert_name]["alert_input_args"])
        alert.run()
    else:
        run_alert(alert_name, alert_class)


if __name__ == "__main__":
    main()
