"""Portal app boundary for Phase 8 dry-run rendering.

This module deliberately does not start a web server and does not implement real auth. It exposes
a small render API that CLIs/tests can call against temp DB/sample data.
"""
from __future__ import annotations

import sqlite3

from . import portal_routes


def render(conn: sqlite3.Connection, path: str, *, customer_id: int | None = None) -> portal_routes.PortalResponse:
    return portal_routes.render_route(conn, path, customer_id=customer_id)


__all__ = ["render", "portal_routes"]

