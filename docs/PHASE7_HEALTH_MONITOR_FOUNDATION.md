# PHASE 7 — health monitor foundation (read-only, dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6.2, §30, §30A, §31; [DECISIONS.md](DECISIONS.md); [PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md); [NODES.md](NODES.md); [SECURITY.md](SECURITY.md)
> **Status:** **PASS — read-only, dry-run only.** No daemon, no systemd, no node modified, no Hiddify mutation, no secrets fetched, no Telegram send. de1 stays `status=test`; live provisioning stays hard-disabled.

## Run metadata
- Date/time (UTC): 2026-06-16T06:35Z
- Scope: a safe monitor foundation that collects **sanitized** node health signals and (only on
  explicit request) writes `node_metrics`/`node_alerts`, feeding the Phase 7 `node_resilience`
  resolver. Probe abstraction, sanitized result model, metric writer, idempotent alert evaluator,
  once-only monitor + CLIs, resolver integration. All dry-run by default.
- **Out of scope (NOT done):** daemon/scheduler, systemd timer/service, package installs, modifying
  de1, restarting Hiddify/SSH, firewall changes, live Hiddify, fetching admin link/API key/proxy
  path/subscription links, Telegram sends, real customers/subscriptions, marking de1 live, Brain API.
- Stack: **stdlib only** (`socket`/`unittest`); no new schema (existing `node_metrics`/`node_alerts`/`settings` suffice).

## Files created
- `backend/probe_sanitizer.py` — map probe errors → sanitized reason codes (strip host/URL/IP).
- `backend/node_probe.py` — `ProbeResult` (sanitized fields) + `MockProber` (default) + `PublicTcpProber` (opt-in).
- `backend/alerting.py` — reason codes, thresholds (from `settings`), idempotent `evaluate`/clear.
- `backend/metric_writer.py` — append-only `node_metrics` writer.
- `backend/health_monitor.py` — `monitor_once` (dry-run default; writes only when `write=True`).
- CLIs: `bin/node_health_probe_dry_run.py`, `bin/node_health_monitor_once.py`, `bin/node_alerts_preview.py`.
- Tests: `tests/test_health_monitor.py`.

## Files changed
- `backend/node_resilience.py` — `node_health` refined: reachability **DOWN → down** (dropped);
  resource **CRITICAL/WARN → degraded** (dry-run candidate but not live-ready). Policy documented.
- `backend/__init__.py` (`__all__`). Docs (below) + regenerated SOURCE_OF_TRUTH.md.

## Probe model
`ProbeResult` carries **only sanitized fields**: `node_code`, `ts`, `status`
(healthy/degraded/down/unknown), `latency_ms`, `tcp_443_ok`/`tcp_80_ok`/`tcp_22_ok`,
`udp_443_status` (`unknown` — not TCP-probeable), `panel_http_status` (from the **public root only**,
never the admin path), `cpu_pct`/`ram_pct`/`disk_pct`/`bandwidth_gb`/`users_count` (safe/local/mock
source), and `reasons` (sanitized codes). A raw probe error is **never** stored — `probe_sanitizer`
maps it to `probe_timeout` / `probe_error_sanitized`. `MockProber` (default for tests/dry-run) uses
no network; `PublicTcpProber` does read-only public TCP connects to 22/80/443 (no payload) and is
opt-in via a CLI flag only — it never touches the admin path or sends a proxy payload.

## Metric writing behavior
`metric_writer.write_metric` appends one `node_metrics` sample (cpu/ram/disk/bandwidth/users) — only
safe numeric fields, append-only (never update/delete). Writes happen **only** when the monitor is
run with `write=True` against an explicit `--db`.

## Alert evaluator behavior
`alerting.evaluate` reconciles OPEN `node_alerts` for a node against a `ProbeResult`:
- Reachability: `tcp_443_ok==False` → **DOWN** (`tcp_443`); `tcp_80_ok==False` → **DOWN** (`tcp_80`);
  `panel_http_status>=500` → **DOWN** (`panel`); `tcp_22_ok==False` → **WARN** (`ssh_22`, management only).
- Resources: cpu/ram/disk `>= critical` (≈90) → **CRITICAL**; `>= warn` (≈75) → **WARN**. Thresholds
  read from `settings` (`node_alert_warn_pct`/`node_alert_critical_pct`) with safe fallbacks.
- **Idempotent:** one open alert per `(node, metric)`; raising the same level again is a no-op (no
  dup); a level change clears the old and raises the new; a resolved condition **clears** the open
  alert (sets `cleared_at`). `node_metrics` is append-only; `node_alerts` is an open/cleared lifecycle.
- Alert rows store only `level`/`metric`/`value` (a percent or 0) — **no secret/URL/host**.

## Readiness / resilience integration
`node_resilience.node_health` consumes OPEN alerts: **DOWN → down** (node dropped from all
candidates), **CRITICAL/WARN → degraded**. **Degraded policy (documented):** a degraded node
**remains a dry-run candidate** (previews still show it) but is **not live-ready** (`node_degraded`
is an open reason → `live_ready=False`); we do not route live traffic to a stressed node. A **down**
node is dropped from candidates entirely; other nodes keep serving (graceful degradation).
Entitlement stays separate from health. A healthy `live` node is candidate-ready; **de1** stays
blocked for live with `node_status_test` + `leaked_key_rebuild_pending`. Availability customer
messages reflect unavailable/degraded honestly with no internal details.

## CLI behavior
- `node_health_probe_dry_run.py` — mock probes by default (no network, no write); prints sanitized
  per-node summary; `--real-public-tcp-only` opts into read-only public TCP 22/80/443 checks.
- `node_health_monitor_once.py` — one pass; **dry-run default writes nothing**; `--write-metrics`
  appends `node_metrics` + reconciles `node_alerts` on the explicit `--db`; `--demo` uses a synthetic
  stressed de1. **No daemon, no systemd.**
- `node_alerts_preview.py` — read-only: open-alert counts by level + per-node readiness.

## Dry-run / no-network / no-secret guarantees
- Default prober is the mock → **no network**; a test patches `urllib.request.urlopen` to throw and
  runs the monitor → proves no network.
- Dry-run (`write=False`) writes nothing (test-asserted: `node_metrics`/`node_alerts` unchanged).
- No probe error, URL, host, IP, admin path, API key, UUID, or proxy payload is stored or printed —
  only sanitized fields/codes. No Hiddify or Telegram call anywhere.

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 163 tests, OK** (144 prior + 19 new). New coverage: error sanitization (host/URL/IP →
code); ProbeResult has no secret-shaped values; metric writer appends; WARN@75 / CRITICAL@90; DOWN
for tcp_443 + panel; no duplicate open alerts; level-change clears+raises; resolved condition clears;
thresholds from settings; DOWN → node_down → dropped + region unavailable; CRITICAL resource →
degraded (candidate, not live-ready); WARN → degraded; de1 still blocks live; monitor dry-run writes
nothing; write mode writes metrics+alerts; monitor idempotent (no dup); no network in monitor;
customer copy has no IP/secret. All Phase 4/5/6/7 tests still pass.

## Secret-safety result
No secrets in source/docs/tests. Probes are read-only and public-only; raw errors are sanitized to
codes; metrics/alerts store only numbers + sanitized check names; customer messages carry no
IP/host/secret (test-asserted incl. de1 IP/hostname). No daemon, no systemd, no node modification.
Pre-commit scan passes.

## Known limits
- `PublicTcpProber` resource metrics are unknown (cpu/ram/disk come from a safe/local/mock source);
  a read-only SSH metrics collector (existing key, test node) is a future, explicitly-configured option.
- UDP/Hysteria2 reachability stays `unknown` (real-device test needed).
- No scheduler: the monitor is single-pass, invoked by a CLI/test. A gated cron/timer is a later task.

## Live blockers (intentional)
- **de1 `status=test`** → `node_status_test`.
- **Leaked-key rebuild required** → `leaked_key_rebuild_pending` (data-driven `node_live_blockers`).
- **Real-device FAST1/FAST2/Secure PASS pending** (`#TASK_for_Charles`, [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)).
- **Live provisioning intentionally disabled** (`config.PHASE4C_LIVE_PROVISION_DISABLED`) → `phase4c_live_disabled`.

## Risks / follow-ups
- Add a **gated** scheduler (cron/systemd timer) to run `monitor_once --write-metrics` periodically on
  the Master against the live DB — separately authorized; keep it sanitized + read-only on nodes.
- Add a read-only SSH metrics collector for real cpu/ram/disk once a node is live (existing key; no secrets).
- Add retention/rolling-window pruning for `node_metrics` (append-only growth).

## Exact next recommended task
**Phase 8 (web portal) or a gated monitor scheduler / de1 rebuild prep:** either start the customer
portal, or add the separately-gated periodic monitor + read-only SSH metrics collector — still dry-run
for provisioning until **de1 is rebuilt** (clears `leaked_key_rebuild_pending`) and a real-device
FAST1/FAST2/Secure PASS is recorded. Live promotion stays Charles-gated.
