# SERVERS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) Appendix F.7
> **Status:** Phase 1 skeleton — decided from plan

Current server inventory (recorded 2026-06-15). These seed the `proxy_nodes` rows. **Specs and addresses are data, not code** — replacing or moving any node is a row update (§6.1). The public IP is stored in `proxy_nodes.public_ip`; the **panel API key and secret admin path live only in `.env`**, referenced by handle. Nodes seed as `planned`/`test` and are promoted to `live` only after the node-verification gate.

## Master VPS (control plane ONLY)

> **Co-location retired** — see [DECISIONS.md](DECISIONS.md) ADR-001. The Master no longer hosts the DE node and
> **carries no proxy traffic**. It runs the control plane only: bots, DB, payments, admin, portal, API, the
> subscription sidecar, monitoring, backups, Git deployment, and node orchestration. Its specs are not "wasted" —
> they protect the business/control plane.

| Field | Value |
|---|---|
| Role | **Master / control plane only** (no Hiddify, no proxy traffic) |
| Region (hosted in) | Germany |
| Public IP | `88.214.56.96` |
| Spec | 4 vCPU, 16 GB RAM, 100 GB SSD |
| Bandwidth budget | 30 TB / month |
| Note | NOT a `proxy_nodes` row (it is the control plane, not a node). Docker engine remains installed but unused. |

**Master history (2026-06-15):** the Master is Ubuntu 24.04.4 (`crimson-gorilla-49484`, KVM/QEMU; 4 vCPU Xeon
E5-2680 v4, ~13 GiB RAM free, 4 GiB swap, 86 GB disk free). A co-location attempt installed Hiddify via Docker
(v12.3.3) here; the panel was non-functional (compose Redis-password bug + DB migration errors) and was **torn down**
— the Master is back to baseline (SSH up, 80/443 free; Docker engine left installed but unused). Co-location is
**retired** ([DECISIONS.md](DECISIONS.md) ADR-001); the Master is control-plane-only henceforth.

## Proxy nodes (data plane)

| node_code | region | Public IP | vCPU | RAM | Disk | Bandwidth budget | Status | OS |
|---|---|---|---|---|---|---|---|---|
| `de1` | DE | `5.249.160.59` | 4 | 4 GB | 25 GB SSD | 30 TB/mo | **planned/test** | Ubuntu 22.04 LTS |
| `sg1` | SG | `64.56.71.64` | 1 | 2 GB | 60 GB SSD | 10 TB/mo | planned | — |
| `sg2` | SG | `104.250.118.37` | 1 | 2 GB | 20 GB SSD | 2 TB/mo | planned | — |
| `us1` | US | `172.245.110.130` | 5 | 6 GB | 100 GB SSD | 9.8 TB/mo | planned | — |

**`de1` (new, 2026-06-15):** the dedicated DE Hiddify node replacing the retired Master co-location — the
**default/entry region** now lives here. Seed: `node_code=de1`, `region_code=de`, `public_ip=5.249.160.59`,
`vcpu_count=4`, `ram_mb=4096`, `disk_gb=25`, `bandwidth_budget_gb=30000`, `status=test`. To be provisioned by
Hiddify's **supported host installer on Ubuntu 22.04** (not Docker, not on the Master) — see
[PHASE2_3_DE_NODE_PLAN.md](PHASE2_3_DE_NODE_PLAN.md). Node domain `node-de.unseen.click`.

> **These values are provider/purchase ESTIMATES (provenance = `estimate`, unverified).** Per
> [DECISIONS.md](DECISIONS.md) ADR-002, the Master must **detect** the node's real OS/CPU/RAM/disk/ports (read-only)
> at preflight and record them as `detected` (authoritative), overriding the estimates here; the **30 TB bandwidth**
> stays `estimate` until `provider-confirmed` via a provider API/dashboard. Don't treat the table as measured fact
> until preflight runs.

Seed values (SG/US): `ram_mb` = 2048/2048/6144; `disk_gb` = 60/20/100; `bandwidth_budget_gb` = 10000/2000/9800. SG has two nodes — the offering/sidecar logic supports multiple nodes per region, and graceful degradation means if `sg1` is down, `sg2` still serves SG (§6.2).

## Capacity notes

- The SG nodes are small (1 vCPU / 2 GB) and `sg2`'s **2 TB/month** budget is modest — these hit the 75% bandwidth alert sooner under load; adding a third SG node is just another row.
- `de1` has a generous **30 TB/month** budget and 4 vCPU / 4 GB, but only **25 GB SSD** — disk is the constraint to watch (Hiddify + logs + sing-box/xray); alert at 75%/90% once monitoring exists.
- The US node is the largest by CPU. The Master is **not** a node and carries no proxy bandwidth (co-location retired).

## Alert thresholds (DB-driven, retunable)

| setting_key | seed value | meaning |
|---|---|---|
| `node_alert_warn_pct` | `75` | WARN when any resource/bandwidth reaches this % of its limit |
| `node_alert_critical_pct` | `90` | CRITICAL threshold |
| `node_alert_warn_snooze_hours` | `6` | Dedup window for WARN |
| `node_alert_critical_snooze_hours` | `2` | Dedup window for CRITICAL |
| `node_metrics_retention_days` | `30` | Rolling window for `node_metrics` history |
