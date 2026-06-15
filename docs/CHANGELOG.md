# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

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
