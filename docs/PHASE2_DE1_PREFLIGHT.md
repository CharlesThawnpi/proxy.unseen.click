# PHASE 2-DE — de1 clean-VPS preflight (node-facts detected)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)
> **Result (re-verified on Ubuntu 22.04):** **PARTIAL** — SSH root key login works, OS is now **Ubuntu 22.04.5 LTS**, node is **clean**, and the network config is **persistent**. Two resource concerns before the Hiddify install: **RAM detected 1.8 GiB** (under the 4 GB estimate and the prior 3.1 GiB reading) and the **root LV is only ~12 GB (5.6 GB free)** of the 25 GB disk. Not a FAIL; not a clean PASS.

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
| Disk (usable `/`) | — | **~12 GB LV, 5.6 GB free** (LVM `ubuntu--vg`; ~11.5 GB unallocated in VG) | `detected` | ⚠ **root LV undersized** |
| Bandwidth | 30 TB/mo | not node-detectable | `estimate` | ⏳ unconfirmed (provider) |
| Public IP | 5.249.160.59 | `ens18 5.249.160.59/24`; egress `5.249.160.59` | `detected` | ✓ match |
| Region | Germany / DE | (not self-reported; per provider) | `estimate` | — |

## Detected facts (sanitized)

- **OS/kernel:** Ubuntu 22.04.5 LTS, kernel 5.15.0-119-generic, KVM; hostname `de1`; up ~1h; cloud-init `done`.
- **CPU/RAM/disk/swap:** 4 vCPU (Xeon E5-2690 v4); **1.8 GiB RAM** (202 MiB used idle) + **2.1 GiB swap** (`/swap.img`);
  disk `sda` 25 GB → `sda2` 2 GB `/boot`, `sda3` 23 GB → LVM `ubuntu--vg/ubuntu--lv` **11.5 GB** mounted `/` (12 GB,
  **5.6 GB free**, 49% used). **~11.5 GB of the VG is unallocated** (Ubuntu live-server default).
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

- **Plan:** add an **A record** `node-de.unseen.click → 5.249.160.59` (node's own domain; never shown to customers).
  **Not changed in this task.** Must resolve before the Hiddify host installer issues TLS.

## Suitability for the Hiddify host install (Ubuntu 22.04)

- **OS now correct:** Ubuntu 22.04.5 LTS — the supported host-install OS (ADR-001). ✓
- **Disk (action needed):** Hiddify recommends **≥10 GB**; `/` currently has only **5.6 GB free**. **Before installing,
  extend the root LV into the ~11.5 GB unallocated VG space** (`lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv &&
  resize2fs …`) to reach ~23 GB. Safe/standard, but a **node change** — out of scope here; do it as the first step of
  Phase 3-DE (or a small authorized task).
- **RAM (clarify):** **1.8 GiB** detected — above Hiddify's 1 GB minimum but tight for the full stack (panel + MariaDB
  + Redis + xray + sing-box), and **lower than both the 4 GB purchased and the 3.1 GiB seen on the old 20.04 image**.
  Worth a provider check (VM may be mis-provisioned / smaller plan). 2.1 GiB swap helps; monitor (75%/90%).
- **Cleanliness/network/firewall:** clean, persistent network, ufw active (SSH allowed) — good baseline.

## Risks / blockers

- ⚠ **RAM 1.8 GiB** — materially under the 4 GB estimate *and* the earlier 3.1 GiB reading. Non-blocking for a light
  test, but **clarify with the provider** whether the VM has the purchased 4 GB; tight for production proxy load.
- ⚠ **Root LV ~12 GB / 5.6 GB free** — below Hiddify's 10 GB rec. **Extend the LV before Hiddify install.**
- **ufw is active** (INPUT DROP). Good for security, but Phase 3-DE must ensure Hiddify's proxy/panel ports are
  allowed (Hiddify manages its own iptables; verify it coexists with ufw and SSH stays open).
- **Password SSH login still enabled** on the node — defer hardening to Phase 3-DE (after key access confirmed; not
  changed now per scope).
- **Bandwidth 30 TB** remains `estimate` (provider) — not node-verifiable.

## PASS / PARTIAL / FAIL

**PARTIAL.** SSH root key login works; **OS is Ubuntu 22.04.5 LTS** ✓; node is clean; network is persistent (static
netplan); ports/firewall understood; DNS plan documented. **Held back from PASS by resource items:** RAM detected
**1.8 GiB** (under estimate/prior — clarify) and root LV **5.6 GB free** (extend before Hiddify). Both are
addressable and non-blocking to *document*, but should be resolved before the Phase 3-DE host install.

## Exact next recommended task

1. **(Resource fixes before Hiddify)** Extend the root LV into the unallocated VG (`lvextend` + `resize2fs`) so `/`
   has ample space; and **clarify the 1.8 GiB RAM** with the provider (expected 4 GB). These are small authorized
   node-ops / a provider ticket.
2. **DNS:** add `node-de.unseen.click → 5.249.160.59` (A record) so TLS issuance works at install time.
3. **Phase 3-DE:** Hiddify **supported host install** on 22.04 + live API-contract verification + one disposable test
   user + FAST1/FAST2/Secure inbound checks (ensure ufw allows the needed ports; keep SSH open). **Phase 4 stays
   blocked** until that verified-live contract exists.
