"""TelegramAdapter — pure boundary, DRY-RUN only in Phase 5 (§9, §10, SECURITY).

This adapter NEVER calls the Telegram API in Phase 5. `send_message` / `edit_message` /
`answer_callback_query` record the *intended* call into an in-memory outbox and return a
synthetic result — no network, no polling, no webhook. Live sends are hard-refused regardless
of env/flags (`config.PHASE5_LIVE_SEND_DISABLED`).

Secret-safety: the bot token is never stored in a public attribute, never logged, and never
included in `repr()`. Only its presence + a redacted fingerprint are exposed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional

from . import config


def redact_token(token: Optional[str]) -> str:
    """Return a non-secret label for a bot token. Never reveals the value."""
    if not token:
        return "tg:<absent>"
    # Telegram tokens look like "<botid>:<35-char-secret>". Show neither half's secret part.
    head = token.split(":", 1)[0]
    head = head if head.isdigit() and len(head) <= 10 else "***"
    return f"tg:{head}:<redacted>"


class LiveSendDisabledError(RuntimeError):
    """Raised if a live send is attempted while Phase 5 disables it."""


@dataclass
class OutboxEntry:
    method: str                 # sendMessage | editMessageText | answerCallbackQuery
    chat_id: Optional[int]
    summary: str                # sanitized; callers must not pass secrets as text in dry-run tests
    extra: dict = field(default_factory=dict)


class TelegramAdapter:
    """Dry-run Telegram boundary. `live=True` is refused in Phase 5."""

    def __init__(self, token: Optional[str] = None, live: bool = False):
        # We accept a token only to prove redaction; we do NOT keep it in a public field.
        self.__token = token if token is not None else os.environ.get(config.TELEGRAM_BOT_TOKEN_ENV)
        self._live = bool(live)
        self.outbox: List[OutboxEntry] = []

    # ---- introspection (secret-safe) ----
    def __repr__(self) -> str:
        return f"<TelegramAdapter live={self._live} token={redact_token(self.__token)} sent={len(self.outbox)}>"

    @property
    def token_fingerprint(self) -> str:
        return redact_token(self.__token)

    def _guard_live(self) -> None:
        if self._live or not config.PHASE5_LIVE_SEND_DISABLED:
            # Phase 5: hard-disable live sends no matter what.
            raise LiveSendDisabledError("live Telegram sends are disabled in Phase 5 (dry-run only)")

    # ---- dry-run "send" surface (records intent; no network) ----
    def send_message(self, chat_id: Optional[int], text: str, **extra) -> dict:
        self._guard_live()
        self.outbox.append(OutboxEntry("sendMessage", chat_id, text, extra))
        return {"ok": True, "dry_run": True, "method": "sendMessage", "chat_id": chat_id}

    def edit_message(self, chat_id: Optional[int], message_id: int, text: str, **extra) -> dict:
        self._guard_live()
        self.outbox.append(OutboxEntry("editMessageText", chat_id, text, {"message_id": message_id, **extra}))
        return {"ok": True, "dry_run": True, "method": "editMessageText", "chat_id": chat_id}

    def answer_callback_query(self, callback_query_id: str, text: str = "", **extra) -> dict:
        self._guard_live()
        self.outbox.append(OutboxEntry("answerCallbackQuery", None, text,
                                       {"callback_query_id": callback_query_id, **extra}))
        return {"ok": True, "dry_run": True, "method": "answerCallbackQuery"}

    # ---- helpers for tests/smoke ----
    def last_text(self) -> Optional[str]:
        return self.outbox[-1].summary if self.outbox else None

    def texts(self) -> List[str]:
        return [e.summary for e in self.outbox]
