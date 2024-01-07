import os
import peewee
from peewee import DatabaseProxy, SqliteDatabase

from smrti_quant_alerts.settings import Config

# in support of multi threading
database_runtime = DatabaseProxy()


def init_database(db_name: str) -> SqliteDatabase:
    database_dir = os.path.join(Config.PROJECT_DIR, "runtime_database")
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)
    db_name = os.path.join(database_dir, db_name)
    return peewee.SqliteDatabase(db_name, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 64000,  # 64MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 2})
