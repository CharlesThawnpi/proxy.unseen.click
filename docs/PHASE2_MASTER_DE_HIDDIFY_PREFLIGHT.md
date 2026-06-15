# PHASE 2 — Protected Master/DE Hiddify Preflight

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §4.1 (co-location exception), §6 (nodes), §34 Phase 2
> **Status:** Preflight COMPLETE — **read-only**, no system changes made. Hiddify NOT installed.
> **Readiness decision:** **PARTIAL / HOLD** — install must not proceed until the manual prerequisites below are met.

This is the protective, read-only preflight for later co-locating the **DE Hiddify test node** on the **Master**
control-plane VPS (the documented §4.1 exception). It installs nothing and changes nothing. It records system
state, evaluates co-location risk, and produces a go/no-go decision for a *separate* future install task.

---

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T11:05:54Z |
| Hostname | `crimson-gorilla-49484` |
| Role | **Master control plane** (NOT disposable — must never be wiped/re-imaged/broken) |
| Intended use | Co-locate the **DE Hiddify node** here, starting as **`status=test`** (never `live` in this phase) |
| Customers | None exist yet |

## Scope of this task

- **Allowed:** read-only system inspection; project docs under `/opt/unseen-proxy/`; commit+push docs.
- **Forbidden (and not done):** no Hiddify/Docker/nginx/certbot/ufw/package install; no firewall/nginx/systemd/DB/
  `.env` changes; no Hiddify API calls; no SG/US node contact; no node marked live; no Phase 2 install; no Phase 3.

## Read-only checks performed

`hostnamectl`, `uname -a`, `uptime`, `nproc`, `/proc/cpuinfo`, `free -h`, `swapon --show`, `df -h`, `lsblk`,
`ss -tulpn`, `ufw status`, `iptables -S`, `nft list ruleset`, `systemctl list-units --state=running`,
`systemctl list-unit-files | grep -Ei 'nginx|hiddify|docker|xray|sing-box|marzban|happ|unseen'`,
`command -v` for nginx/docker/certbot/ufw/iptables/nft/git/python3/curl, a maxdepth-4 legacy `find`, and
`git status/log/remote` + a deploy-key `ls-remote`. No mutating command was run.

## Clean-build / legacy scan result

**CLEAN.** A maxdepth-4 scan of `/opt /etc/systemd/system /etc/nginx /var/www /root` for
`marzban|happ|xray|sing-box|singbox|hiddify|unseenvpn` returned only `/opt/unseen-proxy/docs/HIDDIFY_API_CONTRACT.md`
— an **authorized** project doc (matches `*hiddify*`), not a legacy artifact. No retired UNSEEN VPN / Marzban /
Happ / Xray / sing-box code, services, or configs are present. No `nginx|hiddify|docker|xray|sing-box|marzban|happ|unseen`
systemd unit files exist.

## Current disk / RAM / CPU summary

| Resource | Value | vs Appendix F.7 Master spec | Headroom |
|---|---|---|---|
| CPU | 4 vCPU — Intel Xeon E5-2680 v4 @ 2.40GHz (KVM/QEMU) | 4 vCPU ✓ | load avg ~0.05; idle |
| RAM | 15 GiB total, **~13 GiB available** (1.6 GiB used) | 16 GB ✓ | ample |
| Swap | 4.0 GiB (`/swap.img`), 0 B used | — | present (good) |
| Disk | `/dev/sda2` 100 GB, **86 GB free** (10% used) | 100 GB SSD ✓ | ample |
| OS / kernel | Ubuntu 24.04.4 LTS / 6.8.0-45-generic / x86-64 | — | current |

**Verdict:** resources are **sufficient** to co-locate a light **test** DE node (no real customers). Long-term
live headroom is re-evaluated against the §30.2.1 dashboard once metrics exist.

## Existing nginx / docker / certbot / Hiddify status

| Component | Installed? | Notes |
|---|---|---|
| nginx | **No** | Ports 80/443 are currently **free** — no web server owns them yet. |
| docker | **No** | Hiddify's standard installer is non-Docker; will install many host packages. |
| certbot | **No** | No TLS automation / no `/etc/letsencrypt`. |
| Hiddify Manager | **No** | Nothing installed; no hiddify units/dirs. |
| ufw / iptables / nft | binaries present | **No active ruleset** (see firewall summary). |
| git / python3 / curl | present | git origin is SSH; deploy-key auth OK. |

## Current service / port map

Public-facing listeners and the project's planned loopback ports:

| Port | Bind | Owner now | Planned use | Collision risk at install |
|---|---|---|---|---|
| 22/tcp | `0.0.0.0` + `[::]` | sshd | SSH admin | none (keep) |
| 53 (udp/tcp) | `127.0.0.x` | systemd-resolved | local DNS stub | none (loopback) |
| 43417, 22815/tcp | `127.0.0.1` | transient `MainThread` (tooling/agent harness, ephemeral) | not project services | none (loopback, ephemeral) |
| **80/tcp** | — | **FREE** | nginx (Master control-plane subdomains) **and** Hiddify wants it | ⚠ **HIGH — shared 80/443** |
| **443/tcp** | — | **FREE** | nginx TLS for api/bot/panel/app/sub **and** Hiddify TLS | ⚠ **HIGH — shared 80/443 + TLS ownership** |
| 8190/8191/8192/8197 | — | **FREE** | admin / portal / api / sidecar (loopback) | none now; confirm Hiddify doesn't claim them |
| Hiddify panel/proxy ports | — | unknown | Hysteria2/SS/VLESS-Reality inbounds + panel | **TBD — do not assume until Phase 3 audit** |

No Master application services are running yet (none built). The only public surface today is SSH.

## Current firewall summary

- **ufw:** `inactive`.
- **iptables (filter):** policies `INPUT/FORWARD/OUTPUT ACCEPT`, no rules.
- **nft:** empty ruleset.

➡ **There is no active host firewall.** Today only SSH is bound publicly, so exposure is limited *in practice*,
but any port a future install binds to `0.0.0.0` becomes immediately internet-reachable with no filtering. A
firewall/exposure plan is a prerequisite before opening Hiddify proxy ports.

---

## Co-location risk notes (Master control plane + DE proxy on one box)

1. **Control-plane starvation (resource contention).** Proxy traffic (CPU for crypto, RAM, bandwidth) shares the
   box with the brain (DB, bots, sidecar). *Test* load is negligible; the real risk appears only if this node is
   later promoted to `live`. Mitigation: keep `status=test`; watch Master headroom as first-class in the §30.2.1
   dashboard; DE is movable to its own VPS with no schema/code change (§6.1) if it grows.
2. **nginx / TLS ownership conflict (highest risk).** Hiddify Manager bundles its own web/proxy stack and TLS
   management and expects to own **80/443**. The Master control plane also needs 80/443 for the
   `api/bot/panel/app/sub` subdomains (§5, §8). Two systems cannot both own 443 unmediated. **This must be
   resolved by an explicit strategy before install** (options to evaluate in Phase 3: Hiddify on alternate
   ports behind a single shared reverse proxy; or Hiddify owns 443 and Master services are proxied through it;
   or split by SNI/host). **No assumption is made here.**
3. **Firewall exposure.** With no active firewall, a Hiddify install that binds proxy ports to `0.0.0.0` exposes
   them instantly. The installer *may also* enable/modify ufw/iptables itself — which could inadvertently affect
   SSH:22 or the planned loopback services. Need an exposure plan and a guarantee SSH stays reachable.
4. **Docker / package conflict.** Low (no Docker today), but the non-Docker installer pulls many system packages
   and could change Python/system libs the Master services will later depend on. Pin/record what it changes.
5. **Bandwidth / resource headroom.** 30 TB/mo budget (Appendix F.7) and idle CPU give ample test headroom; live
   promotion is a separate decision gated on dashboard evidence.
6. **Rollback difficulty.** The Hiddify installer changes nginx, systemd, firewall, and packages **host-wide**.
   On a non-disposable Master there is **no clean `apt remove` guarantee**. The only reliable rollback is a
   **provider snapshot taken immediately before install** (see ROLLBACK.md).

## Expected install blockers (must be cleared first)

- **B1 — 80/443 + TLS ownership undecided.** Blocking. Resolve the shared-port strategy (depends on the Phase 3
  audit of Hiddify's actual port/nginx/TLS behavior).
- **B2 — No provider snapshot.** Blocking on a non-disposable Master. Required before any invasive install.
- **B3 — No firewall/exposure plan.** Blocking. Define what stays closed/open and protect SSH:22.
- **B4 — Hiddify port/behavior unknown.** Phase 3 audit (`HIDDIFY_API_CONTRACT.md`) must verify real ports,
  nginx behavior, and whether it touches ufw/iptables — **no assumptions until then**.

## Required manual prerequisites before install

1. **Charles takes a provider snapshot** of the Master VPS and confirms it (B2). This is the rollback path.
2. Decide and document the **80/443 + TLS coexistence strategy** (B1) — informed by Phase 3.
3. Decide and document the **firewall/exposure plan** (B3), guaranteeing SSH stays reachable.
4. Complete the **Phase 3 Hiddify API & port audit** (B4) so the install is not guesswork.
5. Confirm the node will be created as **`status=test`** in `proxy_nodes` and never auto-promoted.

## Rollback / snapshot recommendation

**A provider/VPS snapshot before install is REQUIRED, not optional.** Because the installer mutates nginx,
systemd, firewall, and packages on the live control-plane host, in-place uninstall cannot be trusted to restore
the prior state. Snapshot → install → if anything destabilizes the control plane, restore the snapshot. Project
code/docs are independently safe in git (`origin/main`); the DB (when it exists) has its own §30.3 backup. See
[ROLLBACK.md](ROLLBACK.md).

## Readiness status

**PARTIAL / HOLD.** The preflight itself is a clean **PASS** (system inspected, capable, legacy-free, no changes
made), but **install must NOT proceed** until B1–B4 and the manual prerequisites are cleared. **Phase 2 stops here
and requires Charles's manual provider-snapshot confirmation** plus the port/TLS/firewall decisions before a
separate "Phase 2 protected Hiddify install on Master/DE" task is authorized.

## Phase 3 update (2026-06-15)

The Phase 3 audit plan ([PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md)) has researched B1/B3/B4 from
official Hiddify docs and is the live successor to this preflight's open blockers:
- **B1** is now **resolvable** — recommended **Option A** (Docker Hiddify on remapped ports behind the Master nginx)
  or **Option C** (separate DE VPS, lowest risk). Charles chooses.
- **B3** has a documented firewall/SSH-safety plan (Hiddify manages iptables; verify SSH from a 2nd session).
- **B4** is **reduced** (install path, host services, 24.04/Redis caveat, Docker coexistence now verified) but exact
  ports/units/API fields remain **[LIVE]**.
- **B2** (provider snapshot) is **still pending/manual** — unchanged.

Readiness stays **PARTIAL / HOLD** until Charles's option decision + the B2 snapshot + the live-verify checklist.

## Exact next recommended task

**Phase 3 — Hiddify API & subscription/port compatibility audit** (read-only probe of a pinned Hiddify version),
to produce the verified `HIDDIFY_API_CONTRACT.md` and the real port/nginx/TLS behavior needed to decide B1/B3/B4.
In parallel, **Charles takes and confirms a Master provider snapshot** (B2). Only after both is the protected
co-located install task authorized.
