# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-15 — Phase 3 (Hiddify Docker install attempt — PARTIAL/BLOCKED)

- With Charles's authorization (snapshot confirmed), the agent ran the **official pinned Docker install
  (v12.3.3)** from `/opt` → isolated `/opt/hiddify-manager`. Docker 29.5.3 installed; 3 containers came up.
- **Host stayed safe:** SSH:22 up throughout; iptables INPUT policy `ACCEPT` (Docker added only its own
  NAT/FORWARD chains; Hiddify firewall left OFF); only 80/443 published (bridge); project git clean.
- **Panel is NON-FUNCTIONAL:** 443 returns no response; logs show a **Redis AUTH mis-wiring** + **DB migration
  errors**; the `hiddifypanel` CLI **hangs** on app import. MariaDB reachable, `admin_user` row exists, but the
  web/API never started. → **Live API/Swagger/contract verification BLOCKED; no test user created.** No destructive
  fix attempted (conservative mandate). Empirically confirms the official "Docker not for permanent use" caveat.
- Secret-safe throughout: no admin link generated/printed/committed; install log `0600`; scratch removed.
- Updated `PHASE3_HIDDIFY_LIVE_VERIFY.md` (actual result), `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `NODES`,
  `SERVERS`, `PORTS`, `DEPLOYMENT`. **Decision needed:** host install on a separate DE VPS (Ubuntu 22.04, Option C)
  vs debug Docker vs teardown. Containers left as-installed.

## 2026-06-15 — Phase 3 (Hiddify live-verify PREP — operator install pending)

- **No install performed by the agent; no Hiddify API call; no system change.** Docs/scripts only.
- B2 provider snapshot **confirmed by Charles**; co-location-via-Docker chosen.
- Ran the **read-only pre-install safety gate** → **PASS** (git clean, SSH:22 listening, 80/443 free, no firewall,
  ~13 GiB RAM / 86 GB disk free, legacy-clean, Master ports free). Verified the environment is capable (root,
  internet) but **cannot hold an SSH-recovery session/console**; the official Docker install is **experimental +
  long-running**. Decision: **operator installs, agent verifies after**.
- Verified the **current official Docker install command** (`bash <(curl https://i.hiddify.com/docker/<version>)`;
  it installs Docker itself) and the official caveat: **Docker version "not recommended for permanent use"** — OK
  for a test node; engine revisited before any live promotion.
- New `PHASE3_HIDDIFY_LIVE_VERIFY.md` (operator runbook + safety-gate evidence + live-verify checklist + sanitized
  contract placeholders) and `scripts/phase3_post_install_probe.sh` (read-only, secret-free post-install probe).
  Updated `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `PHASE3_HIDDIFY_AUDIT_PLAN`, `DEPLOYMENT`, `NODES`.
  Status: **PARTIAL / HOLD** — node remains `status=test`.

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
