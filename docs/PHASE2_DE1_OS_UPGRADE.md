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

## Update 2026-06-15T16:36Z — de1 is OFFLINE after a custom-ISO attempt (upgrade attempt = HOLD)

A follow-up task tried to diagnose/fix release-upgrade connectivity (Charles reported `do-release-upgrade` failing on
the console with "Failed to connect to https://changelogs.ubuntu.com/meta-release-lts" after a **custom ISO install
attempt that still booted into 20.04**). From the Master, **`de1` is now completely unreachable**:

- ICMP `ping`: **100% packet loss** (0/3).
- TCP **22, 1022, 80, 443**: all **closed/timeout**.
- SSH: `connect to host 5.249.160.59 port 22: Connection timed out`.

**Conclusion:** this is no longer a DNS/CA/APT issue — the **whole node is offline/unresponsive**, almost certainly
left in a broken state by the custom-ISO attempt (stuck in the installer, powered off, or networking misconfigured).
**SSH-based diagnosis/fix is impossible**, so per the task's Step-1 rule the agent **STOPPED**. No node changes, no
upgrade run. (The earlier `changelogs.ubuntu.com` failure is itself a sign de1's outbound networking was already
disrupted — both point to a node-networking/boot problem only the provider console can resolve.)

### Operator recovery steps (Charles — via provider panel / console)

1. **Check de1's power/boot state** in the provider panel: is it powered on? Is it stuck in the **ISO installer** /
   rescue, or did it boot with broken networking? Open the **console/VNC** to see the actual screen.
2. **Stop using custom ISO.** It hasn't taken and has left the node unreachable. Use the provider's **stock image
   "Reinstall / Rebuild → Ubuntu 22.04 LTS 64-bit (EN)"** instead — this is the agreed path ([decision above]) and
   sidesteps both the boot problem and the release-upgrade connectivity issue entirely. `de1` is empty; nothing to lose.
3. In the reinstall wizard, **add the Master public key** (`ssh-ed25519 …unseen-proxy-master-to-de1`, fingerprint
   `SHA256:jUYAdY0ONdXKzOg2s4OKO27yBGqLvBwapkEy25oA3+I`) so it boots key-ready.
4. If you instead just want it back online on 20.04 first (e.g. to retry in-place): from the console, fix
   networking/boot so the node pings and SSH:22 answers, then tell the agent — but **reinstall to 22.04 is the
   recommended and simpler resolution.**
5. Once de1 responds to ping/SSH again, tell the agent → it refreshes the (likely changed) host key, re-tests SSH,
   and re-runs the Phase 2-DE preflight.

**Result of the connectivity/upgrade attempt: HOLD** — node unreachable; recovery is an operator/console action.

## Exact next recommended task

**`de1` is currently OFFLINE — recover it first (operator/console).** Recommended: provider **Reinstall → Ubuntu
22.04 LTS (EN)** with the Master public key added in the wizard (steps above). Once de1 answers ping/SSH again, the
agent refreshes the host key, re-tests SSH, and **re-runs the Phase 2-DE preflight**. On PASS → **Phase 3-DE**
Hiddify supported host install + live API-contract verification. **Phase 4 stays blocked** until that verified-live
contract exists.
