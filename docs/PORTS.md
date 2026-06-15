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
