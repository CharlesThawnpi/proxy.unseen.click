#!/usr/bin/env python3
"""Dry-run provisioning CLI for an existing subscription (no live Hiddify; sanitized output).

Builds the dry-run provisioning plan + sanitized Hiddify mutation intent and enqueues the
delivery notification (exactly once). LIVE is hard-refused in Phase 4C even with --live
--confirm and the env latch set.

  python3 bin/provision_subscription_dry_run.py --db <db> --subscription <id> [--node de1] [--live --confirm]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config, db as dbmod, provisioning_service as prov  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan provisioning for a subscription (DRY-RUN).")
    ap.add_argument("--db", default=config.db_path())
    ap.add_argument("--subscription", type=int, required=True)
    ap.add_argument("--node", default="de1")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args(argv)

    conn = dbmod.connect(args.db)
    r = prov.plan_and_dry_run_provision(conn, args.subscription, node_code=args.node,
                                        live=args.live, confirm=args.confirm)
    print(json.dumps({
        "subscription_id": r.subscription_id, "duplicate": r.duplicate,
        "provision_status": r.provision_status, "live_refused": r.live_refused,
        "live_blockers": r.live_blockers, "notification_id": r.notification_id,
        "plan_summary": {k: r.plan_summary[k] for k in
                         ("plan_code", "quota_gib", "quota_gb", "package_days", "regions",
                          "profile_labels", "premium_regions")},
        "hiddify_intent": {k: r.hiddify_mutation_plan[k] for k in
                           ("method", "path", "usage_limit_GB", "package_days", "enable")},
    }, indent=2))
    if args.live or args.confirm:
        print("LIVE REFUSED — Phase 4C performs NO live Hiddify mutation (blockers above).")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
