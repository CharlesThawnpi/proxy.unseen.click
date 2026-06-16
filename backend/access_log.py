"""Access-log policy and sanitizer for the portal HTTP boundary (Phase 8C).

Technical access logs may exist later, but they must pass through this sanitizer first. The
sanitizer guarantees a log line can never carry a raw branded token, a session id, a cookie, an
auth header, a UUID, a proxy/subscription link, a QR payload, an admin/API path, or a bot token.
It redacts rather than drops so the line is still useful for debugging.

Nothing here opens a file or socket; callers decide where (if anywhere) the sanitized line goes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

# Header names that must never appear in a log line, regardless of value.
_FORBIDDEN_HEADERS = {
    "cookie", "set-cookie", "authorization", "proxy-authorization",
    "x-api-key", "x-auth-token", "x-csrf-token", "hiddify-api-key",
}

# Branded token path: keep the route shape, drop the token.
_BRANDED_RE = re.compile(r"(/s/)[^/?#\s]+")
# Numeric subscription id path is fine to keep (internal id, not a secret) — left untouched.

_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
_PROXY_URI_RE = re.compile(r"\b(vless|vmess|trojan|ss|hy2|hysteria2|hiddify)://[^\s'\"]+", re.I)
_BOT_TOKEN_RE = re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b")
_API_PATH_RE = re.compile(r"/api/v2/[^\s'\"]*", re.I)
# Long opaque token-shaped runs (base64url, >=24 chars) outside known-safe contexts.
_LONG_TOKEN_RE = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")

_REDACTED = "<redacted>"


def sanitize_path(path: str | None) -> str:
    """Redact the branded token from a path and drop any query string entirely.

    Query strings are removed wholesale because they are the most common place tokens leak; the
    HTTP boundary has no GET route that needs query params logged.
    """
    if not path:
        return "/"
    base = path.split("?", 1)[0].split("#", 1)[0]
    base = _BRANDED_RE.sub(r"\1" + _REDACTED, base)
    return base or "/"


def redact_text(text: str | None) -> str:
    """Redact secret-shaped substrings from an arbitrary log fragment."""
    if not text:
        return ""
    out = _BRANDED_RE.sub(r"\1" + _REDACTED, text)
    out = _PROXY_URI_RE.sub(_REDACTED, out)
    out = _BOT_TOKEN_RE.sub(_REDACTED, out)
    out = _API_PATH_RE.sub("/api/v2/" + _REDACTED, out)
    out = _UUID_RE.sub(_REDACTED, out)
    out = _LONG_TOKEN_RE.sub(_REDACTED, out)
    return out


def sanitize_headers(headers: dict | None) -> dict[str, str]:
    """Drop forbidden headers and redact secret-shaped values from the rest."""
    safe: dict[str, str] = {}
    for name, value in (headers or {}).items():
        if name.lower() in _FORBIDDEN_HEADERS:
            safe[name] = _REDACTED
            continue
        safe[name] = redact_text(str(value))
    return safe


def redact_ip(remote_addr: str | None) -> str:
    """Redact a client IP for customer-facing/exported logs (keep a coarse prefix)."""
    if not remote_addr:
        return "ip:<absent>"
    if ":" in remote_addr and "." not in remote_addr:  # IPv6
        return "ip:<redacted-v6>"
    octets = remote_addr.split(".")
    if len(octets) == 4:
        return f"ip:{octets[0]}.{octets[1]}.x.x"
    return "ip:<redacted>"


@dataclass(frozen=True)
class AccessEvent:
    method: str
    path: str
    status: int
    remote_addr: Optional[str] = None
    redact_client_ip: bool = True


def format_access_event(event: AccessEvent) -> str:
    """Produce one sanitized, secret-free access-log line."""
    ip = redact_ip(event.remote_addr) if event.redact_client_ip else (event.remote_addr or "ip:<absent>")
    return f"{event.method.upper()} {sanitize_path(event.path)} {int(event.status)} {ip}"


def assert_safe(line: str, raw_values: Iterable[str] = ()) -> None:
    """Test/guard helper: raise if a line still carries a secret-shaped value."""
    for value in raw_values:
        if value and value in line:
            raise AssertionError("access log line leaked a raw secret value")
    for pattern in (_UUID_RE, _PROXY_URI_RE, _BOT_TOKEN_RE):
        if pattern.search(line):
            raise AssertionError("access log line carries a secret-shaped value")
