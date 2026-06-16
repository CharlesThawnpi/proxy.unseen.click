"""Outbound worker — thin orchestrator over NotificationSender (§30A.3).

A single-pass worker for the CLI: open a sender with a dry-run transport and process the queued
telegram batch once. No daemon, no loop, no network. This is where a future gated systemd
timer/worker would hook in — for now it is dry-run only and returns a sanitized summary.
"""
from __future__ import annotations

import sqlite3
from typing import Optional

from .notification_sender import NotificationSender, SendSummary, Simulator
from .telegram_transport import TelegramTransport


def run_once(conn: sqlite3.Connection, *, limit: int = 50,
             transport: Optional[TelegramTransport] = None,
             simulate: Optional[Simulator] = None,
             live_send: bool = False, confirm: bool = False) -> SendSummary:
    """Process one batch of queued telegram notifications. Dry-run unless the live send gate
    passes (and even then the injected transport governs whether anything leaves the process)."""
    sender = NotificationSender(conn, transport=transport or TelegramTransport())
    return sender.process_queued(limit=limit, simulate=simulate,
                                 live_send=live_send, confirm=confirm)
