import time

from peewee import Model, PrimaryKeyField, CharField, IntegerField, DateTimeField
from playhouse.shortcuts import ThreadSafeDatabaseMetadata


from smrti_quant_alerts.db.database import database_runtime


class BaseModel(Model):
    class Meta:
        database = database_runtime
        model_metadata_class = ThreadSafeDatabaseMetadata
    id = PrimaryKeyField()


# -------------- price_volume ----------------
class DailyCount(BaseModel):
    exchange = CharField()
    timeframe = CharField()
    alert_type = CharField()
    count = IntegerField()
    date = DateTimeField(default=time.time)


# class MonthlyCount(BaseModel):

# -------------- spot_over_ma ----------------
class LastCount(BaseModel):
    trading_symbol = CharField(unique=True)
    symbol_type = CharField()
    alert_type = CharField()
    count = IntegerField()
    date = DateTimeField(default=time.time)
