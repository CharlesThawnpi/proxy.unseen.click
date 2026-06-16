#!/usr/bin/env python3
"""Dry-run payment-approval CLI (no gateway/OCR; sanitized output).

Approves an existing order idempotently and creates one subscription + access-profile
placeholder. Re-running the same order replays the prior result (no duplicate subscription).

  python3 bin/approve_payment_dry_run.py --db <db> --order <id>
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config, db as dbmod, payment_approval_service as appr  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Approve a payment order (DRY-RUN, idempotent).")
    ap.add_argument("--db", default=config.db_path())
    ap.add_argument("--order", type=int, required=True)
    args = ap.parse_args(argv)

    conn = dbmod.connect(args.db)
    r = appr.approve_order_dry_run(conn, args.order)
    print(json.dumps({"order": args.order, "duplicate": r.duplicate,
                      "subscription_id": r.subscription_id,
                      "access_profile_id": r.access_profile_id,
                      "result_ref": r.result_ref}))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
