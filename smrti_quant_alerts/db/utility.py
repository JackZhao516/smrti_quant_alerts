import time
from typing import Union, Type, Dict, Optional, List, Tuple


from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, ExchangeCount
from smrti_quant_alerts.data_type import TradingSymbol, get_class, BinanceExchange

# ------------ general utilities -------------


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, ExchangeCount], safe=True)


def close_database() -> None:
    database_runtime.close()

# -------------- price_volume ----------------


class PriceVolumeDBUtils:
    @staticmethod
    def update_count(exchange: BinanceExchange, alert_type: str,
                     threshold_time: int, count_type: str = "daily") -> int:
        """
        update daily/monthly count only if new alert is larger than <threshold_time> seconds
        later than the previous count. If there is no previous count, create one. Return the current count.

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
                        (ExchangeCount.count_type == count_type) &
                        (ExchangeCount.date < time.time() - threshold_time))
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
        with database_runtime.atomic("EXCLUSIVE"):
            ExchangeCount.delete().where((ExchangeCount.alert_type == alert_type) &
                                         (ExchangeCount.count_type == count_type)).execute()

# -------------- spot_over_ma ----------------


class SpotOverMaDBUtils:
    @staticmethod
    def remove_older_count(start_timestamp: Union[int, float]) -> None:
        """
        remove older count
        :param start_timestamp: start timestamp
        """
        with database_runtime.atomic():
            LastCount.delete().where(LastCount.date < start_timestamp).execute()

    @staticmethod
    def get_last_count(symbol_type: Optional[Type[TradingSymbol]] = None,
                       alert_type: Optional[str] = None) -> Dict[TradingSymbol, int]:
        """
        get all last count or by symbol type
        :param symbol_type: symbol type
        :param alert_type: alert type

        :return: {TradingSymbol: <count>}
        """
        with database_runtime.atomic():
            if symbol_type and alert_type:
                last_counts = LastCount.select().where(
                    (LastCount.symbol_type == symbol_type.type()) & (LastCount.alert_type == alert_type)).dicts()
            elif symbol_type:
                last_counts = LastCount.select().where(LastCount.symbol_type == symbol_type.type()).dicts()
            elif alert_type:
                last_counts = LastCount.select().where(LastCount.alert_type == alert_type).dicts()
            else:
                last_counts = LastCount.select().dicts()

            res = {}
            for i in last_counts:
                symbol_class = get_class(i["symbol_type"])

                if symbol_class:
                    trading_symbol = symbol_class.get_symbol_object(i["trading_symbol"])
                    res[trading_symbol] = i["count"]

            return res

    @staticmethod
    def update_last_count(last_counts: List[TradingSymbol], alert_type: str) -> None:
        """
        write/update last count for exchanges, only for the first time

        :param last_counts: last counts dict {TradingSymbol: count}
        :param alert_type: alert type
        """
        last_counts_list = [i.str() for i in last_counts]
        with database_runtime.atomic("EXCLUSIVE"):
            LastCount.update(count=LastCount.count + 1, alert_type=alert_type, date=time.time()).where(
                LastCount.trading_symbol.in_(last_counts_list)).execute()
            last_counts_existed = SpotOverMaDBUtils.get_last_count()
            last_counts = [e for e in last_counts if e not in last_counts_existed]
            last_counts = [{"trading_symbol": e.str(), "symbol_type": e.type(), "alert_type": alert_type}
                           for e in last_counts]
            LastCount.insert_many(last_counts).execute()
