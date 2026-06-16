#!/usr/bin/env python3
"""Node health probe DRY-RUN (TEMP DB; MOCK probes by default; NO DB write, NO secrets).

Reads node rows and prints a sanitized probe summary per node. By default uses synthetic/mock
probes (no network). `--real-public-tcp-only` performs read-only PUBLIC TCP connects to 22/80/443
only (no payload, no admin path) — opt-in. Never writes the DB; never prints a secret/URL/IP-laden
error (errors are sanitized to reason codes).

  python3 bin/node_health_probe_dry_run.py --db /tmp/probe.sqlite3
  python3 bin/node_health_probe_dry_run.py --db /tmp/probe.sqlite3 --real-public-tcp-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import db as dbmod, migrate, node_probe, seed  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Node health probe dry-run (temp DB; mock by default).")
    ap.add_argument("--db", default="/tmp/unseenproxy_probe_dry.sqlite3")
    ap.add_argument("--real-public-tcp-only", action="store_true",
                    help="opt-in: real read-only PUBLIC TCP 22/80/443 connects (no payload/admin path)")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    prober = node_probe.PublicTcpProber() if args.real_public_tcp_only else node_probe.MockProber()
    nodes = conn.execute(
        "SELECT node_code, region_code, status, public_hostname, public_ip FROM proxy_nodes "
        "ORDER BY node_code").fetchall()
    out = []
    for node in nodes:
        pr = prober.probe(node)
        d = pr.sanitized()
        out.append({k: d[k] for k in ("node_code", "status", "latency_ms", "tcp_443_ok",
                                      "tcp_80_ok", "tcp_22_ok", "udp_443_status",
                                      "panel_http_status", "cpu_pct", "ram_pct", "disk_pct",
                                      "reasons")})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"PROBE_DRY_RUN_OK: {'real-public-tcp' if args.real_public_tcp_only else 'mock'}; "
          "no DB write; sanitized.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
