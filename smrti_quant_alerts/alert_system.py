import sys
import logging
from decimal import Decimal

from smrti_quant_alerts.alerts.coingecko_market_cap_alert import CoingeckoMarketCapAlert
from smrti_quant_alerts.alerts.binance_price_volume_alert import BinancePriceVolumeAlert
from smrti_quant_alerts.alerts.coingecko_alts_alert import CGAltsAlert
from smrti_quant_alerts.alerts.coingecko_binance_spot_over_ma_alert import SpotOverMAAlert
from smrti_quant_alerts.alerts.binance_bi_hourly_future_funding_rate_alert import FutureFundingRate
from smrti_quant_alerts.alerts.stock_alert import StockAlert
from smrti_quant_alerts.settings import Config
from smrti_quant_alerts.utility import run_task_at_daily_time

logging.disable(logging.DEBUG)


def report_market_cap():
    """
    market cap alerts
    """
    logging.info("report_market_cap start")

    daily_time = "00:00"
    nums = [100, 200, 300, 400, 500]
    cmc_alert = CoingeckoMarketCapAlert(top_n=nums, tg_type="CG_MAR_CAP")
    run_task_at_daily_time(cmc_alert.run, daily_time, duration=60 * 60 * 24)

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
    exclude_week_day = ["Mon", "Wed", "Fri", "Sat"]
    time_frame = 1 if alert_type == "meme_alert" else 4

    spot_over_ma_alert = SpotOverMAAlert(time_frame=time_frame, window=200, tg_mode=tg_mode)
    kwargs = {"alert_type": alert_type, "alert_coins_info": True}
    run_task_at_daily_time(spot_over_ma_alert.run, daily_time, kwargs=kwargs,
                           exclude_week_day=exclude_week_day, duration=60 * 60 * 24)

    logging.info(f"alert_spot_over_ma {alert_type} finished")


def alts_alert():
    """
    alert alt coins
    """
    logging.info("alts_alert start")

    daily_time = {"00:00", "02:00", "04:00", "06:00", "08:00", "10:00",
                  "12:00", "14:00", "16:00", "18:00", "20:00", "22:00"}
    cg_alts_alert = CGAltsAlert(tg_type="ALTS")
    run_task_at_daily_time(cg_alts_alert.run, daily_time, duration=60 * 60 * 2)

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
    run_task_at_daily_time(future_funding_rate.run, daily_time, duration=60 * 60 * 2)

    logging.info("funding_rate finished")


def stock_alert():
    """
    alert top performing stocks daily
    """
    logging.info("stock_alert start")

    daily_time = "08:55"
    alert = StockAlert(tg_type="STOCK")
    run_task_at_daily_time(alert.run, daily_time, duration=60 * 60 * 24, exclude_week_day=["Mon", "Sun"])

    logging.info("stock_alert finished")


if __name__ == "__main__":
    Config()
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
        stock_alert()
