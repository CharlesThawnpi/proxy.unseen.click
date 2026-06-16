"""Hiddify subscription output wrapper — normalize MOCKED output to a sanitized summary.

Phase 6 is dry-run: this accepts a **mocked** subscription-output dict (the shapes the verified
API returns — `all-configs`, `me`/subscription metadata, protocol configs) and returns a
**sanitized summary** (counts + booleans + protocol *engine names*). It NEVER logs or returns
the raw output, and never emits a raw subscription URL, proxy link, UUID, or QR payload.

Raw output exists only in memory in the caller/tests; this wrapper extracts non-secret facts
and discards the rest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .link_renderer import looks_like_raw_proxy_link

# Engine protocol names are catalogue facts (not secrets) — safe to surface.
_KNOWN_ENGINES = ("hysteria2", "shadowsocks", "vless", "vless-reality", "reality", "tuic", "wireguard")


@dataclass(frozen=True)
class SubscriptionOutputSummary:
    profiles_count: int                 # number of config entries seen
    protocols: List[str] = field(default_factory=list)   # engine names only (sanitized)
    has_subscription_url: bool = False  # a copyable branded/sub link is derivable
    has_deep_link: bool = False         # a Hiddify-app import/deep link is derivable
    note: str = "sanitized; raw output discarded"

    def as_dict(self) -> dict:
        return {"profiles_count": self.profiles_count, "protocols": list(self.protocols),
                "has_subscription_url": self.has_subscription_url,
                "has_deep_link": self.has_deep_link, "note": self.note}


def _engine_of(entry: Any) -> str:
    """Best-effort sanitized engine name from a config entry. Never returns a raw link/payload."""
    if isinstance(entry, dict):
        for k in ("protocol", "type", "engine", "engine_protocol"):
            v = entry.get(k)
            if isinstance(v, str):
                low = v.strip().lower()
                for e in _KNOWN_ENGINES:
                    if e in low:
                        return "vless-reality" if e in ("vless", "reality", "vless-reality") else e
    elif isinstance(entry, str):
        low = entry.strip().lower()
        for e in _KNOWN_ENGINES:
            if low.startswith(e) or f"{e}://" in low:
                return "vless-reality" if e in ("vless", "reality", "vless-reality") else e
    return "unknown"


def normalize(mocked_output: Dict[str, Any]) -> SubscriptionOutputSummary:
    """Normalize a mocked Hiddify subscription output dict to a sanitized summary.

    Recognized shapes (any subset):
      - {"all_configs": [ {protocol/type:...}, "vless://..." , ... ]}
      - {"subscription_url": "<raw>"} / {"deep_link": "hiddify://import/..."}
      - {"me": {...}} / {"protocols": [...]}
    The raw values are inspected in memory then DROPPED; only counts/booleans/engine names return.
    """
    if not isinstance(mocked_output, dict):
        return SubscriptionOutputSummary(profiles_count=0)

    configs = mocked_output.get("all_configs") or mocked_output.get("protocols") or []
    if not isinstance(configs, list):
        configs = []

    protocols: List[str] = []
    for entry in configs:
        eng = _engine_of(entry)
        if eng != "unknown" and eng not in protocols:
            protocols.append(eng)

    # A copyable subscription link / deep link is "derivable" if the mock provides one — but we
    # only record the BOOLEAN, never the raw value.
    has_sub = bool(mocked_output.get("subscription_url")) or any(
        looks_like_raw_proxy_link(c) for c in configs if isinstance(c, str))
    deep = mocked_output.get("deep_link") or mocked_output.get("hiddify_deep_link")
    has_deep = bool(deep) or any(
        isinstance(c, str) and c.strip().lower().startswith("hiddify://") for c in configs)

    return SubscriptionOutputSummary(
        profiles_count=len(configs), protocols=protocols,
        has_subscription_url=bool(has_sub), has_deep_link=bool(has_deep))
