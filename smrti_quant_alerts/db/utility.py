import time
from typing import Union, Type

from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, DailyCount
from smrti_quant_alerts.data_type import TradingSymbol, BinanceExchange, CoingeckoCoin


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, DailyCount])


def close_database() -> None:
    database_runtime.close()


# -------------- spot_over_ma ----------------
def remove_older_count(start_timestamp: Union[int, float]) -> None:
    """
    remove older count
    :param start_timestamp: start timestamp
    """
    with database_runtime.atomic():
        LastCount.delete().where(LastCount.date < start_timestamp).execute()


def get_last_count(symbol_type: Type[TradingSymbol] = None, alert_type: str = None) -> dict:
    """
    get all last count
    :param symbol_type: symbol type
    :param alert_type: alert type
    """
    with database_runtime.atomic():
        if symbol_type and alert_type:
            last_counts = LastCount.select().where(
                (LastCount.symbol_type == symbol_type) & (LastCount.alert_type == alert_type)).dicts()
        elif symbol_type:
            last_counts = LastCount.select().where(LastCount.symbol_type == symbol_type).dicts()
        elif alert_type:
            last_counts = LastCount.select().where(LastCount.alert_type == alert_type).dicts()
        else:
            last_counts = LastCount.select().dicts()

        res = {}
        for i in last_counts:
            cls = TradingSymbol

            if i["symbol_type"] == str(type(BinanceExchange("", ""))):
                cls = BinanceExchange
            elif i["symbol_type"] == str(type(CoingeckoCoin("", ""))):
                cls = CoingeckoCoin
            i["trading_symbol"] = cls.get_symbol_object(i["trading_symbol"])
            res[i["trading_symbol"]] = i["count"]

        return res


def update_last_counts(last_counts: Union[dict, set, list]) -> None:
    """
    update last count
    :param last_counts: last counts dict {TradingSymbol: count}
    """
    if isinstance(last_counts, dict):
        last_counts = last_counts.keys()
    last_counts_list = list(last_counts)
    last_counts_list = [i.str() for i in last_counts_list]
    query = LastCount.update(count=LastCount.count + 1, date=time.time()).where(
        LastCount.trading_symbol.in_(last_counts_list))
    query.execute()


def write_last_counts(last_counts: dict, alert_type: str) -> None:
    """
    write last count
    :param last_counts: last counts dict {TradingSymbol: count}
    :param alert_type: alert type
    """
    last_counts_existed = get_last_count()
    print(last_counts_existed)
    last_counts = {k: v for k, v in last_counts.items() if k not in last_counts_existed}
    print(last_counts)
    last_counts = [{"trading_symbol": k.str(), "count": v,
                    "alert_type": alert_type, "symbol_type": type(k)}
                   for k, v in last_counts.items()]
    LastCount.insert_many(last_counts).execute()


if __name__ == "__main__":
    from smrti_quant_alerts.get_exchange_list import GetExchangeList

    gel = GetExchangeList()
    gel.get_all_coingecko_coins()
    gel.get_all_binance_exchanges()
    init_database_runtime("test.db")
    # write_last_counts({BinanceExchange("BTC", "USDT"): 1}, "test")
    l = get_last_count(symbol_type=BinanceExchange, alert_type="test")
    print(l)
    l = get_last_count()
    print(l)
