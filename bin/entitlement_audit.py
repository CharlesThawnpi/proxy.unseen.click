#!/usr/bin/env python3
"""Entitlement audit (TEMP DB; DB-driven; NO network). Prints each public plan's entitled
regions/protocols (FAST display rule applied) + premium/default flags. Sanitized; no secrets.

  python3 bin/entitlement_audit.py --db /tmp/ent.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, entitlements, migrate, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit plan entitlements (temp DB; DB-driven).")
    ap.add_argument("--db", default="/tmp/unseenproxy_ent.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    out = []
    for code in [r[0] for r in conn.execute(
            "SELECT plan_code FROM plans WHERE is_public=1 AND is_enabled=1 ORDER BY sort_order")]:
        e = entitlements.resolve(conn, code)
        out.append({"plan": code, "regions": e.regions, "default_region": e.default_region,
                    "premium_regions": e.premium_regions, "protocols": e.profile_labels})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
