"""Portal HTTP adapter / deployment boundary (Phase 8C).

A framework-free request/response abstraction plus a router that wraps the existing render-only
`portal_routes.render_route`. It exists so a future web server (or the loopback-only preview CLI)
has a single, audited place to translate HTTP into safe portal responses.

What this module does NOT do, by design:
  * does not open a socket, bind a port, or start a server;
  * does not configure nginx/TLS;
  * does not perform live auth against production;
  * does not fetch from Hiddify or send Telegram.

Route allowlist (everything else -> 404 not-found):
  GET /            GET /plans        GET /help            (public)
  GET /dashboard   GET /subscription                      (private — session required)
  GET /s/<opaque-token>                                   (branded resolver, rate-limited)
  GET /expired     GET /not-found                         (state pages)
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import parse_qs, urlsplit

from . import (
    access_log,
    portal_cookies,
    portal_middleware,
    portal_routes,
    portal_sessions,
    rate_limit,
)

# Public routes need no session; private routes require a verified session context.
_PUBLIC_ROUTES = {"/", "/plans", "/help", "/expired", "/not-found"}
_PRIVATE_ROUTES = {"/dashboard", "/subscription"}
_ALLOWED_METHODS = {"GET", "HEAD"}


@dataclass(frozen=True)
class HttpRequest:
    method: str
    path: str
    query: dict[str, list[str]] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    remote_addr: Optional[str] = None

    @classmethod
    def build(
        cls,
        method: str,
        target: str,
        *,
        headers: dict[str, str] | None = None,
        body: bytes | str = b"",
        remote_addr: str | None = None,
    ) -> "HttpRequest":
        split = urlsplit(target or "/")
        hdrs = {str(k): str(v) for k, v in (headers or {}).items()}
        cookie_header = next((v for k, v in hdrs.items() if k.lower() == "cookie"), None)
        body_bytes = body.encode("utf-8") if isinstance(body, str) else (body or b"")
        return cls(
            method=(method or "GET").upper(),
            path=split.path or "/",
            query=parse_qs(split.query),
            headers=hdrs,
            cookies=portal_cookies.parse_cookie_header(cookie_header),
            body=body_bytes,
            remote_addr=remote_addr,
        )


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    body: str
    headers: dict[str, str] = field(default_factory=dict)
    content_type: str = "text/html; charset=utf-8"

    def header_items(self) -> list[tuple[str, str]]:
        items = [("Content-Type", self.content_type)]
        items.extend(self.headers.items())
        return items


def _first_subscription_id(conn: sqlite3.Connection, customer_id: int) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM subscriptions WHERE customer_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
        (customer_id,),
    ).fetchone()
    return int(row[0]) if row else None


class PortalHttpApp:
    """Stateful router: holds the rate limiter and access-log policy across requests."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        rate_limiter: rate_limit.RateLimiter | None = None,
        redact_client_ip: bool = True,
    ):
        self.conn = conn
        self.rate_limiter = rate_limiter or rate_limit.branded_token_limiter()
        self.redact_client_ip = redact_client_ip

    # -- helpers ------------------------------------------------------------
    def _session_context(self, request: HttpRequest) -> Optional[portal_sessions.PortalSessionContext]:
        return portal_middleware.session_context_from_cookies(self.conn, request.cookies)

    def _finalize(self, inner: portal_routes.PortalResponse, *, private: bool,
                  extra_headers: dict[str, str] | None = None) -> HttpResponse:
        headers = portal_middleware.security_headers(private=private)
        if extra_headers:
            headers.update(extra_headers)
        return HttpResponse(
            status_code=inner.status_code,
            body=inner.body,
            headers=headers,
            content_type=inner.content_type,
        )

    # -- routing ------------------------------------------------------------
    def handle(self, request: HttpRequest) -> HttpResponse:
        if request.method not in _ALLOWED_METHODS:
            inner = portal_routes.render_route(self.conn, "/not-found")
            return HttpResponse(405, inner.body, portal_middleware.security_headers(),
                                inner.content_type)

        path = request.path or "/"

        # Branded resolver — rate-limited, token never logged.
        if path.startswith("/s/") and "/" not in path[3:]:
            raw_token = path[3:]
            decision = self.rate_limiter.check(rate_limit.safe_key(raw_token, scope="branded"))
            if not decision.allowed:
                inner = portal_routes.render_route(self.conn, "/not-found")
                headers = portal_middleware.security_headers(private=True)
                headers["Retry-After"] = str(decision.retry_after)
                return HttpResponse(429, inner.body, headers, inner.content_type)
            inner = portal_routes.render_route(self.conn, path)
            return self._finalize(inner, private=True)

        if path in _PUBLIC_ROUTES:
            inner = portal_routes.render_route(self.conn, path)
            return self._finalize(inner, private=False)

        if path in _PRIVATE_ROUTES:
            context = self._session_context(request)
            if context is None or context.customer_id is None:
                # No verified session -> render_route returns the 401 auth-required page.
                inner = portal_routes.render_route(self.conn, "/customer/status")
                return self._finalize(inner, private=True)
            if path == "/dashboard":
                inner = portal_routes.render_route(self.conn, "/customer/status", session_context=context)
                return self._finalize(inner, private=True)
            # /subscription -> the customer's most recent subscription detail.
            sub_id = _first_subscription_id(self.conn, context.customer_id)
            if sub_id is None:
                inner = portal_routes.render_route(self.conn, "/not-found")
                return self._finalize(inner, private=True)
            inner = portal_routes.render_route(self.conn, f"/subscriptions/{sub_id}", session_context=context)
            return self._finalize(inner, private=True)

        # Unknown route — never echo it back; render the safe not-found page.
        inner = portal_routes.render_route(self.conn, "/not-found")
        return self._finalize(inner, private=False)

    # -- observability ------------------------------------------------------
    def access_event(self, request: HttpRequest, response: HttpResponse) -> access_log.AccessEvent:
        return access_log.AccessEvent(
            method=request.method,
            path=request.path,
            status=response.status_code,
            remote_addr=request.remote_addr,
            redact_client_ip=self.redact_client_ip,
        )

    def access_line(self, request: HttpRequest, response: HttpResponse) -> str:
        return access_log.format_access_event(self.access_event(request, response))


def dispatch(conn: sqlite3.Connection, request: HttpRequest, **kwargs) -> HttpResponse:
    """One-off convenience: build an app and handle a single request."""
    return PortalHttpApp(conn, **kwargs).handle(request)
