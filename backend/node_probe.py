"""Node probe abstraction + sanitized ProbeResult (§6.2, §30A; read-only, no secrets).

A `Prober` returns a **sanitized** `ProbeResult` for a node row — only safe health signals, never
a raw error string, URL, admin path, API key, UUID, or proxy payload. Two probers ship:

  - `MockProber` — synthetic results from a dict; the DEFAULT for tests and CLI dry-run (no network).
  - `PublicTcpProber` — real, read-only **public** TCP connects to 22/80/443 (no payload sent) and
    an optional HTTP HEAD to the public root `https://<host>/` for a status code. It NEVER probes
    the secret admin path, never sends a proxy payload, and never uses a third-party tester. Used
    ONLY when a CLI explicitly opts in.

Resource metrics (cpu/ram/disk/bandwidth/users) come from a safe source (mock/local) — this module
does not SSH or scrape secrets. UDP/Hysteria2 is not TCP-probeable → `udp_443_status='unknown'`.
"""
from __future__ import annotations

import socket
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from . import probe_sanitizer as _san

STATUS_HEALTHY = "healthy"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"
STATUS_UNKNOWN = "unknown"


@dataclass
class ProbeResult:
    node_code: str
    ts: str = ""                         # caller stamps (UTC); never Date in business logic
    status: str = STATUS_UNKNOWN
    latency_ms: Optional[int] = None
    tcp_443_ok: Optional[bool] = None
    tcp_80_ok: Optional[bool] = None
    tcp_22_ok: Optional[bool] = None
    udp_443_status: str = "unknown"      # not TCP-probeable; real-device test needed
    panel_http_status: Optional[int] = None   # status code from public root only (no admin path)
    cpu_pct: Optional[int] = None
    ram_pct: Optional[int] = None
    disk_pct: Optional[int] = None
    bandwidth_gb: Optional[float] = None
    users_count: Optional[int] = None
    reasons: List[str] = field(default_factory=list)   # sanitized reason codes only

    def sanitized(self) -> dict:
        """JSON-able dict guaranteed free of secrets (only the declared safe fields)."""
        return asdict(self)


class Prober:
    """Interface: probe(node_row) -> ProbeResult."""
    def probe(self, node_row) -> ProbeResult:  # pragma: no cover - interface
        raise NotImplementedError


class MockProber(Prober):
    """Returns canned results by node_code (default: healthy). No network. For tests/dry-run."""
    def __init__(self, results: Optional[Dict[str, dict]] = None, default_healthy: bool = True):
        self._results = results or {}
        self._default_healthy = default_healthy

    def probe(self, node_row) -> ProbeResult:
        code = node_row["node_code"]
        if code in self._results:
            data = dict(self._results[code])
            data.setdefault("node_code", code)
            return ProbeResult(**data)
        if self._default_healthy:
            return ProbeResult(node_code=code, status=STATUS_HEALTHY, latency_ms=20,
                               tcp_443_ok=True, tcp_80_ok=True, tcp_22_ok=True,
                               panel_http_status=200, cpu_pct=10, ram_pct=30, disk_pct=40)
        return ProbeResult(node_code=code, status=STATUS_UNKNOWN)


class PublicTcpProber(Prober):
    """Read-only public TCP connects (22/80/443) + optional HTTP HEAD to the public root.
    No payload is ever sent; the secret admin path is never touched. Real network — opt-in only."""
    def __init__(self, timeout: float = 5.0, http_head: bool = False):
        self._timeout = float(timeout)
        self._http_head = http_head

    def _tcp_ok(self, host: str, port: int) -> bool:  # pragma: no cover - real network
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(self._timeout)
        try:
            s.connect((host, port))
            return True
        except Exception:
            return False
        finally:
            s.close()

    def probe(self, node_row) -> ProbeResult:  # pragma: no cover - real network (opt-in CLI only)
        code = node_row["node_code"]
        host = node_row["public_hostname"] or node_row["public_ip"]
        res = ProbeResult(node_code=code)
        if not host:
            res.status = STATUS_UNKNOWN
            res.reasons.append(_san.UNKNOWN)
            return res
        try:
            res.tcp_443_ok = self._tcp_ok(host, 443)
            res.tcp_80_ok = self._tcp_ok(host, 80)
            res.tcp_22_ok = self._tcp_ok(host, 22)
        except Exception as e:
            res.reasons.append(_san.sanitize_error(e))
        # status derived purely from public reachability (resources unknown here).
        if res.tcp_443_ok is False:
            res.status = STATUS_DOWN
        elif res.tcp_443_ok:
            res.status = STATUS_HEALTHY
        else:
            res.status = STATUS_UNKNOWN
        return res
