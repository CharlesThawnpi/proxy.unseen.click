"""NotificationSender — consume queued outbound_messages → TelegramTransport (§30A.3).

Dry-run by default: renders each queued telegram message from its `payload_ref` (a template key,
never a raw body/secret) and "sends" it through a dry-run `TelegramTransport` (no network). It
then transitions the row's status via the existing NotificationService helpers:

  queued → sent                         (mocked/real success)
  queued → queued (attempts+1, backoff) (retryable failure, below max_attempts)
  queued → dead                         (permanent failure, or attempts reach max)

Live sending is **hard-refused** unless the runtime double-gate passes (`ALLOW_LIVE_BOT_SENDS=1`
+ `--live-send --confirm`). Even when gated, tests inject a mock transport — no real network.

The recipient chat id is resolved from `platform_accounts` (telegram, customer) — we never store
a raw body, link, token, or chat id in the queue; only the `payload_ref` reference is persisted.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from . import notification_service as _notif, runtime_gates, telegram_messages as _msg
from .telegram_transport import TelegramTransport

# A simulator decides the mock transport outcome per message in tests/dry-run:
#   returns one of "ok" | "retry" | "permanent".  Default: "ok".
Simulator = Callable[[sqlite3.Row], str]


class LiveSendRefusedError(RuntimeError):
    """Raised when a live send is requested but the double gate is not satisfied."""


@dataclass
class SendSummary:
    considered: int = 0
    sent: int = 0
    requeued: int = 0
    dead: int = 0
    skipped_no_recipient: int = 0
    live: bool = False
    handled_refs: List[str] = field(default_factory=list)   # sanitized payload_refs only


class NotificationSender:
    def __init__(self, conn: sqlite3.Connection, transport: Optional[TelegramTransport] = None):
        self._conn = conn
        self._transport = transport or TelegramTransport()    # dry-run by default

    def _telegram_chat_id(self, customer_id: Optional[int]) -> Optional[int]:
        if customer_id is None:
            return None
        row = self._conn.execute(
            "SELECT platform_user_id FROM platform_accounts "
            "WHERE customer_id=? AND platform_name='telegram' AND is_active=1 ORDER BY id LIMIT 1",
            (customer_id,)).fetchone()
        if not row:
            return None
        try:
            return int(row[0])
        except (TypeError, ValueError):
            return None

    def process_queued(self, *, limit: int = 50, simulate: Optional[Simulator] = None,
                       live_send: bool = False, confirm: bool = False) -> SendSummary:
        """Process queued telegram messages. Dry-run unless the live double-gate passes (and even
        then the transport is whatever was injected — tests use a mock)."""
        gate = runtime_gates.live_send_gate(live_send=live_send, confirm=confirm)
        want_live = live_send or confirm
        if want_live and not gate.allowed:
            raise LiveSendRefusedError("live send refused: " + ", ".join(gate.blockers))
        summary = SendSummary(live=gate.allowed and want_live)

        rows = self._conn.execute(
            "SELECT * FROM outbound_messages WHERE channel='telegram' AND status='queued' "
            "ORDER BY id LIMIT ?", (int(limit),)).fetchall()
        for row in rows:
            summary.considered += 1
            mid = int(row["id"])
            chat_id = self._telegram_chat_id(row["customer_id"])
            if chat_id is None:
                # No telegram recipient mapped — treat as retryable (don't lose the message).
                _notif.mark_failed_or_retry(self._conn, mid, error_ref="no_telegram_recipient")
                summary.requeued += 1
                summary.skipped_no_recipient += 1
                continue

            text = _msg.render_payload(row["payload_ref"] or "")
            outcome = (simulate(row) if simulate else "ok")

            if outcome == "ok":
                # Render through the transport (dry-run records intent; live would send).
                result = self._transport.send_message(chat_id, text)
                if result.ok:
                    _notif.mark_sent(self._conn, mid)
                    summary.sent += 1
                else:
                    status = _notif.mark_failed_or_retry(self._conn, mid, error_ref="transport_error")
                    summary.dead += int(status == _notif.STATUS_DEAD)
                    summary.requeued += int(status == _notif.STATUS_QUEUED)
            elif outcome == "retry":
                status = _notif.mark_failed_or_retry(self._conn, mid, error_ref="retryable")
                summary.dead += int(status == _notif.STATUS_DEAD)
                summary.requeued += int(status == _notif.STATUS_QUEUED)
            else:  # "permanent"
                _notif.mark_dead(self._conn, mid, reason_ref="permanent_failure")
                summary.dead += 1
            summary.handled_refs.append(row["payload_ref"] or "")
        return summary
