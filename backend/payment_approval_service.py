"""Payment-approval boundary — DRY-RUN ONLY (§30A.2).

Approves a payment order idempotently and creates exactly one subscription + access-profile
placeholder. **No real payment gateway / OCR / production data** — this is the orchestration
boundary that later wraps real approval. Exactly-once is enforced via `idempotency_keys`
(scope `payment_approval`, key `order:<id>`): a duplicate approval replays the prior result and
never creates a second subscription.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from . import access_profile_service, db as _db, idempotency as _idem, subscription_service, timezone as _tz
from .audit import audit_row


class OrderNotFoundError(ValueError):
    pass


class OrderNotApprovableError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalResult:
    duplicate: bool
    subscription_id: int
    access_profile_id: Optional[int]
    result_ref: str


_SCOPE = "payment_approval"


def _key(order_id: int) -> str:
    return f"order:{order_id}"


def approve_order_dry_run(conn: sqlite3.Connection, order_id: int,
                          now: Optional[str] = None) -> ApprovalResult:
    """Idempotently approve `order_id` (dry-run) and create one subscription + access profile.

    Re-running with the same order_id replays the prior result (duplicate=True) and creates no
    second subscription. `now`, when supplied, should be a Myanmar Time business timestamp;
    otherwise `backend.timezone.now_mmt()` is used.
    """
    begin = _idem.begin_idempotent(conn, _SCOPE, _key(order_id))
    if begin.state == _idem.STATE_ALREADY_COMPLETED:
        sid = _parse_sub(begin.result_ref)
        ap = conn.execute(
            "SELECT id FROM access_profiles WHERE customer_id=("
            "SELECT customer_id FROM subscriptions WHERE id=?) AND revoked_at IS NULL ORDER BY id LIMIT 1",
            (sid,)).fetchone()
        return ApprovalResult(duplicate=True, subscription_id=sid,
                              access_profile_id=int(ap[0]) if ap else None,
                              result_ref=begin.result_ref)
    if begin.state == _idem.STATE_IN_PROGRESS:
        # Another approval holds the key but hasn't completed — refuse rather than risk a dup.
        raise OrderNotApprovableError("approval already in progress for this order")

    # We hold the key (STATE_STARTED). Validate + transition the order, create the subscription.
    order = conn.execute("SELECT * FROM payment_orders WHERE id=?", (order_id,)).fetchone()
    if order is None:
        raise OrderNotFoundError("order not found")
    if order["status"] not in ("pending", "review"):
        raise OrderNotApprovableError("order is not in an approvable state")

    with _db.transaction(conn):
        approved_at = _tz.storage_mmt(_tz.parse_mmt(now) if now is not None else _tz.now_mmt())
        conn.execute(
            "UPDATE payment_orders SET status='approved', approved_at=? WHERE id=?",
            (approved_at, order_id),
        )
        audit_row(conn, "payment_approval_dry_run", f"order:{order_id}",
                  f"customer:{order['customer_id']} plan:{order['plan_code']} (dry-run; no gateway/OCR)")

    sub = subscription_service.create_from_order(conn, order_id, now=now)
    ap = access_profile_service.create_or_reuse(conn, order["customer_id"])

    result_ref = f"sub:{sub.subscription_id}"
    _idem.complete_idempotent(conn, _SCOPE, _key(order_id), result_ref)
    return ApprovalResult(duplicate=False, subscription_id=sub.subscription_id,
                          access_profile_id=ap.access_profile_id, result_ref=result_ref)


def _parse_sub(result_ref: Optional[str]) -> int:
    # result_ref looks like "sub:<id>"
    if result_ref and result_ref.startswith("sub:"):
        return int(result_ref.split(":", 1)[1])
    raise OrderNotApprovableError("prior approval result missing subscription id")
