"""Idempotency helpers — exactly-once for payment approval / provisioning (§30A.2).

Guards operations that must not double-execute on double-taps, webhook re-delivery, or retries.
Backed by `idempotency_keys (scope, key, status, result_ref, ...)` with UNIQUE(scope, key):

  begin_idempotent(scope, key):
    - first caller        → inserts status='in_progress' → state "started"
    - duplicate, completed → returns the prior result      → state "already_completed"
    - duplicate, running   → refuses                        → state "in_progress"
  complete_idempotent(scope, key, result_ref):
    - marks 'completed' and records result_ref; if already completed, the PRIOR result_ref
      is preserved and returned (never overwritten) so replays are stable.

All writes run in a transaction. The UNIQUE constraint is the actual concurrency guard.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from . import db as _db

# The operations that use idempotency keys.
SCOPES = ("payment_approval", "provision_subscription", "referral_grant", "account_link_merge")

STATE_STARTED = "started"                  # we are the first; proceed with the operation
STATE_IN_PROGRESS = "in_progress"          # someone else holds it; refuse / wait
STATE_ALREADY_COMPLETED = "already_completed"  # done before; replay prior result

STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"


class UnknownScopeError(ValueError):
    pass


@dataclass(frozen=True)
class BeginResult:
    state: str                       # STATE_STARTED | STATE_IN_PROGRESS | STATE_ALREADY_COMPLETED
    result_ref: Optional[str] = None  # populated only for STATE_ALREADY_COMPLETED

    @property
    def should_proceed(self) -> bool:
        return self.state == STATE_STARTED


def _validate_scope(scope: str) -> None:
    if scope not in SCOPES:
        raise UnknownScopeError(f"scope must be one of {SCOPES}")


def begin_idempotent(conn: sqlite3.Connection, scope: str, key: str) -> BeginResult:
    """Claim (scope, key). See module docstring for the three outcomes."""
    _validate_scope(scope)
    try:
        with _db.transaction(conn):
            conn.execute(
                "INSERT INTO idempotency_keys(scope, key, status) VALUES (?,?,?)",
                (scope, key, STATUS_IN_PROGRESS),
            )
        return BeginResult(state=STATE_STARTED)
    except sqlite3.IntegrityError:
        # Already claimed — report its current state.
        row = conn.execute(
            "SELECT status, result_ref FROM idempotency_keys WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if row and row["status"] == STATUS_COMPLETED:
            return BeginResult(state=STATE_ALREADY_COMPLETED, result_ref=row["result_ref"])
        return BeginResult(state=STATE_IN_PROGRESS)


def complete_idempotent(conn: sqlite3.Connection, scope: str, key: str,
                        result_ref: str) -> str:
    """Mark (scope, key) completed with `result_ref`. If it was already completed, keep and
    return the prior result_ref (replays are stable). Returns the effective result_ref."""
    _validate_scope(scope)
    with _db.transaction(conn):
        row = conn.execute(
            "SELECT status, result_ref FROM idempotency_keys WHERE scope=? AND key=?",
            (scope, key),
        ).fetchone()
        if row is None:
            # Allow complete without a prior begin (still exactly-once on UNIQUE).
            conn.execute(
                "INSERT INTO idempotency_keys(scope, key, status, result_ref, updated_at) "
                "VALUES (?,?,?,?, datetime('now'))",
                (scope, key, STATUS_COMPLETED, result_ref),
            )
            return result_ref
        if row["status"] == STATUS_COMPLETED:
            return row["result_ref"]
        conn.execute(
            "UPDATE idempotency_keys SET status=?, result_ref=?, updated_at=datetime('now') "
            "WHERE scope=? AND key=?",
            (STATUS_COMPLETED, result_ref, scope, key),
        )
        return result_ref


def status_of(conn: sqlite3.Connection, scope: str, key: str) -> Optional[str]:
    row = conn.execute(
        "SELECT status FROM idempotency_keys WHERE scope=? AND key=?", (scope, key)
    ).fetchone()
    return row["status"] if row else None
