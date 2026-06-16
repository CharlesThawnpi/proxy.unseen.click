"""Compensation / rollback model (§30.4) — forward-only, non-destructive.

When a step after subscription creation fails, we **never** destructively roll back historical
payment/order/subscription rows. Instead we transition the provisioning axis forward to a safe
state and record a sanitized attempt + audit row:

  - provision fails  → subscription.provision_status = 'provision_failed' (subscription row kept;
                       order stays 'approved'); a 'failed' provisioning_attempt is recorded.
  - notification enqueue fails → subscription is kept; a delivery-retry is flagged via an audit
                       row (the queue's own retry/dead-letter handles re-send once a row exists).

This mirrors "prefer reversible actions; never delete financial rows" — the only mutations are
forward status transitions and append-only audit/attempt rows.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from . import db as _db
from .audit import audit_row


def record_attempt(conn: sqlite3.Connection, subscription_id: int, node_code: Optional[str],
                   mode: str, outcome: str, reason: str = "") -> int:
    """Append a provisioning_attempts row (no commit; caller's transaction owns it)."""
    cur = conn.execute(
        "INSERT INTO provisioning_attempts(subscription_id, node_code, mode, outcome, reason) "
        "VALUES (?,?,?,?,?)",
        (subscription_id, node_code, mode, outcome, reason or None),
    )
    return int(cur.lastrowid)


def mark_provision_failed(conn: sqlite3.Connection, subscription_id: int,
                          node_code: Optional[str], reason_ref: str = "") -> None:
    """Forward-transition a subscription to provision_failed and record the failed attempt.
    Non-destructive: subscription/order rows are kept. `reason_ref` must be sanitized."""
    with _db.transaction(conn):
        conn.execute(
            "UPDATE subscriptions SET provision_status='provision_failed' WHERE id=?",
            (subscription_id,),
        )
        record_attempt(conn, subscription_id, node_code, "dry_run", "failed", reason_ref)
        audit_row(conn, "provisioning_failed", f"subscription:{subscription_id}",
                  f"node:{node_code or '?'} reason:{reason_ref or 'unspecified'} (subscription kept)")


def flag_delivery_retry(conn: sqlite3.Connection, subscription_id: int, reason_ref: str = "") -> None:
    """Notification enqueue failed: keep the subscription and flag a delivery retry (audit).
    The subscription is NOT rolled back; re-running the flow will re-attempt the enqueue."""
    with _db.transaction(conn):
        audit_row(conn, "delivery_enqueue_failed_retry_flagged", f"subscription:{subscription_id}",
                  f"reason:{reason_ref or 'unspecified'} (subscription kept; delivery retry flagged)")
