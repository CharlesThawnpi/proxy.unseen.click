# PHASE 7 — entitlement + node-resilience foundation (dry-run)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §6.1, §6.2, §7, §8; [DECISIONS.md](DECISIONS.md); [REGIONS.md](REGIONS.md); [PROTOCOLS.md](PROTOCOLS.md); [NODES.md](NODES.md); [PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)
> **Status:** **PASS — DB-driven, dry-run only.** No node marked live, no live Hiddify call, no de1 metrics fetched, no Telegram send. de1 stays `status=test`; live provisioning stays hard-disabled.

## Run metadata
- Date/time (UTC): 2026-06-16T06:05Z
- Scope: the entitlement + node-resilience layer that makes plan access honest and dynamic —
  a DB-driven plan→region/protocol entitlement resolver, a node status/health/readiness model with
  graceful degradation, an availability resolver that combines them, honest Burmese customer-facing
  status copy, and integration into the Phase 4C provisioning plan. All dry-run.
- **Out of scope (NOT done):** marking any node live, live Hiddify, fetching real de1 metrics,
  real customers/subscriptions, Telegram sends, services, SG/US real nodes, Brain API, endpoints.
- Stack: **stdlib only**; all values DB-driven/admin-editable.

## Files created
- `backend/entitlements.py` — DB-driven plan→region/protocol resolver (FAST rule; default/premium; safe errors).
- `backend/node_resilience.py` — status × health → per-node readiness + reason vocabulary; candidate selection.
- `backend/availability.py` — entitlement × resilience → per-region/protocol availability with graceful degradation.
- `backend/migrations/0005_phase7.sql` — `proxy_node_protocols`, `node_live_blockers` (additive, FK-enforced).
- CLIs: `bin/entitlement_audit.py`, `bin/node_resilience_smoke.py`, `bin/availability_preview.py`.
- Tests: `tests/test_entitlement_resilience.py`.

## Files changed
- `backend/provisioning_plan.py` — `build_plan` now uses the resolver (new summary fields; `live_blockers` unchanged).
- `backend/seed.py` — seeds `node_live_blockers` for de1 (`leaked_key_rebuild_pending`, admin-editable).
- `backend/telegram_messages.py` — Burmese customer-facing availability copy.
- `backend/__init__.py` (`__all__`). Docs (below) + regenerated SOURCE_OF_TRUTH.md.

## Schema / migrations added (0005_phase7 — additive only)
- **`proxy_node_protocols`** (FK→proxy_nodes, protocol_profiles; UNIQUE(node,profile)): node-specific protocol
  availability. **Absence of a row = available** (back-compat); `is_available=0` marks a protocol down on that node.
- **`node_live_blockers`** (FK→proxy_nodes; UNIQUE(node,reason)): **data-driven** per-node live blockers (replaces the
  hardcoded "de1 has leaked keys"). Seeded: de1 → `leaked_key_rebuild_pending`. Clearing = deleting the row (post-rebuild).
- Indexes added. Verified: applies after 0001–0004, integrity `ok`, FK empty, **idempotent re-run** (`[]`).

## Entitlement resolver behavior
`entitlements.resolve(plan_code)` reads **only DB rows** (`plan_region_entitlements`, `plan_protocol_entitlements`,
`proxy_regions`, `protocol_profiles`): entitled regions/profiles, the **FAST display rule** (`display.fast_labels`),
the default region (DE, via `is_default`), and premium-only regions (SG, via `is_premium_only`). Unknown plan →
`UnknownPlanError`; disabled plan (`is_enabled=0`) → `DisabledPlanError` — never crashes. No hardcoded plan values.
Verified: TRIAL/BASIC=DE; CORE/PLUS=DE+US; PRO/MAX=DE+US+SG; SG premium-only PRO/MAX; FAST vs Fast1/Fast2.

## Node resilience behavior
Two axes kept distinct from entitlement:
- **status** (`proxy_nodes.status`): planned | test | standby | live | retired.
- **health** (derived from OPEN `node_alerts`): healthy | degraded (WARN) | down (CRITICAL/DOWN). No real metrics required.
`node_readiness(node)` computes `dry_run_candidate` (test/standby/live & not down — planned/retired excluded),
`live_ready` (live & not down & **no** node-intrinsic blockers), and a sanitized `reasons` list. Per-node **live
blockers are data-driven** (`node_live_blockers`). Graceful degradation: a down node is dropped; the rest keep serving.
Node-specific protocol availability via `proxy_node_protocols` (absent = available). **Per-node readiness reflects
node-intrinsic factors only** — the global phase gate (`phase4c_live_disabled`) is applied separately at the
provisioning layer so degradation stays visible.

## Readiness / blocking reason vocabulary
`node_not_live`, `node_status_test`, `node_status_planned`, `node_status_standby`, `node_status_retired`, `node_down`,
`node_degraded`, `protocol_missing`, `leaked_key_rebuild_pending`, `no_candidate_node`, `region_not_entitled`,
`protocol_not_entitled` (+ the provisioning-layer global `phase4c_live_disabled`). All are sanitized codes — never secrets.

## Provisioning plan integration
`provisioning_plan.build_plan` now calls `availability.resolve(..., dry_run)` and `node_resilience` and adds to the
sanitized summary: `entitled_regions`, `entitled_protocols`, `available_regions`, `unavailable_regions` (with reasons),
and per-node `node_readiness`. The existing `live_blockers` (`phase4c_live_disabled`, `leaked_key_rebuild_pending`,
`node_not_live:<status>`) is **unchanged** — the Phase 4C/6 contract and all prior tests still hold. Live provisioning
remains hard-refused; no Hiddify mutation; no Telegram send; summaries stay sanitized.

## Customer-facing availability behavior
Burmese-primary helpers in `telegram_messages`: `region_available`, `region_unavailable`, `region_test_only`,
`protocol_unavailable`, `plan_excludes_region`. They reference only region codes (DE/US/SG) and protocol **display
labels** — public product facts — and **never** a node IP, hostname, token, UUID, link, or admin path (test-asserted).
Honest, no silent region substitution / protocol downgrade.

## Tests and results
```
cd /opt/unseen-proxy && python3 -m unittest discover -s tests -p 'test_*.py'
```
**Result: 144 tests, OK** (122 prior + 22 new). New coverage: region entitlements per plan; SG premium-only PRO/MAX;
default region DE; FAST rule; unknown/disabled plan safe; de1 test blocks live with `node_status_test` +
`leaked_key_rebuild_pending`; live healthy node is live-ready; down node dropped (live + dry-run); degraded still a
candidate; planned/retired excluded; node-protocol availability default + explicit; dry-run DE available via test node;
graceful degradation (US serves while DE/SG unavailable); all-nodes-down → region unavailable; no-node region →
`no_candidate_node`; disabled protocol → `protocol_missing` in region; disabled/empty region unavailable; SG absence
never affects BASIC/CORE; provisioning plan uses the resolver + preserves `live_blockers`; summary + customer messages
carry no IP/secret. All Phase 4/5/6 tests still pass.

## Secret-safety result
No secrets in source/docs/tests. Reason codes, region/protocol codes, statuses, and counts only — no node IP, token,
UUID, link, QR, or admin path in any resolver output, plan summary, audit, or customer message (test-asserted, incl.
the de1 IP `5.249.160.59`). `node_live_blockers.detail` is a sanitized note. Pre-commit scan passes.

## Known limits
- Health is derived from `node_alerts` only (no real metrics ingestion in this task; mock alerts in tests).
- `proxy_node_protocols` is unseeded (all protocols available by default) until per-node inbound state is recorded.
- Availability is a point-in-time DB view; a health monitor/poller that *writes* alerts is a later phase.

## Live blockers (intentional)
- **de1 `status=test`** → `node_status_test` (data + status).
- **Leaked-key rebuild required** → `leaked_key_rebuild_pending` (now data-driven in `node_live_blockers`).
- **Real-device FAST1/FAST2/Secure PASS pending** (`#TASK_for_Charles`, [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md)).
- **Live provisioning intentionally disabled** (`config.PHASE4C_LIVE_PROVISION_DISABLED`) → `phase4c_live_disabled` at
  the provisioning layer; live refuses even with env latch + flags.

## Risks / follow-ups
- Build the node-health **monitor** that writes `node_metrics`/`node_alerts` from read-only probes (no secrets), so
  availability reflects reality once nodes are live.
- Seed/maintain `proxy_node_protocols` per node as inbounds are verified; wire `availability` into the (future) live
  candidate selection at provisioning time.

## Exact next recommended task
**Phase 7 health monitor (gated) or Phase 8 (web portal) / live bring-up prep:** add a read-only node-health monitor
that populates `node_metrics`/`node_alerts` (sanitized; no secrets) feeding this resolver — still dry-run until **de1
is rebuilt** (clears `leaked_key_rebuild_pending`) and a real-device FAST1/FAST2/Secure PASS is recorded. Live
promotion stays Charles-gated.
