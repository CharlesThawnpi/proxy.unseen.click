#!/usr/bin/env python3
"""Availability preview (TEMP DB; DB-driven; NO network, NO send).

Shows the entitlement × node-resilience availability for a plan in dry-run or live mode, plus the
Burmese customer-facing status lines. Sanitized output only — region/protocol codes + reason
codes; never a node IP, token, UUID, link, or admin path.

  python3 bin/availability_preview.py --db /tmp/avail.sqlite3 --plan PRO_3M --mode live
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import availability, db as dbmod, migrate, seed, telegram_messages as msg  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Plan availability preview (temp DB; dry-run/live).")
    ap.add_argument("--db", default="/tmp/unseenproxy_avail.sqlite3")
    ap.add_argument("--plan", default="PRO_3M")
    ap.add_argument("--mode", choices=["dry_run", "live"], default="dry_run")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    av = availability.resolve(conn, args.plan, mode=args.mode)
    print(json.dumps(av.as_dict(), ensure_ascii=False, indent=2))
    print("\n=== customer-facing status (Burmese; no secrets/IPs) ===")
    for region in av.entitled_regions:
        if region in av.available_regions:
            print(msg.region_available(region))
        else:
            r = av.regions[region]
            if "node_status_test" in r["reasons"]:
                print(msg.region_test_only(region))
            else:
                print(msg.region_unavailable(region))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
