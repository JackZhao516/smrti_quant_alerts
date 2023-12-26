import os
from peewee import DatabaseProxy, SqliteDatabase

from smrti_quant_alerts.settings import Config

# in support of multi threading
database_runtime = DatabaseProxy()
database_dir = os.path.join(Config.PROJECT_DIR, "runtime_database")
if not os.path.exists(database_dir):
    os.mkdir(database_dir)


def init_database(db_name: str) -> SqliteDatabase:
    db_name = os.path.join(database_dir, db_name)
    return SqliteDatabase(db_name, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 64000,  # 64MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 1})
