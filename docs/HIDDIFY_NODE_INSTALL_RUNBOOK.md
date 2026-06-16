# HIDDIFY NODE INSTALL RUNBOOK (reusable)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §6, §8, §14, §31; [DECISIONS.md](DECISIONS.md)
> ADR-001/002/003; derived from the **successful de1 rebuild/install**
> ([PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md](PHASE9_DE1_REBUILD_FRESH_HIDDIFY.md), [PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md](PHASE3_DE1_HIDDIFY_LIVE_VERIFY.md)).
> **Status:** baseline install method for **all future Hiddify nodes** (US, SG1, SG2, future regions).
> **Created:** 2026-06-16 (UTC) / 2026-06-16 19:29 MMT (Asia/Yangon, UTC+06:30).

## 1. Purpose

A reusable, secret-safe guide for bringing up a new Hiddify proxy node. It encodes exactly **how the de1 install
finally succeeded**, the problems hit along the way, and what every future node (`us1`, `sg1`, `sg2`, …) must do **from
the start** so the same issues are not repeated. Follow this end to end; do not improvise around the gates.

**Non-negotiables (from the plan + ADRs):**
- A node is a **dedicated VPS**, never co-located on the Master ([DECISIONS.md](DECISIONS.md) ADR-001). The Master is
  **control-plane only** and carries no proxy traffic.
- Use the **supported Hiddify host installer on Ubuntu 22.04**, **not** Docker (ADR-001; Docker-on-Master failed and
  Hiddify labels Docker "not for permanent use").
- A node is **data, not code**: it is a `proxy_nodes` row + per-node secret handles in `.env`. Nothing about a node
  (IP, hostname, region, existence) is hardcoded.
- A node starts **`status=test`** and is **never** auto-promoted; live promotion is **Charles-gated**.
- **Dry-run first; secrets never printed/committed; never fabricate a PASS.**

## 2. Success pattern from de1 (the order that worked)

Do these in order. Each is a gate — if one fails, STOP and report PARTIAL/HOLD rather than improvising.

1. **Dedicated node VPS, not the Master.** Fresh VPS in the target region.
2. **Ubuntu 22.04.x Server** (official Hiddify OS; the installer refuses < 22.04). Not 24.04.
3. **Confirm SSH root key access from the Master** using the node's managed key
   `/root/.ssh/unseenproxy_<node>_ed25519` (key-only; private half lives on the Master, `0600`, never in git).
4. **Refresh `known_hosts` after a provider reinstall** (the host key changes): `ssh-keygen -R <node-ip> -f
   /root/.ssh/known_hosts`, then reconnect with `-o StrictHostKeyChecking=accept-new`. Refresh **only** that node's entry.
5. **Verify DNS before install:** `getent hosts node-<region>.unseen.click` resolves to the node's IP.
6. **Verify 80/443 are free** before install (`ss -tulpn`): only SSH:22 + loopback resolver should listen.
7. **Verify a clean node:** no legacy/proxy artifacts (`marzban`, `happ`, `hiddify`, `xray`, `sing-box`, old UNSEEN VPN),
   no nginx/docker/certbot already present.
8. **Verify disk free space** (`df -h /`, `vgs`, `lvs`). Hiddify's host install is heavy — require **≥10 GB free**.
9. **Grow disk/LVM first if needed** (de1 shipped with the LV under-allocated + later got extra storage). With explicit
   approval, online/non-destructively: `growpart /dev/sda 3` → `pvresize /dev/sda3` → `lvextend -l +100%FREE
   /dev/<vg>/<lv>` → `resize2fs /dev/<vg>/<lv>`. Back up the partition table first (`sfdisk -d /dev/sda > backup`).
10. **Verify egress IP** matches the node (`curl -4 https://ifconfig.me`).
11. **Verify actual RAM** (`free -h`, `/proc/meminfo`) — provider ballooning can mislead; record the real value.
12. **Use the Hiddify host installer, version-pinned, NOT Docker.** Replicate `download.sh <version> --no-gui` by
    fetching `common/hiddify_installer.sh` + `common/utils.sh` from the pinned **git tag** and running
    `hiddify_installer.sh <version> --no-gui`. Pin the **same version** the project has verified (currently
    **v12.3.3**); never `latest`.
13. **Run the installer under normal `umask 022`.** (A restrictive umask poisons perms — see §3.) Run it **detached**
    (`setsid … >/root/hiddify-<node>-install.log 2>&1`) so an SSH drop cannot kill a mid-install; poll the log.
14. **Store the admin link only in a root-owned `0600` file outside git:** `/root/hiddify-<node>-admin.link` (via the
    venv CLI `hiddifypanel admin-links`, redirected to the file — **never** to stdout). Use it internally; never print it.
15. **Verify services/panel/API after install:** all `hiddify-*` units + mariadb + redis `active`; 443 tcp/udp + 80 up.
16. **Apply the bounded `marshmallow==3.26.1` pin ONLY if the verified API/OpenAPI issue appears** (see §3). Confirm
    first (versions + live 404s), then `uv pip install --python /opt/hiddify-manager/.venv*/bin/python
    "marshmallow==3.26.1"` and `systemctl restart hiddify-panel`. Document it; re-apply after Hiddify updates.
17. **Create/verify/delete one disposable user** to confirm the API contract (see §6 — sanitized).
18. **Verify FAST1/FAST2/Secure inbounds present** from generated config/service state (names/counts only, no keys).
19. **Re-apply SSH hardening after install** (the reinstall resets it — see §3 first-match-wins note).
20. **Verify firewall/ports after install** (Hiddify manages its own iptables; confirm SSH:22 + 80/443 + 443/udp).
21. **Keep node `status=test`** in the Master DB until Charles approves live. Record detected facts in the
    `proxy_nodes` row.

## 3. Problems discovered on de1, and the lessons

| # | Problem | Lesson / what future nodes must do |
|---|---|---|
| 1 | Master/Hiddify **co-location** was risky and invasive on the protected control plane. | **Never co-locate.** Master = control-plane only (ADR-001). Always a dedicated node VPS. |
| 2 | **Docker** Hiddify on the Master was non-functional (Redis AUTH mis-wiring + first-boot DB migration errors). | **Use the host installer**, not Docker. Docker is "not for permanent use" per Hiddify. |
| 3 | Provider **OS/network** did not match expectations (shipped 20.04; needed reinstall to 22.04). | **Always preflight.** Confirm Ubuntu 22.04.x before anything else; reinstall if wrong. |
| 4 | Custom ISO/**network** needed static netplan troubleshooting to persist across reboot. | Verify a **persistent static netplan** (dhcp off, systemd-networkd); confirm egress + reboot-survival. |
| 5 | Provider **RAM ballooning** misled idle readings (~1.8 GiB idle vs ~3.8 GiB under load). | **Verify actual memory**; treat balloon as a risk; lock full RAM before production. |
| 6 | **Disk/LVM too small** after install (LV under-allocated; only ~5 GB free). | **Verify disk and extend BEFORE Hiddify** (growpart→pvresize→lvextend→resize2fs); require ≥10 GB free. |
| 7 | **`umask 077`** when launching the installer poisoned installer/uv-cache/venv perms (700/600 → unusable), needing a remediation cascade. | **Always `umask 022`** before launching third-party installers. Never a restrictive umask. |
| 8 | Hiddify v12.3.3 **API/OpenAPI returned 500/404** (apiflask 3.0.2 declares only `marshmallow>=3.20`, so a fresh install pulls **marshmallow 4.x**, which breaks API-v2 blueprint registration → every `/api/v2/*` 404s). | Apply the bounded **`marshmallow==3.26.1`** pin **inside the Hiddify venv** (the installer's own commented workaround) + restart `hiddify-panel`. **Re-apply after any Hiddify update** that reinstalls marshmallow 4.x. |
| 8b | API path confusion: the admin **UUID is in the header, not the URL path**. `hiddifypanel admin-path` returns `/<proxy_path>/<admin_uuid>/` (UI link), but the **API base is `https://<domain>/<proxy_path>/api/v2/admin/`** with header `Hiddify-API-Key: <admin-uuid>`. Hitting the bare IP/wrong host returns the **decoy/camouflage** site. | Build API URLs as `<proxy_path>/api/v2/admin/…` (UUID in header). Use the configured domain/host. |
| 9 | **Leaked default-user/server protocol secrets** on a test node had no safe surgical regen. | **Rebuild the node** (provider reinstall) before live if any protocol secret leaks; treat leaked secrets as compromised. |
| 10 | **Firewall** behavior changed once Hiddify took over iptables (ufw vs Hiddify-managed rules). | **Verify firewall after install:** SSH:22 stays open; 80/443 tcp + 443 udp permitted; don't run a competing ruleset that fights Hiddify. |
| 11 | **Real-device protocol connect** (Hysteria2/QUIC, Reality) can't be fully verified server-side. | A **real-device test is still required** before live (`realdevice_protocol_test_pending`); document it as a #TASK_for_Charles. |
| 12 | SSH **password auth** came back enabled after the reinstall (cloud-init `50-cloud-init.conf`, first-match-wins). | Re-harden after install: neutralize cloud-init's `PasswordAuthentication yes` **in place** (a `99-` drop-in does NOT win — OpenSSH is first-match) + `ssh_pwauth: false`; verify key login + password refusal. |

## 4. Future node checklist (copy per node)

- [ ] Provider VPS purchased and named (`<node>` = `us1` / `sg1` / `sg2` / …).
- [ ] DNS planned and created: `node-<region>.unseen.click` → node IP.
- [ ] Master→node SSH key created/installed (`/root/.ssh/unseenproxy_<node>_ed25519`, `0600`).
- [ ] `known_hosts` refreshed for this node (after any reinstall).
- [ ] OS verified **Ubuntu 22.04.x** Server.
- [ ] IP / egress verified (egress == node IP).
- [ ] DNS resolves to the correct IP (Master + node).
- [ ] Disk free **≥10 GB** verified; LVM grown first if short.
- [ ] RAM actual value verified (balloon noted).
- [ ] Clean-node scan (no legacy/Hiddify/Marzban/Happ/Xray/sing-box; no nginx/docker/certbot).
- [ ] 80/443 free pre-install.
- [ ] Install Hiddify **host** method, **version-pinned** (match the project's verified version), under **umask 022**, detached.
- [ ] Admin link saved to `/root/hiddify-<node>-admin.link` (`0600`, root); value never printed/committed.
- [ ] Services verified active (hiddify-* + mariadb + redis); 443 tcp/udp + 80 up.
- [ ] API contract verified (auth header; admin base `/<proxy_path>/api/v2/admin/`; **units GB**); apply marshmallow pin only if the issue appears.
- [ ] Disposable user create → get → patch → delete → re-GET 404 (sanitized).
- [ ] FAST1 (Hysteria2) / FAST2 (Shadowsocks) / Secure (VLESS-Reality) inbounds present.
- [ ] SSH hardening re-applied (password auth off, key-only, port unchanged; verified).
- [ ] Firewall/ports verified (SSH safe; 22/80/443 + 443/udp).
- [ ] Docs + `proxy_nodes` row + SOURCE_OF_TRUTH updated.
- [ ] Real-device protocol test done or clearly documented as pending.
- [ ] **Status promotion only when Charles approves** (node stays `status=test` until then).

## 5. Node naming / domain examples

| Node code | Domain | Region |
|---|---|---|
| `de1` | `node-de.unseen.click` | DE (live-verified test node) |
| `us1` | `node-us.unseen.click` | US |
| `sg1` | `node-sg1.unseen.click` | SG |
| `sg2` | `node-sg2.unseen.click` | SG |

These are **examples**. Every node must be a **`proxy_nodes` DB row** (region, public hostname, secret handle, status,
capacity), never hardcoded in source. Adding a node = insert a row + secret handle + follow this runbook; no code change.

## 6. Secret safety (applies to every step)

- **Never print or commit:** Hiddify admin links, admin/proxy paths, admin UUID / API key, private keys,
  default-user/server keys, Reality private keys / short IDs, user UUIDs, subscription URLs, proxy links
  (`hiddify://`/`vless://`/`ss://`/`hy2://`), QR payloads, Telegram token, payment refs, or private customer data.
- **Admin link** lives only in `/root/hiddify-<node>-admin.link` (`0600`, root) — used internally, never echoed.
- **API verification emits only** HTTP status codes, JSON **key names**, counts, and byte sizes — never response bodies
  or values. Always write API bodies to files (`curl -o`), never to stdout; always **quote** UA/headers (an unquoted UA
  once leaked a body to the terminal on de1).
- **Disposable test users only** for contract verification (`name=disposable-test`, minimal quota/days, no real data, no
  payment, no UNSEEN token); delete after.
- **Sanitize all logs;** redact `/s/<token>`, cookies, auth headers, UUIDs, proxy links.

## 7. Rollback

- A **fresh node with no real customers can be provider-reinstalled** cleanly — the Master holds the authoritative user
  set, so a node is disposable. Hiddify also has `uninstall.sh`.
- **Rebuild is preferred if protocol secrets leak** (no safe surgical regen of default-user/server keys).
- **marshmallow pin** is reversible (`uv pip install … "marshmallow==4.3.0"`), but reverting re-breaks the API.
- **SSH/disk changes**: keep on-node backups (sshd drop-in + partition table) for revert; the LVM grow is
  non-destructive but not shrinkable online.
- The node **remains `status=test`** until fully verified; reverting code is `git revert`, independent of node state.

## 8. PASS criteria for a future node

A node may be reported **PASS** only when **all** hold (anything missing → PARTIAL, stated honestly):

- Clean **Ubuntu 22.04.x**.
- Hiddify installed and **healthy** (all services active).
- **API contract verified** (auth, endpoints, fields, **GB units**).
- **Disposable-user lifecycle passes** (create→get→patch→delete→404).
- **FAST1/FAST2/Secure inbounds present.**
- **SSH hardened** (password auth off, key-only; verified).
- **Firewall verified** (SSH safe; required ports open).
- **Docs + SOURCE_OF_TRUTH updated.**
- **No secrets leaked.**
- **Real-device protocol test** passed, or clearly documented as **pending**.
- **Node remains `status=test`** until Charles approves live (never auto-promote).
