# ARCHITECTURE

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §4, §5, §6
> **Status:** Phase 1 skeleton — decided from plan

How UNSEEN PROXY separates business logic from proxy traffic, and the orchestration model that keeps it engine-independent.

## Control plane vs data plane

- **Control plane (Master VPS, "brain").** All business logic, all customer data, all secrets, all bot/admin/portal/API surfaces, and all provisioning orchestration. The Master is the only place that knows who a customer is. It calls each region's Hiddify panel over HTTPS **API v2** to create/update/disable users and read usage.
- **Data plane (Nodes).** Each regional VPS runs **Hiddify Manager** and carries proxy traffic only. A node knows about Hiddify *users* (UUIDs with quotas/expiry) but nothing about payments, identities, or other regions. Customer VPN traffic goes **customer → node directly**; the Master never proxies traffic.

## The co-location exception (DE node on Master)

The general rule is *the Master carries no proxy traffic*. There is **one deliberate, contained exception**: the Master in Germany also hosts the **DE Hiddify node** on the same box, so the default/entry region (DE) is served without a second VPS.

- The DE node is still modeled as an ordinary node in the DB (`node_code=de-master`, `is_master_colocated=1`), addressed through the same API v2 path, subject to the same health/capacity monitoring.
- **Guardrail:** the DE node's proxy resource use is budgeted and watched (Master CPU/RAM/bandwidth headroom is first-class in alerts) so it cannot starve the control plane.
- **Movable:** if DE traffic outgrows the shared box, the DE node moves to its own VPS **with no schema or code change** (the dynamic-node property, §6.1).
- The exception applies **only** to DE-on-Master; no other region is ever co-located on the control plane.
- **Caveat:** a Master outage affects both the control plane and the DE node together — the one place co-location trades isolation for cost.

## Why "Master + independent regional Hiddify panels" (not native multi-server)

Hiddify's native multi-server story (parent-child sync, load-balancing, central user management) is immature/in-progress (open feature requests; only partial `childs`/`child_unique_id` constructs). Betting the architecture on an unfinished feature is a launch risk.

Instead, the Master **orchestrates the same logical customer across independent regional Hiddify panels** — calling each panel's API v2 to create/update/disable the corresponding Hiddify user — and **aggregates the per-region subscription bodies behind the UNSEEN subscription sidecar**. This is a clean, well-understood model (node entitlements + a sidecar that filters/aggregates) that keeps business logic engine-agnostic. If Hiddify's native multi-server matures, it can be adopted later as an internal optimization without changing the customer-facing contract.

## The engine-independent subscription contract

The customer always receives **one UNSEEN-branded subscription URL**: `https://sub.unseen.click/s/<opaque-token>`. The Master's sidecar resolves the token to the customer's entitled regions + protocols, fetches the relevant upstream Hiddify subscription content, filters it to the entitlement set, re-brands it, and serves it. The customer **never** sees a raw Hiddify panel URL, a panel secret path, or a node IP.
