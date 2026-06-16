"""Link rendering + redaction for subscription delivery (§16, SECURITY rule 1).

The **branded** customer-facing link is the only thing a customer should see:
    https://sub.unseen.click/s/<opaque-token>
The raw Hiddify subscription URL / proxy links (`hiddify://`, `vless://`, `ss://`, `hy2://`)
are **internal fallbacks** — never the main product link, never persisted, never logged.

Rules enforced here:
  - The branded link is assembled **in memory only** (at send time) and is NEVER persisted.
  - Only a **hash/handle** of the opaque token is stored (`branded_token_handle`).
  - `redact_link` turns any link into a safe label; `looks_like_raw_proxy_link` detects raw
    proxy/subscription URLs so callers can refuse to persist/log them.
"""
from __future__ import annotations

import hashlib
import re

BRANDED_HOST = "sub.unseen.click"
BRANDED_PATH = "/s/"

# Schemes that must never be persisted/logged as the main product link.
_RAW_SCHEMES = ("hiddify://", "vless://", "vmess://", "trojan://", "ss://", "ssr://",
                "hy2://", "hysteria2://", "tuic://", "wireguard://")

_BRANDED_RE = re.compile(r"^https://" + re.escape(BRANDED_HOST) + re.escape(BRANDED_PATH) + r"[^/?#\s]+$")


def looks_like_raw_proxy_link(value: str) -> bool:
    """True if `value` looks like a raw proxy/subscription link that must not be stored/logged."""
    if not value:
        return False
    v = value.strip().lower()
    if any(v.startswith(s) for s in _RAW_SCHEMES):
        return True
    # A raw Hiddify sub URL often contains an admin/user proxy path + /sub or a long token tail.
    if "/api/v2/" in v or "/all-configs" in v:
        return True
    return False


def branded_token_handle(raw_token: str) -> str:
    """SHA-256 handle of the opaque branded token. The raw token is NEVER stored — only this."""
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def branded_link(raw_token: str) -> str:
    """Assemble the branded customer-facing link IN MEMORY (send-time only; never persist/log)."""
    return f"https://{BRANDED_HOST}{BRANDED_PATH}{raw_token}"


def is_branded_link(value: str) -> bool:
    return bool(_BRANDED_RE.match((value or "").strip()))


def redact_link(value: str) -> str:
    """Return a safe, non-secret label for any link. Never reveals the token/path/host tail."""
    if not value:
        return "link:<absent>"
    v = value.strip()
    if is_branded_link(v):
        return f"branded:{BRANDED_HOST}/s/<redacted>"
    low = v.lower()
    for s in _RAW_SCHEMES:
        if low.startswith(s):
            return f"raw:{s.rstrip(':/')}:<redacted>"
    if low.startswith("https://") or low.startswith("http://"):
        return "url:<redacted>"
    return "link:<redacted>"
