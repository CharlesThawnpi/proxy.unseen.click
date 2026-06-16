"""Bot runtime context — env-driven admin identity, no hardcoded IDs (§9, §31).

Admin Telegram ids come from the env var `ADMIN_TELEGRAM_IDS` (comma-separated integers),
falling back to the older template name `TELEGRAM_ADMIN_IDS`. Parsing is defensive (blank /
non-integer entries are ignored). The full admin list is **never** logged or rendered — only a
sanitized count is exposed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import FrozenSet, Optional

from . import config

DEFAULT_LANGUAGE = "my"  # Burmese-primary


def parse_admin_ids(raw: Optional[str]) -> FrozenSet[int]:
    """Parse a comma-separated admin-id string into a set of ints. Bad entries are skipped."""
    if not raw:
        return frozenset()
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue  # ignore non-integer noise; never raise on config shape
    return frozenset(out)


def _admin_ids_from_env() -> FrozenSet[int]:
    raw = os.environ.get(config.ADMIN_TELEGRAM_IDS_ENV)
    if raw is None:
        raw = os.environ.get(config.ADMIN_TELEGRAM_IDS_ENV_FALLBACK)
    # A placeholder template value must never be treated as a real admin id.
    if raw is None or "__PLACEHOLDER__" in raw or raw.strip() in ("", "replace_me"):
        return frozenset()
    return parse_admin_ids(raw)


@dataclass(frozen=True)
class BotContext:
    admin_ids: FrozenSet[int]
    language: str = DEFAULT_LANGUAGE

    @classmethod
    def from_env(cls) -> "BotContext":
        return cls(admin_ids=_admin_ids_from_env())

    def is_admin(self, telegram_user_id) -> bool:
        try:
            return int(telegram_user_id) in self.admin_ids
        except (TypeError, ValueError):
            return False

    @property
    def admin_count(self) -> int:
        """Sanitized — count only; the actual ids are never exposed."""
        return len(self.admin_ids)

    def token_present(self) -> bool:
        """Whether the bot token env var is set — the VALUE is never read into a field here."""
        val = os.environ.get(config.TELEGRAM_BOT_TOKEN_ENV)
        return bool(val) and "__PLACEHOLDER__" not in val and val.strip() not in ("", "replace_me")
