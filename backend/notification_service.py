"""NotificationService — queue-first outbound notifications (§30A.3, docs/BOT_FLOWS.md).

This slice is **queue-only**: it enqueues, classifies, and manages retry/dead-letter state for
`outbound_messages`. It performs **no real send** and calls no platform API — the actual sender
lands in a later phase (Telegram bot / channel adapters).

Secret-safety: we store a `payload_ref` (a handle/template reference to the content held
elsewhere), never the raw message body. `last_error` holds a sanitized reference, never a secret.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from . import db as _db, timezone as _tz

# Channels we may enqueue for. (Identity platform `web` is not a notification channel.)
ALLOWED_CHANNELS = ("telegram", "messenger", "viber", "whatsapp")
# Message purposes — drives platform policy classification.
ALLOWED_PURPOSES = ("transactional", "reminder", "promo")

# Lifecycle: queued → sent | dead ; queued may be retried (stays queued, attempts++) or
# suppressed by policy. 'dead' is the dead-letter terminal state.
STATUS_QUEUED = "queued"
STATUS_SENT = "sent"
STATUS_SUPPRESSED = "suppressed"
STATUS_DEAD = "dead"


class InvalidChannelError(ValueError):
    pass


class InvalidPurposeError(ValueError):
    pass


@dataclass(frozen=True)
class PolicyDecision:
    """Placeholder platform-policy classification. Real per-platform windowing/templating
    rules land with the channel adapters; this captures the intended shape and defaults."""
    channel: str
    purpose: str
    action: str          # "send" | "queue" | "template_required" | "suppress"
    reason: str


def _validate(channel: str, purpose: str) -> None:
    if channel not in ALLOWED_CHANNELS:
        raise InvalidChannelError(f"channel must be one of {ALLOWED_CHANNELS}")
    if purpose not in ALLOWED_PURPOSES:
        raise InvalidPurposeError(f"purpose must be one of {ALLOWED_PURPOSES}")


def classify_policy(channel: str, purpose: str, within_session: bool = True) -> PolicyDecision:
    """Placeholder policy: how a (channel, purpose) would be handled once a sender exists.

    - Telegram: bot can message its users freely → transactional/reminder/promo all "send".
    - Messenger / WhatsApp: outside the 24h customer-care window, only template/transactional
      may go out → out-of-window non-transactional is "template_required" (or "suppress" for promo).
    - Viber: session/subscription-message rules apply → out-of-session non-transactional "queue".

    NOTE: deliberately conservative placeholders; not the final compliance logic.
    """
    _validate(channel, purpose)

    if channel == "telegram":
        return PolicyDecision(channel, purpose, "send", "telegram bot may message its users")

    if channel in ("messenger", "whatsapp"):
        if within_session or purpose == "transactional":
            return PolicyDecision(channel, purpose, "send", "in 24h window or transactional")
        if purpose == "promo":
            return PolicyDecision(channel, purpose, "suppress", "promo not allowed out-of-window")
        return PolicyDecision(channel, purpose, "template_required",
                              "out-of-window reminder needs an approved template")

    # viber
    if within_session or purpose == "transactional":
        return PolicyDecision(channel, purpose, "send", "in session or transactional")
    return PolicyDecision(channel, purpose, "queue", "out-of-session; queue for session/subscription send")


def enqueue_notification(conn: sqlite3.Connection, customer_id: Optional[int], channel: str,
                         purpose: str, payload_ref: str) -> int:
    """Enqueue a notification (status 'queued', attempts 0). Returns the message id.

    `payload_ref` is a reference/handle to the content (template id, etc.), NOT the raw body.
    """
    _validate(channel, purpose)
    with _db.transaction(conn):
        now = _tz.storage_mmt(_tz.now_mmt())
        cur = conn.execute(
            "INSERT INTO outbound_messages(customer_id, channel, purpose, status, attempts, payload_ref, created_at) "
            "VALUES (?,?,?,?,0,?,?)",
            (customer_id, channel, purpose, STATUS_QUEUED, payload_ref, now),
        )
        return int(cur.lastrowid)


def get_message(conn: sqlite3.Connection, message_id: int) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM outbound_messages WHERE id=?", (message_id,)).fetchone()


def mark_sent(conn: sqlite3.Connection, message_id: int) -> None:
    """Terminal success — records sent_at, clears any retry hint."""
    with _db.transaction(conn):
        now = _tz.storage_mmt(_tz.now_mmt())
        conn.execute(
            "UPDATE outbound_messages SET status=?, sent_at=?, next_attempt_at=NULL "
            "WHERE id=?",
            (STATUS_SENT, now, message_id),
        )


def mark_suppressed(conn: sqlite3.Connection, message_id: int, reason_ref: str = "") -> None:
    """Policy chose not to send (e.g. out-of-window promo). Terminal, non-failure."""
    with _db.transaction(conn):
        conn.execute(
            "UPDATE outbound_messages SET status=?, last_error=? WHERE id=?",
            (STATUS_SUPPRESSED, reason_ref or None, message_id),
        )


def mark_failed_or_retry(conn: sqlite3.Connection, message_id: int,
                         error_ref: str = "") -> str:
    """Record a delivery failure: increment attempts; if attempts reach the row's max_attempts,
    move to the dead-letter state, otherwise leave it 'queued' for another attempt.

    `error_ref` must be a sanitized reference (no secrets / no raw body). Returns the new status.
    """
    with _db.transaction(conn):
        row = conn.execute(
            "SELECT attempts, max_attempts FROM outbound_messages WHERE id=?", (message_id,)
        ).fetchone()
        if row is None:
            raise KeyError("unknown message id")
        attempts = int(row["attempts"]) + 1
        max_attempts = int(row["max_attempts"])
        new_status = STATUS_DEAD if attempts >= max_attempts else STATUS_QUEUED
        retry_at = None
        if new_status == STATUS_QUEUED:
            retry_at = _tz.storage_mmt(_tz.now_mmt() + timedelta(seconds=300))
        conn.execute(
            "UPDATE outbound_messages SET attempts=?, status=?, last_error=?, "
            "next_attempt_at=? "
            "WHERE id=?",
            (attempts, new_status, error_ref or None, retry_at, message_id),
        )
        return new_status


def mark_dead(conn: sqlite3.Connection, message_id: int, reason_ref: str = "") -> None:
    """Force a message into the dead-letter state (manual/operator path)."""
    with _db.transaction(conn):
        conn.execute(
            "UPDATE outbound_messages SET status=?, last_error=?, next_attempt_at=NULL WHERE id=?",
            (STATUS_DEAD, reason_ref or None, message_id),
        )


def queue_counts(conn: sqlite3.Connection) -> dict:
    """Sanitized status histogram for audit/dry-run CLIs (no message content)."""
    return {r["status"]: int(r["n"]) for r in conn.execute(
        "SELECT status, COUNT(*) AS n FROM outbound_messages GROUP BY status")}
