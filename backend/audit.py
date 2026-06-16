"""Sanitized audit-log helper (§31 rule 1).

Writes `audit_logs` rows with a non-secret actor/action/target and a **sanitized** detail.
Callers must pass only non-secret text — never tokens, UUIDs, links, QR payloads, admin
paths, API keys, or private customer data. Customer/order/subscription **internal integer
ids** are not secrets and are fine to record.

`audit_row` only executes the INSERT (use inside an existing transaction). `write_audit`
wraps it in its own transaction for standalone callers.
"""
from __future__ import annotations

import sqlite3

from . import db as _db, timezone as _tz

DEFAULT_ACTOR = "system:phase4c"


def audit_row(conn: sqlite3.Connection, action: str, target: str,
              detail: str = "", actor: str = DEFAULT_ACTOR) -> int:
    """INSERT one sanitized audit row WITHOUT committing (caller's transaction owns the commit)."""
    cur = conn.execute(
        "INSERT INTO audit_logs(actor, action, target, detail, created_at) VALUES (?,?,?,?,?)",
        (actor, action, target, detail, _tz.storage_mmt(_tz.now_mmt())),
    )
    return int(cur.lastrowid)


def write_audit(conn: sqlite3.Connection, action: str, target: str,
                detail: str = "", actor: str = DEFAULT_ACTOR) -> int:
    """Append one sanitized audit row in its own transaction. Returns its id."""
    with _db.transaction(conn):
        return audit_row(conn, action, target, detail, actor)
