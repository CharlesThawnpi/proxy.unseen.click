# PORTS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §5, §8
> **Status:** Phase 1 skeleton — decided from plan

Port allocation on the Master VPS. All application services bind loopback only; nginx owns the public ports.

## Loopback ports (bound to 127.0.0.1)

| Port | Service | Subdomain |
|---|---|---|
| `8197` | `unseenproxy-sidecar` (subscription delivery `/s/<token>`) | `sub.unseen.click` |
| `8190` | `unseenproxy-admin` (web admin dashboard) | `panel.unseen.click` |
| `8191` | `unseenproxy-portal` (customer self-service portal) | `app.unseen.click` |
| `8192` | `unseenproxy-api` (internal/service API layer) | `api.unseen.click` |

The bot uses long-poll (no inbound port) or webhook mode via `bot.unseen.click`.

## Public ports (owned by nginx)

| Port | Owner | Role |
|---|---|---|
| `80` | nginx | HTTP — ACME challenge / redirect to HTTPS |
| `443` | nginx | HTTPS — TLS termination, subdomain routing to loopback services |

nginx is the **sole** owner of `:80`/`:443` on the Master. Node proxy ports are managed independently on each node by Hiddify Manager (not Master concerns).

> Node-side proxy inbound ports: Verified in Phase 3 (node test gate).

## Phase 2 preflight — current live port map (Master, 2026-06-15)

Observed via `ss -tulpn` (read-only). See `PHASE2_MASTER_DE_HIDDIFY_PREFLIGHT.md`.

| Port | Bind | Owner now | Status |
|---|---|---|---|
| 22/tcp | `0.0.0.0` + `[::]` | sshd | in use (keep) |
| 53 udp/tcp | `127.0.0.x` | systemd-resolved | loopback stub |
| 43417 / 22815 tcp | `127.0.0.1` | transient tooling (ephemeral) | not project services |
| **80, 443** | — | **FREE** | reserved for nginx — see conflict below |
| 8190 / 8191 / 8192 / 8197 | — | **FREE** | reserved for admin/portal/api/sidecar |

**⚠ Co-location port conflict (Master = DE node).** Hiddify Manager bundles its own web/proxy stack and TLS and
expects to own **80/443** — the same ports the Master control plane needs for `api/bot/panel/app/sub`. This is the
central blocker (B1); the coexistence strategy (shared reverse proxy / SNI split / alternate ports) must be decided
**before install**, informed by the Phase 3 audit. Hiddify's actual panel/proxy port layout is **not assumed** here.
