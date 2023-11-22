import os
from peewee import DatabaseProxy, SqliteDatabase
from playhouse.sqliteq import SqliteQueueDatabase

# in support of multi threading
database_runtime = DatabaseProxy()
if not os.path.exists("runtime_database"):
    os.mkdir("runtime_database")


def init_database(db_name: str) -> SqliteQueueDatabase:
    db_name = os.path.join("runtime_database", db_name)
    return SqliteDatabase(db_name, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 128000,  # 128MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 0})
                          # , autostart=True, queue_max_size=128, results_timeout=5.0)
    # database_runtime.init(db_name, pragmas={
    #         'journal_mode': 'wal',
    #         'cache_size': -1 * 128000,  # 128MB
    #         'foreign_keys': 1,
    #         'ignore_check_constraints': 0,
    #         'synchronous': 0}, autostart=True, queue_max_size=128, results_timeout=5.0)
