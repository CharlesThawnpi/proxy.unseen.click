"""Runtime gates for live Telegram transport — centralized, fail-closed (§ROLLBACK double-gate).

A live action requires BOTH halves of a double gate:
  - live send    : env `ALLOW_LIVE_BOT_SENDS=1`   AND CLI flags `--live-send --confirm`
  - live polling : env `ALLOW_LIVE_BOT_POLLING=1`  AND CLI flags `--live-poll --confirm`

Anything else (env unset / "0" / "true" / missing flags) → **dry-run, fail-closed**. The check
never raises on bad config; it returns a `GateDecision(allowed=False, blockers=[...])` with
sanitized reasons (no secrets) so callers can log why a live action was refused.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from . import config


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    blockers: List[str] = field(default_factory=list)


def _env_latch_on(env_name: str) -> bool:
    # Strict: only the exact string "1" enables the env half. Everything else is off.
    return os.environ.get(env_name) == "1"


def live_send_gate(live_send: bool = False, confirm: bool = False) -> GateDecision:
    """Decide whether a LIVE Telegram send is permitted. Fail-closed."""
    blockers: List[str] = []
    if not _env_latch_on(config.ALLOW_LIVE_BOT_SENDS_ENV):
        blockers.append(f"env_{config.ALLOW_LIVE_BOT_SENDS_ENV}_not_1")
    if not live_send:
        blockers.append("flag_--live-send_missing")
    if not confirm:
        blockers.append("flag_--confirm_missing")
    return GateDecision(allowed=not blockers, blockers=blockers)


def live_poll_gate(live_poll: bool = False, confirm: bool = False) -> GateDecision:
    """Decide whether LIVE Telegram polling is permitted. Fail-closed."""
    blockers: List[str] = []
    if not _env_latch_on(config.ALLOW_LIVE_BOT_POLLING_ENV):
        blockers.append(f"env_{config.ALLOW_LIVE_BOT_POLLING_ENV}_not_1")
    if not live_poll:
        blockers.append("flag_--live-poll_missing")
    if not confirm:
        blockers.append("flag_--confirm_missing")
    return GateDecision(allowed=not blockers, blockers=blockers)
