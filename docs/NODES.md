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

## DE node — co-located on the Master (NOT disposable)

The DE node is the §4.1 exception: it runs **on the Master control-plane VPS**. The general "test nodes carry no
backup, wipe freely" rule in this doc **does not apply to DE** — the Master must never be wiped/re-imaged. The DE
node's standard provisioning differs from a fresh-VPS node accordingly:

- Provisioning step 1 ("fresh VPS") is replaced by an **in-place, protected install** on the Master, gated behind a
  **provider snapshot** (the only reliable rollback for a host-wide installer).
- It starts as **`status=test`** in `proxy_nodes` and is **never auto-promoted to `live`**.
- **Status (2026-06-15): Docker build proven non-viable & TORN DOWN; DE will move to a separate VPS.** The pinned
  v12.3.3 Docker stack came up but the panel never served (compose `$REDIS_PASSWORD` interpolation bug → Redis ran
  password-less; DB migration errors). It was removed (`docker compose down -v` + dir deleted); Master back to
  baseline. **Decision: the DE node is provisioned by Hiddify's supported host installer on a separate Ubuntu-22.04
  VPS (audit Option C), NOT Docker-on-Master.** This makes DE a normal node (no longer the §4.1 co-location
  exception). Node will start `status=test`. API contract still unverified pending that install. See
  `PHASE3_HIDDIFY_LIVE_VERIFY.md`.
