# PHASE 3 — Hiddify Live-Verify (protected Master/DE)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, §34; builds on
> [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md) and [PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md](PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md)
> **Status:** **PARTIAL / BLOCKED — Docker install executed (v12.3.3) but the panel is NON-FUNCTIONAL.**
> Containers came up; SSH + control plane intact; **but** the panel web/API never served (443 → no response) due to a
> Redis AUTH mis-wiring + DB migration errors in the experimental Docker build. **Live API/Swagger verification could
> not be completed.** The broken stack was then **torn down** (Master back to baseline); decision: provision DE on a
> **separate Ubuntu-22.04 VPS** via the supported host installer (audit Option C). See sections below.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T13:08:48Z |
| Host | Master `crimson-gorilla-49484` — Ubuntu 24.04.4, 4 vCPU / 16 GB / 100 GB (co-located DE test node) |
| Snapshot (B2) | **CONFIRMED by Charles** (provider-side Master snapshot taken before any install). |
| Execution decision | **Charles authorized the agent to install** (accepting the no-console limitation; snapshot as backstop). Earlier "operator installs" stance was superseded by that explicit authorization. |
| Install run (UTC) | 2026-06-15 ~13:25Z |

## Actual install result (2026-06-15) — PARTIAL / BLOCKED

**What worked:**
- Official pinned install ran: `curl -fsSL .../common/docker-installer.sh | bash -s -- v12.3.3` from `/opt`
  (→ isolated `/opt/hiddify-manager/`, outside the project tree; project git stayed clean).
- Docker engine **29.5.3** installed by the script; three containers came up: `hiddify-manager-hiddify-1`
  (`ghcr.io/hiddify/hiddify-manager:v12.3.3`), `mariadb_container`, `redis_container`.
- **SSH:22 stayed up throughout** (verified repeatedly). **iptables INPUT policy remained `ACCEPT`** with 0 INPUT
  rules — Docker added only its own NAT/FORWARD/DOCKER chains; Hiddify firewall feature **left OFF**. Control plane unharmed.
- Host ports published: **80 + 443 via `docker-proxy`** (bridge mode; redis/mariadb stay container-internal). No other
  host ports taken. Resource delta tiny: RAM used 1.7→1.9 GiB; disk 9.0→13 GB (Docker + images); 82 GB free.

**What is broken (why verification is blocked):**
- **Panel does not serve** — `curl -sk https://127.0.0.1/` → `http=000` (nothing listening inside the container on 443;
  the panel web server failed to start).
- **Redis AUTH mis-wiring** — panel logs: `redis.exceptions.AuthenticationError: AUTH <password> called without any
  password configured for the default user` (a docker-compose password-interpolation bug in the experimental build).
- **DB migration errors on first boot** — e.g. `Unknown column 'monthly_usage_limit_GB'`, `Table 'dailyusage' doesn't
  exist`, `Can't DROP INDEX` (migration ran against a partially-initialised schema). MariaDB itself is reachable and an
  `admin_user` row exists, but the panel never came up.
- **CLI unusable** — `python3 -m hiddifypanel <cmd>` (admin-links / spec / --help) **hangs** (timeout) on app import,
  so neither the admin link nor the OpenAPI spec could be obtained.

**Conclusion:** this **empirically confirms Hiddify's official caveat that the Docker version is "experimental / not
recommended for permanent use."** No `admin-links`/Swagger/test-user verification was possible. No destructive fix was
attempted (per the conservative mandate). The containers were **left as-installed** pending an operator disposition
decision (teardown / debug / retry via supported host install or separate DE VPS — see "Exact next recommended task").

**Secret-safety:** the install log (`/root/hiddify-install.log`, `0600`) never received an admin link (none was
generated); the library masked the Redis password as `<password>`. No admin path/UUID/key/proxy/sub link was produced,
printed, or committed. The earlier `/root/hiddify-de-admin.link` scratch held only non-admin URLs and was removed.

## Pre-install safety gate — RESULT: PASS (read-only)

| # | Check | Result |
|---|---|---|
| 1 | Provider snapshot confirmed by Charles | **PASS** — confirmed; recorded here |
| 2 | git working tree clean | **PASS** — clean at `351af19` |
| 3 | SSH:22 listening | **PASS** — `sshd` on `0.0.0.0:22` + `[::]:22` |
| 4 | Second-SSH-session safety | **NOTED** — operator must open a **second SSH session** + keep the **provider console** ready before install (lockout net) |
| 5 | Current listeners (`ss -tulpn`) | Only SSH:22 public; `127.0.0.x:53` resolver; two ephemeral loopback tooling ports. **80/443 free.** |
| 6 | nginx/docker/certbot/ufw/iptables/nft | nginx/docker/certbot **absent**; ufw **inactive**; iptables policy **ACCEPT**, 0 rules; nft **empty** |
| 7 | Disk/RAM/CPU headroom | **PASS** — ~13 GiB RAM free, 86 GB disk free, load ~0 |
| 8 | Legacy artifacts | **PASS** — none (clean) |
| 9 | Master ports 8190/8191/8192/8197 | **PASS** — all free |
| 10 | 80/443 ownership / collision | **Free now.** No Master nginx exists yet, so no live collision today; coexistence still governed by the §B1 plan when control-plane nginx is built. |
| 11 | Rollback path documented | **PASS** — provider snapshot (confirmed) + docs/ROLLBACK.md; Docker narrows blast radius |

No unexpected HIGH risk in the read-only gate. The only unmet item for **autonomous** execution is the live
recovery net (gate #4) — hence the operator-runs-install decision.

---

## Operator install runbook (Charles runs this; agent does NOT)

> **Official method (verified from hiddify.com / wiki, 2026-06-15):** the current Docker install is a one-line
> script that *also installs Docker for you*. Docker support is **experimental** and Hiddify states the Docker
> version is **"not recommended for permanent use"** — acceptable for a **test** node; revisit the engine choice
> before any live promotion (see Risks). Pin a version rather than `latest` for reproducibility.

**Before you start (lockout safety):**
1. Confirm the provider snapshot exists (done) and you can reach the **provider console/VNC** (recovery path).
2. Open a **second SSH session** to the Master and keep it idle/open — if the first session dies, you still have control.
3. Do **NOT** enable Hiddify's built-in firewall feature during this test (it manages iptables and is the main
   SSH-lockout vector). Leave it OFF.

**Install (pin a known version; check the latest stable tag first):**
```bash
# pick a specific stable version tag (example shown — confirm the current stable tag first)
bash <(curl https://i.hiddify.com/docker/v10.80.0)
```
- Run it in `screen`/`tmux` so a dropped connection doesn't abort the install.
- When prompted for a domain, use **`node-de.unseen.click`** (the DE node's own host — see DOMAINS.md), not a
  customer-facing control-plane subdomain.
- After it finishes, it prints an **admin link** containing the secret admin proxy path + admin UUID.

**Secret handling (critical):**
- Do **NOT** paste the admin link / admin path / UUID / any proxy or subscription link into git, docs, chat, or this file.
- Store the admin link only in a **root-owned `0600`** file outside git, e.g. `/root/hiddify-de-admin.link`
  (`chmod 600`). Tell the agent only the **path**, never the value.

**Immediately after install — verify you are NOT locked out:**
- From the **second** SSH session, confirm you still have access.
- `ss -tlnp | grep ':22'` shows sshd still listening.

**Then hand back to the agent** (or run the agent's probe yourself):
```bash
bash /opt/unseen-proxy/scripts/phase3_post_install_probe.sh   # read-only, sanitized — safe output
```

---

## Live-verification checklist (agent performs AFTER the panel is up)

All read-only / sanitized; one disposable test user max; nothing customer-facing.

- [ ] **Record version** — exact Hiddify version + image tag (`docker images | grep hiddify`).
- [ ] **Container/port map** — `docker ps`, `ss -tulpn`: record real panel/subscription/Reality/Hysteria2/SS ports & binds.
- [ ] **SSH safety** — confirm SSH:22 still listening; iptables INPUT still ACCEPT (Hiddify firewall left OFF).
- [ ] **80/443 reality** — what actually owns them; whether it conflicts with the (not-yet-built) Master nginx plan.
- [ ] **Resource delta** — RAM/disk before vs after (baseline: ~1.7 GiB used / 9.0 GB disk used).
- [ ] **Swagger/OpenAPI** — open the panel API docs (Settings → API); fill the contract fields below from it.
- [ ] **API v2 contract** — confirm: base path shape, `Hiddify-API-Key` header, create/update/get/list/disable user
      endpoints, quota field + **units (GB vs GiB)**, expiry/`package_days`/`start_date` fields, usage fields,
      subscription URL + output formats (`auto/sub/sub64/singbox/clash/...`), deep-link import notes.
- [ ] **One disposable test user** — create exactly one, clearly named `disposable-test`, via API/panel; verify it
      appears and returns a subscription. **No real customer data, no UNSEEN token, no payment.** Delete after.
- [ ] **Protocols** — confirm FAST1(Hysteria2)/FAST2(SS)/Secure(VLESS-Reality) inbounds exist & are configured;
      record their ports. Do **not** print raw config/share links.
- [ ] **Real-device App test** — if needed, **Charles manual follow-up** (import on a device); links are never logged here.
- [ ] Fill verified values into [HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md), flipping **[LIVE]** → **[VERIFIED-LIVE]**.

### Fields to capture (sanitized placeholders until verified)

| Field | Value |
|---|---|
| Hiddify version | _pending install_ |
| API v2 base path shape | `https://<node-domain>/<HIDDIFY_ADMIN_PATH_REDACTED>/api/v2/admin/…` (confirm) |
| Auth header | `Hiddify-API-Key: <API_KEY_REDACTED>` (confirm) |
| Create/Update/Get/List/Disable user | _pending Swagger_ |
| Quota field + units | _pending — confirm GB vs GiB_ |
| Expiry/package fields | _pending_ |
| Usage fields | _pending_ |
| Subscription output formats | _pending_ |
| Test user | `<TEST_USER_UUID_REDACTED>` (disposable; deleted after) |
| Panel/sub/Hysteria2/SS/Reality ports | _pending `ss -tulpn`_ |

## Rollback path

- **Primary:** restore the **confirmed provider snapshot** (operator, via provider console). Zero data loss — no
  UNSEEN DB/services/customers exist yet.
- **Docker-local:** `docker compose down` / stop+remove Hiddify containers + remove its install dir; lighter than a
  host install but the snapshot is the authoritative net. See [ROLLBACK.md](ROLLBACK.md).
- **SSH lockout:** second session + provider console; Hiddify firewall left OFF to avoid the main vector.

## Remaining risks

- **Docker "not recommended for permanent use" (official).** Fine for this **test** node, but **before any live
  promotion**, decide between: a **pinned host install on Ubuntu 22.04** (separate DE VPS, Option C) vs keeping Docker.
  This is a real architectural decision, not a detail.
- **Experimental installer reliability** — may need a retry; run under `screen`/`tmux`.
- **Exact ports/units/API fields remain unverified** until the operator install + agent probe complete (**[LIVE]**).
- **80/443 coexistence** with the future Master nginx is still a design item (§B1) — not triggered yet because no
  control-plane nginx exists.

> **Live-verification checklist + field table above remain UNFILLED** — the panel never served, so none of the
> [LIVE] items could be completed. They stay as the to-do for a working install.

## PASS / PARTIAL / FAIL decision

**PARTIAL / BLOCKED.** The install *ran* and the host stayed safe (SSH up, control plane intact, isolated to
`/opt/hiddify-manager`), but the **panel is non-functional** (Redis AUTH mis-wiring + DB migration errors → 443 not
serving; CLI hangs). **No API/Swagger/contract verification, and no disposable test user, were possible.** The
`HIDDIFY_API_CONTRACT.md` [LIVE] fields remain unverified. This is a real, documented outcome — not a PASS — and it
confirms the audit's caveat that the **Docker build is experimental / not for permanent use**.

## Teardown + confirmed root cause (2026-06-15)

**Decision (Charles): tear down + plan a separate DE VPS.** Executed `docker compose down -v` in `/opt/hiddify-manager`,
removed the directory (incl. `docker.env` secrets + `docker-data`), and removed the abandoned install log. **Baseline
restored:** no containers, **SSH:22 up, 80/443 free, iptables INPUT `ACCEPT`**; Docker engine 29.5.3 kept per decision;
project git clean.

**Root cause CONFIRMED at teardown:** compose emitted `The "REDIS_PASSWORD" variable is not set. Defaulting to a blank
string.` — the redis service's `command: redis-server --requirepass "$REDIS_PASSWORD"` is interpolated by *compose*
(which reads vars from the project `.env`/shell, **not** from the `env_file: docker.env`). So Redis started with a
**blank** password while the panel authenticated *with* the `docker.env` password → the `AuthenticationError`, which
cascaded into the panel failing to serve. A genuine bug in the experimental Docker compose, not a transient race.

**Chosen path:** the DE node will be provisioned by the **supported host install on a separate Ubuntu-22.04 VPS**
(audit Option C) — not Docker-on-Master. The protected Master stays clean (control-plane only, per its primary role).

## Exact next recommended task

**Provision the DE node on a separate Ubuntu-22.04 VPS (audit Option C), then re-do live-verify there.** Options
considered (decision made: tear-down + separate VPS):
1. **Supported host install on Ubuntu 22.04, on a separate DE VPS** (audit **Option C** — lowest risk, keeps the
   protected 24.04 Master untouched, and matches Hiddify's officially supported OS). **Recommended.**
2. **Debug the Docker build** (fix the compose Redis-password interpolation + re-run migrations) — only if staying on
   Docker is required; treat as a bounded, separate task. Hiddify still labels Docker "not for permanent use."
3. **Tear down** the current broken stack now (`cd /opt/hiddify-manager && docker compose down -v`; optionally remove
   the dir) to return the Master toward baseline; reinstall later by the chosen path.

Whichever path yields a serving panel, the live-verify checklist + field table above are then completed (admin link →
`0600` file, Swagger → contract, one disposable test user created+deleted). Only then does Phase 4 build against a
verified contract. **The broken stack has been torn down; the Master is back to baseline.** Next concrete step: the
**dedicated DE node VPS is purchased** (`de1`, `5.249.160.59`, Ubuntu 22.04) — run the **supported host installer**
there per [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md). Co-location is retired ([DECISIONS.md](DECISIONS.md) ADR-001).
