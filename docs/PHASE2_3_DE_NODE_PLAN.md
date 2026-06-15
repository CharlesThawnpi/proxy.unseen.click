# PHASE 2-DE / 3-DE — Separate DE Hiddify Node Plan

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §14, §34; decision [DECISIONS.md](DECISIONS.md) ADR-001
> **Status:** PLAN ONLY — **no connection to the node, no install yet.** Prepared 2026-06-15.

The forward workflow for the **new dedicated DE Hiddify node** (separate VPS), replacing the retired Master
co-location. Each step is gated, secret-safe, and managed **from the Master only**. The node stays `planned`/`test`.

## Target node (inventory)

| Field | Value |
|---|---|
| Region | Germany / DE |
| Public IP | `5.249.160.59` |
| Specs | 4 vCPU / 4 GB RAM / 25 GB SSD / 30 TB bandwidth |
| OS (required) | **Ubuntu 22.04 LTS** (Hiddify's supported host-install OS) |
| Role | **Hiddify proxy traffic only** — no business data, no UNSEEN services |
| Status | **planned/test** — never `live` in this workflow |
| Management | from the **Master only**, over Hiddify API v2 |
| Node domain | `node-de.unseen.click` (never shown to customers) |

> **Specs above are provider/purchase ESTIMATES (unverified).** Per [DECISIONS.md](DECISIONS.md) ADR-002, the Master
> must detect and record the node's **actual** facts (read-only) during preflight and treat those as authoritative —
> see "Node-facts verification" below.

## Phase 2-DE — clean-VPS preflight (read-only on the node)

Run as a **separate authorized task** (this plan does not connect yet). Steps:
1. **SSH key setup, Master → DE** (least privilege): generate/managed key at `/root/.ssh/unseenproxy_de_ed25519`
   (`0600`, root-owned) on the Master; install its **public** half on the node; pin the node host key in
   `known_hosts`. Private key never leaves the Master, never enters git.
2. **Verify OS = Ubuntu 22.04 LTS** (`/etc/os-release`). If not 22.04, STOP and reinstall the OS first.
3. **Clean-VPS check** — no legacy Marzban/Happ/Xray/sing-box/old-UNSEEN artifacts; record a per-node
   `CLEAN_VPS_CHECKLIST` entry (mirror the Master's Phase 0).
4. **Resources/ports/firewall baseline** — `ss -tulpn`, disk/RAM, firewall state; confirm SSH:22 and that
   80/443 + the protocol ports are free.
5. **DNS readiness** — plan `node-de.unseen.click` → `5.249.160.59` (A record). **Document only; do not change DNS
   here.** Hiddify's host installer needs the domain resolving before TLS issuance.
6. **Snapshot** — a fresh node is disposable, so a provider snapshot is optional (unlike the protected Master); note
   the rebuild path instead.

**Exit:** node verified Ubuntu 22.04, clean, reachable from Master over SSH (key-only); DNS plan agreed; **actual node
facts detected and recorded (see below), overriding the provider estimates.**

### Node-facts verification ([DECISIONS.md](DECISIONS.md) ADR-002) — read-only, run only when Phase 2-DE begins

The provider/purchase specs (4 vCPU / 4 GB / 25 GB / 30 TB / Ubuntu 22.04) are **estimates only**. During this
preflight the Master runs a **read-only** probe over SSH (suggested `scripts/node_preflight_probe.sh` — written when
Phase 2-DE starts, **not now**) that **never mutates the node and never prints secrets**, and records detected facts
that **override** the estimates.

**Facts to detect (read-only):** OS + version (`/etc/os-release`), kernel (`uname -a`), CPU model/count
(`nproc`/`/proc/cpuinfo`), RAM total/free (`free`), disk layout + usable storage (`lsblk`/`df`), public IP as seen
**from the node** (vs the documented `5.249.160.59`), default route/interface (`ip route`), listening ports
(`ss -tulpn`), firewall state (ufw/iptables/nft), Docker/nginx/Hiddify/service presence, clean-of-legacy check, and
**role-fit** (is disk/RAM sufficient for Hiddify?). Bandwidth allowance is **not** node-detectable — leave it
`estimate` unless a provider API/dashboard later makes it `provider-confirmed`.

**Provenance tiers (record per value):** `estimate` (provider/purchase) · `detected` (from the node) ·
`provider-confirmed` (provider API/dashboard) · `unknown` (not yet verified). Results are saved **sanitized** to
docs/status now, and to the `proxy_nodes` DB metadata once the schema exists (Phase 4) — storing detected separately
from estimate (or a per-field provenance flag), never a single unqualified number. **Re-run the probe after the
Hiddify install** if resource usage changes materially.

## Phase 3-DE — Hiddify supported host install + live verification (on the node)

1. **Host install (Ubuntu 22.04)** — Hiddify's official **host** installer (not Docker), a **pinned stable version**;
   run under `screen`/`tmux`; keep a second SSH session + provider recovery path. Domain `node-de.unseen.click`.
   Hiddify firewall: decide explicitly (leave OFF during first verification to avoid SSH-lockout risk).
2. **Secret handling** — the admin link / admin proxy path / API key (UUID) go **only** into a root-owned `0600` file
   (on the Master or the node), e.g. `/root/hiddify-de-admin.link`. **Never** in git, docs, logs, or chat — record only
   the **path**. Reality keys/short-ids likewise stay secret.
3. **Live verification** (sanitized; managed from Master):
   - Record exact Hiddify **version**; container/process + **real listening ports** (`ss -tulpn`).
   - Confirm **SSH still up** + the firewall state after install.
   - Pull the panel **Swagger/OpenAPI**; fill [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md) with verified values:
     API v2 base path shape, `Hiddify-API-Key` header, user create/update/get/list/disable endpoints, quota field +
     **units (GB vs GiB)**, expiry/`package_days`/`start_date`, usage fields, subscription URL + output formats
     (`auto/sub/sub64/singbox/clash/...`), deep-link import notes — flip **[LIVE]** → **[VERIFIED-LIVE]**.
   - **Create exactly one disposable test user** (`disposable-test`, no real data/payment/UNSEEN token); confirm it
     returns a subscription (do **not** print raw proxy/sub links); **delete it** after.
   - Confirm **FAST1/Hysteria2, FAST2/Shadowsocks, Secure/VLESS-Reality** inbounds exist and record their ports.
   - Optional real-device App import = **Charles manual follow-up** (links never logged).
4. **Record the node** in `proxy_nodes` design (Phase 4) as `de1`, region `de`, `5.249.160.59`, `status=test`.

**Exit:** a **verified-live** Hiddify API contract + working inbounds on the DE node, node still `test`. **Only then is
Phase 4 (DB/backend orchestrator) unblocked.**

## Risk notes (this node)

- **25 GB SSD** is fine for a test/early node but **watch disk** (Hiddify + logs + sing-box/xray); monitor and alert at
  **75% WARN / 90% CRITICAL** once monitoring exists.
- **4 GB RAM** is adequate for early Hiddify usage; watch under load.
- **30 TB bandwidth** is strong for the role.
- **No business DB / customer data on the node** — proxy traffic only.
- Node is **dynamic/replaceable** (§6.1): IP/host/specs are data in `proxy_nodes`, not code.
