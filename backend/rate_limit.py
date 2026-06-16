"""In-memory rate-limit foundation for the portal HTTP boundary (Phase 8C).

A small fixed-window counter with a cooldown/block window. It is deliberately process-local and
dependency-free: no daemon, no Redis, no DB. It protects the `/s/<opaque-token>` resolver and
future login/session endpoints from brute-force/enumeration of branded tokens.

Policy: fail closed for suspicious repeated attempts — once a key exceeds the threshold inside the
window it is blocked for `block_seconds`, and the block timer refreshes on every further attempt so
a persistent attacker stays blocked. Keys passed in MUST already be sanitized (e.g. a token
fingerprint), never a raw token or path; this module never logs the key.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from . import portal_tokens, timezone as _tz


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    reason: str
    remaining: int
    retry_after: int = 0


@dataclass
class _Window:
    count: int = 0
    window_start: float = 0.0
    blocked_until: float = 0.0


def safe_key(raw_token: str | None, *, scope: str = "branded") -> str:
    """Derive a non-secret rate-limit key from a raw token. Safe to keep in memory/logs."""
    return f"{scope}:{portal_tokens.fingerprint(raw_token or '')}"


class RateLimiter:
    """Fixed-window limiter with a refreshing block window. Not thread-safe by design (single
    request loop); a future multi-worker deployment will need a shared store."""

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 60, block_seconds: int = 300):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.max_attempts = int(max_attempts)
        self.window_seconds = int(window_seconds)
        self.block_seconds = int(block_seconds)
        self._state: dict[str, _Window] = {}

    @staticmethod
    def _epoch(now: datetime | None) -> float:
        base = _tz.to_mmt(now) if now is not None else _tz.now_mmt()
        return base.timestamp()

    def check(self, key: str, *, now: datetime | None = None) -> RateLimitDecision:
        """Record an attempt for `key` and decide whether it is allowed.

        Fails closed: the attempt that crosses the threshold is itself blocked.
        """
        ts = self._epoch(now)
        win = self._state.get(key)
        if win is None:
            win = _Window(window_start=ts)
            self._state[key] = win

        # Still inside an active block: refresh the timer and stay blocked.
        if win.blocked_until > ts:
            win.blocked_until = ts + self.block_seconds
            return RateLimitDecision(False, "blocked", remaining=0, retry_after=int(win.blocked_until - ts))

        # Roll the window if it has elapsed.
        if ts - win.window_start >= self.window_seconds:
            win.window_start = ts
            win.count = 0
            win.blocked_until = 0.0

        win.count += 1
        if win.count > self.max_attempts:
            win.blocked_until = ts + self.block_seconds
            return RateLimitDecision(False, "rate_limited", remaining=0, retry_after=self.block_seconds)
        return RateLimitDecision(True, "ok", remaining=max(0, self.max_attempts - win.count))

    def reset(self, key: str | None = None) -> None:
        if key is None:
            self._state.clear()
        else:
            self._state.pop(key, None)


def branded_token_limiter() -> RateLimiter:
    """Default policy for the `/s/<opaque-token>` resolver and branded-token attempts."""
    return RateLimiter(max_attempts=5, window_seconds=60, block_seconds=300)
