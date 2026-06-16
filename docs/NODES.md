# NODES

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §6.1, §6.2
> **Status:** Phase 1 skeleton — decided from plan

What a node is, how it's provisioned, and why nodes are disposable.

## Node responsibilities (Hiddify only, no business data)

Each region is one or more independent node VPS, each running a full **Hiddify Manager** install. Responsibilities are strictly limited:

- **On a node:** Hiddify Manager (panel + Hysteria2/SS/VLESS-Reality inbounds), TLS for the node's own domain(s), the node's local Hiddify SQLite/user store, and nothing else.
- **No customer business data, no bot, no payments.** A node knows only Hiddify users (UUIDs with quotas/expiry).
- **The Master never proxies traffic.** Customer VPN traffic goes customer → node directly. The Master only calls each node's Hiddify **API v2** to create/update/disable users and read usage.

## Node provisioning standard (per node)

> **Step-by-step runbook: [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md)** — the reusable, ordered,
> secret-safe install guide derived from the successful de1 build. **All future nodes (US, SG1, SG2, …) follow it**; the
> summary below is the high-level standard. Do **not** repeat Master co-location or Docker-on-Master (ADR-001).

1. Fresh VPS, hardened SSH (key-only; managed keys held on Master under `/root/.ssh/unseenproxy_<region>_ed25519`).
2. Install Hiddify Manager (official installer).
3. Configure the protocol inbounds: **Hysteria2 (FAST1)**, **Shadowsocks (FAST2)**, **VLESS-Reality (Secure)**. Keep the panel admin path secret; expose only proxy ports + the sub domain publicly.
4. Create a dedicated **service admin UUID / API key** for the Master orchestrator (least privilege).
5. Record the node in the Master DB (`proxy_nodes`): region, public hostname, panel API base (handle; secret in `.env`), status (`test`/`standby`/`live`), capacity/bandwidth budget.
6. Validate with a **disposable test user** through the Master orchestrator before marking `live`.

Test nodes carry **no backup** and may be wiped freely; live nodes are production data plane but still rebuildable, because the Master holds the authoritative user set.

## Dynamic, replaceable nodes — nodes are data, not code (§6.1)

The set of nodes lives entirely in the `proxy_nodes` table plus per-node secrets in `.env` referenced by handle. **Nothing about a specific node — IP, hostname, region, capacity, or its existence — is ever hardcoded.**

- **Add a node:** insert a row + secret handle, mark `test`, validate with a disposable user, promote to `live`. No code change, no redeploy.
- **Replace a node** (cancelled service, migrating provider, moving DE off the Master): stand up the replacement, point the row's `public_hostname`/`panel_api_base_ref`/secret handle at it, re-provision the authoritative user set, promote, retire the old row. The subscription token is unchanged — the sidecar resolves regions/protocols dynamically, not fixed hosts.
- **Remove a node:** mark `standby`/`retired`; the system continues on the remaining nodes.
- **Single control point:** all node management happens through the Master's gated CLIs/admin surface; operators (or coding tools) connect **only to the Master**. No tool talks to a node directly for management.

## Graceful degradation / fail-soft (§6.2)

A single node being damaged, cancelled, overloaded, or unreachable must **never** take down the whole system.

- **Health-driven offering.** Node-health monitor marks each node `healthy`/`degraded`/`down`; a region needs ≥1 healthy `live` node to be offered. When a node goes `down`, the Master stops offering it and serves the customer's other entitled regions.
- **Sidecar fail-soft.** An unreachable node's entries are **omitted** rather than failing the whole subscription response; fetches are time-boxed so a slow/dead node cannot hang the response.
- **Honest customer-facing status.** A customer on a `down` region sees an honest message (e.g. "DE is temporarily unavailable — please use SG/US, or try again shortly") instead of silent failure.
- **No single point of proxy failure for multi-region plans.** A PRO/MAX customer entitled to DE+US+SG keeps working on the survivors if one region drops.
- **Master/DE caveat.** Because DE is co-located on the Master (§4.1), a Master outage affects both control plane and DE node together — mitigated by headroom alerts and by DE being movable to its own VPS without code change.

## DE node — dedicated separate VPS (co-location RETIRED)

The DE node is now an **ordinary, dedicated node on its own VPS** — **not** co-located on the Master. The §4.1
co-location exception is **retired** ([DECISIONS.md](DECISIONS.md) ADR-001); the standard node-provisioning standard
above applies normally (fresh VPS, host install, least-privilege API key, managed from Master).

- **Node:** `de1` — `5.249.160.59`, 4 vCPU / 4 GB / 25 GB SSD / 30 TB, **Ubuntu 22.04 LTS**, domain
  `node-de.unseen.click` **(set as a Hiddify `direct` domain with a valid Let's Encrypt cert, 2026-06-16 — API +
  subscription verified-live over the public node-de path; before this the install used only raw-IP/sslip.io defaults,
  which broke real-device import. See [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5A)**.
  **Real-device import readiness (2026-06-16): server subscription output verified CLEAN via sanitized scan (admin
  `all-configs` ~16 KB, no `127.0.0.1`/`localhost`/`64127`, protocols present, node-de listed). The first phone import
  failed app-side with `127.0.0.1:64127` (the Hiddify App's own local core port) — not a node fault; see runbook §5B +
  PHASE9 addendum. The Windows app then hit a parser error (`outbounds[N].tunnel-per-resolver: unknown field`) from the
  DNSTT outbound — FIXED by disabling DNSTT (`set-setting dnstt_enable=false` + apply; not FAST1/FAST2/Secure);
  after-render confirms the field is gone, FAST1/Secure intact. Then the broad Hiddify default profile (100 outbounds)
  was PRUNED to a clean UNSEEN-only set (2026-06-16): exactly Hysteria2(FAST1)+Shadowsocks(FAST2)+VLESS-Reality(Secure)
  on node-de only (FAST1 udp:14430, FAST2 :16753, Secure tcp:443+decoy SNI), raw-IP/sslip excluded via `sub_link_only`,
  all noise protocols off — see runbook §5C. Protocols await Charles's real-device connect (not yet PASS).** Starts
  **`status=test`**, never auto-promoted to `live`; proxy traffic only.
  **Specs are provider/purchase ESTIMATES (unverified)** — per [DECISIONS.md](DECISIONS.md) ADR-002 the Master detects
  and records the node's **actual** facts (read-only) at preflight and those override the estimates; bandwidth stays
  `estimate` until provider-confirmed.
- **Why separate (not co-located):** the Master co-location attempt used Hiddify's experimental Docker (v12.3.3) and
  the panel was non-functional (compose `$REDIS_PASSWORD` interpolation bug → Redis password-less; DB migration
  errors); it was torn down. Hiddify officially labels Docker "not for permanent use." A separate VPS with the
  **supported Ubuntu-22.04 host install** is the chosen path, and it keeps the protected control plane clean.
- **Provisioning + live-verify workflow:** see [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md). API contract
  remains unverified until that install succeeds; **Phase 4 is blocked** until then.
- **Hiddify INSTALLED (2026-06-16): v12.3.3, host install on Ubuntu 22.04.5 — running. Result PARTIAL.** All services
  active; **443 up**; **FAST1(Hysteria2)/FAST2(Shadowsocks)/Secure(VLESS-Reality) inbounds present**; admin link secured
  (`/root/hiddify-de1-admin.link`, 0600); SSH safe; ufw active. RAM balloon-dynamic (~1.8 idle → ~3.8 under load,
  accepted risk). **Deferred (blocks Phase 4):** exact API v2 CRUD contract + disposable test user — read from browser
  Swagger (v12.3.3 API path not black-box-discoverable; OpenAPI route errors). Node stays `status=test`. Detail:
  [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md). (Preflight history: [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md).)
- **Update (2026-06-16): API v2 contract VERIFIED-LIVE; Phase 3-DE PASS (w/ follow-ups).** Disposable test user
  create→sub→delete confirmed; Phase 4 API layer unblocked (contract in [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md);
  **Hiddify uses GB**). Node-tuning before live: SS:8388/UDP reachability, RAM lock, SSH hardening, regenerate the
  leaked default-user keys. Still `status=test`.

## de1 pre-live tuning (2026-06-16) — PARTIAL

Test-safe hardening (no customers/live; `status=test`) — [PHASE4_PRELIVE_DE1_TUNING.md](PHASE4_PRELIVE_DE1_TUNING.md):
firewall verified (no change needed), **SSH password login disabled (root key-only kept, verified)**, Hiddify services
healthy, host key pinned in the Master `known_hosts`. **Leaked default-user/server keys → `REBUILD_REQUIRED_BEFORE_LIVE`**
— first real/live provisioning is blocked until de1 is rebuilt (provider reinstall → re-key → preflight → fresh Hiddify
install → re-apply hardening → fresh least-privilege API key → disposable-user verify). Dry-run work may continue.

## de1 fresh rebuild + clean Hiddify reinstall (2026-06-16) — PASS; leaked-key blocker CLEARED

Charles rebuilt de1 fresh (provider reinstall, Ubuntu 22.04.5) and re-added the Master root key; a clean **Hiddify
v12.3.3 host reinstall** (pinned `download.sh v12.3.3 --no-gui`, NOT Docker, **umask 022** — no permission cascade)
was verified ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)):

- **Preflight PASS** after Charles's storage upgrade (disk 53.7 GB) + an approved online root-volume grow
  (`growpart`→`pvresize`→`lvextend`→`resize2fs`) to ~48 GB / 40 GB free. Detected facts updated in seed: disk ~48 GB,
  RAM ~3.9 GB.
- **API v2 contract RE-VERIFIED-LIVE** (Hiddify API v2.2.0; auth header; admin base `/<proxy>/api/v2/admin/`; units
  **GB**) after a bounded `marshmallow==3.26.1` venv pin (apiflask 3.0.2 had pulled incompatible marshmallow 4.x).
- **Disposable-user lifecycle PASS** (create→get→all-configs→patch→delete→404). FAST1/FAST2/Secure inbounds present.
- **SSH re-hardened** (password-auth off, key-only, port unchanged; verified). Firewall: 22/80/443 tcp + 443 udp
  allowed; SSH safe.
- **`leaked_key_rebuild_pending` CLEARED** — fresh rebuild regenerated all node secrets. Seed now records
  `realdevice_protocol_test_pending`. **de1 stays `status=test`**; remaining pre-live: a real-device FAST1/FAST2/Secure
  connect PASS (#TASK_for_Charles) + RAM lock + set `node-de.unseen.click` panel domain/cert.

## de1 real-device protocol diagnosis (2026-06-16) — PARTIAL (server-side READY; client connect unconfirmed)

After Charles's clean import (iOS shows two auto selectors "lowest"/"balance" + VLESS-Reality + Shadowsocks + Hysteria2),
a node-side diagnosis ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md) addendum) found the
node **server-side READY and externally reachable for all three protocols**, but **real-device connect is unconfirmed**:

- **Sanitized render still clean:** 1 `disposable-test-realdevice` user; 7 outbounds (hy2 + ss + vless-Reality + 2
  client selector groups + 2 direct); 0 raw-IP/sslip/dnstt/non-Reality/private-keys; all product → node-de.
- **Health:** all `hiddify-*` active (`ss-faketls` intentionally inactive); panel API re-verified **200**; **marshmallow
  3.26.1** pin intact (`openapi.json` 500 is cosmetic). A controlled ~19:19 restart cluster (Charles re-applied SSH/DNS)
  cycled the stack with full recovery — **no ongoing crash**.
- **Reachability:** DNS ✓, TLS verify=0 ✓, TCP 443/16753/80/22 OPEN ✓, UDP 14430/443 open|filtered ✓.
- **Selectors:** "lowest"/"balance"/auto are **client selector/urltest groups, not protocols** and **not UNSEEN's final
  labels** (backend/portal handle UNSEEN naming).
- **Decision = HOLD (no node tuning):** UDP buffers already 64 MB, no server errors, all reachable. **Windows VPN-mode
  "failed to start background core" = client-side**; Windows **Proxy mode is not full-VPN proof**; **iOS SS upload drop**
  = mobile-network/client. **`realdevice_protocol_test_pending` REMAINS; de1 stays `status=test`; no node change made.**
- **Phase 10 note:** SS `16753` is reachable only via default `INPUT=ACCEPT`; add an explicit allow before tightening to DROP.

## Phase 4C — de1 in dry-run provisioning (2026-06-16)

The dry-run provisioning orchestration ([PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md)) may select
`de1` as a candidate node for **dry-run planning only** (`usable_for_dry_run=True`, `usable_for_live=False`). Live
provisioning is **hard-refused**: blockers `node_not_live:test`, `leaked_key_rebuild_pending`, and
`phase4c_live_disabled` are always present, so live refuses even with the env latch + `--live --confirm`. de1 stays
`status=test`.

## Phase 7 — node status/health resilience (2026-06-16)

`backend/node_resilience.py` ([PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md)) resolves
two axes: **status** (`planned|test|standby|live|retired`) and **health** (from OPEN `node_alerts`:
healthy|degraded|down). For **live**, only a `live` + not-down node with no data-driven blocker is eligible; for
**dry-run**, test/standby/live (not down) are candidates (planned/retired excluded). A **down** node is dropped;
remaining nodes keep serving (graceful degradation). **de1** stays `status=test` and is blocked from live with
`node_status_test` + `leaked_key_rebuild_pending` — the leaked-key blocker is now a **data-driven** `node_live_blockers`
row (delete it after the rebuild), not hardcoded.

## Phase 7 — health monitor foundation (read-only, dry-run, 2026-06-16)

`backend/health_monitor.py` ([PHASE7_HEALTH_MONITOR_FOUNDATION.md](PHASE7_HEALTH_MONITOR_FOUNDATION.md)) runs a
**single pass** (no daemon/systemd) that probes each node via an injected `Prober` (mock by default; opt-in read-only
public TCP 22/80/443 — no payload, no admin path) and, only with `--write-metrics`, appends `node_metrics` and
reconciles `node_alerts`. **Degraded policy:** a node with a resource WARN/CRITICAL alert is `degraded` — it stays a
**dry-run candidate** but is **not live-ready**; a node with a reachability DOWN alert is dropped from all candidates
(other nodes keep serving). de1 stays `status=test` and is blocked from live (`node_status_test` +
`leaked_key_rebuild_pending`). No node is ever modified; no secret is fetched or printed.
