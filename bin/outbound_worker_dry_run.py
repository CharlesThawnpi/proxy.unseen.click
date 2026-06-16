#!/usr/bin/env python3
"""Outbound worker DRY-RUN (explicit/temp DB; mock transport; NO network, NO live send).

Processes queued telegram outbound_messages once via the dry-run NotificationSender and prints
sanitized counts only (no bodies, no recipients, no secrets). Live send refused unless the
double gate is present. Use --seed-demo to enqueue a couple of synthetic rows on a temp DB.

  python3 bin/outbound_worker_dry_run.py --db /tmp/worker.sqlite3 --seed-demo
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    account_service, db as dbmod, migrate, notification_sender, notification_service as notif,
    outbound_worker, seed,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Outbound worker dry-run (temp DB, mock transport).")
    ap.add_argument("--db", default="/tmp/unseenproxy_worker_dry.sqlite3")
    ap.add_argument("--seed-demo", action="store_true", help="enqueue synthetic telegram rows")
    ap.add_argument("--live-send", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    if args.seed_demo:
        cid = account_service.resolve_customer(conn, "telegram", "700200")
        notif.enqueue_notification(conn, cid, "telegram", "transactional", "bot:welcome:demo")
        notif.enqueue_notification(conn, cid, "telegram", "transactional", "delivery:sub:demo")

    if args.live_send or args.confirm:
        try:
            outbound_worker.run_once(conn, live_send=args.live_send, confirm=args.confirm)
        except notification_sender.LiveSendRefusedError as e:
            print(f"LIVE SEND REFUSED — {e}")
            conn.close()
            return 0

    summary = outbound_worker.run_once(conn)   # dry-run; mocked success path
    print(json.dumps({
        "considered": summary.considered, "sent": summary.sent, "requeued": summary.requeued,
        "dead": summary.dead, "live": summary.live,
        "queue_counts": notif.queue_counts(conn),
    }, indent=2))
    print("OUTBOUND_WORKER_DRY_RUN_OK: no network; no live send.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
