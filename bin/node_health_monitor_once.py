#!/usr/bin/env python3
"""Health monitor — ONE pass (NO daemon, NO systemd). Dry-run by default.

Probes every node once (mock prober). With `--write-metrics` it appends `node_metrics` and
reconciles `node_alerts` — ONLY against the explicit `--db` (intended for a local/test DB).
Default `--dry-run` writes nothing. Prints a sanitized summary. No Hiddify/Telegram network.

  python3 bin/node_health_monitor_once.py --db /tmp/mon.sqlite3                 # dry-run (no write)
  python3 bin/node_health_monitor_once.py --db /tmp/mon.sqlite3 --write-metrics  # writes to that DB
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import alerting, db as dbmod, health_monitor, migrate, node_probe, seed  # noqa: E402

# Optional demo: a synthetic stressed/down node so --write-metrics shows alert creation on a temp DB.
_DEMO_RESULTS = {
    "de1": {"status": "degraded", "tcp_443_ok": True, "tcp_80_ok": True, "tcp_22_ok": True,
            "panel_http_status": 200, "cpu_pct": 92, "ram_pct": 60, "disk_pct": 40},
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run the health monitor once (no daemon).")
    ap.add_argument("--db", default="/tmp/unseenproxy_monitor.sqlite3")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--write-metrics", action="store_true",
                    help="append node_metrics + reconcile node_alerts on the explicit --db")
    ap.add_argument("--demo", action="store_true", help="use a synthetic stressed de1 result")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    prober = node_probe.MockProber(_DEMO_RESULTS) if args.demo else node_probe.MockProber()
    write = bool(args.write_metrics)   # explicit opt-in overrides the dry-run default
    summary = health_monitor.monitor_once(conn, prober=prober, write=write)
    print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
    print(f"open_alert_counts={alerting.open_alert_counts(conn)}")
    print(f"MONITOR_ONCE_OK: write={write}; no daemon; no Hiddify/Telegram network.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
