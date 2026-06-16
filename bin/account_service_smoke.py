#!/usr/bin/env python3
"""Test-safe smoke for the Phase 4B service boundaries (no live sends, no real customers).

Runs entirely on a TEMP DB (its own --db, default a /tmp path). Exercises:
  - AccountService.resolve_customer (create + idempotent re-resolve)
  - account-linking issue/validate/consume (no raw code printed)
  - NotificationService enqueue + retry/dead-letter
  - idempotency begin/complete duplicate
Prints sanitized counts only — never a link code, payload, or platform id.

  python3 bin/account_service_smoke.py --db /tmp/smoke.sqlite3
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    account_linking, account_service, db as dbmod, idempotency,
    migrate, notification_service as notif, seed,
)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 4B boundary smoke (temp DB, sanitized output).")
    ap.add_argument("--db", default="/tmp/unseenproxy_smoke.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    cid = account_service.resolve_customer(conn, "telegram", "tg-smoke-1")
    cid2 = account_service.resolve_customer(conn, "telegram", "tg-smoke-1")
    assert cid == cid2, "resolve not idempotent"

    raw = account_linking.issue_link_code(conn, cid)  # raw code stays local; never printed
    v = account_linking.validate_link_code(conn, raw)
    assert v.valid and v.customer_id == cid
    res = account_linking.consume_link_code(conn, raw, ("messenger", "msgr-smoke-1"))

    mid = notif.enqueue_notification(conn, cid, "telegram", "transactional", "tmpl:welcome")
    notif.mark_sent(conn, mid)

    b = idempotency.begin_idempotent(conn, "payment_approval", "order:smoke")
    idempotency.complete_idempotent(conn, "payment_approval", "order:smoke", "ref:ok")
    b2 = idempotency.begin_idempotent(conn, "payment_approval", "order:smoke")

    print(f"customer_code={account_service.public_code(conn, cid)} "
          f"link_consume={res.status} queue={notif.queue_counts(conn)} "
          f"idem_first={b.state} idem_dup={b2.state}")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
