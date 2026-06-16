#!/usr/bin/env python3
"""Node alerts + readiness preview (TEMP DB; read-only; sanitized). NO network, NO write.

Shows OPEN alert counts (by level) and per-node readiness (status/health/live_ready/reasons) so an
operator can see how current alerts affect candidate selection. Sanitized — no IP/secret.

  python3 bin/node_alerts_preview.py --db /tmp/mon.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import alerting, config, db as dbmod, migrate, node_resilience as nr, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Preview open alerts + node readiness (read-only).")
    ap.add_argument("--db", default=config.db_path())
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    nodes = conn.execute("SELECT DISTINCT region_code FROM proxy_nodes").fetchall()
    regions = [r[0] for r in nodes]
    readiness = [r.as_dict() for r in nr.readiness_for_regions(conn, regions)]
    print(json.dumps({
        "open_alert_counts": alerting.open_alert_counts(conn),
        "readiness": readiness,
    }, ensure_ascii=False, indent=2))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
