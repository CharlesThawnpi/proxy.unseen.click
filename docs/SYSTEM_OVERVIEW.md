# SYSTEM OVERVIEW

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §3.2, §3.3, §4
> **Status:** Phase 1 skeleton — decided from plan

One-page overview of what UNSEEN PROXY is and the words used to describe it.

## What the system is

UNSEEN PROXY is a Hiddify-based VPN/proxy platform. A central **Master VPS** (the brain) runs all business logic, customer data, and chat-bot/admin/portal/API surfaces, and orchestrates one independent **Hiddify Manager** panel per region over API v2. Each region's node VPS carries proxy traffic only. Customers connect through the **Hiddify App** using a single UNSEEN-branded subscription URL.

> **Master is control-plane ONLY** — it never carries proxy traffic. The earlier DE-on-Master co-location idea is
> **retired** ([DECISIONS.md](DECISIONS.md) ADR-001); the DE node runs on its own dedicated VPS like every other region.

## Key nouns

- **Customer** — the canonical person (`customers.id` / `public_customer_code`), reachable across Telegram/Messenger/Viber/etc.
- **Subscription** — the one UNSEEN-branded URL (`sub.unseen.click/s/<token>`) a customer imports; resolves to their entitled regions + protocols.
- **Profile** — a user-facing protocol tier (FAST1 / FAST2 / Secure), mapped to an engine protocol.
- **Region** — a served location (e.g. DE, SG, US), DB-driven with explicit states.
- **Node** — a regional VPS running Hiddify Manager that carries the proxy traffic for a region.
- **Token** — the opaque per-customer subscription token the sidecar resolves to entitlements.

## The two product wins

1. **FAST1 (Hysteria2) is real.** Hiddify bundles the Hysteria2 core, so FAST1 is the default, deliverable, high-performance protocol — a genuine differentiator for high-latency / lossy Myanmar↔overseas links. (The older Xray-core-only approach could not deliver it at all.)
2. **One-tap deep-link onboarding.** Hiddify App supports `hiddify://import/<sub-link>#name`. The bot sends a button; tapping it opens Hiddify and imports automatically — removing the hardest UX step (no reliance on scanning a QR from the photo gallery).
