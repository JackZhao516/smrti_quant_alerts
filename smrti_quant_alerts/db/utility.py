import time
from decimal import Decimal
from typing import Union, Type, Dict, Optional, List, Tuple, Iterable, Set
from threading import RLock


from smrti_quant_alerts.db.database import database_runtime, init_database
from smrti_quant_alerts.db.models import LastCount, ExchangeCount, StockAlertCount, MACDAlertValue, StockInfo
from smrti_quant_alerts.data_type import TradingSymbol, get_class, BinanceExchange, StockSymbol

# ------------ general utilities -------------


def init_database_runtime(db_name: str) -> None:
    database_runtime.initialize(init_database(db_name))
    database_runtime.create_tables([LastCount, ExchangeCount, StockAlertCount, MACDAlertValue, StockInfo], safe=True)


def is_database_runtime_initialized() -> bool:
    return database_runtime.obj is not None


def close_database() -> None:
    database_runtime.close()

# -------------- price_volume ----------------


class PriceVolumeDBUtils:
    db_lock = RLock()

    @classmethod
    def update_count(cls, exchange: BinanceExchange, alert_type: str,
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
            cls.db_lock.acquire()
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
                cls.db_lock.release()
                return count

            else:
                # insert exchange
                ExchangeCount.insert(exchange=exchange.exchange, alert_type=alert_type,
                                     count=1, count_type=count_type).execute()
                cls.db_lock.release()
                return 1

    @classmethod
    def get_count(cls, alert_type: str, exchange: Optional[BinanceExchange] = None,
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
                cls.db_lock.acquire()
                res = ExchangeCount.select().where((ExchangeCount.exchange == exchange.exchange) &
                                                   (ExchangeCount.alert_type == alert_type) &
                                                   (ExchangeCount.count_type == count_type)).dicts()
                cls.db_lock.release()
                if res:
                    return {exchange: (res[0]["count"], res[0]["date"])}
                else:

                    return {}
        else:
            with database_runtime.atomic():
                cls.db_lock.acquire()
                counts = ExchangeCount.select().where((ExchangeCount.alert_type == alert_type) &
                                                      (ExchangeCount.count_type == count_type)).dicts()
                cls.db_lock.release()

            return {BinanceExchange.get_symbol_object(i["exchange"]): (i["count"],  i["date"]) for i in counts}

    @classmethod
    def reset_count(cls, alert_type: str, count_type: str = "daily") -> None:
        """
        delete all counts for <alert_type>

        :param alert_type: alert_type
        :param count_type: "daily" or "monthly"
        """
        with database_runtime.atomic("EXCLUSIVE"):
            cls.db_lock.acquire()
            ExchangeCount.delete().where((ExchangeCount.alert_type == alert_type) &
                                         (ExchangeCount.count_type == count_type)).execute()
            cls.db_lock.release()
# -------------- spot_over_ma ----------------


class SpotOverMaDBUtils:
    db_lock = RLock()

    @classmethod
    def remove_older_count(cls, start_timestamp: Union[int, float]) -> None:
        """
        remove older count
        :param start_timestamp: start timestamp
        """
        with database_runtime.atomic():
            cls.db_lock.acquire()
            LastCount.delete().where(LastCount.date < start_timestamp).execute()
            cls.db_lock.release()

    @classmethod
    def get_last_count(cls, symbol_type: Optional[Type[TradingSymbol]] = None,
                       alert_type: Optional[str] = None) -> Dict[TradingSymbol, int]:
        """
        get all last count or by symbol type
        :param symbol_type: symbol type
        :param alert_type: alert type

        :return: {TradingSymbol: <count>}
        """
        with database_runtime.atomic():
            cls.db_lock.acquire()
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
            cls.db_lock.release()
            return res

    @classmethod
    def update_last_count(cls, last_counts: List[TradingSymbol], alert_type: str) -> None:
        """
        write/update last count for exchanges, only for the first time

        :param last_counts: last counts dict {TradingSymbol: count}
        :param alert_type: alert type
        """
        last_counts_list = [i.db_repr() for i in last_counts]
        with database_runtime.atomic("EXCLUSIVE"):
            cls.db_lock.acquire()
            LastCount.update(count=LastCount.count + 1, alert_type=alert_type, date=time.time()).where(
                LastCount.trading_symbol.in_(last_counts_list)).execute()
            last_counts_existed = SpotOverMaDBUtils.get_last_count()
            last_counts = [e for e in last_counts if e not in last_counts_existed]
            last_counts = [{"trading_symbol": e.db_repr(), "symbol_type": e.type(), "alert_type": alert_type}
                           for e in last_counts]
            LastCount.insert_many(last_counts).execute()
            cls.db_lock.release()


class StockAlertDBUtils:
    @staticmethod
    def get_stocks(alert_type: str = "") -> Set[StockSymbol]:
        """
        get all stocks
        :param alert_type: alert type
        """
        with database_runtime.atomic():
            return {StockSymbol.get_symbol_object(i.stock_symbol) for i in StockAlertCount.select().where(
                StockAlertCount.alert_type == alert_type)}

    @staticmethod
    def get_all_stocks() -> Set[StockSymbol]:
        """
        get all stocks
        """
        with database_runtime.atomic():
            return {StockSymbol.get_symbol_object(i.stock_symbol) for i in StockAlertCount.select()}

    @staticmethod
    def add_stocks(stock_symbols: Iterable[StockSymbol], alert_type: str = "") -> None:
        """
        add stock symbols to the database
        :param stock_symbols: list of stock symbols
        :param alert_type: alert type
        """
        with database_runtime.atomic():
            StockAlertCount.insert_many([{"stock_symbol": i.ticker, "alert_type": alert_type}
                                         for i in stock_symbols]).execute()

    @staticmethod
    def reset_stocks(alert_type: str = "") -> None:
        """
        reset all stocks
        :param alert_type: alert type
        """
        with database_runtime.atomic():
            StockAlertCount.delete().where(StockAlertCount.alert_type == alert_type).execute()

    @staticmethod
    def get_stocks_info(stocks: Union[Iterable[StockSymbol], Iterable[str]], full: bool = True) \
            -> Tuple[List[StockSymbol], List[StockSymbol]]:
        """
        get stock info
        :param stocks: list of stock symbols
        :param full: if True, stocks without full info will be counted as without info

        :return: list of stock symbols with info, list of stock symbols without info
        """
        if not stocks:
            return [], []

        if isinstance(stocks, set):
            stocks = list(stocks)
        if isinstance(stocks[0], str):
            stocks = [StockSymbol(i) for i in stocks]

        stocks_with_info, stocks_without_info = [], []
        with database_runtime.atomic():
            res = StockInfo.select().where(StockInfo.symbol.in_([i.ticker for i in stocks])).dicts()
            for i in res:
                stock = StockSymbol(
                    i["symbol"], i["security_name"], i["gics_sector"], i["gics_sub_industry"],
                    i["location"], i["cik"], i["founded_time"])
                if full:
                    if stock.has_stock_info:
                        stocks_with_info.append(stock)
                    else:
                        stocks_without_info.append(stock)
                stocks_with_info.append(stock)
        stocks_with_info_set = set(stocks_with_info)
        for stock in stocks:
            if stock not in stocks_with_info_set:
                stocks_without_info.append(stock)
        return stocks_with_info, stocks_without_info

    @staticmethod
    def add_stocks_info(stocks: Iterable[StockSymbol]) -> None:
        """
        add stock info
        :param stocks: list of stock symbols
        """
        with database_runtime.atomic():
            StockInfo.replace_many([{"symbol": i.ticker, "security_name": i.security_name,
                                    "gics_sector": i.gics_sector, "gics_sub_industry": i.gics_sub_industry,
                                     "location": i.location, "cik": i.cik, "founded_time": i.founded_time}
                                   for i in stocks]).execute()


class MACDAlertDBUtils(StockAlertDBUtils):
    @staticmethod
    def get_last_week_value(symbol_left: str, symbol_right: str) -> Optional[float]:
        """
        get last week value
        :param symbol_left: symbol left
        :param symbol_right: symbol right

        :return: last week value
        """
        with database_runtime.atomic():
            res = MACDAlertValue.select().where((MACDAlertValue.symbol_left == symbol_left) &
                                                (MACDAlertValue.symbol_right == symbol_right)).dicts()
            if res:
                return res[0]["last_week_value"]
            else:
                return None

    @staticmethod
    def update_last_week_value(symbol_left: str, symbol_right: str, last_week_value: Decimal) -> None:
        """
        update last week value
        :param symbol_left: symbol left
        :param symbol_right: symbol right
        :param last_week_value: last week value
        """
        with database_runtime.atomic("EXCLUSIVE"):
            # if update fails, insert
            MACDAlertValue.insert(symbol_left=symbol_left, symbol_right=symbol_right,
                                  last_week_value=last_week_value).on_conflict(
                conflict_target=[MACDAlertValue.symbol_left, MACDAlertValue.symbol_right],
                update={MACDAlertValue.last_week_value: last_week_value}).execute()
