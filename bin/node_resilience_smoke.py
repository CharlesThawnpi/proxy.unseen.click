#!/usr/bin/env python3
"""Node resilience smoke (TEMP DB; mocked statuses/alerts; NO network, NO de1 metrics fetch).

Demonstrates readiness + graceful degradation on a temp DB by adding synthetic nodes/alerts
(US live-healthy, a second DE node down) and printing sanitized readiness + PRO_3M availability.
de1 stays status=test. No real node is contacted. Sanitized output only.

  python3 bin/node_resilience_smoke.py --db /tmp/nrs.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import availability, db as dbmod, migrate, node_resilience as nr, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Node resilience smoke (temp DB; mocked).")
    ap.add_argument("--db", default="/tmp/unseenproxy_nrs.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    # Synthetic topology (mock; no real nodes): a healthy live US node, and a DOWN extra DE node.
    conn.execute("INSERT OR IGNORE INTO proxy_nodes(node_code,region_code,status) VALUES ('us1','us','live')")
    conn.execute("INSERT OR IGNORE INTO proxy_nodes(node_code,region_code,status) VALUES ('de2','de','live')")
    conn.execute("INSERT INTO node_alerts(node_code,level,metric) VALUES ('de2','DOWN','reachability')")
    conn.commit()

    readiness = [r.as_dict() for r in nr.readiness_for_regions(conn, ["de", "us", "sg"])]
    av = availability.resolve(conn, "PRO_3M", mode=availability.MODE_LIVE)
    print(json.dumps({
        "readiness": readiness,
        "live_available_regions": av.available_regions,
        "live_unavailable_regions": av.unavailable_regions,
    }, ensure_ascii=False, indent=2))
    print("SMOKE_OK: down node dropped; de1 blocks live (test + leaked_key); healthy live nodes serve.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
