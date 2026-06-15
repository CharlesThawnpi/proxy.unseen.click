# SERVICES

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §5
> **Status:** Phase 1 skeleton — decided from plan

The Master VPS services and systemd timers. Each service binds to `127.0.0.1` and is fronted by **nginx** (sole owner of public `:80/:443`, TLS via Let's Encrypt/Certbot). Project root: `/opt/unseen-proxy/`, one subdir per service.

## Master service table

| Service (unit) | Purpose | Framework | Loopback port | Subdomain |
|---|---|---|---|---|
| `unseenproxy-bot.service` | Telegram bot (then Messenger/Viber adapters) | python-telegram-bot (async) | n/a (long-poll) or webhook | `bot.unseen.click` (webhooks if used) |
| `unseenproxy-sidecar.service` | Subscription delivery `/s/<token>` | stdlib WSGI (thin) | `127.0.0.1:8197` | `sub.unseen.click` |
| `unseenproxy-admin.service` | Web admin dashboard | FastAPI + Uvicorn | `127.0.0.1:8190` | `panel.unseen.click` |
| `unseenproxy-portal.service` | Customer self-service web portal | FastAPI + Uvicorn (server-rendered) | `127.0.0.1:8191` | `app.unseen.click` |
| `unseenproxy-api.service` | Internal/service API layer | FastAPI + Uvicorn | `127.0.0.1:8192` | `api.unseen.click` |
| (nginx) | Marketing site (static) | nginx static | n/a | `unseen.click` / `www` |
| Hiddify orchestrator | API v2 client + provisioner (library + CLI scripts used by bot/admin) | python | n/a | n/a |

**Shared database:** a single SQLite file (e.g. `/opt/unseen-proxy/data/unseenproxy.sqlite3`) accessed by bot/admin/portal/sidecar using WAL-safe patterns. Postgres migration path noted in Appendix A if/when concurrency demands it.

## systemd timers

| Timer | Interval | Purpose |
|---|---|---|
| `unseenproxy-notify.timer` | ~60s | Flush queued notifications; auto-issue/auto-delivery pass; usage sync |
| `unseenproxy-backup.timer` | daily | WAL-safe DB snapshot + `.env` + units backup |
| `unseenproxy-leak-watcher.timer` | ~30min | Subscription IP-diversity watcher; sanitized admin alerts |
| `unseenproxy-node-health.timer` | ~hourly | Per-node Hiddify health + bandwidth/capacity |
| `unseenproxy-payment-timeout.timer` | ~60s | Expire stale payment/screenshot sessions |

**Secrets at rest:** every service `.env` is `0600`, root-owned. The subscription-token encryption secret (`ACCESS_TOKEN_ENCRYPTION_SECRET`) lives in the bot/sidecar `.env` and is backup-critical.
