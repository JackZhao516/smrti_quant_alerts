"""Persist dated Stable shares-float snapshots; never invent missing history."""

import datetime
import sqlite3
from pathlib import Path


class ShareHistory:
    def __init__(self, project_dir):
        self.path = Path(project_dir) / "runtime_database" / "shares_history.sqlite3"

    def update(self, symbol, rows):
        valid = []
        for row in rows:
            try:
                date = datetime.date.fromisoformat(str(row["date"])[:10]).isoformat()
                shares = int(row["floatShares"])
                if shares > 0:
                    valid.append((symbol, date, shares))
            except (KeyError, TypeError, ValueError):
                continue
        if not valid:
            return []
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path, timeout=30) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS shares(symbol TEXT,date TEXT,shares INTEGER,PRIMARY KEY(symbol,date))"
            )
            db.executemany("INSERT OR REPLACE INTO shares VALUES(?,?,?)", valid)
            return [
                {"date": date, "floatShares": shares}
                for date, shares in db.execute(
                    "SELECT date,shares FROM shares WHERE symbol=? ORDER BY date DESC", (symbol,)
                )
            ]
