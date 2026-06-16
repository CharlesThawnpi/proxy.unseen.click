#!/usr/bin/env python3
"""Telegram polling DRY-RUN (TEMP DB; mock/fixture updates; NO network, NO live poll).

Loads update(s) from --updates-json (a JSON string or @file) or a built-in sample, routes them
through the real TelegramRouter via the dry-run TelegramPollingRunner, and prints a sanitized
summary (handler labels + offset). Live polling is refused unless the double gate is present.

  python3 bin/telegram_poll_dry_run.py --db /tmp/poll.sqlite3
  python3 bin/telegram_poll_dry_run.py --db /tmp/poll.sqlite3 --updates-json @/path/to/updates.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import bot_context, db as dbmod, migrate, seed, telegram_polling  # noqa: E402

_SAMPLE = [
    {"update_id": 1001, "message": {"from": {"id": 700100}, "chat": {"id": 700100}, "text": "/start"}},
    {"update_id": 1002, "message": {"from": {"id": 700100}, "chat": {"id": 700100}, "text": "/plans"}},
    {"update_id": 1003, "message": {"from": {"id": 700100}, "chat": {"id": 700100}, "text": "??x"}},
]


def _load_updates(spec: str):
    if not spec:
        return _SAMPLE
    if spec.startswith("@"):
        with open(spec[1:], encoding="utf-8") as fh:
            return json.load(fh)
    return json.loads(spec)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Telegram polling dry-run (temp DB, mock updates).")
    ap.add_argument("--db", default="/tmp/unseenproxy_poll_dry.sqlite3")
    ap.add_argument("--updates-json", default="", help="JSON string or @file; default built-in sample")
    ap.add_argument("--live-poll", action="store_true")
    ap.add_argument("--confirm", action="store_true")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)
    ctx = bot_context.BotContext.from_env()
    runner = telegram_polling.TelegramPollingRunner(conn, ctx)

    if args.live_poll or args.confirm:
        try:
            runner.run_live_once(live_poll=args.live_poll, confirm=args.confirm)
        except telegram_polling.LivePollingRefusedError as e:
            print(f"LIVE POLL REFUSED — {e}")
            conn.close()
            return 0

    summary = runner.poll_batch(_load_updates(args.updates_json))
    print(json.dumps({"processed": summary.processed, "next_offset": summary.next_offset,
                      "handled": summary.handled}, ensure_ascii=False, indent=2))
    print("POLL_DRY_RUN_OK: routed via router; no network; no live poll.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
