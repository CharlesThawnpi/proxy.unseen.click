"""Render-only routes for the customer portal foundation.

No socket, server, framework, or live auth is created here. A future HTTP layer can wrap
`render_route`, but Phase 8 only returns safe response objects for local dry-run rendering.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from urllib.parse import urlparse

from . import portal_templates as tpl, portal_viewmodels as vm


@dataclass(frozen=True)
class PortalResponse:
    status_code: int
    body: str
    content_type: str = "text/html; charset=utf-8"


_SUB_RE = re.compile(r"^/subscriptions/([0-9]+)$")
_BRANDED_RE = re.compile(r"^/s/[^/?#\s]+$")


def render_route(conn: sqlite3.Connection, path: str, *, customer_id: int | None = None) -> PortalResponse:
    parsed = urlparse(path or "/")
    route = parsed.path or "/"
    if route == "/":
        return PortalResponse(200, tpl.render_home())
    if route == "/plans":
        return PortalResponse(200, tpl.render_plans(vm.plans(conn)))
    if route == "/customer/status":
        cid = customer_id or vm.first_customer_id(conn)
        data = vm.customer_dashboard(conn, cid) if cid is not None else None
        if not data:
            return PortalResponse(404, tpl.render_state_page("not-found"))
        return PortalResponse(200, tpl.render_dashboard(data))
    match = _SUB_RE.match(route)
    if match:
        data = vm.subscription_detail(conn, int(match.group(1)))
        if not data:
            return PortalResponse(404, tpl.render_state_page("not-found"))
        return PortalResponse(200, tpl.render_subscription(data))
    if _BRANDED_RE.match(route):
        return PortalResponse(200, tpl.render_branded_placeholder())
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
