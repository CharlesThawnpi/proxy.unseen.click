# DOMAINS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §8
> **Status:** Phase 1 skeleton — decided from plan

The subdomain map for UNSEEN PROXY. **This file is the recorded Phase 1 naming/subdomain decision.**

## Subdomain table

Brand domain: **unseen.click**. UNSEEN PROXY uses its own fresh subdomains; it does not reuse any subdomain or endpoint from the retired UNSEEN VPN system.

| Subdomain | Service | Public? | Notes |
|---|---|---|---|
| `unseen.click`, `www.unseen.click` | Marketing site | yes | Static |
| `app.unseen.click` | Customer portal | yes | Self-service status / import-guide |
| `api.unseen.click` | API layer | yes (authenticated) | Service/integration API |
| `bot.unseen.click` | Bot webhooks | yes | Only if webhook mode is used |
| `panel.unseen.click` | Web admin | yes (auth) | Admin dashboard (consider IP allowlist) |
| `sub.unseen.click` | Subscription sidecar | yes | `https://sub.unseen.click/s/<token>` — the customer's subscription URL |
| `node-sg.unseen.click`, `node-de.unseen.click`, … | Per-node Hiddify domains | yes | Each node's own domain(s); **never shown to customers directly** |

## Naming & DNS plan

- **Brand domain:** `unseen.click`. All UNSEEN PROXY surfaces live under fresh subdomains here.
- **DNS safety — add only:** add new DNS records only; **never alter existing records** (e.g. do not touch existing `s`/`speed` records).
- **TLS / Certbot:** nginx + Certbot on the Master for Master subdomains; each node manages its own TLS for its node domain. Use a **separate Certbot lineage per new subdomain**.
- **Node domains are internal-facing:** `node-*.unseen.click` exist for each node's proxy/sub endpoints but are **never shown to customers** — customers only ever see `sub.unseen.click/s/<token>`.
