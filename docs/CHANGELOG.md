# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-15 — Phase 3 (Hiddify install & API audit PLAN)

- **Read-only research only — no install, no Hiddify API call, no system change.** Docs-only.
- Researched official/primary Hiddify sources (hiddify.com docs, DeepWiki, GitHub) and produced
  `PHASE3_HIDDIFY_AUDIT_PLAN.md` with tiered findings (**[VERIFIED]** / **[LIVE]** / **[ASSUMPTION]**).
- **Verified:** install path `/opt/hiddify-manager`; standard install brings nginx+HAProxy+Xray+sing-box+MariaDB+
  Redis and **takes 80/443**; **Docker** install can **remap ports and run behind an existing nginx**; firewall is
  **iptables, Hiddify-managed**; API v2 base paths + `Hiddify-API-Key: <admin-UUID>` header auth; official OS is
  **22.04** (24.04 had Redis-7.0 install issues, since fixed — Docker bundles Redis and sidesteps it).
- **B1 resolvable:** recommended **Option A** (Docker behind Master nginx) or **Option C** (separate DE VPS, lowest
  risk); proxy inbounds (Hysteria2/Reality/SS) need dedicated ports (not HTTP-proxyable). **B3** firewall/SSH-safety
  plan documented. **B4** reduced but exact ports/units/API fields remain **[LIVE]**. **B2** snapshot still manual.
- Updated `HIDDIFY_API_CONTRACT` (base/auth now docs-verified; CRUD/fields **[LIVE]**), `PORTS`, `NETWORK`,
  `DEPLOYMENT`, `ROLLBACK`, `SECURITY`, `PHASE2_…PREFLIGHT`, `CURRENT_STATUS`. Readiness: **PARTIAL / HOLD**.

## 2026-06-15 — Phase 2 (protected Master/DE Hiddify preflight)

- **Read-only preflight only — Hiddify NOT installed; no system changes made** (no nginx/docker/certbot/ufw/
  package/systemd/firewall/DB/`.env` changes).
- Inspected the Master: 4 vCPU / 15 GiB RAM (~13 GiB free) / 4 GiB swap / 86 GB free disk — sufficient for a
  co-located **test** DE node.
- Confirmed ports 80/443 and Master loopback ports 8190/8191/8192/8197 are currently **free**; only SSH:22 is
  public. **No active host firewall** (ufw inactive, iptables all-ACCEPT, empty nft).
- Legacy scan **CLEAN** (only the authorized `HIDDIFY_API_CONTRACT.md` matched `*hiddify*`).
- Identified the central co-location blocker: **80/443 + TLS ownership** must be decided before install; a
  **provider snapshot is required** before the invasive installer touches the live control plane.
- Readiness decision: **PARTIAL / HOLD** — install authorized only after B1–B4 prerequisites.
- New doc `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`; updated SERVERS/NODES/PORTS/NETWORK/DEPLOYMENT/ROLLBACK and
  marked `HIDDIFY_API_CONTRACT.md` ports as not-verified-until-Phase-3.

## 2026-06-15 — Phase 0 + Phase 1

- Phase 0 clean-VPS verification signed off: **PASS** (gate passed before any build).
- Git repository initialized at the project root with a private origin (later pushed to `origin/main`, 25e5ddc).
- Added `.gitignore` and a pre-commit secret-scan hook.
- Added `.env.example` placeholder files (no real secrets).
- Created the full `docs/` skeleton per §32.
- Recorded naming and subdomain decisions in `DOMAINS.md`.
