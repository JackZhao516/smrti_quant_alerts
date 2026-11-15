from pathlib import Path
import playhouse.pool
from peewee import DatabaseProxy, SqliteDatabase

from smrti_quant_alerts.settings import Config

database_runtime = DatabaseProxy()


def runtime_database_path(db_name: str, project_dir: str | Path | None = None) -> Path:
    root = Path(Config.PROJECT_DIR if project_dir is None else project_dir)
    return root / "runtime_database" / db_name


def init_database(db_name: str) -> SqliteDatabase:
    path = runtime_database_path(db_name)
    path.parent.mkdir(exist_ok=True)
    # in support of multi threading
    return playhouse.pool.PooledSqliteDatabase(
        str(path),
        stale_timeout=500,
        max_connections=20,
        pragmas={
            "journal_mode": "wal",
            "cache_size": -1 * 64000,  # 64MB
            "foreign_keys": 1,
            "ignore_check_constraints": 0,
            "synchronous": 2,
        },
    )
