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
