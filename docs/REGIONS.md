# REGIONS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §7, §6.2
> **Status:** decided from plan; **seeded in DB (Phase 4A)** — `proxy_regions`: de(default,test)/us(planned)/sg(premium-only,planned); `plan_region_entitlements` enforce SG only on PRO/MAX. Admin-editable rows, not constants.

How regions are modeled, offered, and commercially tiered.

## Region states

Regions are **DB-driven** (`proxy_regions` table) and not all live by default. Each progresses through explicit states:

```
planned → test → standby → live
```

Only `live` regions are offered to customers.

## The offering rule

A region is offered to a customer only when **both**:
1. The plan **entitles** the region, **and**
2. At least **one node in that region is healthy and `live`**.

A region with entitlements but **no live node** must **not** be advertised as available (the "entitled but no node" gap must be explicitly avoided). When a node goes `down`, the Master stops offering it and serves the customer's other entitled regions (§6.2 graceful degradation).

## Commercial decision

- **Germany (DE) is the default/entry region** — present on **every plan**; the only region guaranteed on every plan. Mature EU egress; the operator's existing familiarity; the location of the Master VPS.
- **Singapore (SG) is premium-only (PRO/MAX)** — the closest low-latency hub to Myanmar, positioned as the top-tier differentiator rather than the baseline. (This reverses v1.0's "Singapore as default" recommendation.)
- **Latency note:** Myanmar↔Germany is ~8000 km. With DE as entry, **FAST1 (Hysteria2) is the mitigation** for long-haul latency; entry-tier DE customers are steered to FAST1 by default. Customers needing the lowest latency are the target for the SG premium tier.

## Candidate region table

| Region | Code | Priority rationale |
|---|---|---|
| Germany | `de` | **Default/entry region** — present on every plan; mature EU egress; Master VPS location |
| USA | `us` | Content access; added from CORE upward; higher latency |
| Singapore | `sg` | **Premium-only** (PRO/MAX) — closest low-latency hub to Myanmar; top-tier differentiator |
| Thailand | `th` | Regional proximity (evaluate routing/legal) |
| Vietnam | `vn` | Regional proximity |
| Japan | `jp` | Low-latency East-Asia alternative |
| Others | — | Add as demand/capacity justify |

Enable regions incrementally, never all at once.

## Phase 4C — entitlements resolved from DB in the provisioning plan (2026-06-16)

The dry-run provisioning plan (`backend/provisioning_plan.py`, [PHASE4C_DRY_RUN_PROVISIONING.md](PHASE4C_DRY_RUN_PROVISIONING.md))
resolves a plan's regions **from `plan_region_entitlements` rows** (never hardcoded): **DE = default/entry**, **SG =
premium-only** (surfaced in `premium_regions`, present only for PRO/MAX), US as entitled. Candidate nodes are selected
by region + status; **de1 (`status=test`) is usable for dry-run only**, never live. Tested: SG excluded from
BASIC/CORE, included for PRO/MAX.

## Phase 7 — entitlement vs availability (2026-06-16)

Phase 7 ([PHASE7_ENTITLEMENT_NODE_RESILIENCE.md](PHASE7_ENTITLEMENT_NODE_RESILIENCE.md)) makes region access honest and
dynamic, all DB-driven (`backend/entitlements.py` + `backend/availability.py`):

- **Entitlement** (plan is *allowed* the region) vs **availability** (a usable node exists *now*) are distinct.
- **DE** = default/entry (`proxy_regions.is_default`); **SG** = premium-only PRO/MAX (`is_premium_only`); US on CORE+.
- A region is **unavailable** if entitled but no eligible node (test/standby/live & not down for dry-run; live-ready
  for live). Reasons are explicit (`no_candidate_node`, `node_down`, `node_status_test`, …) — **no silent substitution**
  of another region. SG being absent never affects BASIC/CORE (not entitled). Customer copy is Burmese & secret-free.
