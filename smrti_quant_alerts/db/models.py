import time

from peewee import Model, CharField, IntegerField, DateTimeField, CompositeKey, DecimalField, BooleanField
from playhouse.shortcuts import ThreadSafeDatabaseMetadata


from smrti_quant_alerts.db.database import database_runtime


class BaseModel(Model):
    class Meta:
        database = database_runtime
        model_metadata_class = ThreadSafeDatabaseMetadata


# -------------- price_volume ----------------
class ExchangeCount(BaseModel):
    exchange = CharField()
    alert_type = CharField()
    count = IntegerField()
    count_type = CharField()
    date = DateTimeField(default=time.time)

    class Meta:
        primary_key = CompositeKey('exchange', 'alert_type', 'count_type')


# -------------- spot_over_ma ----------------
class LastCount(BaseModel):
    trading_symbol = CharField(unique=True)
    symbol_type = CharField()
    alert_type = CharField()
    count = IntegerField(default=1)
    date = DateTimeField(default=time.time)


# -------------- stock_alert ----------------
class StockAlertCount(BaseModel):
    stock_symbol = CharField()


# -------------- macd_alert ----------------
class MACDAlertValue(BaseModel):
    symbol_left = CharField()
    symbol_right = CharField()
    last_week_value = DecimalField()

    class Meta:
        primary_key = CompositeKey('symbol_left', 'symbol_right')


# -------------- stock_alert ----------------
class StockInfo(BaseModel):
    symbol = CharField(unique=True, primary_key=True)
    security_name = CharField()
    gics_sector = CharField()
    gics_sub_industry = CharField()
    location = CharField()
    cik = CharField()
    founded_time = CharField()
