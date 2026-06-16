"""SQLite connection helper — WAL-safe, foreign keys enforced.

All callers must use `connect()` so PRAGMAs are applied consistently. We never raw-copy
WAL files; backups use the online backup API (see scripts/, future BACKUPS work).
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator


def connect(db_path: str) -> sqlite3.Connection:
    """Open a connection with foreign keys ON and WAL journaling.

    `db_path` may be a file path or ":memory:" (tests). Row access is by name.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    # WAL is a no-op for :memory:; harmless. Improves concurrent read/write on disk.
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Commit on success, rollback on error."""
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def integrity_ok(conn: sqlite3.Connection) -> bool:
    return conn.execute("PRAGMA integrity_check;").fetchone()[0] == "ok"


def foreign_key_violations(conn: sqlite3.Connection) -> list:
    return conn.execute("PRAGMA foreign_key_check;").fetchall()
