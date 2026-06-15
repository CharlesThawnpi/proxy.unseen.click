# SERVERS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) Appendix F.7
> **Status:** Phase 1 skeleton — decided from plan

Current server inventory (recorded 2026-06-15). These seed the `proxy_nodes` rows. **Specs and addresses are data, not code** — replacing or moving any node is a row update (§6.1). The public IP is stored in `proxy_nodes.public_ip`; the **panel API key and secret admin path live only in `.env`**, referenced by handle. Nodes seed as `planned`/`test` and are promoted to `live` only after the node-verification gate.

## Master VPS (control plane + co-located DE node)

| Field | Value |
|---|---|
| Role | **Master** (brain) **+ DE Hiddify node** co-located (§4.1 exception) |
| Region | Germany (DE) — default/entry region |
| Public IP | `88.214.56.96` |
| Spec | 4 vCPU, 16 GB RAM, 100 GB SSD |
| Bandwidth budget | 30 TB / month |
| `proxy_nodes` row | `node_code=de-master`, `region_code=de`, `is_master_colocated=1`, `vcpu_count=4`, `ram_mb=16384`, `disk_gb=100`, `bandwidth_budget_gb=30000` |

**Preflight-observed state (2026-06-15, read-only).** Hostname `crimson-gorilla-49484`, Ubuntu 24.04.4 LTS,
kernel 6.8.0-45, KVM/QEMU. Live readings: 4 vCPU (Xeon E5-2680 v4), 15 GiB RAM (~13 GiB free, 1.6 GiB used),
4 GiB swap (0 used), 100 GB disk (86 GB free, 10% used) — consistent with the spec above and **sufficient for a
co-located test DE node**. The DE node is **not disposable**.

**Install attempt (2026-06-15):** Docker (29.5.3) + a pinned Hiddify Docker stack (v12.3.3) were installed to
`/opt/hiddify-manager` (containers up; host safe — SSH up, control plane intact, only 80/443 published). **The panel
was non-functional** (compose Redis-password bug + DB migration errors), so it was **torn down** (`docker compose
down -v` + dir removed); the Master is back to baseline (SSH up, 80/443 free, Docker engine kept). **Decision: the DE
node moves to a separate Ubuntu-22.04 VPS** via the supported host installer — so DE is no longer co-located on the
Master (the §4.1 exception is dropped for DE). The Master row above stays as the control-plane host only. See
`PHASE3_HIDDIFY_LIVE_VERIFY.md`.

## Proxy nodes (data plane)

| node_code | region | Public IP | vCPU | RAM | Disk | Bandwidth budget |
|---|---|---|---|---|---|---|
| `sg1` | SG | `64.56.71.64` | 1 | 2 GB | 60 GB SSD | 10 TB/mo |
| `sg2` | SG | `104.250.118.37` | 1 | 2 GB | 20 GB SSD | 2 TB/mo |
| `us1` | US | `172.245.110.130` | 5 | 6 GB | 100 GB SSD | 9.8 TB/mo |

Seed values: `ram_mb` = 2048/2048/6144; `disk_gb` = 60/20/100; `bandwidth_budget_gb` = 10000/2000/9800. SG has two nodes — the offering/sidecar logic supports multiple nodes per region, and graceful degradation means if `sg1` is down, `sg2` still serves SG (§6.2).

## Capacity notes

- The SG nodes are small (1 vCPU / 2 GB) and `sg2`'s **2 TB/month** budget is modest — these hit the 75% bandwidth alert sooner under load; adding a third SG node is just another row.
- The US node is the largest by CPU. The Master has the most bandwidth headroom (30 TB), appropriate since it also carries DE proxy traffic.

## Alert thresholds (DB-driven, retunable)

| setting_key | seed value | meaning |
|---|---|---|
| `node_alert_warn_pct` | `75` | WARN when any resource/bandwidth reaches this % of its limit |
| `node_alert_critical_pct` | `90` | CRITICAL threshold |
| `node_alert_warn_snooze_hours` | `6` | Dedup window for WARN |
| `node_alert_critical_snooze_hours` | `2` | Dedup window for CRITICAL |
| `node_metrics_retention_days` | `30` | Rolling window for `node_metrics` history |
