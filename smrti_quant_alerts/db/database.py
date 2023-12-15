import os
from peewee import DatabaseProxy, SqliteDatabase

# in support of multi threading
database_runtime = DatabaseProxy()
if not os.path.exists("runtime_database"):
    os.mkdir("runtime_database")


def init_database(db_name: str) -> SqliteDatabase:
    db_name = os.path.join("runtime_database", db_name)
    return SqliteDatabase(db_name, pragmas={
            'journal_mode': 'wal',
            'cache_size': -1 * 256000,  # 256MB
            'foreign_keys': 1,
            'ignore_check_constraints': 0,
            'synchronous': 1})
