import time

from peewee import Model, CharField, IntegerField, DateTimeField, CompositeKey
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
