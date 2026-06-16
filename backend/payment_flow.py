"""Payment-approval → provisioning boundary (DRY-RUN ONLY).

This is a thin, idempotent *boundary* over the approval/provision flow — NOT real payment
processing and NOT live Hiddify provisioning. It exists to prove the idempotency contract on
the two scopes that must be exactly-once (`payment_approval`, `provision_subscription`):
a double-tap / re-delivered webhook must yield ONE approval and ONE provisioning intent.

No money moves, no subscription is activated, and no Hiddify endpoint is called here.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from . import idempotency as _idem


@dataclass(frozen=True)
class FlowResult:
    duplicate: bool      # True if this call replayed a prior completed result
    result_ref: str      # stable reference for the approval/provision (e.g. "order:42:approved")


def approve_payment_dry_run(conn: sqlite3.Connection, order_id: int) -> FlowResult:
    """Idempotently 'approve' a payment order (dry-run). Re-running with the same order_id
    returns the prior result_ref and duplicate=True — never a second approval."""
    key = f"order:{order_id}"
    begin = _idem.begin_idempotent(conn, "payment_approval", key)
    if begin.state == _idem.STATE_ALREADY_COMPLETED:
        return FlowResult(duplicate=True, result_ref=begin.result_ref)
    # (real flow would verify the payment here — dry-run: no-op)
    result_ref = f"order:{order_id}:approved"
    stored = _idem.complete_idempotent(conn, "payment_approval", key, result_ref)
    return FlowResult(duplicate=False, result_ref=stored)


def provision_subscription_dry_run(conn: sqlite3.Connection, order_id: int) -> FlowResult:
    """Idempotently record a provisioning intent (dry-run). NO live Hiddify call. Re-running
    returns the prior result_ref and duplicate=True — never a second provisioning."""
    key = f"order:{order_id}"
    begin = _idem.begin_idempotent(conn, "provision_subscription", key)
    if begin.state == _idem.STATE_ALREADY_COMPLETED:
        return FlowResult(duplicate=True, result_ref=begin.result_ref)
    # (real flow would call the provisioner — dry-run: record intent only, no network)
    result_ref = f"order:{order_id}:provisioned(dry-run)"
    stored = _idem.complete_idempotent(conn, "provision_subscription", key, result_ref)
    return FlowResult(duplicate=False, result_ref=stored)
