#!/usr/bin/env python3
"""Enqueue + dry-run send a single telegram notification (TEMP DB; NO network, NO live send).

Resolves/creates a synthetic telegram customer, enqueues one notification with a payload_ref
(template key only — no body/secret), then runs the dry-run sender once. Prints sanitized
result. Live send refused unless the double gate is present.

  python3 bin/send_notification_dry_run.py --db /tmp/send.sqlite3 --payload-ref bot:welcome:1
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    account_service, db as dbmod, migrate, notification_service as notif, outbound_worker, seed,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Enqueue + dry-run send one telegram notification.")
    ap.add_argument("--db", default="/tmp/unseenproxy_send_dry.sqlite3")
    ap.add_argument("--payload-ref", default="bot:welcome:demo",
                    help="template key only — never a raw body/link/secret")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    cid = account_service.resolve_customer(conn, "telegram", "700300")
    mid = notif.enqueue_notification(conn, cid, "telegram", "transactional", args.payload_ref)
    summary = outbound_worker.run_once(conn)        # dry-run
    row = notif.get_message(conn, mid)
    print(json.dumps({"message_id": mid, "payload_ref": row["payload_ref"],
                      "status_after": row["status"], "sent": summary.sent}, indent=2))
    print("SEND_DRY_RUN_OK: payload_ref only; no network; no live send.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
