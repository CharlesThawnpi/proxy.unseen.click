# ARCHITECTURE

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §4, §5, §6
> **Status:** Phase 1 skeleton — decided from plan

How UNSEEN PROXY separates business logic from proxy traffic, and the orchestration model that keeps it engine-independent.

## Control plane vs data plane

- **Control plane (Master VPS, "brain").** All business logic, all customer data, all secrets, all bot/admin/portal/API surfaces, and all provisioning orchestration. The Master is the only place that knows who a customer is. It calls each region's Hiddify panel over HTTPS **API v2** to create/update/disable users and read usage.
- **Data plane (Nodes).** Each regional VPS runs **Hiddify Manager** and carries proxy traffic only. A node knows about Hiddify *users* (UUIDs with quotas/expiry) but nothing about payments, identities, or other regions. Customer VPN traffic goes **customer → node directly**; the Master never proxies traffic.

## The co-location exception — RETIRED (DE moved to its own VPS)

> **Superseded by [DECISIONS.md](DECISIONS.md) ADR-001 (2026-06-15).** The §4.1 co-location exception is **retired for
> this build.** **The Master carries no proxy traffic — full stop, no exception.**

**The rule is now absolute:** the Master is **control-plane only**. The DE Hiddify node runs on its **own dedicated
VPS** (`de1`, `5.249.160.59`, Ubuntu 22.04 — see [SERVERS.md](SERVERS.md)), an ordinary node managed from the Master
over API v2 like any other region.

**Historical note (why retired):** co-location was planned (§4.1), preflighted (Phase 2), audited (Phase 3), and
**tested** — Hiddify's experimental **Docker** install (v12.3.3) on the Ubuntu-24.04 Master. The panel was
non-functional (compose `$REDIS_PASSWORD` interpolation bug → Redis password-less; DB migration errors); Hiddify
officially calls Docker "not for permanent use." It was torn down and the decision made to keep the control plane
clean and run DE on a separate, supported Ubuntu-22.04 host install. The dynamic-node property (§6.1) made this a
data-only move (no schema/code change). A bonus: there is no longer a single box whose outage takes down both control
plane and DE together.

## Why "Master + independent regional Hiddify panels" (not native multi-server)

Hiddify's native multi-server story (parent-child sync, load-balancing, central user management) is immature/in-progress (open feature requests; only partial `childs`/`child_unique_id` constructs). Betting the architecture on an unfinished feature is a launch risk.

Instead, the Master **orchestrates the same logical customer across independent regional Hiddify panels** — calling each panel's API v2 to create/update/disable the corresponding Hiddify user — and **aggregates the per-region subscription bodies behind the UNSEEN subscription sidecar**. This is a clean, well-understood model (node entitlements + a sidecar that filters/aggregates) that keeps business logic engine-agnostic. If Hiddify's native multi-server matures, it can be adopted later as an internal optimization without changing the customer-facing contract.

## The engine-independent subscription contract

The customer always receives **one UNSEEN-branded subscription URL**: `https://sub.unseen.click/s/<opaque-token>`. The Master's sidecar resolves the token to the customer's entitled regions + protocols, fetches the relevant upstream Hiddify subscription content, filters it to the entitlement set, re-brands it, and serves it. The customer **never** sees a raw Hiddify panel URL, a panel secret path, or a node IP.
