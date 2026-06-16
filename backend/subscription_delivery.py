"""SubscriptionDelivery — prepare one branded delivery (dry-run; §16, §30A.3, SECURITY).

Ties the pieces together WITHOUT any network or live send:
  1. normalize a **mocked** Hiddify subscription output → sanitized modes (deep-link / copy-link)
  2. choose the primary delivery mode (Hiddify App deep link first, then copy-link, then QR)
  3. build a `DeliveryPayload` (safe refs only) + persist a `subscription_deliveries` row
     (no raw link/token/QR column exists) — only the branded token **hash** is stored
  4. enqueue a NotificationService delivery message (channel telegram, `payload_ref` only)
  5. write a sanitized audit row

The raw branded link is assembled **in memory only** for the (future, gated) send — it is never
returned by persistence helpers, never stored, never logged.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from . import (
    db as _db, hiddify_subscription_output as _hout, link_renderer, notification_service as _notif,
    qr_renderer,
)
from .audit import audit_row
from .delivery_payloads import DeliveryPayload


class RawLinkPersistenceError(ValueError):
    """Raised if a caller tries to persist/audit a value that looks like a raw proxy/sub link."""


def _guard_no_raw_link(*values: str) -> None:
    for v in values:
        if isinstance(v, str) and link_renderer.looks_like_raw_proxy_link(v):
            raise RawLinkPersistenceError("refusing to persist/log a raw proxy/subscription link")


@dataclass(frozen=True)
class DeliveryResult:
    delivery_id: int
    notification_id: int
    payload: DeliveryPayload


def prepare_delivery(conn: sqlite3.Connection, *, customer_id: int,
                     subscription_id: Optional[int], access_profile_id: Optional[int],
                     mocked_hiddify_output: dict, raw_branded_token: Optional[str] = None,
                     channel: str = "telegram") -> DeliveryResult:
    """Prepare (dry-run) one subscription delivery. Persists safe refs only + enqueues a
    notification. `mocked_hiddify_output` is an in-memory mock; `raw_branded_token` (if given)
    is hashed to a handle and then DROPPED — never stored/returned."""
    summary = _hout.normalize(mocked_hiddify_output)
    qr = qr_renderer.qr_plan()

    deep = summary.has_deep_link
    # A branded copy-link is always derivable once a token exists (or any sub URL is present).
    copy = bool(raw_branded_token) or summary.has_subscription_url
    primary = DeliveryPayload.choose_primary_mode(deep, copy, qr.available)

    template_key = f"delivery:sub:{subscription_id}" if subscription_id else "delivery:generic"
    token_handle = link_renderer.branded_token_handle(raw_branded_token) if raw_branded_token else None

    payload = DeliveryPayload(
        customer_id=customer_id, subscription_id=subscription_id,
        access_profile_id=access_profile_id, channel=channel, template_key=template_key,
        deep_link_available=deep, copy_link_available=copy, qr_available=qr.available,
        primary_mode=primary, branded_token_sha256=token_handle)

    # Defensive: never persist/audit anything that looks like a raw link.
    _guard_no_raw_link(template_key, token_handle or "")

    with _db.transaction(conn):
        cur = conn.execute(
            "INSERT INTO subscription_deliveries"
            "(customer_id, subscription_id, access_profile_id, channel, template_key, primary_mode,"
            " deep_link_available, copy_link_available, qr_available, branded_token_sha256, status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?, 'prepared')",
            (customer_id, subscription_id, access_profile_id, channel, template_key, primary,
             int(deep), int(copy), int(qr.available), token_handle))
        delivery_id = int(cur.lastrowid)
        audit_row(conn, "delivery_prepared", f"delivery:{delivery_id}", payload.audit_detail())

    # Queue-first notification: payload_ref/template key only (no link/body). No live send.
    notif_id = _notif.enqueue_notification(conn, customer_id, channel, "transactional", template_key)
    with _db.transaction(conn):
        conn.execute("UPDATE subscription_deliveries SET status='queued' WHERE id=?", (delivery_id,))
        audit_row(conn, "delivery_queued", f"delivery:{delivery_id}",
                  f"notification:{notif_id} channel:{channel} tmpl:{template_key}")

    return DeliveryResult(delivery_id=delivery_id, notification_id=notif_id, payload=payload)


def render_preview(payload: DeliveryPayload) -> str:
    """Safe Burmese-primary preview of the delivery modes — NO link/token/QR. For dry-run display."""
    from . import telegram_messages as _msg
    return _msg.delivery_preview(payload.deep_link_available, payload.copy_link_available,
                                 payload.qr_available)


def build_branded_link_in_memory(raw_token: str) -> str:
    """Assemble the branded link IN MEMORY for a (future, gated) send. Caller must NOT persist/log
    the return value — use `link_renderer.redact_link` before any logging."""
    return link_renderer.branded_link(raw_token)
