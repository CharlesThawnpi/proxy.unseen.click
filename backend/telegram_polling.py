"""TelegramPollingRunner — getUpdates → TelegramRouter, offset-tracked (§transport).

Pulls updates from a `TelegramTransport` (dry-run by default) and routes each through the
existing `TelegramRouter`, tracking the `update_id` offset like a real long-poll loop would.
**No persistent daemon** is started in this task: `poll_batch` processes a provided/fetched
batch once and returns. Live polling is **hard-refused** unless the runtime double-gate passes
(`ALLOW_LIVE_BOT_POLLING=1` + `--live-poll --confirm`).
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional

from . import bot_context, runtime_gates, telegram_router
from .telegram_transport import TelegramTransport


class LivePollingRefusedError(RuntimeError):
    """Raised when live polling is requested but the double gate is not satisfied."""


@dataclass
class PollSummary:
    processed: int = 0
    next_offset: Optional[int] = None
    handled: List[str] = field(default_factory=list)   # sanitized handler labels (e.g. "/start")


class TelegramPollingRunner:
    def __init__(self, conn: sqlite3.Connection, ctx: bot_context.BotContext,
                 transport: Optional[TelegramTransport] = None,
                 router: Optional[telegram_router.TelegramRouter] = None):
        self._conn = conn
        self._ctx = ctx
        self._transport = transport or TelegramTransport()       # dry-run by default
        self._router = router or telegram_router.TelegramRouter(conn, ctx)
        self._offset: Optional[int] = None

    @property
    def offset(self) -> Optional[int]:
        return self._offset

    def _route_updates(self, updates) -> PollSummary:
        summary = PollSummary(next_offset=self._offset)
        if not isinstance(updates, list):
            return summary
        for upd in updates:
            uid = upd.get("update_id") if isinstance(upd, dict) else None
            res = self._router.handle_update(upd)     # routes safely; invalid → no crash
            summary.processed += 1
            summary.handled.append(res.handled)
            if isinstance(uid, int):
                # Telegram offset convention: acknowledge up to update_id by passing update_id+1.
                self._offset = uid + 1
        summary.next_offset = self._offset
        return summary

    def poll_batch(self, updates: Optional[list] = None) -> PollSummary:
        """Process one batch of updates (dry-run). If `updates` is None, fetch via the transport
        (dry-run transport returns no updates — no network)."""
        if updates is None:
            result = self._transport.get_updates(offset=self._offset)
            updates = result.data if isinstance(result.data, list) else []
        return self._route_updates(updates)

    def run_live_once(self, *, live_poll: bool = False, confirm: bool = False) -> PollSummary:
        """Skeleton live entry point: enforce the double gate, then (if ever allowed) process a
        SINGLE batch — never a daemon loop in this task. Refuses unless gated."""
        gate = runtime_gates.live_poll_gate(live_poll=live_poll, confirm=confirm)
        if not gate.allowed:
            raise LivePollingRefusedError("live polling refused: " + ", ".join(gate.blockers))
        # NOTE: even when gated open, this task does NOT loop or start a daemon — single batch only.
        return self.poll_batch()
