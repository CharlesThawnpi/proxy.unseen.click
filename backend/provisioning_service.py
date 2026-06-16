"""HiddifyProvisioningService — dry-run provisioning orchestration (§6, §8, §30A.2).

Plans a subscription's Hiddify provisioning **without touching live Hiddify**. Live mutation is
**hard-refused in Phase 4C** regardless of env/flags/node status (see config.PHASE4C_LIVE_*).
Exactly-once is enforced via `idempotency_keys` (scope `provision_subscription`, key
`sub:<id>`): the dry-run plan + delivery notification + audit happen exactly once; a replay
returns the prior result and enqueues no duplicate notification.

Secret-safety: the produced plan summary and the Hiddify mutation plan contain NO API key,
admin path, user UUID, subscription URL, proxy link, or QR payload.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

from . import (
    account_service, compensation, config, db as _db, idempotency as _idem,
    notification_service as _notif, provisioning_plan as _plan,
)
from .audit import audit_row, write_audit

_SCOPE = "provision_subscription"


def _key(subscription_id: int) -> str:
    return f"sub:{subscription_id}"


@dataclass(frozen=True)
class ProvisionResult:
    duplicate: bool
    subscription_id: int
    provision_status: str          # dry_run_planned | provision_failed
    live_refused: bool
    live_blockers: List[str]
    plan_summary: dict             # sanitized
    hiddify_mutation_plan: dict    # sanitized intended call (NOT sent)
    notification_id: Optional[int]
    result_ref: str


def _live_requested(live: bool, confirm: bool) -> bool:
    return bool(live or confirm or config.live_latch_enabled())


def plan_and_dry_run_provision(conn: sqlite3.Connection, subscription_id: int,
                               node_code: str = "de1", live: bool = False,
                               confirm: bool = False) -> ProvisionResult:
    """Build the dry-run provisioning plan for a subscription and enqueue its delivery
    notification, exactly once. Live is hard-refused in Phase 4C."""
    sub = conn.execute("SELECT * FROM subscriptions WHERE id=?", (subscription_id,)).fetchone()
    if sub is None:
        raise ValueError("subscription not found")

    plan = _plan.build_plan(conn, sub["plan_code"], preferred_node=node_code)
    cust_code = account_service.public_code(conn, sub["customer_id"]) or f"cust{sub['customer_id']}"
    mutation = _plan.hiddify_mutation_plan(plan, cust_code)

    # LIVE GATE — even with env latch + --live --confirm + a live node, Phase 4C refuses.
    live_refused = True
    blockers = list(plan.live_blockers)
    if _live_requested(live, confirm) and config.PHASE4C_LIVE_PROVISION_DISABLED:
        if "phase4c_live_disabled" not in blockers:
            blockers.append("phase4c_live_disabled")

    begin = _idem.begin_idempotent(conn, _SCOPE, _key(subscription_id))
    if begin.state == _idem.STATE_ALREADY_COMPLETED:
        existing_notif = conn.execute(
            "SELECT id FROM outbound_messages WHERE customer_id=? AND payload_ref=? ORDER BY id LIMIT 1",
            (sub["customer_id"], f"delivery:sub:{subscription_id}")).fetchone()
        fresh = conn.execute("SELECT provision_status FROM subscriptions WHERE id=?",
                             (subscription_id,)).fetchone()
        return ProvisionResult(
            duplicate=True, subscription_id=subscription_id,
            provision_status=fresh["provision_status"], live_refused=True, live_blockers=blockers,
            plan_summary=plan.sanitized_summary(), hiddify_mutation_plan=mutation,
            notification_id=int(existing_notif[0]) if existing_notif else None,
            result_ref=begin.result_ref or f"provisioned_dry_run:sub:{subscription_id}")
    if begin.state == _idem.STATE_IN_PROGRESS:
        raise RuntimeError("provisioning already in progress for this subscription")

    # STARTED — do the dry-run work exactly once.
    with _db.transaction(conn):
        conn.execute("UPDATE subscriptions SET provision_status='dry_run_planned' WHERE id=?",
                     (subscription_id,))
        compensation.record_attempt(conn, subscription_id, node_code, "dry_run", "dry_run_planned",
                                    f"regions:{','.join(plan.regions)} live_refused:{';'.join(blockers)}")
        audit_row(conn, "provisioning_dry_run_planned", f"subscription:{subscription_id}",
                  f"node:{node_code} quota_gib:{plan.quota_gib} quota_gb:{plan.quota_gb} "
                  f"days:{plan.package_days} live_refused:{';'.join(blockers)}")

    # Delivery notification — queue-first, payload_ref only (NO link/body). Enqueued once.
    notif_id = _notif.enqueue_notification(
        conn, sub["customer_id"], "telegram", "transactional", f"delivery:sub:{subscription_id}")
    write_audit(conn, "notification_queued", f"subscription:{subscription_id}",
                f"channel:telegram purpose:transactional payload_ref:delivery:sub:{subscription_id}")

    result_ref = f"provisioned_dry_run:sub:{subscription_id}"
    _idem.complete_idempotent(conn, _SCOPE, _key(subscription_id), result_ref)

    return ProvisionResult(
        duplicate=False, subscription_id=subscription_id, provision_status="dry_run_planned",
        live_refused=live_refused, live_blockers=blockers,
        plan_summary=plan.sanitized_summary(), hiddify_mutation_plan=mutation,
        notification_id=notif_id, result_ref=result_ref)


@dataclass(frozen=True)
class FlowResult:
    subscription_id: int
    approval_duplicate: bool
    provision: ProvisionResult


def dry_run_provision_flow(conn: sqlite3.Connection, order_id: int, node_code: str = "de1",
                           now: Optional[str] = None) -> FlowResult:
    """End-to-end dry-run orchestration: approve order → create subscription → plan provisioning
    (dry-run) → enqueue delivery notification → audit. Idempotent end-to-end."""
    from . import payment_approval_service as _appr
    approval = _appr.approve_order_dry_run(conn, order_id, now=now)
    prov = plan_and_dry_run_provision(conn, approval.subscription_id, node_code=node_code)
    return FlowResult(subscription_id=approval.subscription_id,
                      approval_duplicate=approval.duplicate, provision=prov)
