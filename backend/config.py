"""Runtime config from the environment by handle — no hardcoded secrets/values.

Secrets (Hiddify API key, admin proxy path) are read from env var *handles* recorded on
the node row (`proxy_nodes.api_secret_handle`), never stored in the DB or source. A node's
public hostname/IP are data (DB), not secrets.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_DB_PATH = "/opt/unseen-proxy/data/unseenproxy.sqlite3"


def db_path() -> str:
    return os.environ.get("DB_PATH", DEFAULT_DB_PATH)


@dataclass(frozen=True)
class NodeApiConfig:
    """Connection config for one node's Hiddify API. Built from the node row + env handles."""
    node_code: str
    base_host: str                 # node-de.unseen.click  (public, not secret)
    admin_proxy_path: str          # secret URL segment (from env)
    api_key: str                   # admin UUID credential (from env)

    @property
    def admin_api_base(self) -> str:
        # https://<host>/<proxy_path>/api/v2/admin  — proxy_path is secret; never log this.
        return f"https://{self.base_host}/{self.admin_proxy_path}/api/v2/admin"

    def fingerprint(self) -> str:
        """Loggable, non-secret identifier."""
        return f"node={self.node_code} host={self.base_host} key=***{self.api_key[-0:] and ''}"


def load_node_api_config(node_code: str, base_host: str,
                         path_env: str, key_env: str) -> NodeApiConfig:
    """Resolve a node's secret proxy path + API key from env var handles.

    Raises KeyError if the handles aren't set — callers in dry-run mode should NOT call this.
    """
    proxy_path = os.environ[path_env]
    api_key = os.environ[key_env]
    return NodeApiConfig(node_code=node_code, base_host=base_host,
                         admin_proxy_path=proxy_path, api_key=api_key)


# Live-mutation latch (env half of the double gate; the other half is --live --confirm).
LIVE_ENV_LATCH = "UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED"


def live_latch_enabled() -> bool:
    return os.environ.get(LIVE_ENV_LATCH) == "1"


# ---- Phase 4C live-provisioning blockers ----------------------------------------------------
# Phase 4C is dry-run ONLY: live Hiddify provisioning is hard-disabled in code regardless of
# env/flags/node status. Flipping this to False is a future, separately-gated task.
PHASE4C_LIVE_PROVISION_DISABLED = True

# de1's leaked default-user/server keys mean it must be rebuilt before serving live traffic
# (docs/PHASE4_PRELIVE_DE1_TUNING.md → REBUILD_REQUIRED_BEFORE_LIVE). Until cleared, live is blocked.
LEAKED_KEY_REBUILD_PENDING = True


# ---- Phase 5 Telegram bot blockers ----------------------------------------------------------
# Phase 5 is dry-run ONLY: the bot never calls the Telegram API, never sends a message, and
# never starts polling/webhook. The adapter hard-refuses live sends regardless of env/flags.
PHASE5_LIVE_SEND_DISABLED = True

# Env var NAMES the bot reads (values live in .env on the Master only — never in git/source).
TELEGRAM_BOT_TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
# Primary admin-ids env name (per Phase 5 spec); falls back to the older template name.
ADMIN_TELEGRAM_IDS_ENV = "ADMIN_TELEGRAM_IDS"
ADMIN_TELEGRAM_IDS_ENV_FALLBACK = "TELEGRAM_ADMIN_IDS"
