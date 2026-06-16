# PHASE 4 — de1 pre-live tuning & security hardening (test-safe)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §8, §31; [DECISIONS.md](DECISIONS.md);
> [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md); [SECURITY.md](SECURITY.md); [PORTS.md](PORTS.md); [ROLLBACK.md](ROLLBACK.md)
> **Status:** **PARTIAL — node made safer; LIVE STILL BLOCKED on leaked-key rebuild.** No customers, no subscriptions,
> no live provisioning. de1 stays `status=test`.
>
> ## ✅ Phase 9 update (2026-06-16): leaked-key blocker CLEARED by fresh rebuild
> The `REBUILD_REQUIRED_BEFORE_LIVE` / `leaked_key_rebuild_pending` blocker recorded below is **CLEARED**. Charles did
> a fresh provider reinstall (Ubuntu 22.04.5) and a clean Hiddify v12.3.3 host reinstall was verified — regenerating
> all node secrets. SSH was re-hardened (password-auth off, key-only), the API v2 contract re-verified, and a
> disposable-user lifecycle passed. `config.LEAKED_KEY_REBUILD_PENDING=False`; the seed `node_live_blockers` row is now
> `realdevice_protocol_test_pending`. **de1 stays `status=test`**; the remaining pre-live requirement is a real-device
> FAST1/FAST2/Secure connect PASS (see [PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md)).

## Run metadata
- Date/time (UTC): 2026-06-16T03:50Z
- Scope: harden `de1` and move it closer to live-readiness **without** creating real customers/subscriptions or doing
  any live Hiddify mutation — verify ports/firewall, keep SSH working, disable SSH password login, resolve-or-document
  the leaked-key issue, prepare sanitized real-device test instructions. All actions were read-only except the SSH
  hardening drop-ins (reversible, verified) and pinning the node host key in the Master's `known_hosts`.
- **Out of scope (NOT done):** marking de1 live, real customers/subscriptions, live Hiddify create/update/delete,
  starting bot/admin/portal/API/sidecar, Brain API, SG/US nodes, payments, SSH port change, disabling root key login.

## Node identity
- Node: **de1**
- Domain: **node-de.unseen.click**
- IP: **5.249.160.59**
- Region: DE / Germany
- Status: **test** (unchanged; not live)
- OS: Ubuntu 22.04.5 LTS · Hiddify v12.3.3 host install
- SSH host key (public, for pinning): `ED25519 SHA256:lsD6hjAKLOdH/jqQZ28Ps0/1NLW5fW6/aV+nuwxn3gg`
  — now pinned in the Master's `/root/.ssh/known_hosts` so future connections can use `StrictHostKeyChecking=yes`.

## Pre-check results
- **SSH root key login:** works (key-only; `BatchMode=yes` so a failed key would NOT fall back to a password). Verified
  again under `StrictHostKeyChecking=yes` after pinning the host key.
- **OS / uptime:** Ubuntu 22.04.5 LTS, kernel 5.15.0-119, up ~10h.
- **Hiddify services (all `active`):** hiddify-nginx, hiddify-haproxy, hiddify-xray, hiddify-singbox, hiddify-panel,
  hiddify-panel-background-tasks, hiddify-redis, hiddify-dnstm-router, hiddify-ss-faketls, mariadb, ssh. (Stock
  `redis-server` is inactive — Hiddify uses its own `hiddify-redis` unit.)
- **Panel reachable:** `https://5.249.160.59/` → HTTP 200 via HAProxy/nginx (TLS front). Admin path **not** probed/printed.
- **SSH :22:** listening (`0.0.0.0` + IPv6) and allowed by both ufw and Hiddify's iptables.
- **Disk:** `/` 23 GB, 37% used (~14 GB free). **RAM:** 3911 MB total, ~2890 MB available at check (idle); swap 2.2 GB.
- **de1 status:** remains `test` in the Master seed (`backend/seed.py`); no DB promotion.

## Firewall / port results — NO CHANGE REQUIRED
Both ufw and Hiddify use the **same nf_tables backend** (`iptables-nft`), so there is one coherent ruleset. In the
`INPUT` chain, **Hiddify's explicit `ACCEPT` rules sit ahead of ufw's chains**, so required ports are accepted before
ufw's default-deny is ever reached. ufw provides default-deny for everything else, and SSH is allowed by both.

External reachability verified from the Master (TCP connect only, **no proxy payloads sent anywhere**):

| Port | Proto | Result | Note |
|---|---|---|---|
| 22 | tcp | **OPEN** | SSH (kept) |
| 80 | tcp | **OPEN** | ACME / redirect |
| 443 | tcp | **OPEN** | panel/sub + VLESS-Reality front; TLS → HTTP 200 |
| 443 | udp | open (Hiddify ACCEPT) | Hysteria2/QUIC — **needs real-device test** (not TCP-probeable) |
| 55573 | tcp | **OPEN** | Hiddify proxy inbound |
| (dynamic UDP/TCP inbounds) | — | open (Hiddify ACCEPT) | Hysteria2/TUIC/etc; **real-device test** |
| 8388 | tcp/udp | **filtered (by design)** | `ss-server` binds **loopback only**; Shadowsocks reaches clients via HAProxy/faketls over 443, not raw 8388 — correct, do **not** open it |

3306 (mariadb) and 6379 (redis) are loopback-only. **No ufw rule was added or removed** — opening the dynamic
Hiddify ports in ufw would be redundant (already accepted) and they are regenerated on rebuild anyway.

## SSH hardening result — PASS
- **Trap found & handled:** `/etc/ssh/sshd_config.d/50-cloud-init.conf` set `PasswordAuthentication yes`. Because sshd
  uses the **first** value of each keyword and `50-` sorts before `99-`, a `99-` drop-in alone would **not** take
  effect. So: the cloud-init line was **neutralized** (backed up to `/root/50-cloud-init.conf.bak-unseen-<ts>` on the
  node, replaced with a comment), and `/etc/cloud/cloud.cfg.d/99-unseen-ssh.cfg` (`ssh_pwauth: false`) prevents
  cloud-init re-enabling it on a future boot.
- **Drop-in created:** `/etc/ssh/sshd_config.d/99-unseen-proxy-hardening.conf` →
  `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`.
- **Root key login intentionally kept** (`PermitRootLogin without-password`). SSH port unchanged.
- **Safety:** a persistent ControlMaster session was held open throughout as a revert path; `sshd -t` validated syntax;
  `sshd -T` confirmed `passwordauthentication no` **before** reloading; `systemctl reload ssh` (graceful, no dropped
  connections) was used.
- **Verified after reload:** a fresh independent key login succeeds (`StrictHostKeyChecking=yes`, BatchMode); a
  password-only attempt (`PreferredAuthentications=password,PubkeyAuthentication=no`) is **refused** with
  `Permission denied (publickey)`; all Hiddify services remain `active`.

## Hiddify service health result — PASS
All Hiddify units `active` both before and after the SSH reload (panel/nginx/haproxy/xray/singbox/redis/mariadb/
background-tasks/ss-faketls/dnstm-router). Panel front returns HTTP 200. No service was restarted except a graceful
`reload` of `ssh`.

## Leaked-key handling result — REBUILD_REQUIRED_BEFORE_LIVE
The earlier incident exposed the Hiddify **default-user** secrets (ed25519 private key, WireGuard keys, UUID) and
potentially server protocol material (Reality keypair/short-id) in terminal output (never committed to git; test node).

Investigation (read-only, **no secret values printed**): Hiddify exposes `menu.sh` ("Reinstall the server"),
`reset-owner-password` (admin **password** only — does **not** rotate the leaked proxy/protocol secrets), and
`apply_configs.sh`. There is **no clearly-documented, safe, surgical command** to regenerate the leaked
default-user/server protocol keys in place; the only paths that would rotate them are a reinstall/rebuild
(destructive, interactive). Per project rules ("do not improvise; do not hand-edit private keys"):

- **Decision: `REBUILD_REQUIRED_BEFORE_LIVE`.** The leaked secrets are treated as compromised. Before de1 serves any
  real customer / goes live, **rebuild the node** (provider reinstall of Ubuntu 22.04 → re-add the Master SSH key →
  re-run preflight → fresh Hiddify host install under the default umask 022 → re-apply this hardening), which
  regenerates all server/user secrets. A surgical regenerate may be substituted later only if a Hiddify-supported,
  non-destructive command is confirmed.
- **Phase 4/5 dry-run work may continue** on de1 as a test node (no real customers). The **first** real
  customer / live provisioning is **blocked** until rebuild (or a confirmed safe regeneration).

## Real-device testing instructions for Charles (sanitized) — `#TASK_for_Charles`
Manual, on a real phone/PC. **Do not paste any subscription/proxy link, QR, or admin path into ChatGPT, GitHub,
logs, or any third-party tester.** Report back **PASS/FAIL per protocol + rough behavior only** (no links).

1. From the de1 Hiddify **panel** (admin link you hold privately at `/root/hiddify-de1-admin.link`), copy a **test
   user's** subscription link manually (do not share it).
2. Open the **Hiddify app** on the device → import that subscription link.
3. Test each profile and note PASS/FAIL + approximate speed/latency:
   - **FAST1 / Hysteria2** (UDP/QUIC — this is the one the Master can't probe; your test is the real signal).
   - **FAST2 / Shadowsocks** (reaches you via 443/faketls, not raw 8388).
   - **Secure / VLESS-Reality** (443 SNI front).
4. Report only: `FAST1=PASS/FAIL`, `FAST2=PASS/FAIL`, `Secure=PASS/FAIL`, plus a one-line behavior note.
5. **Reminder:** these tests are on **test-node keys that are slated for rebuild** — don't rely on them for anything
   real; treat any link as disposable.

## Remaining risks
- **Leaked test-node keys remain on the node** until rebuild — hence LIVE is blocked (above).
- **UDP/Hysteria2 + dynamic inbounds** are accepted by Hiddify's firewall but only **real-device** testing confirms
  end-to-end reachability (carrier/UDP path); the Master can't TCP-probe them.
- **RAM is balloon-dynamic** (~1.8 GB idle, can deflate toward ~3.8 GB under load) on a 4 GB box — **accepted risk**
  (Charles); ~2.9 GB free at check, 2.2 GB swap present. Lock/limit before heavy live load.
- **Firewall is Hiddify-managed and order-dependent** (its ACCEPTs precede ufw). A future Hiddify `apply_configs` or
  ufw change could reorder rules — re-verify reachability after any firewall-touching operation.
- de1 pre-live tuning items still open beyond this task: confirm RAM lock approach for live; re-verify all served
  inbounds after the rebuild.

## PASS/PARTIAL/FAIL
**PARTIAL.** Firewall verified (no change needed), SSH password login hardened off (root key-only, verified), services
healthy, host key pinned — but the **leaked-key issue forces a rebuild before live**, so de1 is *safer* but not
*live-ready*. de1 stays `status=test`.

## Exact next recommended task
**Either** continue backend (Phase 5 bot foundation / Phase 4C provisioning wiring — all dry-run, de1 as test node is
fine), **or** when Charles wants de1 live: schedule the **de1 rebuild** (provider reinstall → re-key SSH → preflight →
fresh Hiddify install under umask 022 → re-apply this hardening → fresh least-privilege service admin API key →
disposable-user verify), which clears the leaked-key blocker. Live promotion remains Charles-gated.
