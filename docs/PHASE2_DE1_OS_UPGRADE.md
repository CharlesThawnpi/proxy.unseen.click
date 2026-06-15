# PHASE 2-DE — de1 OS to Ubuntu 22.04 (decision: clean reinstall, not in-place)

> **Source of truth:** [PHASE2_DE1_PREFLIGHT.md](PHASE2_DE1_PREFLIGHT.md), [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md), [DECISIONS.md](DECISIONS.md)
> **Result:** **HOLD — no in-place upgrade performed by the agent.** Decision (Charles): get to 22.04 via a **clean
> provider reinstall** (node is empty), then re-add the Master key and re-run preflight. No changes made to `de1`.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T15:59:12Z |
| Node | `de1` — `5.249.160.59` — Germany / DE — status `planned/test` |
| Starting OS | Ubuntu 20.04.6 LTS (kernel 5.4.0-196) |
| Target OS | Ubuntu 22.04 LTS |
| Method chosen | **Clean provider reinstall (operator)** — *not* in-place `do-release-upgrade` |
| Agent actions on node | **read-only pre-upgrade gate only**; nothing installed/changed/rebooted |

## Pre-upgrade safety gate — RESULT: PASS (read-only)

| Check | Result |
|---|---|
| Master git clean | PASS (clean) |
| SSH root key login to `de1` | PASS |
| OS currently 20.04.6 | confirmed |
| Hiddify installed? | **no** (none) |
| Customers / production data? | **none** |
| Disk ≥ 10 GB free | PASS — 18 GB free of 25 GB |
| RAM / swap adequate | 3.1 GiB RAM (2.6 avail) + 1.9 GiB swap |
| Only expected services | PASS — stock + ssh; only SSH:22 public |
| SSH:22 listening | PASS |
| 80/443 free | PASS |
| apt/dpkg healthy + unlocked | PASS (`dpkg --audit` rc 0, `apt-get check` rc 0, no lock) |
| Legacy artifacts | none (clean) |
| Note | `reboot-required` flag is **set** (pending reboot from earlier package updates) |

## Decision & rationale — reinstall, not in-place upgrade

The original task proposed an **in-place `do-release-upgrade`** over SSH. Given that **`de1` is confirmed empty**
(no data, no Hiddify, no customers), Charles chose the **clean reinstall** path instead. Rationale:

- **Same end-state, far less risk.** A fresh 22.04 image yields exactly what we need; an in-place release-upgrade
  over SSH (no console for the agent) risks dropping SSH, config-prompt stalls, or an unbootable node mid-upgrade.
- **Failure mode of in-place is *also* a reinstall.** If the SSH-driven upgrade broke the node, recovery would be a
  provider reinstall anyway — so reinstall-first is strictly better here.
- **Nothing to preserve.** No data/keys/configs of value exist on the node yet (the Master holds the authoritative
  state for nodes, §6.1).

**Therefore the agent did NOT run any upgrade commands.** Only the read-only gate above was executed on `de1`.

## Commands run (sanitized)

- On the Master: `git status`. 
- On `de1` (read-only, over SSH): `/etc/os-release`, `uname -r`, `df -h /`, `free -h`, `dpkg --audit`,
  `apt-get check`, `ss -tulpn`, presence checks for hiddify/nginx/docker/xray/sing-box, a maxdepth legacy `find`,
  and the `reboot-required` flag. **No mutating command, no reboot, no install.**

## Operator steps for the reinstall (Charles)

1. **Reinstall `de1` to Ubuntu 22.04 LTS** via the VPS provider panel (no data to preserve).
2. **Re-add the Master public key** to root `authorized_keys` (the reinstall wipes it):
   `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIABHKgQZkRTmmQw5D0ECI+SljBYeCBqXSoOLwDttg7be unseen-proxy-master-to-de1`
   (fingerprint `SHA256:jUYAdY0ONdXKzOg2s4OKO27yBGqLvBwapkEy25oA3+I`). The **private** key stays on the Master.
3. The reinstall **changes the node's SSH host key** — on the next connect the Master refreshes `known_hosts`
   (`ssh-keygen -R 5.249.160.59` then re-pin via `accept-new`); a host-key-mismatch warning is **expected**, not an attack.
4. Tell the agent when done → the agent **re-runs the Phase 2-DE preflight** to confirm 22.04 + clean + key access +
   resources, recording detected facts.

## PASS / PARTIAL / FAIL

**HOLD.** No upgrade executed by the agent (by decision). The OS blocker is resolved by the operator reinstall above,
then verified by a re-run of `PHASE2_DE1_PREFLIGHT.md`. Not a FAIL (node healthy/clean), not a PASS (still on 20.04
until the reinstall + verification complete).

## Exact next recommended task

After Charles reinstalls `de1` to **Ubuntu 22.04** and re-adds the Master public key: **re-run the Phase 2-DE
preflight** (agent refreshes the changed host key). On PASS → **Phase 3-DE** Hiddify supported host install + live
API-contract verification + one disposable test user + FAST1/FAST2/Secure checks. **Phase 4 stays blocked** until
that verified-live contract exists.
