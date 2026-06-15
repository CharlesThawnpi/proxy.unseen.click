# CHANGELOG

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §32, §34
> **Status:** Phase 1 skeleton — running log of changes by date

Chronological record of notable changes to the UNSEEN PROXY project.

## 2026-06-15 — Phase 2-DE: OS-to-22.04 path decided = clean reinstall (no in-place upgrade)

- Ran a **read-only pre-upgrade gate** on `de1` (SSH OK; 20.04.6; 18 GB free; RAM 3.1 GiB + 1.9 GiB swap; apt/dpkg
  healthy & unlocked; only SSH:22 + 80/443 free; clean; **`reboot-required` flag set**). Gate **PASS** (upgrade
  feasible).
- **Decision (Charles): clean provider reinstall to Ubuntu 22.04, NOT in-place `do-release-upgrade`** — `de1` is
  empty, so reinstall is the same end-state with far less risk (in-place over SSH could drop SSH/brick the node, and
  its failure mode is a reinstall anyway). **No upgrade command run; no node changes.**
- New `PHASE2_DE1_OS_UPGRADE.md` (gate result + decision/rationale + operator reinstall steps incl. re-add key +
  known_hosts refresh). Updated `CURRENT_STATUS`, `PHASE2_DE1_PREFLIGHT`, `PHASE2_3_DE_NODE_PLAN`. Docs only.
- **Next:** Charles reinstalls to 22.04 + re-adds the Master key → agent re-runs Phase 2-DE preflight → Phase 3-DE.

## 2026-06-15 — Clarify de1 preflight blocker + reinstall requirement (docs audit)

- Audited all DE docs for the Phase 2-DE finding (PARTIAL; clean node; detected specs; OS-mismatch blocker). Most was
  already recorded in the prior commit. **Gap patched:** made the **host-key-change → `known_hosts` refresh** point
  explicit (alongside the existing re-add-public-key note) in `PHASE2_DE1_PREFLIGHT.md` and `CURRENT_STATUS.md` — the
  reinstall changes the node's SSH host key, so the Master must `ssh-keygen -R 5.249.160.59` / re-pin on next connect
  (host-key-mismatch warning expected, not an attack). Docs only.

## 2026-06-15 — Phase 2-DE: de1 SSH verified + clean preflight — PARTIAL (OS = 20.04)

- Root key SSH to `de1` now **works** (key-only, host key pinned). Ran a **read-only** node-facts preflight (no
  writes/installs/changes on the node).
- **Detected (authoritative, ADR-002):** Ubuntu **20.04.6** LTS / kernel 5.4 (hostname `white-cobra-75504`); 4 vCPU
  (Xeon E5-2690 v4); **3.1 GiB RAM** (+1.9 GiB swap); 25 GB disk (18 GB free); `eth0 5.249.160.59`, egress matches;
  only SSH:22 public, 80/443 free; **no firewall**; nginx/docker/certbot absent; **legacy scan CLEAN**.
- **Estimate vs detected:** CPU ✓, disk ✓, IP ✓; **RAM under** (3.1 vs 4 GB); **OS MISMATCH** (20.04 vs required 22.04).
- **Result: PARTIAL — blocker is OS.** `de1` must be **reinstalled to Ubuntu 22.04 LTS** (then re-add the Master key,
  re-run preflight) before the Hiddify host install. Node hardening (disable password login, firewall) deferred to
  Phase 3-DE. New report `PHASE2_DE1_PREFLIGHT.md`; updated SERVERS/NODES/NETWORK/PORTS/DEPLOYMENT/SECURITY/
  CURRENT_STATUS. Docs only.

## 2026-06-15 — de1 SSH connectivity test — PARTIAL/HOLD (key not yet authorized)

- Tested Master→`de1` SSH with the dedicated key (`/root/.ssh/unseenproxy_de1_ed25519`, `IdentitiesOnly`,
  `BatchMode`, `accept-new`, `ConnectTimeout=10`). **Node reachable** (handshake OK, host key pinned) but
  **`Permission denied (publickey)`** for **both** `root@5.249.160.59` and `ubuntu@5.249.160.59` — the public key is
  not in `authorized_keys` yet. No brute-force, no password login, no node changes.
- **Action for Charles (run on `de1` via provider console):**
  `mkdir -p /root/.ssh && chmod 700 /root/.ssh && echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIABHKgQZkRTmmQw5D0ECI+SljBYeCBqXSoOLwDttg7be unseen-proxy-master-to-de1' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys`
  (for a `ubuntu`-only image, run the same under `/home/ubuntu/.ssh` owned by `ubuntu`). Then re-run the connectivity test.

## 2026-06-15 — Prepared Master→de1 SSH key (no connection yet)

- Generated a dedicated ed25519 keypair on the Master for `de1`: `/root/.ssh/unseenproxy_de1_ed25519` (private
  `600`, root-only) / `.pub` (`644`), comment `unseen-proxy-master-to-de1`, fingerprint
  `SHA256:jUYAdY0ONdXKzOg2s4OKO27yBGqLvBwapkEy25oA3+I`. Private key stays on the Master, never in git.
- **Action for Charles:** add the **public** key in the VPS provider panel before first login. No SSH/connection to
  `de1` performed. Reconciled the key path in `PHASE2_3_DE_NODE_PLAN.md`. Docs only.

## 2026-06-15 — Requirement: future Master cleanup of co-location leftovers (ADR-003)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-003** ("Master minimalism and cleanup of abandoned co-location
  dependencies"): the Master is control-plane only; anything installed solely for the retired co-location path is a
  **cleanup candidate**. The idle **Docker engine** (leftover from the failed Hiddify-on-Master test) is the primary
  candidate, to be removed in a **future audited "Master cleanup after retired co-location attempt" task** — **not
  now**, and not during node onboarding.
- Documented the pre-removal verification gate (no containers/volumes/deps, no docs/scripts need Docker, no Hiddify
  remnants, 80/443 free, SSH untouched) and a backup-first rule (snapshot or git-clean + service-state backup).
- Added cleanup-candidate notes to `DEPLOYMENT`, `SECURITY`, `ROLLBACK`, `SERVERS`, `CURRENT_STATUS`,
  `PHASE3_HIDDIFY_LIVE_VERIFY`, and a "not during onboarding" note to `PHASE2_3_DE_NODE_PLAN`. **Docs only — nothing
  uninstalled, no services touched.**

## 2026-06-15 — Requirement: verify ACTUAL node specs at onboarding (ADR-002)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-002**: provider/purchase specs are **estimates only**; on real node
  onboarding the Master must collect the node's **actual** facts via **read-only** SSH probes (no mutation, no
  secrets) and treat detected values as authoritative.
- Established per-value **provenance tiers**: `estimate` / `detected` / `provider-confirmed` / `unknown`. Bandwidth
  stays `estimate` until `provider-confirmed`. Verify before Hiddify install + re-check after if usage changes;
  role-fit (disk/RAM sufficient) gated before install.
- Documented the future read-only probe (`scripts/node_preflight_probe.sh`) in `PHASE2_3_DE_NODE_PLAN.md` (facts to
  detect: OS/kernel/CPU/RAM/disk/public-IP/route/ports/firewall/service-presence/clean-check/role-fit). **Written/run
  only when Phase 2-DE begins — not now.**
- Labelled `de1` specs as **provider-estimate (unverified)** in `SERVERS.md`/`NODES.md`/`CURRENT_STATUS.md`; added
  notes to `DEPLOYMENT.md` (verify-before-install) and `SECURITY.md` (probe is read-only, no secrets, don't trust
  manual specs). **Docs only — no node connection.**

## 2026-06-15 — Decision: Master control-plane-only; DE node → separate VPS (ADR-001)

- Recorded **[DECISIONS.md](DECISIONS.md) ADR-001**: the §4.1 **co-location exception is RETIRED**. The Master is
  **control-plane only** (no proxy traffic); the DE Hiddify node moves to a **dedicated separate VPS**.
- New DE node `de1` registered in inventory: **`5.249.160.59`**, 4 vCPU / 4 GB / 25 GB SSD / 30 TB, **Ubuntu 22.04**,
  `status=test`, domain `node-de.unseen.click` — to be provisioned by Hiddify's **supported host installer**.
- New `PHASE2_3_DE_NODE_PLAN.md` (forward workflow: preflight, Master→node SSH key, DNS plan, host install, live
  Swagger/API verify, disposable test user, FAST1/FAST2/Secure checks).
- Updated ARCHITECTURE / SYSTEM_OVERVIEW / SERVERS / NODES / NETWORK / PORTS (co-location retired; Master never
  proxies; 80/443 conflict resolved by separation), DEPLOYMENT / ROLLBACK / SECURITY / HIDDIFY_API_CONTRACT
  (point to the DE VPS host install), and marked PHASE2/PHASE3 docs superseded/historical. `IMPLEMENTATION_PLAN.md`
  left as source-history; the decision lives in `DECISIONS.md`. **Docs only — no node connection, no install.**

## 2026-06-15 — Phase 3 (Hiddify Docker install attempt — PARTIAL/BLOCKED)

- With Charles's authorization (snapshot confirmed), the agent ran the **official pinned Docker install
  (v12.3.3)** from `/opt` → isolated `/opt/hiddify-manager`. Docker 29.5.3 installed; 3 containers came up.
- **Host stayed safe:** SSH:22 up throughout; iptables INPUT policy `ACCEPT` (Docker added only its own
  NAT/FORWARD chains; Hiddify firewall left OFF); only 80/443 published (bridge); project git clean.
- **Panel is NON-FUNCTIONAL:** 443 returns no response; logs show a **Redis AUTH mis-wiring** + **DB migration
  errors**; the `hiddifypanel` CLI **hangs** on app import. MariaDB reachable, `admin_user` row exists, but the
  web/API never started. → **Live API/Swagger/contract verification BLOCKED; no test user created.** No destructive
  fix attempted (conservative mandate). Empirically confirms the official "Docker not for permanent use" caveat.
- Secret-safe throughout: no admin link generated/printed/committed; install log `0600`; scratch removed.
- Updated `PHASE3_HIDDIFY_LIVE_VERIFY.md` (actual result), `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `NODES`,
  `SERVERS`, `PORTS`, `DEPLOYMENT`.
- **Decision (Charles): tear down + separate DE VPS.** Removed the broken stack (`docker compose down -v` + deleted
  `/opt/hiddify-manager`); Master back to baseline (SSH up, 80/443 free, INPUT ACCEPT; Docker engine kept).
  **Root cause confirmed:** compose `$REDIS_PASSWORD` interpolation bug (Redis ran password-less while the panel used
  a password). **DE node will move to a separate Ubuntu-22.04 VPS** via Hiddify's supported host installer — DE is no
  longer the §4.1 co-location exception; the Master stays control-plane-only.

## 2026-06-15 — Phase 3 (Hiddify live-verify PREP — operator install pending)

- **No install performed by the agent; no Hiddify API call; no system change.** Docs/scripts only.
- B2 provider snapshot **confirmed by Charles**; co-location-via-Docker chosen.
- Ran the **read-only pre-install safety gate** → **PASS** (git clean, SSH:22 listening, 80/443 free, no firewall,
  ~13 GiB RAM / 86 GB disk free, legacy-clean, Master ports free). Verified the environment is capable (root,
  internet) but **cannot hold an SSH-recovery session/console**; the official Docker install is **experimental +
  long-running**. Decision: **operator installs, agent verifies after**.
- Verified the **current official Docker install command** (`bash <(curl https://i.hiddify.com/docker/<version>)`;
  it installs Docker itself) and the official caveat: **Docker version "not recommended for permanent use"** — OK
  for a test node; engine revisited before any live promotion.
- New `PHASE3_HIDDIFY_LIVE_VERIFY.md` (operator runbook + safety-gate evidence + live-verify checklist + sanitized
  contract placeholders) and `scripts/phase3_post_install_probe.sh` (read-only, secret-free post-install probe).
  Updated `CURRENT_STATUS`, `HIDDIFY_API_CONTRACT`, `PHASE3_HIDDIFY_AUDIT_PLAN`, `DEPLOYMENT`, `NODES`.
  Status: **PARTIAL / HOLD** — node remains `status=test`.

## 2026-06-15 — Phase 3 (Hiddify install & API audit PLAN)

- **Read-only research only — no install, no Hiddify API call, no system change.** Docs-only.
- Researched official/primary Hiddify sources (hiddify.com docs, DeepWiki, GitHub) and produced
  `PHASE3_HIDDIFY_AUDIT_PLAN.md` with tiered findings (**[VERIFIED]** / **[LIVE]** / **[ASSUMPTION]**).
- **Verified:** install path `/opt/hiddify-manager`; standard install brings nginx+HAProxy+Xray+sing-box+MariaDB+
  Redis and **takes 80/443**; **Docker** install can **remap ports and run behind an existing nginx**; firewall is
  **iptables, Hiddify-managed**; API v2 base paths + `Hiddify-API-Key: <admin-UUID>` header auth; official OS is
  **22.04** (24.04 had Redis-7.0 install issues, since fixed — Docker bundles Redis and sidesteps it).
- **B1 resolvable:** recommended **Option A** (Docker behind Master nginx) or **Option C** (separate DE VPS, lowest
  risk); proxy inbounds (Hysteria2/Reality/SS) need dedicated ports (not HTTP-proxyable). **B3** firewall/SSH-safety
  plan documented. **B4** reduced but exact ports/units/API fields remain **[LIVE]**. **B2** snapshot still manual.
- Updated `HIDDIFY_API_CONTRACT` (base/auth now docs-verified; CRUD/fields **[LIVE]**), `PORTS`, `NETWORK`,
  `DEPLOYMENT`, `ROLLBACK`, `SECURITY`, `PHASE2_…PREFLIGHT`, `CURRENT_STATUS`. Readiness: **PARTIAL / HOLD**.

## 2026-06-15 — Phase 2 (protected Master/DE Hiddify preflight)

- **Read-only preflight only — Hiddify NOT installed; no system changes made** (no nginx/docker/certbot/ufw/
  package/systemd/firewall/DB/`.env` changes).
- Inspected the Master: 4 vCPU / 15 GiB RAM (~13 GiB free) / 4 GiB swap / 86 GB free disk — sufficient for a
  co-located **test** DE node.
- Confirmed ports 80/443 and Master loopback ports 8190/8191/8192/8197 are currently **free**; only SSH:22 is
  public. **No active host firewall** (ufw inactive, iptables all-ACCEPT, empty nft).
- Legacy scan **CLEAN** (only the authorized `HIDDIFY_API_CONTRACT.md` matched `*hiddify*`).
- Identified the central co-location blocker: **80/443 + TLS ownership** must be decided before install; a
  **provider snapshot is required** before the invasive installer touches the live control plane.
- Readiness decision: **PARTIAL / HOLD** — install authorized only after B1–B4 prerequisites.
- New doc `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`; updated SERVERS/NODES/PORTS/NETWORK/DEPLOYMENT/ROLLBACK and
  marked `HIDDIFY_API_CONTRACT.md` ports as not-verified-until-Phase-3.

## 2026-06-15 — Phase 0 + Phase 1

- Phase 0 clean-VPS verification signed off: **PASS** (gate passed before any build).
- Git repository initialized at the project root with a private origin (later pushed to `origin/main`, 25e5ddc).
- Added `.gitignore` and a pre-commit secret-scan hook.
- Added `.env.example` placeholder files (no real secrets).
- Created the full `docs/` skeleton per §32.
- Recorded naming and subdomain decisions in `DOMAINS.md`.
