"""Hiddify Manager API v2 client (verified live on de1, Hiddify v12.3.3 / API v2.2.0).

Contract (docs/HIDDIFY_API_CONTRACT.md):
  base   : https://<host>/<admin_proxy_path>/api/v2/admin
  auth   : header  Hiddify-API-Key: <admin-UUID>
  users  : GET|POST  /user/         ;  GET|PATCH|DELETE  /user/{uuid}/
  configs: GET /all-configs/?uuid=<uuid>   (subscription/config output)
  units  : usage_limit_GB / current_usage_GB are GB → we convert from UNSEEN GiB here.

Safety:
  - secrets (proxy path, API key, UUIDs) are NEVER logged; only node fingerprints/status.
  - raw subscription/proxy/config payloads are returned but never logged/printed by this module.
  - stdlib urllib only (no third-party deps on the control plane); timeouts + bounded retries.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from ..config import NodeApiConfig
from ..units import gib_to_gb


class HiddifyError(Exception):
    """Structured client error (status optional)."""

    def __init__(self, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.status = status


@dataclass
class HiddifyResult:
    ok: bool
    status: int
    data: Any = None
    error: Optional[str] = None


class HiddifyClient:
    """Thin wrapper over the verified API v2 admin endpoints.

    Pass a NodeApiConfig (built from env handles). `session` is injectable for tests so
    no network call happens unless explicitly wired to the real urllib opener.
    """

    def __init__(self, node: NodeApiConfig, timeout: float = 10.0, retries: int = 2,
                 opener: Optional[Any] = None):
        self._node = node
        self._timeout = timeout
        self._retries = max(0, retries)
        self._opener = opener  # callable(method, url, headers, body) -> (status, bytes); for tests

    # ---- path builders (relative; tests assert these without secrets) ----
    @staticmethod
    def user_list_path() -> str:
        return "/user/"

    @staticmethod
    def user_path(uuid: str) -> str:
        return f"/user/{uuid}/"

    @staticmethod
    def all_configs_path(uuid: str) -> str:
        return "/all-configs/?uuid=" + urllib.parse.quote(uuid, safe="")

    def _url(self, rel: str) -> str:
        return self._node.admin_api_base + rel

    def _headers(self) -> dict:
        return {"Hiddify-API-Key": self._node.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "UnseenProxy-Orchestrator/1.0"}

    def _request(self, method: str, rel: str, payload: Optional[dict] = None) -> HiddifyResult:
        url = self._url(rel)
        body = json.dumps(payload).encode() if payload is not None else None
        headers = self._headers()
        last_err = None
        for attempt in range(self._retries + 1):
            try:
                if self._opener is not None:
                    status, raw = self._opener(method, url, headers, body)
                else:  # pragma: no cover - real network path (not exercised in tests)
                    req = urllib.request.Request(url, data=body, headers=headers, method=method)
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        status, raw = resp.status, resp.read()
                data = json.loads(raw) if raw else None
                if 200 <= status < 300:
                    return HiddifyResult(ok=True, status=status, data=data)
                return HiddifyResult(ok=False, status=status,
                                     error=f"HTTP {status}")  # body intentionally not surfaced raw
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                last_err = e
                if attempt < self._retries:
                    time.sleep(0.5 * (attempt + 1))
        # sanitized error — never include url (it contains the secret proxy path)
        return HiddifyResult(ok=False, status=0,
                             error=f"request failed for node {self._node.node_code}: {type(last_err).__name__}")

    # ---- verified endpoints ----
    def list_users(self) -> HiddifyResult:
        return self._request("GET", self.user_list_path())

    def get_user(self, uuid: str) -> HiddifyResult:
        return self._request("GET", self.user_path(uuid))

    def create_user(self, name: str, data_limit_gib: float, package_days: int,
                    comment: str = "", enable: bool = True, mode: str = "no_reset") -> HiddifyResult:
        # Convert UNSEEN GiB -> Hiddify GB at the boundary (deliberate).
        payload = {"name": name,
                   "usage_limit_GB": gib_to_gb(data_limit_gib),
                   "package_days": int(package_days),
                   "comment": comment, "enable": bool(enable), "mode": mode}
        return self._request("POST", self.user_list_path(), payload)

    def patch_user(self, uuid: str, **fields: Any) -> HiddifyResult:
        if "data_limit_gib" in fields:
            fields["usage_limit_GB"] = gib_to_gb(fields.pop("data_limit_gib"))
        return self._request("PATCH", self.user_path(uuid), fields)

    def disable_user(self, uuid: str) -> HiddifyResult:
        """Prefer disable (reversible) over delete."""
        return self._request("PATCH", self.user_path(uuid), {"enable": False})

    def delete_user(self, uuid: str) -> HiddifyResult:
        return self._request("DELETE", self.user_path(uuid))

    def all_configs(self, uuid: str) -> HiddifyResult:
        """Subscription/config output for a user. Caller must NOT log the payload."""
        return self._request("GET", self.all_configs_path(uuid))
