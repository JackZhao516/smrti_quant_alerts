import os
import playhouse.pool
from peewee import DatabaseProxy, SqliteDatabase

from smrti_quant_alerts.settings import Config

database_runtime = DatabaseProxy()


def init_database(db_name: str) -> SqliteDatabase:
    database_dir = os.path.join(Config.PROJECT_DIR, "runtime_database")
    if not os.path.exists(database_dir):
        os.mkdir(database_dir)
    db_name = os.path.join(database_dir, db_name)
    # in support of multi threading
    return playhouse.pool.PooledSqliteDatabase(db_name, stale_timeout=500, max_connections=20, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 64000,  # 64MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 2})
