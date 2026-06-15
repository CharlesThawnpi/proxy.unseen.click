# PHASE 3-DE — Hiddify host install + live verify on de1

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md)
> **Result:** **HOLD — Hiddify NOT installed.** The pre-install gate **STOPPED on the RAM check**: de1 still reports
> **~1.8 GiB** RAM after "disable ballooning" was toggled (gate requires ~3.5–4.0 GiB). All other gates passed.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T19:25Z |
| Node | `de1` — Germany / DE — `5.249.160.59` — status `planned/test` — hostname `de1` |
| SSH | root key login OK (`/root/.ssh/unseenproxy_de1_ed25519`); host key pinned |
| Probe | **read-only** — no install, no node changes |

## Pre-install gate — RESULT: STOP (RAM)

| Check | Result |
|---|---|
| Master git clean | PASS |
| SSH root key login | PASS |
| OS Ubuntu 22.04.x | PASS — **22.04.5 LTS** (kernel 5.15) |
| **RAM (re-detect after ballooning off)** | **FAIL — still ~1.8 GiB** (`MemTotal: 1908140 kB`, free shows 1.8Gi) + 2.1 GiB swap. Gate wants 3.5–4.0 GiB. |
| Disk root ~23 GB, ≥10 GB free | PASS — 23 GB, **17 GB free** (24% used) |
| Network static/persistent | PASS — `ens18 5.249.160.59/24`, default via `5.249.160.1`, egress `5.249.160.59` |
| DNS `node-de.unseen.click` → `5.249.160.59` | PASS — resolves from **both** Master and node |
| SSH:22 listening | PASS |
| UFW active + SSH allowed | PASS — `Status: active`, `22/tcp ALLOW IN Anywhere` |
| 80/443 free | PASS — only SSH:22 + loopback:53 listening |
| No nginx/docker/certbot/hiddify | PASS — all absent |
| Legacy scan | PASS — clean |
| Rollback path | node is fresh/rebuildable, no data; provider reinstall is acceptable rollback |

## Why HOLD — RAM still under-provisioned

Charles enabled **"Disable ballooning (dynamic RAM)"** in the provider panel, but the node **still detects ~1.8 GiB**.
The node **`uptime` is ~1h31m** — i.e. it has **not been power-cycled** since the panel change. A provider
memory/ballooning change almost always requires a **full VM stop → start** (a *soft* `reboot` from inside the OS does
**not** re-negotiate the host memory allocation). So the change is most likely **not yet applied**.

Per the task's explicit gate ("If still around 1.8 GiB, STOP"), **the agent did not install Hiddify** and made **no
node changes** (read-only gate only).

## Operator step (Charles)

1. In the provider panel, **fully stop `de1` and start it again** (power cycle, not a soft reboot) so the
   ballooning-disabled / full 4 GB allocation takes effect. Confirm the VM's **assigned memory** in the panel shows 4 GB.
2. When it's back up, tell the agent → it re-checks RAM (`free -h` / `/proc/meminfo`).
   - If RAM is now **~3.5–4.0 GiB** → proceed with the Hiddify host install (this Phase 3-DE).
   - If RAM is **still ~1.8 GiB** → it's a provider plan/config issue (the VM may genuinely be a 2 GB plan); **open a
     provider ticket** before installing. (Hiddify can run on ~1.8 GiB for light testing, but that's below what was
     purchased and tight for the full panel + MariaDB + Redis + xray + sing-box stack — decision deferred to Charles.)

## Fields pending (filled once install proceeds on adequate RAM)

| Field | Value |
|---|---|
| Hiddify version | _pending install_ |
| Install method | host installer for Ubuntu 22.04 (not Docker) — _pending_ |
| Admin-link storage path | `/root/hiddify-de1-admin.link` (`0600`, value never printed/committed) — _pending_ |
| API v2 base path / auth header | _pending Swagger_ |
| user create/update/get/list/disable | _pending_ |
| quota field + units / expiry / usage | _pending_ |
| subscription output formats / deep-link | _pending_ |
| FAST1/FAST2/Secure inbounds + ports | _pending_ |
| disposable test user | _pending (one, `disposable-test`, created+deleted)_ |

## Resources after gate (no install)

- RAM 1.8 GiB (+2.1 GiB swap); disk `/` 23 GB (17 GB free); only SSH:22 public; ufw active.

## Rollback path

n/a (nothing installed). de1 remains a clean, rebuildable test node; provider reinstall is the rollback if a future
install misbehaves.

## Remaining risks / blockers

- **BLOCKER (gate): RAM ~1.8 GiB** — needs a VM power-cycle to apply the ballooning-disable, then re-verify; escalate
  to provider if it stays 1.8 GiB.
- ufw active (good) — Hiddify ports must be allowed without closing SSH when install proceeds.
- Password SSH login still enabled — harden after install.

## PASS / PARTIAL / FAIL

**HOLD / PARTIAL.** Every gate passed **except RAM**; per the task's stop rule the agent did not install Hiddify.
Resume once de1 is power-cycled and RAM re-detects at the purchased level.

## Exact next recommended task

Charles **power-cycles `de1`** (stop→start) to apply the RAM change → tell the agent → agent **re-checks RAM**; if
≥~3.5 GiB, it proceeds with the **Hiddify supported host install on Ubuntu 22.04** + live API/Swagger contract
verification + one disposable test user + FAST1/FAST2/Secure checks (ufw allows ports, SSH stays open). **Phase 4
stays blocked** until that verified-live contract exists.
