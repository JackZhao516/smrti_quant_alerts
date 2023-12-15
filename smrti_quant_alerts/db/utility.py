from typing import Union, Type

from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, DailyCount
from smrti_quant_alerts.data_type import TradingSymbol


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, DailyCount])


# -------------- spot_over_ma ----------------
def remove_older_count(start_timestamp: Union[int, float]) -> None:
    """
    remove older count
    :param start_timestamp: start timestamp
    """
    with database_runtime.atomic():
        LastCount.delete().where(LastCount.date < start_timestamp).execute()


def get_last_count(alert_type: str,
                   symbol_type: Type[TradingSymbol] = None) -> dict:
    """
    get all last count
    :param alert_type: alert type
    :param symbol_type: symbol type
    """
    with database_runtime.atomic():
        if symbol_type:
            last_counts = LastCount.select().where(LastCount.alert_type == alert_type,
                                                   LastCount.symbol_type == symbol_type).dicts()
        else:
            last_counts = LastCount.select().where(LastCount.alert_type == alert_type).dicts()
        return {i["trading_symbol"]: i["count"] for i in last_counts}


def write_last_counts(last_counts: dict, alert_type: str) -> None:
    """
    write last count
    :param last_counts: last counts dict {TradingSymbol: count}
    :param alert_type: alert type
    """
    last_counts = [{"trading_symbol": k.str(), "count": v,
                    "alert_type": alert_type, "symbol_type": type(k)}
                   for k, v in last_counts.items()]
    LastCount.insert_many(last_counts).execute()
