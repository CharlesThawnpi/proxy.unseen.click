"""Probe error/result sanitization (§31 rule 1).

A raw probe error can contain a hostname, URL, IP, or path. We NEVER store/log those — only a
**reason code** from a fixed vocabulary. `sanitize_error` maps any exception/text to a code; it
strips anything URL/host-shaped defensively. Reason codes are sanitized constants (see alerting).
"""
from __future__ import annotations

import socket

# Sanitized reason codes (mirrored in alerting; kept here for probe-time use).
PROBE_TIMEOUT = "probe_timeout"
PROBE_ERROR_SANITIZED = "probe_error_sanitized"
UNKNOWN = "unknown"


def sanitize_error(exc: BaseException) -> str:
    """Map a probe exception to a sanitized reason code — never the raw message (which may carry a
    host/URL/IP)."""
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return PROBE_TIMEOUT
    # Any other connection/OS error → generic sanitized code; the raw text is discarded.
    return PROBE_ERROR_SANITIZED


def safe_int_pct(value) -> int:
    """Clamp a percentage to 0..100 int, or -1 if not a usable number (treated as unknown)."""
    try:
        v = int(round(float(value)))
    except (TypeError, ValueError):
        return -1
    return max(0, min(100, v))
