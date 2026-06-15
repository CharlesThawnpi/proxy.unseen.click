# DECISIONS — Architecture Decision Record (ADR) log

> **Purpose:** durable record of architectural decisions that **supersede or refine** parts of
> [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md). The plan is kept as **source-history** (not edited per-decision);
> where this log and the plan differ, **this log wins** for the named section.

---

## ADR-001 — Master is control-plane-only; DE Hiddify node moves to a separate VPS (co-location retired)

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles)
- **Supersedes:** IMPLEMENTATION_PLAN.md **§4.1 co-location exception** (DE node co-located on the Master) — **retired for this build.**

### Context

The plan's §4.1 allowed one deliberate exception: the Master (control plane) would also host the DE Hiddify node to
save a VPS. Phase 2 preflight + Phase 3 audit prepared this, and Phase 3 live-verify **attempted it** with Hiddify's
official pinned **Docker** install (v12.3.3) on the Ubuntu-24.04 Master.

### What happened (evidence)

- The Docker stack came up (containers running; host stayed safe — SSH up, control plane intact, isolated to
  `/opt/hiddify-manager`), **but the panel never served** (443 → no response).
- **Root cause (confirmed at teardown):** the experimental `docker-compose.yml` interpolates `$REDIS_PASSWORD` from
  the compose project `.env`/shell — **not** from the `env_file: docker.env` where the installer writes it. So Redis
  started with a **blank** password while the panel authenticated *with* one → `redis.exceptions.AuthenticationError`,
  which cascaded into the panel failing to start. First-boot DB migration errors and a hanging `hiddifypanel` CLI
  compounded it.
- This matches Hiddify's **official caveat** that the Docker version is *"experimental / not recommended for permanent use."*
- The broken stack was torn down (`docker compose down -v` + dir removed); the Master returned to baseline
  (SSH up, 80/443 free, iptables INPUT `ACCEPT`; Docker engine left installed but unused).

### Decision

1. **The Master VPS is CONTROL-PLANE ONLY.** It never carries proxy traffic. It runs: bots, the unified DB, payments,
   admin, customer portal, API, the subscription sidecar, monitoring, backups, Git-based deployment, and node
   orchestration. Its specs are not "wasted" — they protect the business/control plane.
2. **The DE Hiddify node moves to a separate, dedicated VPS** (details in [SERVERS.md](SERVERS.md)), provisioned with
   Hiddify's **supported host installer on Ubuntu 22.04 LTS** (not Docker, not on the Master).
3. **Hiddify-Docker-on-Master is NOT a viable path for this build** and will not be retried; Docker on the Master is
   left installed but unused (removal deferred unless Charles asks).
4. The DE node starts **`planned`/`test`**, never auto-promoted to `live`, carries **no** customer/business data, and is
   **managed only from the Master** over Hiddify API v2.

### Consequences

- The "Master never proxies" rule is now **absolute** — no co-location exception anywhere in this build.
- DE becomes an **ordinary dynamic node** (§6.1): pure data in `proxy_nodes`, replaceable by a row update.
- **Phase 4 (DB/backend orchestrator) remains BLOCKED** until the Hiddify API v2 contract is **verified live** on the
  new DE node (see [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md)).
- Affected docs updated: ARCHITECTURE, SYSTEM_OVERVIEW, SERVERS, NODES, NETWORK, PORTS, DEPLOYMENT, ROLLBACK,
  SECURITY, HIDDIFY_API_CONTRACT, the PHASE2/PHASE3 docs, CURRENT_STATUS, CHANGELOG.

---

## ADR-002 — Provider/purchase specs are ESTIMATES; the Master must verify actual node facts on onboarding

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles) — **requirement for the future node-preflight phase; not executed now.**

### Context

Node specs/limits in our docs (e.g. `de1`: 4 vCPU / 4 GB / 25 GB / 30 TB / Ubuntu 22.04) currently come **only** from
the provider/purchase page. These are **expected values**, not measured facts — a provider page can be rounded,
mislabelled, or differ from what the OS actually reports (CPU count, usable disk after the image, real RAM, the OS
version actually installed, the bandwidth cap the provider truly enforces).

### Decision

1. **Treat all pre-provided specs as preliminary estimates only.** The Master **must not blindly trust** manually
   entered/purchase specs for operational decisions.
2. **On node onboarding (the real preflight phase), the Master collects actual node facts** directly from the node via
   **read-only SSH probes** — never mutating the node, never printing secrets.
3. **Detected facts override estimates** in operational docs/status and (later) in the DB node metadata.
4. **Every spec value carries a provenance tier:**
   - `estimate` — provider/purchase value (unverified)
   - `detected` — read by the Master from the node itself (authoritative for hardware/OS/ports)
   - `provider-confirmed` — from a provider API/dashboard (e.g. the real bandwidth allowance), where available
   - `unknown` — not yet verified
   Bandwidth allowance stays **`estimate`** until **`provider-confirmed`** (the node can't self-report its contractual cap).
5. **Verify before Hiddify install, and re-check after install** if resource usage materially changes.
6. **Role-fit gate:** the preflight must confirm detected resources meet the node's role (enough disk/RAM for Hiddify)
   and that the node is clean of legacy artifacts, before any install proceeds.

### Consequences

- The future probe (read-only, no-secrets, no-mutation) is specified in
  [PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md); suggested name `scripts/node_preflight_probe.sh`. It is
  **written/run only when Phase 2-DE actually begins** — not now.
- Operational docs ([SERVERS.md](SERVERS.md), [NODES.md](NODES.md)) now label `de1`'s specs as **provider-estimate
  (unverified)** and reserve a place for detected/confirmed values.
- When the DB schema exists (Phase 4), `proxy_nodes` should store both the estimate and the detected value (or a
  provenance flag per field) rather than a single unqualified number.

---

## ADR-003 — Master minimalism and cleanup of abandoned co-location dependencies

- **Date:** 2026-06-15
- **Status:** ACCEPTED (Charles) — **future requirement; NOT executed now.**
- **Relates to:** ADR-001 (co-location retired).

### Decision

The **Master is control-plane only.** Any package/service/feature installed **solely** for the abandoned co-located
DE-Hiddify path is a **cleanup candidate**. In particular, the **Docker engine** remains installed only as a leftover
from the failed Hiddify-on-Master test (ADR-001); if no control-plane task needs it, it should be **removed in a
future audited cleanup task**, *not* during node onboarding.

### Rationale

Unused infrastructure packages add attack surface, maintenance burden, port/firewall confusion, and operational
drift. The Master should run **only** what the control plane needs: bots, DB, payments, admin, customer portal, API,
the subscription sidecar, monitoring, backups, Git-based deployment, and node orchestration.

### Future cleanup task — "Master cleanup after retired co-location attempt"

Done in a **safe, audited phase of its own** (not during node onboarding). **Pre-removal verification (all must hold):**
- no running containers; no Docker volumes/networks/images that are needed;
- no project **service** depends on Docker; no **docs/scripts** currently require Docker;
- no Hiddify remnants remain on the Master (no `/opt/hiddify-manager`, no hiddify units/images);
- Master **80/443 remain free**; **SSH untouched**.

**If safe, may remove:** the unused Docker engine/packages; unused Docker networks/volumes/images; any abandoned
Hiddify-on-Master remnants; any other package/service installed only for the retired co-location path.

**Safety:** consider a provider snapshot — or at minimum a **git-clean tree + a recorded service/package-state
backup** — before host package removal. Removal steps are dry-run/audited; **stop and report** on any unexpected
dependency. Update docs + commit/push afterward.

### Current state (for the cleanup task to act on)

Docker **29.5.3** is installed and **idle** (no Hiddify; `/opt/hiddify-manager` already removed; 80/443 free) — it is
the primary cleanup candidate. Left installed for now per ADR-001; removal deferred to the audited cleanup task above.
