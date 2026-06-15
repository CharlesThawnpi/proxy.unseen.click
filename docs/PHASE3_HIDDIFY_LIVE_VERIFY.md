# PHASE 3 — Hiddify Live-Verify (protected Master/DE)

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §14, §34; builds on
> [PHASE3_HIDDIFY_AUDIT_PLAN.md](PHASE3_HIDDIFY_AUDIT_PLAN.md) and [PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md](PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md)
> **Status:** **PARTIAL / HOLD — install NOT executed by the agent.** Pre-install safety gate PASSED; by decision the
> **operator (Charles) runs the install**, then the agent performs live verification. Node stays `status=test`.

## Run metadata

| Field | Value |
|---|---|
| Date/time (UTC) | 2026-06-15T13:08:48Z |
| Host | Master `crimson-gorilla-49484` — Ubuntu 24.04.4, 4 vCPU / 16 GB / 100 GB (co-located DE test node) |
| Snapshot (B2) | **CONFIRMED by Charles** (provider-side Master snapshot taken before any install). |
| Execution decision | **"Operator installs, agent verifies."** The agent did **not** install — it cannot hold a second SSH session / provider console, and the official Docker method is **experimental** + long-running, unsafe to drive one-shot non-interactively on a protected control plane. |

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

## PASS / PARTIAL / FAIL decision

**PARTIAL / HOLD.** Safety gate passed and the install is fully prepared, but per the agreed decision the **agent has
not installed Hiddify**. Completion requires: (1) Charles runs the runbook above with the recovery net; (2) the agent
(next task) runs the probe + Swagger inspection, fills the verified contract, creates/【deletes】one disposable test
user. Node remains `status=test`; nothing live, no production DB, no customer delivery.

## Exact next recommended task

**"Phase 3 live-verify — post-install"**: after Charles completes the runbook and shares only the `0600` admin-link
**path** (never the value), the agent runs `scripts/phase3_post_install_probe.sh`, inspects the panel Swagger, fills
[HIDDIFY_API_CONTRACT.md](HIDDIFY_API_CONTRACT.md) with verified values, creates and then deletes one disposable test
user, and updates this doc to PASS. Only then does Phase 4 (DB/backend orchestrator) build against the verified contract.
