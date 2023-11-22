import datetime

from peewee import Model, PrimaryKeyField, CharField, IntegerField, DateTimeField
from playhouse.shortcuts import ThreadSafeDatabaseMetadata


from smrti_quant_alerts.db.database import database_runtime, init_database


class BaseModel(Model):
    class Meta:
        database = database_runtime
        print(database_runtime)
        model_metadata_class = ThreadSafeDatabaseMetadata
    id = PrimaryKeyField()


# -------------- price_volume ----------------
class DailyCount(BaseModel):
    exchange = CharField()
    # timeframe = CharField()
    # alert_type = CharField()
    # count = IntegerField()
    # date = DateTimeField(default=datetime.datetime.now)


# class MonthlyCount(BaseModel):



if __name__ == "__main__":
    database_runtime.initialize(init_database("test.db"))
    print(database_runtime.connect())
    database_runtime.create_tables([DailyCount])
    # with database_runtime.atomic():
    #     # Attempt to create the user. If the username is taken, due to the
    #     # unique constraint, the database will raise an IntegrityError.
    #     user = DailyCount.create(
    #         exchange="binance")

    print(database_runtime.get_tables())


