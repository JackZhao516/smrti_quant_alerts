import sys
import logging
from decimal import Decimal

from smrti_quant_alerts.alerts.coingecko_market_cap_alert import CoingeckoMarketCapAlert
from smrti_quant_alerts.alerts.binance_price_volume_alert import BinancePriceVolumeAlert
from smrti_quant_alerts.alerts.coingecko_alts_alert import CGAltsAlert
from smrti_quant_alerts.alerts.coingecko_binance_spot_over_ma_alert import SpotOverMAAlert
from smrti_quant_alerts.alerts.binance_bi_hourly_future_funding_rate_alert import FutureFundingRate
from smrti_quant_alerts.alerts.stock_alert import StockAlert
from smrti_quant_alerts.alerts.coingecko_price_increase_alert import CoingeckoPriceIncreaseAlert

from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.utility import run_task_at_daily_time

logging.disable(logging.DEBUG)
configs = Config()

def report_market_cap():
    """
    market cap alerts
    """
    logging.info("report_market_cap start")

    daily_time = "00:00"
    nums = [100, 200, 300, 400, 500]
    cmc_alert = CoingeckoMarketCapAlert(top_n=nums, tg_type="CG_MAR_CAP")
    run_task_at_daily_time(cmc_alert.run, daily_time)

    logging.info("report_market_cap finished")


def price_volume():
    """
    price/volume alerts
    """
    BinancePriceVolumeAlert().klines_alert()


def alert_spot_over_ma(alert_type):
    """
    alert spot over ma, for alert_100, alert_300, alert_500, meme_alert, sequential

    :param alert_type: alert type
    """
    logging.info(f"alert_spot_over_ma {alert_type} start")

    daily_time = "08:50" if alert_type == "meme_alert" else "09:00"
    tg_mode = "MEME" if alert_type == "meme_alert" else "CG_SUM"
    excluded_week_day = ["Mon", "Wed", "Fri", "Sat"]
    time_frame = 1 if alert_type == "meme_alert" else 4

    spot_over_ma_alert = SpotOverMAAlert(time_frame=time_frame, window=200, tg_mode=tg_mode)
    kwargs = {"alert_type": alert_type, "alert_coins_info": True}
    run_task_at_daily_time(spot_over_ma_alert.run, daily_time, kwargs=kwargs,
                           excluded_week_days=excluded_week_day)

    logging.info(f"alert_spot_over_ma {alert_type} finished")


def alts_alert():
    """
    alert alt coins
    """
    logging.info("alts_alert start")

    daily_time = {"00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
                  "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"}
    cg_alts_alert = CGAltsAlert(tg_type="ALTS")
    run_task_at_daily_time(cg_alts_alert.run, daily_time)

    logging.info("alts_alert finished")


def funding_rate():
    """
    alert funding rate
    """
    logging.info("funding_rate start")

    daily_time = {"00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
                  "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"}
    future_funding_rate = FutureFundingRate(rate_threshold=Decimal(0.002),
                                            tg_type="FUNDING_RATE")
    run_task_at_daily_time(future_funding_rate.run, daily_time)

    logging.info("funding_rate finished")


def stock_alert(longer_timeframe=False):
    """
    alert top performing stocks daily
    """
    logging.info("stock_alert start")
    config_name = "stock_alert_1d" if not longer_timeframe else "stock_alert_longer_timeframe"
    settings = configs.SETTINGS[config_name]
    alert = StockAlert(**settings["alert_input_args"])
    run_task_at_daily_time(alert.run, **settings["run_time_input_args"])
    logging.info("stock_alert finished")


def price_increase_alert(timeframe_in_days=14):
    """
    alert price increase
    """
    logging.info("price_increase_alert start")
    settings = configs.SETTINGS[f"price_increase_alert_{timeframe_in_days}d"]
    alert = CoingeckoPriceIncreaseAlert(**settings["alert_input_args"])
    run_task_at_daily_time(alert.run, **settings["run_time_input_args"])

    logging.info("price_increase_alert finished")


if __name__ == "__main__":
    # sys.argv[1] is the mode
    if sys.argv[1] == "market_cap":
        report_market_cap()
    elif sys.argv[1] == "price_volume":
        price_volume()
    elif sys.argv[1] == "alts":
        alts_alert()
    elif sys.argv[1] in ("alert_100", "alert_300", "alert_500", "meme_alert", "sequential"):
        alert_spot_over_ma(sys.argv[1])
    elif sys.argv[1] == "funding_rate":
        funding_rate()
    elif sys.argv[1] == "stock_alert":
        if len(sys.argv) == 2:
            stock_alert()
        else:
            stock_alert(longer_timeframe=(sys.argv[2] != "1d"))
    elif sys.argv[1] == "price_increase_alert":
        if len(sys.argv) == 2:
            price_increase_alert()
        else:
            price_increase_alert(timeframe_in_days=int(sys.argv[2]))
