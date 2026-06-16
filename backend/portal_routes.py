"""Render-only routes for the customer portal foundation.

No socket, server, framework, or live auth is created here. A future HTTP layer can wrap
`render_route`, but Phase 8 only returns safe response objects for local dry-run rendering.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from urllib.parse import unquote, urlparse

from . import branded_link_resolver, portal_sessions, portal_templates as tpl, portal_viewmodels as vm


@dataclass(frozen=True)
class PortalResponse:
    status_code: int
    body: str
    content_type: str = "text/html; charset=utf-8"


_SUB_RE = re.compile(r"^/subscriptions/([0-9]+)$")
_BRANDED_RE = re.compile(r"^/s/[^/?#\s]+$")


def _customer_code(conn: sqlite3.Connection, customer_id: int | None) -> str:
    if customer_id is None:
        return "UP-PENDING"
    row = conn.execute("SELECT public_customer_code FROM customers WHERE id=?", (customer_id,)).fetchone()
    return row[0] if row and row[0] else "UP-PENDING"


def render_route(
    conn: sqlite3.Connection,
    path: str,
    *,
    customer_id: int | None = None,
    session_context: portal_sessions.PortalSessionContext | None = None,
) -> PortalResponse:
    parsed = urlparse(path or "/")
    route = parsed.path or "/"
    if route == "/":
        return PortalResponse(200, tpl.render_home())
    if route == "/plans":
        return PortalResponse(200, tpl.render_plans(vm.plans(conn)))
    if route == "/customer/status":
        if session_context is None:
            return PortalResponse(401, tpl.render_auth_required())
        cid = session_context.customer_id
        data = vm.customer_dashboard(conn, cid) if cid is not None else None
        if not data:
            return PortalResponse(404, tpl.render_state_page("not-found"))
        return PortalResponse(200, tpl.render_dashboard(data))
    match = _SUB_RE.match(route)
    if match:
        if session_context is None:
            return PortalResponse(401, tpl.render_auth_required())
        data = vm.subscription_detail(conn, int(match.group(1)))
        if not data or data.get("customer_id") != session_context.customer_id:
            return PortalResponse(404, tpl.render_state_page("not-found"))
        return PortalResponse(200, tpl.render_subscription(data))
    if _BRANDED_RE.match(route):
        raw_token = unquote(route.split("/s/", 1)[1])
        if raw_token == "<opaque-token>":
            return PortalResponse(200, tpl.render_branded_placeholder())
        resolved = branded_link_resolver.resolve(conn, raw_token)
        if resolved.valid:
            body = tpl.render_branded_resolved({
                "public_customer_code": _customer_code(conn, resolved.customer_id),
                "subscription_code": f"SUB-{int(resolved.subscription_id):06d}" if resolved.subscription_id else "SUB-PENDING",
            })
            return PortalResponse(200, body)
        if resolved.status in {"expired", "revoked"}:
            return PortalResponse(410, tpl.render_state_page("expired"))
        return PortalResponse(404, tpl.render_state_page("not-found"))
    if route == "/help":
        return PortalResponse(200, tpl.render_help())
    if route == "/unavailable":
        return PortalResponse(503, tpl.render_state_page("unavailable"))
    if route == "/degraded":
        return PortalResponse(200, tpl.render_state_page("degraded"))
    if route == "/expired":
        return PortalResponse(410, tpl.render_state_page("expired"))
    if route == "/not-found":
        return PortalResponse(404, tpl.render_state_page("not-found"))
    return PortalResponse(404, tpl.render_state_page("not-found"))
