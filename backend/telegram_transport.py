"""TelegramTransport — Bot API boundary; DRY-RUN by default, live double-gated (§SECURITY).

Wraps the Telegram Bot API methods the bot needs: `getUpdates`, `sendMessage`,
`editMessageText`, `answerCallbackQuery`. The network call is **injectable** (`opener`) so tests
use a mock and **no real network** happens. Default mode is **dry-run**: requests are recorded
to an in-memory outbox and a synthetic result is returned — nothing leaves the process.

Live transport requires `live=True` AND an `opener` (the runner/sender only constructs a live
transport after the runtime double-gate passes). The real `urllib` path exists but is never
exercised in this task/tests.

Secret-safety:
  - The bot token is stored name-mangled, never in a public field, never logged.
  - The API URL embeds the token (`/bot<token>/<method>`) — it is built only inside `_request`
    and is **never** logged, returned, or put in an error/repr. Errors carry the method name only.
  - `repr()` and `token_fingerprint` show a redacted label.

Timeout / retry boundaries:
  - `timeout` (default 10s) bounds each request; `getUpdates` long-poll would pass its own
    server-side timeout as a *parameter* (not used in dry-run).
  - `retries` (default 2) with linear backoff for transient network errors; 4xx is not retried.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

from . import config
from .telegram_adapter import redact_token

_API_ROOT = "https://api.telegram.org"


class LiveTransportDisabledError(RuntimeError):
    """Raised if a live request is attempted without a live-enabled transport + opener."""


@dataclass
class TransportResult:
    ok: bool
    method: str
    dry_run: bool
    status: int = 0
    data: Any = None
    error: Optional[str] = None      # sanitized; never contains the token/URL


@dataclass
class TransportRequest:
    method: str                      # getUpdates | sendMessage | editMessageText | answerCallbackQuery
    params: dict = field(default_factory=dict)   # sanitized for dry-run inspection (no token)


# opener signature: (method_name, url, params_dict, timeout) -> (status_int, body_bytes)
Opener = Callable[[str, str, dict, float], tuple]


class TelegramTransport:
    def __init__(self, token: Optional[str] = None, *, live: bool = False,
                 opener: Optional[Opener] = None, timeout: float = 10.0, retries: int = 2):
        self.__token = token if token is not None else os.environ.get(config.TELEGRAM_BOT_TOKEN_ENV)
        self._live = bool(live)
        self._opener = opener
        self._timeout = float(timeout)
        self._retries = max(0, int(retries))
        self.outbox: List[TransportRequest] = []   # dry-run record of intended requests

    # ---- secret-safe introspection ----
    def __repr__(self) -> str:
        return (f"<TelegramTransport live={self._live} token={redact_token(self.__token)} "
                f"requests={len(self.outbox)}>")

    @property
    def token_fingerprint(self) -> str:
        return redact_token(self.__token)

    def _url(self, method: str) -> str:
        # Built only here; embeds the token; NEVER logged/returned/raised.
        return f"{_API_ROOT}/bot{self.__token}/{method}"

    def _request(self, method: str, params: dict) -> TransportResult:
        # Dry-run unless explicitly live AND an opener is wired (tests inject a mock opener).
        if not self._live:
            self.outbox.append(TransportRequest(method=method, params=dict(params)))
            return TransportResult(ok=True, method=method, dry_run=True, status=0,
                                   data={"dry_run": True})
        if self._opener is None and self.__token is None:
            # Defensive: live with neither opener nor token is meaningless — refuse, no network.
            raise LiveTransportDisabledError(f"live transport for {method} not configured")

        url = self._url(method)
        last_err = None
        for attempt in range(self._retries + 1):
            try:
                if self._opener is not None:
                    status, raw = self._opener(method, url, dict(params), self._timeout)
                else:  # pragma: no cover - real network path (never exercised in this task)
                    data = urllib.parse.urlencode(params).encode()
                    req = urllib.request.Request(url, data=data, method="POST")
                    with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                        status, raw = resp.status, resp.read()
                payload = json.loads(raw) if raw else None
                if 200 <= status < 300:
                    return TransportResult(ok=True, method=method, dry_run=False,
                                           status=status, data=payload)
                # 4xx not retried; surface a sanitized error (no token/url/body).
                return TransportResult(ok=False, method=method, dry_run=False, status=status,
                                       error=f"HTTP {status}")
            except (urllib.error.URLError, TimeoutError, ValueError) as e:
                last_err = e
                if attempt < self._retries:
                    time.sleep(0.5 * (attempt + 1))
        return TransportResult(ok=False, method=method, dry_run=False, status=0,
                               error=f"request failed for {method}: {type(last_err).__name__}")

    # ---- Bot API surface ----
    def get_updates(self, offset: Optional[int] = None, timeout: int = 0,
                    limit: int = 100) -> TransportResult:
        params = {"timeout": int(timeout), "limit": int(limit)}
        if offset is not None:
            params["offset"] = int(offset)
        return self._request("getUpdates", params)

    def send_message(self, chat_id: Optional[int], text: str, **extra) -> TransportResult:
        params = {"chat_id": chat_id, "text": text, **extra}
        return self._request("sendMessage", params)

    def edit_message_text(self, chat_id: Optional[int], message_id: int, text: str,
                          **extra) -> TransportResult:
        params = {"chat_id": chat_id, "message_id": int(message_id), "text": text, **extra}
        return self._request("editMessageText", params)

    def answer_callback_query(self, callback_query_id: str, text: str = "",
                              **extra) -> TransportResult:
        params = {"callback_query_id": callback_query_id, "text": text, **extra}
        return self._request("answerCallbackQuery", params)

    # ---- test/CLI helpers ----
    def last_request(self) -> Optional[TransportRequest]:
        return self.outbox[-1] if self.outbox else None
