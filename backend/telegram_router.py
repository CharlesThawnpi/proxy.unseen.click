"""TelegramRouter — route incoming update dicts to dry-run handlers (§9, §10, BOT_FLOWS).

Pure orchestration: parse an update, resolve identity via AccountService (telegram platform),
build Burmese-primary reply copy from DB rows, and render it through the TelegramAdapter's
**dry-run** outbox. NOTHING is sent, no Telegram API is called, no polling/webhook is started.

Identity rule: the Telegram user id is stored as a `platform_accounts` row keyed by
(telegram, <id>) — it is NEVER the customer identity (that's the internal customers.id /
public_customer_code). /start is idempotent.

Errors: a malformed update returns a safe reply with no stack trace and no secrets.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from . import (
    account_service, bot_context, bot_flows, telegram_commands as tc,
    telegram_messages as msg,
)
from .telegram_adapter import TelegramAdapter


@dataclass
class RouterResult:
    handled: str                 # command/kind that was handled (e.g. "/start", "unknown", "invalid")
    reply_text: str
    customer_id: Optional[int] = None
    is_admin: bool = False


class TelegramRouter:
    def __init__(self, conn: sqlite3.Connection, ctx: bot_context.BotContext,
                 adapter: Optional[TelegramAdapter] = None):
        self._conn = conn
        self._ctx = ctx
        self._adapter = adapter or TelegramAdapter()  # dry-run by default

    def _reply(self, chat_id, text: str) -> None:
        # Dry-run render into the adapter outbox (no network).
        self._adapter.send_message(chat_id, text)

    def handle_update(self, update) -> RouterResult:
        p = tc.parse_update(update)
        if p.kind == "invalid":
            # No identity resolution, no crash — safe no-op reply.
            self._reply(None, msg.INVALID_UPDATE)
            return RouterResult(handled="invalid", reply_text=msg.INVALID_UPDATE)

        # Resolve identity for every real interaction (idempotent). Telegram id is a platform key.
        customer_id = account_service.resolve_customer(self._conn, "telegram", str(p.user_id))
        is_admin = self._ctx.is_admin(p.user_id)
        cmd = p.command

        if cmd == tc.CMD_START or (p.kind == "message" and not cmd and not p.text):
            text = f"{msg.WELCOME}\n\n{msg.MAIN_MENU}"
            handled = tc.CMD_START
        elif cmd == tc.CMD_HELP:
            text, handled = msg.help_text(), tc.CMD_HELP
        elif cmd == tc.CMD_PLANS:
            text, handled = bot_flows.build_plans_view(self._conn), tc.CMD_PLANS
        elif cmd in (tc.CMD_ACCOUNT, tc.CMD_STATUS):
            code = account_service.public_code(self._conn, customer_id) or f"cust{customer_id}"
            text = bot_flows.build_account_status(self._conn, customer_id, code)
            handled = cmd
        elif cmd == tc.CMD_LINK:
            text, handled = msg.LINK_PROMPT, tc.CMD_LINK
        elif cmd == tc.CMD_ADMIN:
            if is_admin:
                text = bot_flows.build_admin_summary(self._conn)
            else:
                text = msg.ADMIN_DENIED
            handled = tc.CMD_ADMIN
        else:
            text, handled = msg.UNKNOWN, "unknown"

        self._reply(p.chat_id, text)
        return RouterResult(handled=handled, reply_text=text,
                            customer_id=customer_id, is_admin=is_admin)
