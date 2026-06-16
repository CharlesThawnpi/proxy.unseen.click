#!/usr/bin/env python3
"""Outbound notification queue — DRY-RUN / AUDIT ONLY (docs/BOT_FLOWS.md, §30A.3).

This slice has NO sender. This CLI only *reports* the queue and shows how each queued row
would be classified by the (placeholder) platform policy. It sends nothing and calls no
platform API. Output is sanitized: status counts + per-row policy action only, never the
payload_ref body, customer identity, or any secret.

  python3 bin/queue_notifications.py --db /tmp/dev.sqlite3 audit
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import config, db as dbmod, notification_service as notif  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Audit the outbound notification queue (no send).")
    ap.add_argument("--db", default=config.db_path())
    ap.add_argument("command", choices=["audit"], help="audit: print sanitized queue summary")
    args = ap.parse_args(argv)

    conn = dbmod.connect(args.db)
    counts = notif.queue_counts(conn)
    queued = conn.execute(
        "SELECT id, channel, purpose, attempts, max_attempts FROM outbound_messages "
        "WHERE status='queued' ORDER BY id"
    ).fetchall()
    print(f"queue_counts={counts}")
    for r in queued:
        decision = notif.classify_policy(r["channel"], r["purpose"])
        print(f"  msg#{r['id']} {r['channel']}/{r['purpose']} "
              f"attempts={r['attempts']}/{r['max_attempts']} policy={decision.action}")
    print("NOTE: dry-run/audit only — no messages were sent.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
