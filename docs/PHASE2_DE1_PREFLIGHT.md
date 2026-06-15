# PHASE 2-DE — de1 clean-VPS preflight (node-facts detected)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §34; [DECISIONS.md](DECISIONS.md) ADR-001/002; [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)
> **Result:** **PARTIAL** — SSH works and the node is **clean**, but the **OS is Ubuntu 20.04.6, not the required 22.04** (blocker for the supported Hiddify host install). RAM is under estimate.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T15:40:41Z |
| Node | `de1` — Germany / DE — `5.249.160.59` — status `planned/test` |
| SSH user verified | **root** (key-only) |
| Key used (not contents) | `/root/.ssh/unseenproxy_de1_ed25519` (private stays on Master) |
| Host key | pinned in Master `known_hosts` (StrictHostKeyChecking=yes) |
| Probe | **read-only inline SSH** — no files written, nothing installed/changed on `de1` |

## Provider-estimate vs node-detected (provenance)

| Field | Provider-estimate | Node-detected | Provenance | Verdict |
|---|---|---|---|---|
| **OS** | Ubuntu 22.04 LTS | **Ubuntu 20.04.6 LTS (focal)**, kernel 5.4.0-196 | `detected` | ❌ **MISMATCH (blocker)** |
| vCPU | 4 | 4 — Intel Xeon E5-2690 v4 @ 2.60GHz (KVM) | `detected` | ✓ match |
| RAM | 4 GB | **3.1 GiB total** (~2.6 GiB avail) + 1.9 GiB swap | `detected` | ⚠ under estimate |
| Disk | 25 GB SSD | 25 GB (`/dev/sda2`, 18 GB free, 25% used) | `detected` | ✓ match |
| Bandwidth | 30 TB/mo | not node-detectable | `estimate` | ⏳ unconfirmed (provider) |
| Public IP | 5.249.160.59 | `eth0 5.249.160.59/24`; egress `5.249.160.59` | `detected` | ✓ match |
| Region | Germany / DE | (not self-reported; per provider) | `estimate` | — |
| Hostname | — | `white-cobra-75504` | `detected` | — |

## Detected facts (sanitized)

- **OS/kernel:** Ubuntu 20.04.6 LTS (focal), kernel 5.4.0-196-generic, virtualization KVM.
- **CPU/RAM/disk:** 4 vCPU (Xeon E5-2690 v4); 3.1 GiB RAM (237 MiB used at idle) + 1.9 GiB swap; 25 GB disk (5.6 GB used).
- **Network:** `eth0` = `5.249.160.59/24`, default route via `5.249.160.1`; egress public IP `5.249.160.59` (matches).
- **Listening ports:** only **SSH `:22`** (public) and `systemd-resolved` `:53` (loopback). **80/443 free; no proxy ports.**
- **Firewall:** ufw **inactive**; iptables INPUT policy `ACCEPT`, 0 rules; nft absent. **No active host firewall.**
- **Tooling:** nginx / docker / certbot / nft **absent**; ufw, iptables, git, python3, curl, wget present.
- **Running services:** stock Ubuntu 20.04 set + `snapd` + `ssh` — **no** nginx/hiddify/docker/xray/proxy services.
- **Relevant unit files:** none matching nginx/hiddify/docker/xray/sing-box/marzban/happ/unseen/certbot.
- **Legacy artifact scan:** **CLEAN** — no marzban/happ/hiddify/xray/sing-box/unseenvpn artifacts under
  `/opt /etc/systemd/system /etc/nginx /var/www /root`.

## DNS plan for `node-de.unseen.click`

- **Plan:** add an **A record** `node-de.unseen.click → 5.249.160.59` (the node's own domain; never shown to
  customers). **Not changed in this task.** Must resolve before the Hiddify host installer issues TLS.

## Suitability for the Hiddify host install (Ubuntu 22.04)

- **OS is the blocker.** The node is **Ubuntu 20.04.6**, but the supported Hiddify host install (and ADR-001's chosen
  path) requires **Ubuntu 22.04 LTS**. Installing on 20.04 is **not** the supported path and risks the same class of
  failure we hit on the Master — do **not** proceed on 20.04.
- **Resources:** CPU (4) and disk (25 GB, 18 GB free) are adequate for a test/early node. **RAM 3.1 GiB** is on the
  low side for the full Hiddify stack (panel + MariaDB + Redis + xray + sing-box) but workable for early testing with
  the 1.9 GiB swap present — **watch RAM/disk** (alert 75%/90% once monitoring exists).
- **Cleanliness:** node is clean and free of legacy/proxy artifacts — good.

## Risks / blockers

- **BLOCKER — OS = 20.04, not 22.04.** Requires an **OS reinstall to Ubuntu 22.04 LTS** via the provider panel
  before Phase 3-DE. After reinstall the node is wiped, so: (a) the **Master public key must be re-added** to root
  `authorized_keys`; (b) the node's **SSH host key changes**, so the Master's `known_hosts` entry for `5.249.160.59`
  must be **refreshed** on the next connect (`ssh-keygen -R 5.249.160.59` then re-pin via `accept-new`) — otherwise
  SSH will warn of a host-key mismatch (expected, not an attack); (c) this **preflight is re-run**.
- **RAM under estimate** (3.1 GiB vs 4 GB) — non-blocking for testing; monitor.
- **No active firewall** + **password login still enabled** on the node — to be addressed during Phase 3-DE
  hardening (after key access is confirmed on the 22.04 rebuild). Not changed now (per task scope).
- **Bandwidth 30 TB** remains `estimate` (provider) — not node-verifiable.

## PASS / PARTIAL / FAIL

**PARTIAL.** SSH root key login works; the node is clean and adequately resourced (CPU/disk; RAM tight); ports/
firewall understood; DNS plan documented — **but the OS is Ubuntu 20.04, not the required 22.04**, which blocks the
supported Hiddify host install. Not a FAIL (node is reachable and clean), not a PASS (OS criterion unmet).

## Exact next recommended task

1. **Charles reinstalls `de1` to Ubuntu 22.04 LTS** (provider panel), then **re-adds the Master public key**
   (`ssh-ed25519 …unseen-proxy-master-to-de1` — see CHANGELOG) to root `authorized_keys`. (The reinstall changes the
   node's host key — the Master will refresh `known_hosts` for `5.249.160.59` on the next connect.)
2. **Re-run this Phase 2-DE preflight** to confirm OS 22.04, clean, key access, resources.
3. Then **Phase 3-DE**: Hiddify **supported host install** on 22.04 + live API-contract verification + one disposable
   test user + FAST1/FAST2/Secure inbound checks. **Phase 4 stays blocked** until that verified-live contract exists.
