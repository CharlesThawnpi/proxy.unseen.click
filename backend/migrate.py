"""Ordered, idempotent schema-migration runner ("the logbook", §30A.1).

Applies `backend/migrations/NNNN_*.sql` in filename order, recording each in
`schema_migrations`. Re-running is a safe no-op (already-applied migrations are skipped,
and the SQL itself uses CREATE TABLE IF NOT EXISTS). Same registry guarantees test and
live DBs evolve identically.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

try:  # works as a package module (tests, imports)
    from . import db as _db
except ImportError:  # also runnable directly: `python3 backend/migrate.py`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from backend import db as _db

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"

_REGISTRY = """
CREATE TABLE IF NOT EXISTS schema_migrations (
  version     TEXT PRIMARY KEY,
  applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _applied(conn: sqlite3.Connection) -> set[str]:
    conn.executescript(_REGISTRY)
    return {r[0] for r in conn.execute("SELECT version FROM schema_migrations").fetchall()}


def discover() -> list[Path]:
    return sorted(p for p in MIGRATIONS_DIR.glob("*.sql"))


def migrate(conn: sqlite3.Connection) -> list[str]:
    """Apply all pending migrations. Returns the list of versions newly applied."""
    done = _applied(conn)
    newly: list[str] = []
    for path in discover():
        version = path.stem  # e.g. "0001_initial"
        if version in done:
            continue
        sql = path.read_text(encoding="utf-8")
        with _db.transaction(conn):
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
        newly.append(version)
    return newly


def migrate_path(db_path: str) -> list[str]:
    conn = _db.connect(db_path)
    try:
        return migrate(conn)
    finally:
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser(description="Apply UNSEEN PROXY schema migrations (idempotent).")
    ap.add_argument("--db", default=os.environ.get("DB_PATH", "/opt/unseen-proxy/data/unseenproxy.sqlite3"))
    args = ap.parse_args()
    applied = migrate_path(args.db)
    print(f"applied: {applied or '(none — up to date)'}")
