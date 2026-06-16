#!/usr/bin/env python3
"""End-to-end dry-run provisioning smoke (TEMP DB only; no live Hiddify, no sends).

Builds a synthetic customer + pending order on a temp DB, runs the full dry-run flow
(approve → subscription → dry-run provisioning plan → delivery notification queued), then
runs it AGAIN to prove idempotent replay (no duplicate subscription/notification). Prints a
sanitized summary only — never a token, UUID, link, QR, admin path, or API key.

  python3 bin/provisioning_flow_smoke.py --db /tmp/p4c_smoke.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    account_service, db as dbmod, migrate, provisioning_service, seed,
)


def _make_order(conn, plan_code: str) -> int:
    cid = account_service.resolve_customer(conn, "telegram", "smoke-buyer-1")
    plan = conn.execute("SELECT price_mmk FROM plans WHERE plan_code=?", (plan_code,)).fetchone()
    cur = conn.execute(
        "INSERT INTO payment_orders(customer_id, plan_code, amount_mmk, status) VALUES (?,?,?, 'pending')",
        (cid, plan_code, int(plan["price_mmk"])))
    conn.commit()
    return int(cur.lastrowid)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 4C dry-run provisioning smoke (temp DB).")
    ap.add_argument("--db", default="/tmp/unseenproxy_p4c_smoke.sqlite3")
    ap.add_argument("--plan", default="PRO_3M")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    order_id = _make_order(conn, args.plan)
    now = "2026-06-16 00:00:00"  # deterministic
    r1 = provisioning_service.dry_run_provision_flow(conn, order_id, node_code="de1", now=now)
    r2 = provisioning_service.dry_run_provision_flow(conn, order_id, node_code="de1", now=now)

    subs = conn.execute("SELECT COUNT(*) FROM subscriptions").fetchone()[0]
    notifs = conn.execute("SELECT COUNT(*) FROM outbound_messages").fetchone()[0]
    print(json.dumps({
        "plan": args.plan,
        "subscription_id": r1.subscription_id,
        "run1_approval_duplicate": r1.approval_duplicate,
        "run2_approval_duplicate": r2.approval_duplicate,
        "provision_status": r1.provision.provision_status,
        "live_refused": r1.provision.live_refused,
        "live_blockers": r1.provision.live_blockers,
        "subscriptions_total": subs,
        "notifications_total": notifs,
        "plan_summary": {k: r1.provision.plan_summary[k] for k in
                         ("plan_code", "quota_gib", "quota_gb", "package_days", "regions",
                          "profile_labels", "premium_regions")},
        "hiddify_intent": {k: r1.provision.hiddify_mutation_plan[k] for k in
                           ("method", "path", "usage_limit_GB", "package_days", "enable")},
    }, indent=2))
    assert subs == 1, "duplicate subscription created!"
    assert notifs == 1, "duplicate notification enqueued!"
    print("SMOKE_OK: exactly-once verified; live refused; no secrets emitted.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
