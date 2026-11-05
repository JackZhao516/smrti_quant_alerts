import argparse
import logging

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.alerts import (
    CoingeckoMarketCapAlert,
    BinancePriceVolumeAlert,
    CGAltsAlert,
    SpotOverMAAlert,
    FutureFundingRate,
    StockPriceTopPerformerAlert,
    CoingeckoPriceIncreaseAlert,
    MACDAlert,
    FloatingSharesAlert,
    StockScreenerAlert,
)
from smrti_quant_alerts.utility import run_alert


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
    "floating_shares": FloatingSharesAlert,
    "stock_screener": StockScreenerAlert,
}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run a configured crypto or stock alert")
    parser.add_argument("alert_name", help="Entry name in configs.json")
    args = parser.parse_args(argv)
    configs = Config(True)
    logging.warning("alert system started")
    alert_name = args.alert_name
    if alert_name not in configs.SETTINGS:
        parser.error("Alert name is not defined in configs.json")

    alert_type = configs.SETTINGS[alert_name]["alert_type"]
    alert_class = alert_type_to_alert_class[alert_type]
    configs.SETTINGS[alert_name]["alert_input_args"]["alert_name"] = alert_name
    if alert_type == "price_volume":
        alert = alert_class(**configs.SETTINGS[alert_name]["alert_input_args"])
        alert.run()
    else:
        run_alert(alert_name, alert_class)


if __name__ == "__main__":
    main()
