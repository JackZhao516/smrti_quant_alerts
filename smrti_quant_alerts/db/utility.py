import time
from typing import Union, Type
from threading import RLock


from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, DailyCount
from smrti_quant_alerts.data_type import TradingSymbol, get_class


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, DailyCount])


def close_database() -> None:
    database_runtime.close()


# -------------- spot_over_ma ----------------
spot_over_ma_lock = RLock()


def remove_older_count(start_timestamp: Union[int, float]) -> None:
    """
    remove older count
    :param start_timestamp: start timestamp
    """
    spot_over_ma_lock.acquire()
    with database_runtime.atomic():
        LastCount.delete().where(LastCount.date < start_timestamp).execute()
    spot_over_ma_lock.release()


def get_last_count(symbol_type: Type[TradingSymbol] = None, alert_type: str = None) -> dict:
    """
    get all last count
    :param symbol_type: symbol type
    :param alert_type: alert type
    """
    with database_runtime.atomic():
        spot_over_ma_lock.acquire()
        if symbol_type and alert_type:
            last_counts = LastCount.select().where(
                (LastCount.symbol_type == symbol_type.type()) & (LastCount.alert_type == alert_type)).dicts()
        elif symbol_type:
            last_counts = LastCount.select().where(LastCount.symbol_type == symbol_type.type()).dicts()
        elif alert_type:
            last_counts = LastCount.select().where(LastCount.alert_type == alert_type).dicts()
        else:
            last_counts = LastCount.select().dicts()

        spot_over_ma_lock.release()

        res = {}
        for i in last_counts:
            cls = get_class(i["symbol_type"])

            if cls:
                trading_symbol = cls.get_symbol_object(i["trading_symbol"])
                res[trading_symbol] = i["count"]

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
    spot_over_ma_lock.acquire()
    query = LastCount.update(count=LastCount.count + 1, date=time.time()).where(
        LastCount.trading_symbol.in_(last_counts_list))
    query.execute()
    spot_over_ma_lock.release()


def write_last_counts(last_counts: dict, alert_type: str) -> None:
    """
    write last count, only for the first time
    :param last_counts: last counts dict {TradingSymbol: count}
    :param alert_type: alert type
    """
    spot_over_ma_lock.acquire()
    last_counts_existed = get_last_count()
    last_counts = {k: v for k, v in last_counts.items() if k not in last_counts_existed}
    last_counts = [{"trading_symbol": k.str(), "count": v,
                    "alert_type": alert_type, "symbol_type": k.type()}
                   for k, v in last_counts.items()]
    LastCount.insert_many(last_counts).execute()
    spot_over_ma_lock.release()
