"""node_metrics writer — append-only sanitized samples (§30A).

Writes one `node_metrics` row from a sanitized `ProbeResult`. Only the safe numeric fields are
stored (cpu/ram/disk/bandwidth/users) — never a raw error, URL, or secret. Append-only: each call
is a new sample; nothing is updated or deleted.
"""
from __future__ import annotations

import sqlite3

from . import db as _db
from .node_probe import ProbeResult


def write_metric(conn: sqlite3.Connection, pr: ProbeResult) -> int:
    """Append one node_metrics sample. Returns the row id."""
    with _db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO node_metrics(node_code, cpu_pct, ram_pct, disk_pct, bandwidth_gb, users_count) "
            "VALUES (?,?,?,?,?,?)",
            (pr.node_code, pr.cpu_pct, pr.ram_pct, pr.disk_pct, pr.bandwidth_gb, pr.users_count))
        return int(cur.lastrowid)
