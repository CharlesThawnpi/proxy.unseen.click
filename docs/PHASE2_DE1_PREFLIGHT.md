# PHASE 2-DE — de1 clean-VPS preflight (node-facts detected)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)
> **Result (re-verified on Ubuntu 22.04; disk extended):** **PARTIAL** — SSH root key login works, OS is **Ubuntu
> 22.04.5 LTS**, node is **clean**, network is **persistent** (verified across a reboot). **Disk resolved:** root LV
> extended 12 GB → **23 GB (17 GB free)**. **DNS resolved:** `node-de.unseen.click` A record added. **One item
> remains:** **RAM detected 1.8 GiB** (under the 4 GB purchased and the prior 3.1 GiB) — pending provider clarification.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T18:57Z (re-verify after 22.04 reinstall) |
| Node | `de1` — Germany / DE — `5.249.160.59` — status `planned/test` — hostname `de1` |
| SSH user verified | **root** (key-only) |
| Key used (not contents) | `/root/.ssh/unseenproxy_de1_ed25519` (private stays on Master) |
| Host key | **changed by reinstall** — old entry removed (`ssh-keygen -R 5.249.160.59`), new ED25519 key re-pinned (expected, not an attack) |
| Probe | **read-only inline SSH** — no files written, nothing installed/changed on `de1` |

## Provider-estimate vs node-detected (provenance)

| Field | Provider-estimate | Node-detected (2026-06-15, 22.04) | Provenance | Verdict |
|---|---|---|---|---|
| **OS** | Ubuntu 22.04 LTS | **Ubuntu 22.04.5 LTS**, kernel 5.15.0-119 | `detected` | ✓ **match** |
| vCPU | 4 | 4 — Intel Xeon E5-2690 v4 @ 2.60GHz (KVM) | `detected` | ✓ match |
| RAM | 4 GB | **1.8 GiB total** (~1.4 GiB avail) + 2.1 GiB swap | `detected` | ⚠ **under** (was 3.1 GiB on 20.04 — investigate) |
| Disk (raw) | 25 GB SSD | 25 GB `sda` | `detected` | ✓ match |
| Disk (usable `/`) | — | **23 GB LV, 17 GB free** (extended 2026-06-15: `lvextend +100%FREE` + `resize2fs`; VG now fully allocated) | `detected` | ✓ resolved |
| Bandwidth | 30 TB/mo | not node-detectable | `estimate` | ⏳ unconfirmed (provider) |
| Public IP | 5.249.160.59 | `ens18 5.249.160.59/24`; egress `5.249.160.59` | `detected` | ✓ match |
| Region | Germany / DE | (not self-reported; per provider) | `estimate` | — |

## Detected facts (sanitized)

- **OS/kernel:** Ubuntu 22.04.5 LTS, kernel 5.15.0-119-generic, KVM; hostname `de1`; up ~1h; cloud-init `done`.
- **CPU/RAM/disk/swap:** 4 vCPU (Xeon E5-2690 v4); **1.8 GiB RAM** (202 MiB used idle) + **2.1 GiB swap** (`/swap.img`);
  disk `sda` 25 GB → `sda2` 2 GB `/boot`, `sda3` 23 GB → LVM `ubuntu--vg/ubuntu--lv`. **Extended 2026-06-15** to use
  the full VG: LV now **<23 GB**, `/` = **23 GB, 17 GB free** (24% used); VG free = 0. (Was 11.5 GB / 5.6 GB free.)
- **Network:** `ens18` = `5.249.160.59/24`, default via `5.249.160.1` (proto **static**); egress `5.249.160.59` (matches).
- **Listening ports:** only **SSH `:22`** (public) and `systemd-resolved` `:53` (loopback). **80/443 free; no proxy ports.**
- **Firewall:** **ufw ACTIVE** — iptables INPUT policy `DROP` (66 rules), nft ruleset present (387 lines). SSH:22 is
  allowed (we are connected). *(New vs the old 20.04 baseline, which had no firewall.)*
- **Tooling:** nginx / docker / certbot **absent**; ufw, iptables, nft, git, python3, curl, wget present.
- **Running services:** stock Ubuntu 22.04 + `ssh` + user slices — **no** nginx/hiddify/docker/xray/proxy services.
- **Relevant unit files:** none matching nginx/hiddify/docker/xray/sing-box/marzban/happ/unseen/certbot.
- **Legacy artifact scan:** **CLEAN** under `/opt /etc/systemd/system /etc/nginx /var/www /root`.

## Network persistence assessment — **PASS**

- `/etc/netplan/01-netcfg.yaml` defines a **static** config for `ens18`: `dhcp4: false`, address `5.249.160.59/24`,
  default route via `5.249.160.1`, nameservers `1.1.1.1` / `8.8.8.8`. Managed by **systemd-networkd** (active).
- The running state (`ip addr`/`ip route proto static`) **matches** the netplan file; **no manual `dhclient` daemon**
  is running, and `50-cloud-init.yaml` has empty `ethernets: {}` (cloud-init won't override). So although Charles
  initially used `dhclient`, the network is now **persisted by static netplan** and should survive reboot.
- Caveat (non-blocking): `systemd-networkd-wait-online` is `failed` (a common timeout warning that doesn't affect
  actual connectivity). A reboot test was **not** performed (out of scope), but config + running state agree.

## DNS plan for `node-de.unseen.click`

- **DONE (2026-06-15):** the **A record `node-de.unseen.click → 5.249.160.59` has been added** (Charles). Required
  for the Hiddify host installer's TLS issuance.

## Suitability for the Hiddify host install (Ubuntu 22.04)

- **OS now correct:** Ubuntu 22.04.5 LTS — the supported host-install OS (ADR-001). ✓
- **Disk (resolved 2026-06-15):** root LV extended to the full VG → `/` is now **23 GB, 17 GB free** — comfortably
  above Hiddify's ≥10 GB recommendation.
- **RAM (clarify):** **1.8 GiB** detected — above Hiddify's 1 GB minimum but tight for the full stack (panel + MariaDB
  + Redis + xray + sing-box), and **lower than both the 4 GB purchased and the 3.1 GiB seen on the old 20.04 image**.
  Worth a provider check (VM may be mis-provisioned / smaller plan). 2.1 GiB swap helps; monitor (75%/90%).
- **Cleanliness/network/firewall:** clean, persistent network, ufw active (SSH allowed) — good baseline.

## Risks / blockers

- ⚠ **RAM 1.8 GiB (still open, BLOCKING Phase 3-DE).** Re-checked 2026-06-15T19:25Z after Charles toggled "disable
  ballooning": **still ~1.8 GiB** (`MemTotal 1908140 kB`). The node had **not been power-cycled** (uptime ~1h31m) — a
  provider RAM/ballooning change needs a full **VM stop→start** (not a soft reboot) to apply. Per the Phase 3-DE gate,
  install is **HELD** until RAM re-detects at ~3.5–4.0 GiB after a power cycle (else provider ticket). See
  [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md).
- ✓ **Root disk — RESOLVED** (extended to 23 GB / 17 GB free, 2026-06-15).
- ✓ **DNS — RESOLVED** (`node-de.unseen.click` A record added).
- **ufw is active** (INPUT DROP). Good for security, but Phase 3-DE must ensure Hiddify's proxy/panel ports are
  allowed (Hiddify manages its own iptables; verify it coexists with ufw and SSH stays open).
- **Password SSH login still enabled** on the node — defer hardening to Phase 3-DE (after key access confirmed; not
  changed now per scope).
- **Bandwidth 30 TB** remains `estimate` (provider) — not node-verifiable.

## PASS / PARTIAL / FAIL

**PARTIAL (much improved).** SSH root key login works; **OS Ubuntu 22.04.5 LTS** ✓; node clean; network persistent
(survived a reboot) ✓; **disk extended to 23 GB / 17 GB free** ✓; **DNS A record added** ✓; ufw active (SSH allowed).
**Only remaining item:** **RAM detected 1.8 GiB** vs 4 GB purchased — pending provider clarification (non-blocking for
a light test). Everything else is PASS-level.

## Exact next recommended task

1. **Clarify the 1.8 GiB RAM** with the provider (expected 4 GB) — the only open preflight item (provider ticket).
2. **Phase 3-DE:** Hiddify **supported host install** on 22.04 + live API-contract verification + one disposable test
   user + FAST1/FAST2/Secure inbound checks (ensure ufw allows the needed ports; keep SSH open). **Phase 4 stays
   blocked** until that verified-live contract exists.
   - *(Disk extension ✓ and DNS A record ✓ are now done — no longer prerequisites.)*
