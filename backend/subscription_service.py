"""SubscriptionService — create a subscription from an approved order (§14, §30A.2).

A subscription is created with **order-time snapshots** of the plan's quota/duration/price, so
later edits to the plan catalogue never alter an existing subscription. Lifecycle `status`
starts `pending` (not active); the provisioning axis is `provision_status` (see
provisioning_service). Dates are computed deterministically from a caller-supplied `now` in
tests so expiry is reproducible.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from . import db as _db, timezone as _tz
from .audit import audit_row


class UnknownPlanError(ValueError):
    pass


class OrderNotApprovedError(ValueError):
    pass


@dataclass(frozen=True)
class SubscriptionResult:
    subscription_id: int
    plan_code: str
    snap_data_limit_gib: int
    snap_duration_days: int
    snap_price_mmk: int


def _plan(conn: sqlite3.Connection, plan_code: str):
    p = conn.execute("SELECT * FROM plans WHERE plan_code=?", (plan_code,)).fetchone()
    if not p:
        raise UnknownPlanError("unknown plan_code")  # value not echoed
    return p


def create_from_order(conn: sqlite3.Connection, order_id: int,
                      now: Optional[str] = None) -> SubscriptionResult:
    """Create a subscription from an **approved** order, copying plan snapshots.

    `now` should be a Myanmar Time business timestamp string and makes start/expiry
    deterministic for tests. If None, `backend.timezone.now_mmt()` is used. expiry = start +
    plan.duration_days. Runs in one transaction.
    """
    order = conn.execute("SELECT * FROM payment_orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        raise OrderNotApprovedError("order not found")
    if order["status"] != "approved":
        raise OrderNotApprovedError("order is not approved")

    p = _plan(conn, order["plan_code"])
    gib = int(p["data_limit_gib"])
    days = int(p["duration_days"])
    price = int(p["price_mmk"])

    with _db.transaction(conn):
        start_dt = _tz.parse_mmt(now) if now is not None else _tz.now_mmt()
        expiry_dt = start_dt + timedelta(days=days)
        start_value = _tz.storage_mmt(start_dt)
        expiry_value = _tz.storage_mmt(expiry_dt)
        params = [order["customer_id"], order["plan_code"], gib, days, price]
        cur = conn.execute(
            "INSERT INTO subscriptions"
            "(customer_id, plan_code, snap_data_limit_gib, snap_duration_days, snap_price_mmk,"
            " status, provision_status, start_date, expiry_date) "
            "VALUES (?,?,?,?,?, 'pending', 'unprovisioned', ?, ?)",
            params + [start_value, expiry_value],
        )
        sid = int(cur.lastrowid)
        audit_row(conn, "subscription_plan_created", f"subscription:{sid}",
                  f"order:{order_id} plan:{order['plan_code']} gib:{gib} days:{days}")

    return SubscriptionResult(subscription_id=sid, plan_code=order["plan_code"],
                              snap_data_limit_gib=gib, snap_duration_days=days, snap_price_mmk=price)


def get(conn: sqlite3.Connection, subscription_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM subscriptions WHERE id=?", (subscription_id,)).fetchone()
