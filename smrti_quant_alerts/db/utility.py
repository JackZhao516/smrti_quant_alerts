import time
from typing import Union, Type, Dict, Optional, Set, List, Tuple
from threading import RLock


from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, ExchangeCount
from smrti_quant_alerts.data_type import TradingSymbol, get_class, BinanceExchange

# ------------ general utilities -------------


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, ExchangeCount])


def close_database() -> None:
    database_runtime.close()

# -------------- price_volume ----------------


class PriceVolumeDBUtils:
    @staticmethod
    def update_count(exchange: BinanceExchange, alert_type: str,
                     threshold_time: int, count_type: str = "daily") -> int:
        """
        update daily/monthly count only if new alert is larger than <threshold_time> seconds
        later than the previous count

        :param exchange: BinanceExchange
        :param alert_type: alert type
        :param threshold_time: threshold time
        :param count_type: "daily" or "monthly"

        :return: current count
        """
        with database_runtime.atomic("EXCLUSIVE"):
            count = PriceVolumeDBUtils.get_count(alert_type, exchange, count_type)
            if count:
                count, date = count[exchange]
                if date < time.time() - threshold_time:
                    # update count
                    query = ExchangeCount.update(count=count + 1, date=time.time()).where(
                        (ExchangeCount.exchange == exchange.exchange) &
                        (ExchangeCount.alert_type == alert_type) &
                        (ExchangeCount.count_type == count_type))
                    query.execute()
                    count += 1
                return count

            else:
                # insert exchange
                ExchangeCount.insert(exchange=exchange.exchange, alert_type=alert_type,
                                     count=1, count_type=count_type).execute()
                return 1

    @staticmethod
    def get_count(alert_type: str, exchange: Optional[BinanceExchange] = None,
                  count_type: str = "daily") -> Dict[BinanceExchange, Tuple[int, float]]:
        """
        get daily/monthly count for a certian exchange or all exchanges

        :param exchange: BinanceExchange
        :param alert_type: alert type
        :param count_type: "daily" or "monthly"

        :return: {BinanceExchange: (<count>, <timestamp>)}
        """
        if exchange:
            with database_runtime.atomic():
                res = ExchangeCount.select().where((ExchangeCount.exchange == exchange.exchange) &
                                                   (ExchangeCount.alert_type == alert_type) &
                                                   (ExchangeCount.count_type == count_type)).dicts()
                if res:
                    return {exchange: (res[0]["count"], res[0]["date"])}
                else:
                    return {}
        else:
            with database_runtime.atomic():
                counts = ExchangeCount.select().where((ExchangeCount.alert_type == alert_type) &
                                                      (ExchangeCount.count_type == count_type)).dicts()

            return {BinanceExchange.get_symbol_object(i["exchange"]): (i["count"],  i["date"]) for i in counts}

    @staticmethod
    def reset_count(alert_type: str, count_type: str = "daily") -> None:
        """
        delete all counts for <alert_type>

        :param alert_type: alert_type
        :param count_type: "daily" or "monthly"
        """
        with database_runtime.atomic():
            ExchangeCount.delete().where((ExchangeCount.alert_type == alert_type) &
                                         (ExchangeCount.count_type == count_type)).execute()


# -------------- spot_over_ma ----------------

class SpotOverMaDBUtils:
    spot_over_ma_lock = RLock()

    @classmethod
    def remove_older_count(cls, start_timestamp: Union[int, float]) -> None:
        """
        remove older count
        :param start_timestamp: start timestamp
        """
        cls.spot_over_ma_lock.acquire()
        with database_runtime.atomic():
            LastCount.delete().where(LastCount.date < start_timestamp).execute()
        cls.spot_over_ma_lock.release()

    @classmethod
    def get_last_count(cls, symbol_type: Optional[Type[TradingSymbol]] = None,
                       alert_type: Optional[str] = None) -> Dict[TradingSymbol, int]:
        """
        get all last count
        :param symbol_type: symbol type
        :param alert_type: alert type

        :return: {TradingSymbol: <count>}
        """
        with database_runtime.atomic():
            cls.spot_over_ma_lock.acquire()
            if symbol_type and alert_type:
                last_counts = LastCount.select().where(
                    (LastCount.symbol_type == symbol_type.type()) & (LastCount.alert_type == alert_type)).dicts()
            elif symbol_type:
                last_counts = LastCount.select().where(LastCount.symbol_type == symbol_type.type()).dicts()
            elif alert_type:
                last_counts = LastCount.select().where(LastCount.alert_type == alert_type).dicts()
            else:
                last_counts = LastCount.select().dicts()

            cls.spot_over_ma_lock.release()

            res = {}
            for i in last_counts:
                symbol_class = get_class(i["symbol_type"])

                if symbol_class:
                    trading_symbol = symbol_class.get_symbol_object(i["trading_symbol"])
                    res[trading_symbol] = i["count"]

            return res

    @classmethod
    def update_last_counts(
            cls, last_counts: Union[Dict[TradingSymbol, int], Set[TradingSymbol], List[TradingSymbol]]) -> None:
        """
        update last count
        :param last_counts: last counts dict {TradingSymbol: count}
        """
        if isinstance(last_counts, dict):
            last_counts = last_counts.keys()
        last_counts_list = list(last_counts)
        last_counts_list = [i.str() for i in last_counts_list]
        cls.spot_over_ma_lock.acquire()
        query = LastCount.update(count=LastCount.count + 1, date=time.time()).where(
            LastCount.trading_symbol.in_(last_counts_list))
        query.execute()
        cls.spot_over_ma_lock.release()

    @classmethod
    def write_last_counts(cls, last_counts: Dict[TradingSymbol, int], alert_type: str) -> None:
        """
        write last count, only for the first time
        :param last_counts: last counts dict {TradingSymbol: count}
        :param alert_type: alert type
        """
        cls.spot_over_ma_lock.acquire()
        last_counts_existed = cls.get_last_count()
        last_counts = {k: v for k, v in last_counts.items() if k not in last_counts_existed}
        last_counts = [{"trading_symbol": k.str(), "count": v,
                        "alert_type": alert_type, "symbol_type": k.type()}
                       for k, v in last_counts.items()]
        LastCount.insert_many(last_counts).execute()
        cls.spot_over_ma_lock.release()
