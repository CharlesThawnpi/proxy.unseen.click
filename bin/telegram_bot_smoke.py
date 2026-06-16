#!/usr/bin/env python3
"""Telegram bot foundation smoke (TEMP DB only; DRY-RUN — no Telegram API, no send, no polling).

Feeds synthetic update dicts through TelegramRouter on a temp DB and prints a sanitized summary:
which handler fired, the customer code resolved, and whether the adapter stayed dry-run. It never
prints a bot token or admin id, and asserts no duplicate customer on repeated /start.

  python3 bin/telegram_bot_smoke.py --db /tmp/tg_smoke.sqlite3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import (  # noqa: E402
    account_service, bot_context, db as dbmod, migrate, seed,
    telegram_adapter, telegram_router,
)


def _update(uid: int, text: str) -> dict:
    return {"message": {"from": {"id": uid}, "chat": {"id": uid}, "text": text}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Phase 5 Telegram bot smoke (temp DB, dry-run).")
    ap.add_argument("--db", default="/tmp/unseenproxy_tg_smoke.sqlite3")
    args = ap.parse_args(argv)

    migrate.migrate_path(args.db)
    conn = dbmod.connect(args.db)
    seed.seed(conn)

    ctx = bot_context.BotContext.from_env()          # admin ids from env (none in smoke)
    adapter = telegram_adapter.TelegramAdapter()      # dry-run
    router = telegram_router.TelegramRouter(conn, ctx, adapter)

    uid = 555001
    results = []
    for text in ("/start", "/start", "/plans", "/account", "/link", "/help", "/admin", "??garbage"):
        r = router.handle_update(_update(uid, text))
        results.append({"input": text, "handled": r.handled, "is_admin": r.is_admin})
    # invalid update shape must not crash
    bad = router.handle_update({"weird": True})
    results.append({"input": "<malformed>", "handled": bad.handled})

    # Redaction proof: a SYNTHETIC token (built at runtime so no token-shaped literal is in
    # source) must never appear in repr.
    fake = "1111111111:" + ("A" * 35)
    redacted_repr = repr(telegram_adapter.TelegramAdapter(token=fake))

    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    print(json.dumps({
        "adapter": repr(adapter),                     # token redacted in repr
        "admin_count": ctx.admin_count,
        "customers_after_two_starts": customers,
        "outbox_messages": len(adapter.outbox),
        "results": results,
    }, ensure_ascii=False, indent=2))
    assert customers == 1, "duplicate customer on repeated /start!"
    assert fake not in redacted_repr and "<redacted>" in redacted_repr, "token not redacted!"
    print("SMOKE_OK: dry-run; identity idempotent; token redacted; no network/send.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
