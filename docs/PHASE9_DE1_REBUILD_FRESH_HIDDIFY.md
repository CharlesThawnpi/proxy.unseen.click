# PHASE 9 — de1 rebuild + fresh Hiddify reinstall + API/protocol verify

> **Date/time:** 2026-06-16T12:43Z UTC — 2026-06-16 19:13 MMT (Myanmar Time, UTC+06:30, `Asia/Yangon`)
> **Result:** **PASS** — fresh rebuild verified, clean Hiddify v12.3.3 reinstall, API v2 contract re-verified-live,
> disposable-user lifecycle PASS, FAST1/FAST2/Secure inbounds present, SSH hardened, firewall safe.
> **`leaked_key_rebuild_pending` CLEARED.** de1 stays **`status=test`**; live still gated. No live provisioning,
> no real customers, no Telegram/portal exposure.
>
> **Real-device follow-up (2026-06-16, see addendum below): PARTIAL.** Clean import succeeds on iOS and the node is
> **server-side READY + reachable for FAST1/FAST2/Secure**, but **real-device per-protocol connect is unconfirmed**
> (iOS SS upload drops, Windows VPN-mode core failure = client-side, Facebook unreliable). **`realdevice_protocol_test_pending`
> remains.** No node change made.

## Scope

Verify the freshly rebuilt de1, reinstall Hiddify cleanly via the supported pinned host method, re-verify the
API v2 contract + protocols on a real install, run a single disposable test-user lifecycle, re-harden SSH, verify
firewall/ports, and clear the leaked-key blocker **only** if the clean rebuild + install verification pass. No live
promotion.

> **Reusable runbook:** the working method documented here is generalized into
> [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) — the baseline for all future nodes (US, SG1, SG2,
> …). Future installs follow that runbook (dedicated VPS, host install, umask 022, the marshmallow pin if needed, etc.)
> and must not repeat Master co-location or Docker-on-Master.

## Node identity

| Field | Value |
|---|---|
| Node | `de1` |
| Domain | `node-de.unseen.click` |
| IP | `5.249.160.59` |
| Status | **`test`** (unchanged — NOT live) |
| OS | Ubuntu 22.04.5 LTS (kernel 5.15) |
| Master→node SSH key | `/root/.ssh/unseenproxy_de1_ed25519` (root, key-only) |

## Rebuild reason

Earlier test-node Hiddify **default-user/server key exposure** (terminal-only, never committed; on a no-customer test
node) set the `leaked_key_rebuild_pending` / `REBUILD_REQUIRED_BEFORE_LIVE` blocker (Hiddify has no safe surgical
default-key regen). Charles did a fresh provider reinstall to Ubuntu 22.04.5 and re-added the Master root key, so a
clean Hiddify reinstall regenerates all node secrets and clears the blocker.

## Preflight result — PASS (after disk provisioning)

- SSH root key login: **OK** (host key changed by reinstall → refreshed only the de1 `known_hosts` entry).
- OS **Ubuntu 22.04.5 LTS** ✓ · egress IP **5.249.160.59** ✓ · DNS `node-de.unseen.click → 5.249.160.59` ✓.
- 80/443 **free** pre-install ✓ (only SSH:22 + loopback systemd-resolved:53 listening).
- No legacy/Hiddify/Marzban/Happ/Xray/sing-box artifacts; no nginx/docker/certbot present; clean `/opt` ✓.
- **Disk gate initially FAILED:** root LV was 11.5 GB with only **5.4 GB free** (< 10 GB gate). Charles had just
  upgraded VPS storage (disk now 53.7 GB; the kernel already saw it — no reboot needed). With his explicit approval,
  the root volume was grown **online, non-destructively**: `growpart /dev/sda 3` → `pvresize /dev/sda3` →
  `lvextend -l +100%FREE` → `resize2fs`, yielding **48 GB / ~40 GB free**. Partition table backed up first to
  `/root/disk-rollback/` on the node. Disk gate then **PASS**.

## Install method

- **Official supported host installer, version-pinned, non-interactive:** the `download.sh v12.3.3 --no-gui` flow,
  replicated exactly by fetching `common/hiddify_installer.sh` + `common/utils.sh` from the **`v12.3.3` git tag** and
  running `hiddify_installer.sh v12.3.3 --no-gui`. **NOT Docker.** Install path `/opt/hiddify-manager/`.
- **umask 022** was set in the install shell (the prior `umask 077` permission-cascade lesson applied) — **no
  permission cascade occurred this time**; the install completed cleanly (`####100#### Done`, "Finished!").
- Ran **detached** on the node (logging to `/root/hiddify-de1-install.log`) so an SSH drop could not kill a
  mid-install. `--no-gui` auto-configured the panel domain (defaulted to the server IP; a valid cert was obtained).

## Hiddify version

- **Hiddify Manager 12.3.3**; panel API title **"Hiddify API" v2.2.0**.
- Services all `active`/`running`: hiddify-panel, hiddify-nginx, hiddify-haproxy, hiddify-xray, hiddify-singbox,
  hiddify-redis, hiddify-ss-faketls, hiddify-dnstm-router, hiddify-panel-background-tasks, mariadb. (wg-quick inbound
  exited — WireGuard inbound disabled, expected.)

## Admin-link storage (path only)

- Admin links stored **only** at **`/root/hiddify-de1-admin.link`** (`0600`, root-owned). **Value never printed or
  committed.** The admin proxy path + admin UUID were used internally on the node to drive API verification; they were
  never emitted to logs, stdout, or git.

## API / Swagger contract result — VERIFIED-LIVE (after a bounded, documented fix)

- **Confirmed-live** (see [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md)): auth header **`Hiddify-API-Key:
  <admin-UUID>`**; admin API base **`https://<domain>/<proxy_path>/api/v2/admin/…`** (UUID in header, **not** in the
  API path — the UUID appears only in the admin *UI* link). `GET /admin/me/` → 200; `GET /admin/user/` → 200 (array).
- **User fields (sanitized — names only):** `uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date,
  mode, comment, telegram_id, enable, is_active, lang, last_online, last_reset_time, added_by_uuid, id` (+
  server-generated key fields). **Units = GB** (`usage_limit_GB`/`current_usage_GB`) — orchestrator converts GiB↔GB.
- **Bounded fix applied (apiflask/marshmallow-v4 incompatibility):** the fresh install pulled **marshmallow 4.3.0**
  because **apiflask 3.0.2 declares only `marshmallow>=3.20` (no upper bound)**; marshmallow 4.x removed APIs
  apiflask/hiddifypanel rely on, so the API-v2 blueprint failed to register (all `/api/v2/*` → app-level 404). This is
  exactly the incompatibility the installer references with a commented `marshmallow<=3.26.1` pin. Confirmed from
  installed versions + live behavior, then fixed inside the Hiddify venv only:
  `uv pip install --python /opt/hiddify-manager/.venv313/bin/python "marshmallow==3.26.1"` → `systemctl restart
  hiddify-panel`. API then served 200s. **No secrets printed; only hiddify-panel restarted; health re-verified.**
  - **Rollback:** `uv pip install --python /opt/hiddify-manager/.venv313/bin/python "marshmallow==4.3.0"` (or node
    reinstall). **Durability caveat:** a future Hiddify `apply_configs`/update may reinstall marshmallow 4.x and
    require re-applying this pin until upstream pins it.

## Disposable test user result (sanitized)

One disposable user (`name=disposable-test`, `comment=disposable-test`, `usage_limit_GB=1`, `package_days=1`, **no real
data / no payment / no UNSEEN token**) was created and fully exercised, then removed:

| Step | Result |
|---|---|
| users before | 1 |
| CREATE `POST /admin/user/` | **200** (uuid + fields returned) |
| GET `/admin/user/<uuid>/` | **200** |
| subscription `GET /admin/all-configs/?...` | **200** (~14.8 KB) |
| PATCH `enable=false` | **200** |
| DELETE | **200** |
| re-GET | **404** (confirmed gone) |
| users after | 1 (clean) |

No UUID, subscription URL, proxy link, QR, or raw response body was printed or stored.

## Protocol / inbound verification (sanitized — presence/counts only)

- **FAST1 = Hysteria2** — present (singbox `hysteria2` inbound; **443/udp** listening). ✓
- **FAST2 = Shadowsocks** — present (singbox/xray `shadowsocks` inbound; `hiddify-ss-faketls` active; faketls-fronted,
  8388 loopback). ✓
- **Secure = VLESS-Reality** — present (xray `vless` inbounds + a `reality` config file). ✓
- External listeners: **443/tcp, 443/udp, 80/tcp** + SSH 22. Real-device QUIC/Reality **connect** test not performed
  here (needs a Hiddify-App import) → **#TASK_for_Charles**.

## SSH hardening result — PASS

- Effective: **`PasswordAuthentication no`**, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`,
  `PermitRootLogin prohibit-password`. **Port unchanged (22); root key login retained.**
- Applied via drop-in `/etc/ssh/sshd_config.d/99-unseen-proxy-hardening.conf`. Because OpenSSH is **first-match-wins**,
  cloud-init's `50-cloud-init.conf` (`PasswordAuthentication yes`) was neutralized in place (backed up first to
  `/root/disk-rollback/`), and a `/etc/cloud/cloud.cfg.d/99-unseen-ssh-pwauth.cfg` (`ssh_pwauth: false`) prevents a
  future cloud-init run from re-enabling it.
- Validated `sshd -t`, reloaded (no session drop). **Fresh key login verified OK**; **password auth refused**
  (`Permission denied (publickey)`).

## Firewall / port result — PASS

- `ufw` **inactive**; Hiddify manages its own iptables (default INPUT policy ACCEPT) with explicit ACCEPT for
  **22/tcp, 80/tcp, 443/tcp, 443/udp**. SSH:22 listening and reachable throughout. No firewall change made (all
  required ports already permitted; changing it risks SSH/proxy).
- Follow-up (Phase 10 hardening, not this task): tighten the default INPUT policy to deny + explicit allow-list.

## leaked_key_rebuild_pending decision — CLEARED

All clear-conditions met: de1 rebuilt fresh ✓, Hiddify freshly reinstalled ✓, no prior leaked secret material remains
(all node secrets regenerated) ✓, disposable-user verification complete ✓, protocol configs verified ✓, SSH hardened
✓, docs updated ✓. Therefore:

- `backend/config.py`: `LEAKED_KEY_REBUILD_PENDING = False`.
- `backend/seed.py` `NODE_LIVE_BLOCKERS`: the `leaked_key_rebuild_pending` row is **replaced** by
  `realdevice_protocol_test_pending` (de1 stays data-driven-gated until the real-device PASS is recorded).
- de1 **stays `status=test`**; **not promoted to live.** Live also remains hard-disabled by
  `PHASE4C_LIVE_PROVISION_DISABLED`.

## Remaining pre-live blockers

1. **Real-device FAST1/FAST2/Secure connect PASS** (seeded as `realdevice_protocol_test_pending`).
2. **`phase4c_live_disabled`** — Phase 4C live provisioning is hard-disabled in code (separate gated flip).
3. **de1 `status=test`** — promotion to `live` is a separate Charles-gated decision.
4. ~~**Panel domain** is currently the auto/IP value; set `node-de.unseen.click` + its cert before the live sidecar.~~
   **RESOLVED 2026-06-16** — `node-de.unseen.click` added (`hiddifypanel add-domain -m direct` + `apply_configs.sh`),
   valid Let's Encrypt cert issued/installed, API + subscription verified-live over the public node-de path with valid
   TLS. See the addendum below and [HIDDIFY_NODE_INSTALL_RUNBOOK.md](HIDDIFY_NODE_INSTALL_RUNBOOK.md) §5A.
5. **RAM** balloon-dynamic (~3.8 GiB under load) — lock full 4 GB for production.
6. **marshmallow pin durability** — re-apply after any Hiddify update that reinstalls marshmallow 4.x.

## #TASK_for_Charles

1. **Real-device protocol test:** open the admin link (in `/root/hiddify-de1-admin.link`) → create/import a client and
   confirm **FAST1 (Hysteria2)**, **FAST2 (Shadowsocks)**, **Secure (VLESS-Reality)** actually connect from a real
   device. Report PASS/FAIL (no links/secrets shared). This clears `realdevice_protocol_test_pending`.
2. Decide whether to set the panel domain to `node-de.unseen.click` (with cert) now or at sidecar bring-up.

## Rollback path

- **Node:** clean provider reinstall (proven), or Hiddify `uninstall.sh`. The Master holds no live dependency on de1.
- **marshmallow pin:** reinstall `marshmallow==4.3.0` in the venv (above).
- **SSH:** remove `99-unseen-proxy-hardening.conf` + restore `/root/disk-rollback/50-cloud-init.conf.bak`.
- **Disk:** partition-table backup saved under `/root/disk-rollback/` on the node (LV/fs grow is not reversible online,
  but is non-destructive).
- **Repo:** `git revert` the Phase 9 commit restores the prior `leaked_key_rebuild_pending` seed/flag.

## Secret-safety result

No secrets were printed or committed: admin link/proxy_path/admin-UUID, user UUIDs, ed25519/WireGuard/Reality keys,
subscription URLs, proxy/`vless`/`ss`/`hy2` links, QR payloads, bot token, and admin Telegram IDs were all kept on the
node only. API verification emitted **only** HTTP status codes, JSON **key names**, counts, and byte sizes. The admin
link lives solely in `/root/hiddify-de1-admin.link` (`0600`). Repo changes are docs/seed/config/tests only.

## PASS/PARTIAL/FAIL

**PASS** (with documented bounded marshmallow fix and a real-device protocol connect test deferred to Charles).

## Addendum (2026-06-16) — node domain `node-de.unseen.click` + TLS set for real-device import

Charles's real-device Hiddify-App import was failing (admin/terminal QR → HTTP 500; user QR → "connection reset").

- **Root cause:** the `--no-gui` install configured **only** `5.249.160.59` + `5.249.160.59.sslip.io` as Hiddify
  domains; `node-de.unseen.click` was **never** added and the served cert was **IP-only** (`SAN = IP Address:5.249.160.59`).
  All links/QRs used raw-IP hosts with an IP-only cert → import failed. The bare-root **502 is Hiddify camouflage**
  (sslip.io 502s on `/` too), not a fault — the panel was healthy internally throughout.
- **Fix (supported, sanitized):** backed up `current.json` on-node → `hiddifypanel add-domain -d node-de.unseen.click
  -m direct` → `apply_configs.sh` (run through a PTY via `script`, detached; final whiptail dialog dismissed). acme.sh
  issued + installed a **Let's Encrypt ECC** cert (SAN `DNS:node-de.unseen.click`). Only the standard apply-managed
  service reloads occurred; all 10 `hiddify-*` services active afterward.
- **Verified-live over the public node-de path (valid TLS, no `-k`, `ssl_verify=0`):** `GET /admin/me/` 200, `GET
  /admin/user/` 200; disposable-user lifecycle PASS (create 200 → all-configs 200 ~16.4 KB → delete 200 → re-GET 404);
  **subscription output references `node-de.unseen.click`** (raw-IP/sslip refs remain — install artifacts). Firewall
  unchanged (22/80/443 tcp + 443 udp ACCEPT; ufw inactive).
- **Left for Charles:** one clearly-marked disposable user `disposable-test-realdevice` (enabled, 1 GB / 1 day) — pull
  its **node-de** subscription from the panel and run the real-device FAST1/FAST2/Secure connect test. **Do not scan
  the admin/terminal QR; do not use raw-IP links.** de1 stays **`status=test`**. No secrets printed or committed.

## Addendum (2026-06-16) — Hiddify App import failure `127.0.0.1:64127` diagnosed (app-side; server output clean)

First real-device import of the `disposable-test-realdevice` subscription failed **before the profile saved**: "Failed to
add profile / Unexpected error / Error connecting: SocketException / Connection refused / 127.0.0.1:64127".

- **Inspection (sanitized — counts/bytes only; temp files shredded; no links/configs printed):** the real config
  (admin `all-configs`, ~16.4 KB / 322 lines) is **clean** — `127.0.0.1`=0, `localhost`=0, `64127`=0, protocols
  present. User-facing format URLs (auto/singbox/clash/sub) redirect to the **HTML user portal** for an unmatched UA
  (text/html, no `outbounds`) — expected, not anomalous. On-disk: **`64127` is in NO Hiddify config/template** (only an
  unrelated `jqvmap` map-JS asset); the client sing-box template's clash-api `external_controller` is the standard
  **`127.0.0.1:9090`**.
- **Root cause = B (app-side):** `127.0.0.1:64127` is the **Hiddify App's own embedded core / clash-api local control
  port**, refused because the app's core/VPN service wasn't running/reachable when adding the profile (fresh-install
  core not started / VPN permission not granted / app-version import bug). The node never emits it. **Not** a
  FAST1/FAST2/Secure protocol failure.
- **Secondary = C:** the subscription legitimately lists **node-de (valid TLS) + raw-IP + sslip.io** endpoints; the
  raw-IP/sslip ones won't connect (no matching cert) but don't cause the 64127 error. **No safe automated cleanup**
  (`hiddifypanel` = `add-domain` only; no remove/set-default; removing raw-IP breaks the IP-based admin link) → **HOLD**;
  manual prune only (panel **Settings → Domains** → delete `5.249.160.59` + `5.249.160.59.sslip.io`, keep
  `node-de.unseen.click`, then regenerate the admin link).
- **No node change made** (none safe/needed for an app-side error). de1 stays **`status=test`**; one import-clean
  `disposable-test-realdevice` user kept.
- **Charles app-side remediation (server output confirmed clean):** remove the failed profile; ensure the Hiddify App
  has VPN permission and the core can start (update the app to latest; restart app/device; clear app cache if needed);
  then re-import the **node-de** subscription from the panel (never the admin/terminal QR, never a raw-IP/sslip link).

## Addendum (2026-06-16) — Hiddify App parser error `tunnel-per-resolver` fixed (DNSTT disabled)

The Windows Hiddify App downloaded the profile but its sing-box parser rejected it:
`[SingboxParser] unmarshal error: outbounds[37].tunnel-per-resolver: json: unknown field "tunnel-per-resolver"`.
This is a **generator↔parser schema mismatch** — distinct from the earlier mobile `127.0.0.1:64127` app-core symptom.

- **Root cause (C):** `tunnel-per-resolver` is emitted **only** for the **DNSTT** (DNS-tunnel) outbound —
  `hutils/proxy/shared.py` sets `tunnel_per_resolver=4` inside `if base["proto"]==ProxyProto.dnstt`, and
  `singbox.py:add_dnstt` writes it hyphenated into the sing-box config. DNSTT was enabled (`dnstt_enable=true`); the
  installed app's sing-box core doesn't recognize the field and rejects the whole profile. **DNSTT is not one of
  FAST1/FAST2/Secure** (it's a niche last-resort DNS tunnel).
- **Fix (supported, reversible):** `hiddifypanel set-setting -k dnstt_enable -v false` → `apply_configs.sh` (PTY method;
  `current.json` backed up to `/root/disk-rollback/` first). `get_proxies()` strips DNSTT proxies when `dnstt_enable` is
  false (`shared.py:154-155`), so no DNSTT outbound is generated. **Rollback:** set it back to `true` + apply.
- **Verified (sanitized; bodies rendered to a root-only temp and shredded):** an app-context render of the disposable
  user's sing-box config now shows **`tunnel-per-resolver`=0, `dnstt`=0**, FAST1(Hysteria2)/Secure(VLESS) outbounds
  intact. `dnstt_enable=false` in DB (`bool_config`) + `current.json` (`hconfig=False`); all 10 services active; node-de
  TLS still valid. **No cert/firewall/port change; no node secret edited.**
- **Disposable user:** recreated one `disposable-test-realdevice` (1 GB/1 day, enabled) so links are freshly generated
  DNSTT-free (also rotated a UUID inadvertently surfaced during diagnosis — see Secret-safety addendum).
- **Secondary (deferred — Step 6 of this task forbids domain deletion here):** the sing-box output is still
  multi-domain — node-de **plus** raw-IP + sslip outbounds. The raw-IP/sslip ones have no matching cert and won't
  connect, but they don't block parsing. Pruning is a manual panel action (Settings → Domains) + admin-link regenerate.

### Secret-safety addendum (honest disclosure)
During diagnosis, two over-broad sanitized queries briefly surfaced secret values **to the operator terminal only**
(never to git): (1) the **DNSTT keypair** (a value-dumping `jq`), and (2) the **disposable user's UUID** (a redirect
`&user=<uuid>` query my regex missed). Remediation: DNSTT is now **disabled** (its keys are unused and live only in the
node's root-only `current.json`); the exposed disposable **UUID was rotated** by delete+recreate. de1 is a
no-customer **test** node; per the project's standing guidance this is **not** recorded as a new leaked-key rebuild
blocker. Lesson captured in the runbook: only ever emit counts/booleans, never value dumps, and sanitize query-param
UUIDs too.

## Addendum (2026-06-16) — pruned Hiddify output to a clean UNSEEN-only profile

Charles imported successfully on Windows but the profile was Hiddify's broad default: **100 outbounds** (vmess×42,
non-Reality vless×36, naive/tuic/mieru/ssh/wireguard) across **raw-IP + sslip + node-de**, with **no clean
FAST1/FAST2/Secure** — and Shadowsocks + VLESS-Reality were *missing* from the sing-box output. He also pasted disposable
profile text, so that test user was rotated.

- **Disposable rotation:** deleted + recreated one `disposable-test-realdevice` (1 GB/1 d). Burned because Charles pasted
  its profile text — **not** a real-customer leak and **not** a rebuild blocker (de1 is test-only, no customers, nothing
  committed).
- **Protocol pruning (supported `hiddifypanel set-setting`, grounded in `hutils/proxy/shared.py:get_proxies`):**
  - Enabled: `hysteria_enable` (FAST1), `shadowsocks2022_enable` (FAST2 — plain SS; faketls isn't sing-box-native),
    `reality_enable` (Secure); kept `tcp_enable`.
  - Disabled: `vmess, tuic, naive, mieru, ssh_server, wireguard, trojan, grpc, xhttp, httpupgrade, h2, ws, ssfaketls,
    shadowtls, kcp`, and **`vless_enable=false`** — which per `get_proxies` keeps **only** Reality vless (`'vless' not in
    proto or 'reality' in l3`), cleanly isolating Secure from every non-Reality VLESS transport. DNSTT already off.
- **Domain cleanup (supported visibility flag, non-destructive):** `sub_link_only=1` on `5.249.160.59` +
  `5.249.160.59.sslip.io` (`user.py:362` selects `Domain.sub_link_only != True` for customer subs). They're excluded
  from customer subscriptions but stay configured, so the admin link is unaffected. node-de + Reality decoy
  `i.pinimg.com` remain. (No `remove-domain` CLI exists; deletion would also break the IP-based admin link — so the
  visibility flag is preferred.)
- **Result (app-context sing-box render; sanitized counts only; bodies shredded):** **100 → 9 outbounds (3.7 KB).**
  Exactly **hysteria2 (FAST1) → node-de udp:14430**, **shadowsocks (FAST2) → node-de :16753**, **vless-Reality (Secure)
  → node-de tcp:443 + decoy SNI i.pinimg.com**. `vless_nonreality=0`; no vmess/tuic/naive/mieru/ssh/wireguard;
  `tunnel-per-resolver=0`; `dnstt=0`; **no private-key fields**; no raw-IP/sslip in customer outbounds. Each port has a
  live node listener; INPUT policy ACCEPT → reachable.
- **Services/ports:** `hiddify-ss-faketls` now **inactive** (intended — faketls SS replaced by plain SS); all other
  hiddify-* + mariadb/redis active. node-de TLS valid. **No cert/firewall/port change made.**
- **Rollback:** restore protocol flags to prior values (`vmess/tuic/naive/mieru/ssh_server/wireguard/grpc/xhttp/
  httpupgrade/h2=true`, `vless_enable=true`, `reality_enable/shadowsocks2022_enable=false`, `ssfaketls`→prior) via
  `set-setting`; `UPDATE domain SET sub_link_only=0 WHERE domain IN (raw-IP,sslip)`; `current.json` backups in
  `/root/disk-rollback/`; then `apply_configs.sh`.
- **Not a PASS for protocols** — output is import-clean, but FAST1/FAST2/Secure **connectivity** must be confirmed by
  Charles on a real device. de1 stays **`status=test`**.

## Addendum (2026-06-16) — real-device protocol connectivity diagnosis after clean import — PARTIAL

Charles's fresh pruned import now **succeeds on iOS** (profile shows two auto selectors "lowest"/"balance" +
VLESS-Reality + Shadowsocks + Hysteria2). Remaining symptoms: iOS SS connects but **Speedtest upload often
fails/drops**; **Facebook not reliably loaded**; **Windows VPN mode fails** ("Unexpected failure failed to start
background core"); Windows Proxy mode connects but is **not** full-VPN proof. This addendum is a node-side
protocol/client-routing diagnosis — **NOT a PASS**.

**Result classification: PARTIAL.** Import-clean ✓ and **server-side READY/reachable for all three protocols** ✓, but
**real-device per-protocol connect is unconfirmed**. de1 stays **`status=test`**; **`realdevice_protocol_test_pending`
remains** (not cleared).

- **Clean output (sanitized app-context render, counts only):** **1** `disposable-test-realdevice` user (only
  customer-type user; 2 non-customer install users `default`/`Test` also present). **7 outbounds (3.7 KB)** = hysteria2×1
  + shadowsocks×1 + vless-Reality×1 + **2 client selector groups** (`selector`×1 + `urltest`×1) + `direct`×2.
  `vless_nonreality=0`, raw-IP=0, sslip=0, `dnstt=0`, `tunnel-per-resolver=0`, private-key fields=0; all 3 product
  outbounds → node-de (Hy2 udp/14430, SS 16753, Reality tcp/443). `loopback_refs=3` = standard sing-box client-local
  (clash-api `127.0.0.1:9090` + local DNS), not product endpoints, not the App's `64127`.
- **Selector groups:** "lowest"/"balance"/auto are sing-box **client selector/urltest GROUP outbounds** (Hiddify
  template), **not extra protocols** and **not** UNSEEN's final labels (UNSEEN naming handled later by backend/portal/
  delivery: FAST1=Hysteria2, FAST2=Shadowsocks, Secure=VLESS-Reality). Template-generated; no supported `set-setting`
  removes/renames them; **not changed** (out of scope, not clearly safe).
- **Node health:** all `hiddify-*`/mariadb/redis active (`ss-faketls` intentionally inactive). **Panel API live over
  node-de:** `admin/me/`, `admin/user/`, `admin/server_status/` → **200**; no-key `me/` → **403**. **marshmallow 3.26.1**
  (pin intact). `openapi.json` → **500** = cosmetic apiflask schema-doc artifact (functional CRUD is 200). A controlled
  **restart cluster ~19:19** (Charles ran `systemctl unmask systemd-resolved` + `restart sshd/ssh` from
  `/opt/hiddify-manager/common`, pts/1) cycled the stack — reload churn, **not an ongoing crash**; all recovered.
  haproxy code-143 ALERTs = normal seamless-reload churn. Resources healthy. Minor/benign: `UdpSndbufErrors=742`
  (historical), RX dropped 13240 (0.23%, 0 errors), conntrack 76 / 2.1M.
- **External reachability (Master, no payloads):** DNS ✓; TLS @443 **verify=0** ✓; TCP 443/16753/80/22 **OPEN** ✓; UDP
  14430/443 **open|filtered** ✓.
- **Per protocol (server-side READY):**
  - **FAST1/Hysteria2:** udp/14430 listener (`hiddify-core`) + **explicit iptables ACCEPT 14430/udp** (plus port-hop
    14428/14765/14767/36675/36677); no handshake/timeout errors; UDP `rmem/wmem_max`=64 MB (already tuned).
  - **FAST2/Shadowsocks:** tcp+udp/16753 (`hiddify-core`, **plain SS**, faketls inactive); reachable; logs clean.
    **No explicit firewall rule for 16753** → works only via default `INPUT=ACCEPT`. **Phase 10 hardening MUST add an
    explicit `-A INPUT -p tcp --dport 16753 -j ACCEPT` (and udp) before tightening INPUT to DROP.**
  - **Secure/VLESS-Reality:** 443 → internal `realityin_tcp_19411` (haproxy SNI-fronts 443); reality inbound present with
    **decoy SNI `i.pinimg.com`** + dest + serverNames; valid TLS; no handshake failures (xray "non-443 ports" warning is
    a benign haproxy-fronting artifact).
- **Tuning decision = HOLD.** No server-side fault; buffers already tuned; all reachable. No node change made.
- **Windows VPN-mode diagnosis:** "failed to start background core" is **client-side** (TUN/Wintun driver,
  Administrator/privilege, or app-version) — node logs show no failed connection attempts implicating the server, and
  the node is healthy + reachable. Windows **Proxy mode is not full-device VPN proof** (only proxies system-proxy-aware
  apps; a Facebook/browser test under Proxy mode is inconclusive).
- **iOS/mobile diagnosis:** import passes; green VPN = tunnel active. **SS Speedtest upload drop alone is not proof** —
  mobile carriers shape UDP/upload; check VPN permission, Low Power Mode, background refresh, app version. Test each
  protocol with an external-IP check + a blocked site + 3–5 min browsing stability, repeated on Wi-Fi and mobile data.
- **Facebook** is useful field evidence, **not** formal proof alone.

### #TASK_for_Charles (this addendum)

- **Windows (VPN-mode core failure):** run Hiddify App **as Administrator** → switch to **VPN mode**; if it prompts,
  **install/repair the Wintun/TUN driver**; **update Hiddify App to latest stable (non-dev)**; if it still fails,
  capture **only the first 5 sanitized log lines** around "failed to start background core" (no profile links/configs).
- **iOS/per-protocol:** for **each** of Secure(VLESS-Reality), FAST2(Shadowsocks), FAST1(Hysteria2) individually:
  external-IP check → open a blocked site/app → browse 3–5 min for stability; repeat on **Wi-Fi** and **mobile data**.
  Report per-protocol PASS/FAIL (no links/secrets). Do **not** use third-party config validators or paste configs.
- This is what clears `realdevice_protocol_test_pending` — only on confirmed per-protocol connect PASS.

## Addendum (2026-06-16) — mobile import PASS after app reinstall; Hiddify label/selector control = Decision C

After Charles **deleted + reinstalled** the Hiddify App on mobile, **import now works** (Windows import also works; the
clean de1 profile is importable). The earlier iOS "connection refused" / failed-add-profile symptom was an
**app/cache/install-state** condition — **not** a node or profile fault (server output was already verified import-clean).
This addendum answers whether the Hiddify-generated client profile can be made to show UNSEEN labels.

- **Profile re-scan (sanitized, counts/booleans only):** unchanged/clean — **7 outbounds** = hysteria2×1 + shadowsocks×1
  + vless-Reality×1 + `selector`("Select", 4 members) + `urltest`("Auto", 3 members) + `direct`×2; `vless_nonreality=0`,
  raw-IP=0, sslip=0, dnstt=0, tunnel-per-resolver=0, private-key=0, vmess/tuic/naive/wireguard=0.
- **"lowest"/"balance" are NOT emitted by de1.** The node's sing-box output has only **"Select"** + **"Auto"**;
  "load-balance" exists only in the **Clash** templates (`clash_config*.yml`), which the Hiddify App (sing-box core) does
  not use. **"lowest"/"balance" are Hiddify App (HiddifyNext) client-side UI groups**, added by the app post-import —
  **not UNSEEN protocols and not node-controllable.**
- **Label/group control — no safe supported method (Decision C):**
  - **Rename Hysteria2→FAST1 / Shadowsocks→FAST2 / VLESS-Reality→Secure:** no supported `hiddifypanel` setting / DB flag
    / API. Outbound tag = `singbox.py:to_singbox` → `f"{extra_info} {name} § {port} {dbdomain.id}"`, with
    `name = proxy.name` (auto-generated Proxy DB field, regenerated by `apply_configs`). No custom-display-name setting;
    `ConfigEnum` exposes only `branding_title`/`branding_site`/`branding_freetext` (panel branding).
  - **Hide/remove "Select"/"Auto":** hardcoded in `singbox.py:configs_as_json`; template uses `"final": "Select"` + dns
    `detour: "Select"` → removal breaks the profile.
  - Both would need **venv source/DB edits that Hiddify overwrites on upgrade/reinstall** and risk the clean profile →
    **not done** (per task rules: no template/secret-config hand-edits without clear safety + durability).
- **Decision = C.** Keep the clean profile **unchanged**. **UNSEEN labels (FAST1=Hysteria2, FAST2=Shadowsocks,
  Secure=VLESS-Reality) are presented in the bot/portal/customer instructions/delivery layer.** If a fully custom-labeled
  client profile is ever needed, the **UNSEEN backend generates/sanitizes the customer sing-box profile itself** (the
  existing delivery/link layer already mediates output) — Hiddify templates are never hand-patched.
- **No node change made** (no setting, no template edit, no restart, no disposable-user recreate). de1 stays
  **`status=test`**; **`realdevice_protocol_test_pending` remains** (awaits Charles's actual per-protocol connectivity PASS).

### #TASK_for_Charles (this addendum)

- The **"lowest"/"balance"/Hysteria2/Shadowsocks/VLESS-Reality** entries in the app are **Hiddify/sing-box generated and
  expected** — there is nothing to fix on the node. Pick **any one** product entry (or the "Auto" group) and run the
  real-device per-protocol connectivity test (external-IP check + a blocked site + 3–5 min browse; repeat on Wi-Fi and
  mobile data). UNSEEN's customer-facing FAST1/FAST2/Secure naming will come from the bot/portal, not the raw profile.
- This per-protocol connectivity PASS is what clears `realdevice_protocol_test_pending`.

## Addendum (2026-06-16) — FAST1/Hysteria2 timeout diagnosis — server EXONERATED; likely mobile-network UDP (Decision C, HOLD)

Mobile/Windows **import PASS**, but Charles reports **FAST1/Hysteria2 times out on connect**. This is a **protocol-level
connectivity** failure, **not** an import/profile-shape failure. Labels unchanged (FAST1=Hysteria2, FAST2=Shadowsocks,
Secure=VLESS-Reality). All inspection sanitized (counts/booleans/ports/HTTP-status only; on-node comparisons reported as
booleans — no obfs/auth/keys/UUIDs printed; temp scanners shredded).

**Profile scan (Hysteria2 detail):** 1 disposable user; 7 outbounds (clean — raw-IP/sslip/dnstt/tpr/private-key/vmess/
tuic/naive/wireguard all 0). The Hysteria2 outbound = **server node-de, port 14430**, salamander **obfs (+password)**,
**auth password** present, **TLS** enabled (insecure=true, sni=node-de, alpn present).

**Server-side EXONERATED — causes A (listener/firewall) and B (profile mismatch) ruled out:**

- Hiddify created **one Hy2 inbound per configured domain** — `hysteria_in_14427` / `_14428` / `_14430` (raw-IP / sslip /
  node-de). hiddify-core **listens on all three udp ports**; **explicit iptables ACCEPT** exists for `14430/14428/14427 udp`
  (INPUT policy ACCEPT). The customer profile (node-de) targets **14430**.
- On-node boolean comparison of the **14430** inbound vs the client outbound: **port match ✓, salamander obfs-password
  match ✓, user auth-password present ✓, TLS sni=node-de ✓**. No mismatch.
- hiddify-singbox active (no restart in the test window); **0 logged hysteria/quic/auth/obfs/handshake errors** (2h);
  resources healthy (load ~0.15, ~2.9 GiB free, disk 17%). `UdpRcvbufErrors ≈ 380/180240` (~0.2%) = negligible
  background, not a connection-killer.

**External reachability (from the Master, no payloads):** DNS node-de → 5.249.160.59 ✓; TCP control **443/16753 OPEN**;
UDP **14430/14428/14427 open|filtered** (not refused) from a clean datacenter network. **Honest limitation:** UDP
*delivery* cannot be definitively proven with generic tools without a Hysteria2 handshake payload, which was intentionally
**not** sent (no credentials/payload disclosure).

**Control (FAST2/Secure — recorded, NOT tuned):** SS **16753 tcp+udp** listening; Reality **443** listening; xray/haproxy
active; **0 reality handshake errors**. So TCP-based protocols are up — **only the UDP/Hysteria2 path is in question.**

**Likely cause = C — mobile-network UDP/Hysteria2 instability.** The server is correct and reachable from a clean
network; the failure is a **timeout** (not a refusal, not an auth/obfs rejection) on a **QUIC/UDP** protocol on a high
port (14430) **while TCP-based import/SS/Reality work** — the classic signature of **mobile-carrier UDP/QUIC throttling
or blocking** (common on Myanmar mobile data). **D (client app) is a secondary possibility** to rule out via a network
swap (Wi-Fi vs mobile data).

**Supported Hiddify Hy2 settings (researched, NOT applied):** `hysteria_enable=true`, `hysteria_obfs_enable=true`
(**salamander already on** — best available DPI evasion), `hysteria_port` (→14430), `hysteria_up/down_mbps` (150/300).
**No supported Hysteria2 port-hopping toggle exists** (the three inbounds are per-domain, not a hop range; `mieru_udp_ports`
is Mieru-only). Therefore **no safe/supported server change would fix a carrier-side UDP block.**

**Decision = C → HOLD. No node change made** (no setting, no template edit, no restart, no disposable-user recreate).
de1 stays **`status=test`**; **`realdevice_protocol_test_pending` remains** (Hysteria2 not PASS; FAST2/Secure still need
their own tests).

### #TASK_for_Charles (this addendum)

1. **Retest Hysteria2/FAST1 on a different network:** try it on **Wi-Fi** and on **mobile data** separately. If it works
   on Wi-Fi but times out on mobile data → confirmed **mobile-carrier UDP** restriction (expected for Hysteria2/QUIC).
2. **Test FAST2/Shadowsocks (TCP 16753) and Secure/VLESS-Reality (TCP 443) next** — these are TCP-based and far more
   likely to connect on restrictive/UDP-throttling networks. Report per-protocol PASS/FAIL (no links/secrets).
3. Optionally confirm the Hiddify App has VPN permission + latest version (rules out client-side D).
4. **Do not paste configs/links.** Hysteria2 being premium/fast but **network-dependent** is expected behavior, not a
   node fault. `realdevice_protocol_test_pending` clears only on confirmed per-protocol connectivity.

## Exact next recommended task

**Charles records the real-device FAST1/FAST2/Secure connect PASS** (clears `realdevice_protocol_test_pending`). After
that, the remaining live gates are the Charles-gated `status=test → live` promotion and the separately-gated Phase 4C
live-provisioning flip — neither in scope here.
