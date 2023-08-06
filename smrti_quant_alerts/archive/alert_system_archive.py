# def alert_indicator(alert_type="alert_100"):
#     logging.info(f"{alert_type} start")
#     if alert_type == "alert_100":
#         exchanges, coin_ids, coin_symbols = cg.get_exchanges(num=100)
#     else:
#         exchanges, coin_ids, coin_symbols = cg.get_coins_with_weekly_volume_increase()
#     logging.warning("start coingecko alert")
#     tg_type = "CG_ALERT"
#     coins_thread = alert_coins(coin_ids, coin_symbols, alert_type=alert_type, tg_type=tg_type)
#     execution_time = 60 * 60 * 24 * 3 + 60 * 35
#     logging.warning(f"start binance indicator alert")
#     logging.warning(f"exchanges: {len(exchanges)}, coins: {len(coin_ids)}")
#     binance_alert = BinanceIndicatorAlert(exchanges, alert_type=alert_type, execution_time=execution_time, tg_type=tg_type)
#     binance_alert.run()
#
#     close_all_threads(coins_thread)
#     logging.warning(f"{alert_type} finished")
