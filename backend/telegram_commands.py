"""Telegram command constants + safe update parsing (§10 error handling).

Parsing never raises on a malformed update — it returns a structured `ParsedUpdate` with
`kind="invalid"` instead, so the router can fall back safely with no stack trace to the user.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# Supported commands (slash form). Plain-text fallback maps a few Burmese/English menu words too.
CMD_START = "/start"
CMD_HELP = "/help"
CMD_PLANS = "/plans"
CMD_ACCOUNT = "/account"
CMD_STATUS = "/status"
CMD_LINK = "/link"
CMD_ADMIN = "/admin"

KNOWN_COMMANDS = (CMD_START, CMD_HELP, CMD_PLANS, CMD_ACCOUNT, CMD_STATUS, CMD_LINK, CMD_ADMIN)


@dataclass(frozen=True)
class ParsedUpdate:
    kind: str                       # "message" | "callback" | "invalid"
    user_id: Optional[int] = None   # telegram from.id (platform_user_id)
    chat_id: Optional[int] = None
    text: str = ""                  # message text or callback data
    command: Optional[str] = None   # normalized leading command, if any
    callback_query_id: Optional[str] = None


def _norm_command(text: str) -> Optional[str]:
    if not text:
        return None
    first = text.strip().split()[0].lower()
    # strip @botname suffix (e.g. /start@unseen_bot)
    if "@" in first:
        first = first.split("@", 1)[0]
    return first if first in KNOWN_COMMANDS else None


def parse_update(update) -> ParsedUpdate:
    """Defensively parse a Telegram update dict. Returns kind='invalid' on any bad shape."""
    if not isinstance(update, dict):
        return ParsedUpdate(kind="invalid")
    try:
        if isinstance(update.get("message"), dict):
            msg = update["message"]
            frm = msg.get("from") or {}
            chat = msg.get("chat") or {}
            uid = frm.get("id")
            text = msg.get("text") or ""
            if uid is None:
                return ParsedUpdate(kind="invalid")
            return ParsedUpdate(kind="message", user_id=int(uid),
                                chat_id=chat.get("id"), text=str(text),
                                command=_norm_command(str(text)))
        if isinstance(update.get("callback_query"), dict):
            cq = update["callback_query"]
            frm = cq.get("from") or {}
            uid = frm.get("id")
            data = cq.get("data") or ""
            if uid is None:
                return ParsedUpdate(kind="invalid")
            msg = cq.get("message") or {}
            chat = (msg.get("chat") or {}) if isinstance(msg, dict) else {}
            return ParsedUpdate(kind="callback", user_id=int(uid), chat_id=chat.get("id"),
                                text=str(data), command=_norm_command(str(data)),
                                callback_query_id=cq.get("id"))
    except (TypeError, ValueError, KeyError, AttributeError):
        return ParsedUpdate(kind="invalid")
    return ParsedUpdate(kind="invalid")
