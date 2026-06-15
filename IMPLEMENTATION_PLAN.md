# UNSEEN PROXY — Hiddify-Based Future-Proof VPN/Proxy Platform

**Master Implementation Plan (v1.9)**

> **v1.9 changes (2026-06-15).** Added **GitHub as the authorized code/docs home** with **manual pull-to-deploy** (new Section 31A): private repo `https://github.com/CharlesThawnpi/proxy.unseen.click.git`; **code + docs only — never secrets, `.env`, the database, or backups** (enforced by `.gitignore` + a pre-commit secret-scan hook); branching/tags for rollback; deploy by `git pull` on the Master via a read-only, least-privilege deploy key (the Master keeps its own `.env`/DB; nodes are not deployed from git); CI is deferred (checks-only, optional, later). Recorded the repo in metadata, clarified the clean-build isolation rule (this repo is *authorized*, not a forbidden legacy artifact), added repo-init + secret-free-first-push to Phase 1, added `DEPLOYMENT.md`/`VERSION_CONTROL.md` to docs, and added risks 20–21. Also fixed a stale legacy doc reference in Section 32.
>
> **v1.8 changes (2026-06-15).** Refined the language requirement (Section 9.4): the frontend is **Burmese-primary (~90% Burmese / ~10% English)** rather than all-Burmese — English is deliberately kept for terminology that reads better in English (e.g. **"Plan"**, profile labels, GB/QR/VPN), with the exact term list recorded in `docs/LOCALIZATION.md`. **Invoices and receipts are in English** (not Burmese) — only the bot/portal interaction layer is Burmese-primary. Updated Product Goal #9, the Telegram menu (Section 10, "Plan" stays English), Phases 5 and 9, and risk #19 (dropped the Burmese-invoice-font concern accordingly).
>
> **v1.7 changes (2026-06-15).** Added a full **cross-platform account-linking feature** (new Section 9.3): a customer on any front-end can link to **one profile** using a **short link code — no email, no password** — designed for non-technical/older users; the code is valid 24h and one-time, and linking **merges** both sides so all subscriptions/keys are visible on every platform (gated, dry-run-first, audited, reversible via a new `customer_merges` table; `account_link_tokens` now stores a hashed code; `customers` gains `merged_into_customer_id`). Established a Burmese-default frontend (refined in v1.8 above). Reflected in Product Goals #4 and #9, the Telegram menu (Section 10), Phases 5 and 9, docs (`ACCOUNT_LINKING.md`, `LOCALIZATION.md`), and risks 17–19.
>
> **v1.6 changes (2026-06-15).** Reframed the entire plan from a **clone-and-adapt fork** of the prior UNSEEN VPN system into a **greenfield clean build**, because that system is now **fully retired** and must not be referenced. Established **clean-build isolation** as the single most important rule (header): build from this plan only, scope the coding tool to the UNSEEN PROXY root, never search/import/clone any legacy artifact. Added **Phase 0 — Clean-VPS verification** (a hard gate with `CLEAN_VPS_CHECKLIST.md` before any build), a per-phase **isolation guard** (Section 33), and a matching definition-of-done item. Rewrote Section 35 ("clone strategy" → "clean-build strategy"), Section 3 ("differences vs current" → "core design and technology rationale"), Product Goal #1 ("re-platform" → "build clean"), Appendix B ("old→new mapping" → "canonical component list", removing pointers to legacy filenames), and risk #11 (legacy contamination). Stripped legacy attributions throughout while **keeping the lessons** as plain design requirements (gap-safe customer codes, WAL-safe backups, allowlist-before-approval, etc.).
>
> **v1.5 changes (2026-06-15).** Recorded the **current server inventory** (Master DE `88.214.56.96` + co-located DE node; SG1 `64.56.71.64`; SG2 `104.250.118.37`; US `172.245.110.130`) in **Appendix F.7** with specs and bandwidth budgets, seeded into an expanded `proxy_nodes` schema. Added three capabilities: (a) a **node performance dashboard + threshold alerting** — visualize CPU/RAM/disk/bandwidth/users/connect-quality for all nodes, with a **75% WARN / 90% CRITICAL / down** alert system to the admin, all DB-driven (Section 30.2.1, `node_metrics`/`node_alerts` tables, Phase 10); (b) **graceful degradation** — if any node is damaged/cancelled/unreachable the system keeps serving on the remaining nodes and shows the customer an honest "region unavailable" status instead of failing as a whole (Section 6.2, Phases 6–7); (c) **dynamic, replaceable nodes** — nodes are pure data managed only through the Master, so add/replace/retire is a row update with no code change; an operator/coding tool connects only to the Master, which controls every node (Section 6.1). Also documented the **co-location exception**: the Master in DE also hosts the DE node (Section 4.1), with guardrails and risks 13–16.
>
> **v1.4 changes (2026-06-15).** Made **platform-first messaging compliance** an explicit, non-negotiable principle: for every front-end platform we plan to that platform's rules/policies first and build notification content/types/timing to comply with its allowances *before* the channel launches (new **Section 9.1**), with a **per-channel launch compliance gate** (Section 9.2) and a matching prerequisite added to **Phase 9**. Recorded per-platform policy contracts (Telegram terms; Meta Messenger 24-hour window + approved templates + app review; Viber session/subscription rules; WhatsApp 24-hour window + pre-approved templates + opt-in/out) in `docs/BOT_FLOWS.md`, enforced centrally by NotificationService (send-now / queue / template / suppress). Reflected in Product Goal #4.
>
> **v1.3 changes (2026-06-15).** Added **future-proofing primitives** (new Section 30A + schema rows in Appendix A) and two operational safeguards: (a) **schema migrations registry** — an ordered "logbook" so structural DB changes are safe to re-run and identical across test/live (30A.1); (b) **idempotency** on payment approval and provisioning so a double-tap/retry can never create two subscriptions or two referral grants (30A.2); (c) **outbound notification queue with retry/dead-letter** so reminders/deliveries are never silently lost and the Messenger/WhatsApp window rules are handled cleanly (30A.3); (d) **anonymous connect-success/latency telemetry** per region+protocol to make the FAST1-on-DE bet evidence-based, with no customer identity/IP/PII (30A.4); (e) **no-downtime secret-rotation runbook** for the encryption secret and node API keys (30A.5, `docs/SECRET_ROTATION.md`); (f) a gated **customer data export/deletion** admin action (Section 28). Phase 4 now builds the migrations/idempotency/queue mechanisms. **Not adopted:** multi-currency money modeling — the product is MMK-only with no cash-credit system, so it was deliberately left out.
>
> **v1.2 changes (2026-06-15).** (a) **TRIAL is now 10 GB / 7 days** (was 30 GB / 30 days in v1.0, 30 GB / 7 days mid-edit) — corrected everywhere (Section 18, Appendix F). (b) Added a **referral system** (new Section 20A) — double-sided, credit-ledger, bonus-day rewards triggered on the referee's first approved paid order; all parameters DB-driven (Appendix F.6); schema additions in Appendix A (`referral_credits` ledger + `customers` referral fields); activation-flow hook added (Section 21, step 8). (c) Reinforced the **dynamic-config invariant** (Section 18, "Dynamic-config invariant") — every plan allowance/limitation is a runtime-editable DB value, never a code constant; the seed values document only the starting state.
>
> **v1.1 reconciliation (2026-06-15).** This version folds in the concrete plan catalogue from `Plan_Rules.md`, which is now the **authoritative source** for plan values wherever it and this document once differed. The substantive changes from v1.0: (a) firm MMK prices, per-plan regions, per-plan profiles, and recommended-device counts are now seeded (Section 18); (b) **Germany (DE) is the default/entry region** and **Singapore (SG) is premium-only** (PRO/MAX) — this reverses v1.0's "SG as default" recommendation everywhere it appeared (Sections 7, 25, 34/Phase 2, 36); (c) the **"Fast" display rule** is specified — a profile is shown as **"Fast"** when a plan carries only one Fast tier, and as **"Fast1"/"Fast2"** when it carries both, computed automatically from entitlements, not stored as a label (Sections 18, 26); (d) **FAST2 (Shadowsocks)** is fully wired for PLUS/PRO/MAX and goes live once node-tested; (e) the first disposable test node is **DE**, not SG (Phase 2).

| Field | Value |
|---|---|
| Project | **UNSEEN PROXY** (new) |
| Built-from | **This plan only** — greenfield build on freshly cleaned VPS; the prior UNSEEN VPN system is fully retired and must not be referenced (see "clean-build isolation" rule below) |
| Proxy engine | **Hiddify Manager / Hiddify Server** (sing-box + Hysteria2 core) |
| Client app | **Hiddify App** |
| Primary protocols | **Hysteria2 (FAST1)**, **Shadowsocks (FAST2)**, **VLESS-Reality (Secure)** + other Hiddify-supported |
| Brand domain | **unseen.click** (subdomains: `app/api/sub/bot/panel/...`) |
| Frontends | Telegram bot (first), Facebook Messenger bot, Viber bot; later WhatsApp |
| Backend identity | Unified **customer_id**; all platform IDs are linked identities only |
| Source control | **GitHub (private):** `https://github.com/CharlesThawnpi/proxy.unseen.click.git` — the authorized code/docs home (Section 31A). Holds **code + docs only**; never secrets, `.env`, the database, tokens, or keys. |
| Plan date | 2026-06-15 (v1.9; v1.0 was 2026-06-14) |
| Status of this doc | Architecture/planning artifact — **no code written yet** |

> **How to use this document.** This plan is written to be read top-to-bottom by a coding tool (Claude Code, Cursor, Codex, Gemini, VS Code agents, etc.) and by a human operator. It is deliberately phased so an agent implements **one safe slice at a time**, never "everything at once." Sections 1–33 describe *what to build*; Section 34 describes *the order to build it in*; Sections 35–36 cover migration and risk. Appendices give concrete schema, an old→new mapping table, and a Hiddify technical reference.
>
> **The single most important rule (clean-build isolation):** UNSEEN PROXY is a **greenfield build on freshly cleaned VPS**. The prior UNSEEN VPN system (Marzban + Happ) is **fully retired** and nothing depends on it. **This plan is the sole specification — no UNSEEN VPN code, repositories, file paths, databases, services, configs, or backups may be present on, copied to, or referenced by the new build.** The Vibe Code tool (or any coding agent) must build **only** from this document, scoped to the UNSEEN PROXY project root, and must never search for, import, clone, or "match against" any earlier UNSEEN VPN artifact. (The project's **own** GitHub repo — `https://github.com/CharlesThawnpi/proxy.unseen.click.git`, Section 31A — is the *authorized* home for this new code and is **not** a legacy artifact; the prohibition is specifically on the retired UNSEEN VPN repos/code.) If any legacy artifact is found on a target VPS, the build **stops** and the operator clears it first (Phase 0 pre-build checklist). This guarantees the new system is clean, self-contained, and free of stale assumptions or accidental cross-wiring.

---

## Table of Contents

0. Executive summary
1. Project overview
2. Product goals
3. Core design and technology rationale
4. System architecture
5. Master VPS architecture
6. Multiple-node VPS architecture
7. Supported regions
8. Domain and subdomain structure
9. Bot platform architecture (multi-platform identity)
10. Telegram bot settings and flow
11. Facebook Messenger bot settings and flow
12. Viber bot settings and flow
13. Future WhatsApp bot support
14. Hiddify Manager integration
15. Hiddify App user onboarding
16. Web app / customer portal
17. Subscription URL and QR/link delivery
18. Plan structure
19. Customer registration flow
20. Payment flow
20A. Referral system
21. Subscription activation flow
22. Renewal flow
23. Expiry handling
24. Data/bandwidth allowance handling
25. Region entitlement handling
26. Protocol entitlement handling
27. Device recommendation policy
28. Admin control requirements
29. Support flow
30. Logging, monitoring, backup, and rollback procedures
30A. Data integrity & resilience primitives
31. Security and secret-safety rules
31A. Source control & deployment (GitHub)
32. Documentation requirements
33. Testing and verification procedures
34. Deployment phases
35. Clean-build strategy (no legacy reference)
36. Risks, limitations, and follow-up tasks
- Appendix A — Proposed database schema (cloned + adapted)
- Appendix B — Old→New mapping (services, scripts, env, tables)
- Appendix C — Hiddify technical reference (sub URLs, deep links, API)
- Appendix D — Coding-agent task checklist / "definition of done"
- Appendix E — Glossary
- Appendix F — Authoritative seed data (plans, regions, profiles, entitlements)

---

## 0. Executive summary

UNSEEN PROXY is built **fresh, from this plan alone**, on cleaned VPS. Its design embodies a **proven business architecture** — a unified `customer_id` identity model, dynamic DB-driven plans, a payment flow (manual + wallet-screenshot OCR), invoice/receipt PDFs, a per-customer opaque subscription token wrapped behind an UNSEEN-branded subscription domain, a User-Agent filter, an IP-leak watcher, a dry-run/gated/latched operational safety culture, and a WAL-safe backup discipline. These are written here as **design requirements to implement**, not as code to copy from anywhere; the prior UNSEEN VPN system is retired and is not a reference.

The proxy engine and client app are **Hiddify Manager + Hiddify App** (sing-box + Hysteria2 core), chosen for two product wins:

1. **FAST1 = Hysteria2 actually works.** Marzban/Xray-core (the prior, now-retired stack) could not run Hysteria2 inbounds, so a "FAST1" tier was never deliverable there. Hiddify ships sing-box + the Hysteria2 core natively, so FAST1 becomes a genuine, deliverable, high-performance protocol from day one.
2. **One-tap onboarding via deep links.** Hiddify App supports the `hiddify://import/<sub-link>` URL scheme. The bot sends a tappable button that opens Hiddify and imports the subscription automatically — no "scan a QR from your photo album" step. This is the simplest possible onboarding for a non-technical user.

The build is split into **12 phases** (Section 34), preceded by a **Phase 0 clean-VPS verification**. Phases 1–4 are documentation, a throwaway test VPS, a Hiddify API/subscription compatibility audit, and the fresh database/backend — all reversible and non-customer-facing. Customer-facing capability (Telegram bot → Hiddify delivery) does not arrive until Phases 5–6, behind feature flags, on a controlled internal beta. Messenger/Viber, the web portal, monitoring hardening, and public launch follow.

Every phase carries the same non-negotiable rules: **clean-build isolation (no legacy UNSEEN VPN code/paths/repos referenced — build from this plan only)**, **dynamic config (never hardcode plans/prices/regions/protocols/nodes)**, **no secrets ever exposed**, **not all regions/nodes live by default**, **back up DB + `.env` together before schema changes**, and **dry-run before every live mutation**.

---

## 1. Project overview

UNSEEN PROXY is a multi-region, multi-protocol VPN/proxy subscription service sold and supported entirely through chat-app bots. A customer talks to a bot (Telegram first), chooses a plan, pays via a local Myanmar mobile-wallet method, and receives a single subscription that they import into the **Hiddify App** with one tap. Behind the scenes a **Master VPS** runs the entire business brain (customer database, bots, payments, admin tools, subscription generation, monitoring, backups) while **regional node VPS servers** run **Hiddify Manager** and carry only proxy traffic.

The business model, customer treatment, plan formats, payment handling, support flow, and admin logic follow a **proven design** (validated by the now-retired UNSEEN VPN product), but UNSEEN PROXY is built **fresh from this plan** — it is a new, self-contained system on clean infrastructure, not a fork of or reference to any existing codebase.

Key nouns:

- **Customer** — a person, identified by a backend `customer_id` and a human-friendly `public_customer_code` (e.g. `UP0001`).
- **Subscription** — one purchased plan instance with a data cap, an expiry, a status, and a delivery lifecycle.
- **Profile (protocol)** — FAST1 / FAST2 / Secure (see Section 26). Customer-facing names are simple; technical protocol names live only in admin docs.
- **Region** — a geographic egress (Singapore, Germany, USA, …), each backed by one or more node VPS.
- **Node** — a single regional VPS running Hiddify Manager.
- **Subscription token** — a per-customer opaque secret that resolves, on the Master, to that customer's entitled set of region/protocol configs, served from an UNSEEN-branded subscription URL.

---

## 2. Product goals

1. **Build clean.** Stand up UNSEEN PROXY fresh on cleaned VPS from this plan alone, with no legacy code, paths, or data referenced — a self-contained system with zero stale assumptions.
2. **Future-proof protocol stack.** Default to Hysteria2 (fast, censorship-resistant) with Shadowsocks and VLESS-Reality as alternatives; keep the protocol set admin-configurable so new Hiddify protocols can be enabled without code changes.
3. **One-tap onboarding.** The bot must get a non-technical user connected with the fewest taps possible — deep-link import first, copy-paste second, guided walkthrough third.
4. **Multi-platform reach, one profile, platform-compliant by design.** Telegram now; Messenger and Viber next; WhatsApp later — all sharing one customer identity and one backend. A customer can **link any platform to the same profile with a simple code (no email)** so purchases made on one app appear on all of them (Section 9.3). **For each platform we plan to that platform's messaging rules and policies first, and build notification content/types/timing to comply with its allowances (e.g. Meta's 24-hour window + approved templates) before that channel launches** (Section 9.1).
5. **Dynamic everything.** Plans, prices, data allowances, durations, device recommendations, region entitlements, and protocol entitlements are all DB-driven and admin-editable. No hardcoded business values.
6. **Server-side control, honest promises.** Never claim configs are uncopyable. Enforce value with per-user tokens, usage caps, expiry, token rotation, UA-filtering, and abuse monitoring.
7. **Operational safety as a feature.** Dry-run-first, gated/latched live actions, WAL-safe backups, reversible changes, sanitized logging, and "never fabricate a PASS — always verify artifacts on disk."
8. **Production-oriented from day one.** Every major change updates documentation; every phase has explicit exit criteria and rollback steps.
9. **Burmese-primary frontend.** The customer interaction layer — bots, portal, buttons, errors, reminders, onboarding, account-linking — is ≈90% Burmese with English kept for terminology that reads better in English (e.g. "Plan"), designed for non-technical and older users; **invoices/receipts are in English**; no email or password is ever required of a customer (Section 9.4).

---

## 3. Core design and technology rationale

### 3.1 Core business capabilities to build

The following are the engine-agnostic business capabilities UNSEEN PROXY implements. They are written as **what to build**, from this plan — not copied from any prior codebase:

- Unified identity: `customer_id` canonical, platform IDs (Telegram/Messenger/Viber/WhatsApp) linked via a `platform_accounts` table.
- Public customer code generation (a stable, gap-safe `PREFIX + zero-padded id`; use **max-numeric-id + 1**, not count + 1, so deletions never cause collisions).
- Dynamic plan catalog (data cap, duration, price, currency, device recommendation, public/admin flags), with **order-time price/cap/duration snapshots** so plan edits never invalidate old orders.
- Payment flow: plan selection → payment-method selection → wallet-screenshot upload → OCR auto-verify (Tesseract) → auto-approve or admin review → reject path; plus a Manual Payment (admin-reviewed) method.
- Invoice + receipt PDF generation (with a "pre-live / not final" watermark until public launch).
- "My Account" features: subscription cards (plan, usage, remaining, expiry), re-show subscription/QR, invoice/receipt download.
- Per-customer **opaque subscription token**, SHA-256 hashed in the DB, **durable encrypted at rest** (decryptable only with the `.env` encryption secret), served from an UNSEEN-branded subscription host behind nginx with `access_log off`.
- **User-Agent filter** on the subscription endpoint (off / report / enforce; reason-opaque 404; allowlist of real proxy clients).
- **IP-leak watcher** (masked-prefix diversity, report-only, sanitized admin alerts, dedup/snooze) and the **gated suspender** that refuses the admin profile.
- Region/protocol **entitlement** model (plan → region, plan → protocol, profile availability per region/node).
- Admin surfaces: a web admin app + a Telegram admin mode.
- Backups (WAL-safe `conn.backup()`, DB **and** `.env` together), monitoring timers, and the dry-run/gated culture.

### 3.2 Technology choices (and why)

| Concern | Choice for UNSEEN PROXY | Why (vs. the older Marzban/Xray/Happ approach) |
|---|---|---|
| Proxy panel | **Hiddify Manager**, one independent panel **per region**, orchestrated from Master via API | Mature multi-protocol panel; per-region independence enables graceful degradation (Section 6.2) |
| Proxy core | **sing-box + Hysteria2 + Xray** (Hysteria2, SS, VLESS-Reality all supported) | Xray-core alone could not run Hysteria2; Hiddify's core can |
| Client app | **Hiddify App** | Supports one-tap deep-link import |
| Default protocol | **Hysteria2 ("FAST1")** default; SS ("FAST2"); VLESS-Reality ("Secure") | Hysteria2 (QUIC/UDP) handles lossy long-haul links best |
| Onboarding | **`hiddify://import/...` deep-link button** (one tap) + copy-link + QR fallback | Fewest taps for a non-technical user; no gallery-QR dependence |
| Provisioning API | **Hiddify Manager API v2** (`hiddify_customer_provisioner.py`) | Per-region user create/update/disable over HTTPS |
| Per-user identity in engine | **Hiddify user UUID** (per region panel) | One stable per-customer UUID reused across panels |
| Subscription upstream | **Per-region Hiddify sub body**, aggregated/filtered by the Master sidecar | Lets the sidecar fail-soft and filter by entitlement |
| Brand / domain | **unseen.click** (api/bot/sub/panel/app subdomains) | Fresh domains; no legacy endpoints reused |

### 3.3 The two product wins these choices unlock

1. **FAST1 (Hysteria2) is real.** Hiddify bundles the Hysteria2 core, so FAST1 is the default, deliverable, high-performance protocol — a real marketing differentiator for high-latency / lossy Myanmar↔overseas links. (The older Xray-core-only approach could not deliver it at all.)
2. **Deep-link onboarding removes the hardest UX step.** Hiddify App supports `hiddify://import/<sub-link>#name` and related schemes (`install-sub`, `install-config`, `install-proxy`). The bot sends a button; tapping it opens Hiddify and imports automatically — no reliance on scanning a QR from the photo gallery.

---

## 4. System architecture

### 4.1 Control plane vs data plane

```
                         ┌──────────────────────────────────────────────────────┐
   Customers             │                  MASTER VPS (brain)                    │
  (chat apps)            │                                                        │
  Telegram ──────────────┤  bot adapters ─┐                                       │
  Messenger ─────────────┤  (TG/Msgr/Viber)│                                      │
  Viber ─────────────────┤                 ▼                                      │
                         │           core backend  ──────►  unified SQLite DB     │
                         │      (plans, payments, identity,                       │
                         │       entitlements, deliveries)                        │
                         │                 │                                      │
                         │                 ├──► subscription sidecar (sub.unseen.click)
                         │                 │      per-user token → entitled configs│
                         │                 ├──► web admin (panel.unseen.click)     │
                         │                 ├──► customer portal (app.unseen.click) │
                         │                 ├──► API layer (api.unseen.click)       │
                         │                 ├──► monitoring / leak-watcher / backups│
                         │                 │                                      │
                         │   Hiddify orchestrator (API v2 client, per region)     │
                         └───────┬─────────────────┬──────────────────┬───────────┘
                                 │ HTTPS API v2     │ HTTPS API v2      │ HTTPS API v2
                                 ▼                  ▼                   ▼
                        ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                        │ NODE: SG    │     │ NODE: DE    │     │ NODE: US ... │
                        │ Hiddify Mgr │     │ Hiddify Mgr │     │ Hiddify Mgr  │
                        │ Hysteria2 / │     │ ...         │     │ ...          │
                        │ SS / Reality│     │             │     │              │
                        └─────────────┘     └─────────────┘     └─────────────┘
                          (proxy traffic only — no customer DB, no business logic)
```

- **Control plane (Master):** all business logic, all customer data, all secrets, all bot/admin/portal/API surfaces, and all provisioning orchestration. The Master is the only place that knows who a customer is.
- **Data plane (Nodes):** each regional VPS runs **Hiddify Manager** and carries proxy traffic only. A node knows about *Hiddify users* (UUIDs with quotas/expiry) but not about payments, identities, or other regions.
- **Co-location exception (documented).** The general rule is *the Master carries no proxy traffic*. There is **one deliberate, contained exception**: the **Master in Germany also hosts the DE Hiddify node** on the same box, so the default/entry region (DE) is served without a second VPS. This is treated as the Master running a *co-located* node — the DE node is still modeled in the database as an ordinary node (Section 6 / Appendix F), addressed through the same API v2 path, and subject to the same health/capacity monitoring. Guardrails: the DE node's proxy resource use is **budgeted and watched** so it cannot starve the control plane (alerts in 30A/the dashboard treat the Master's CPU/RAM/bandwidth headroom as first-class); if DE traffic ever outgrows the shared box, the DE node can be **moved to its own VPS with no schema or code change** (this is exactly the dynamic-node property in Section 6.1). The exception applies **only** to DE-on-Master; no other region is ever co-located on the control plane.

### 4.2 Why "Master + independent regional Hiddify panels" (not native Hiddify multi-server)

Hiddify's native multi-server story (parent-child sync, load-balancing, central user management) is still **immature/in-progress** at the time of writing (open feature requests for multi-server load-balancing and central user management; partial `childs`/`child_unique_id` constructs only). Betting the architecture on an unfinished feature is a launch risk.

Instead, the Master **orchestrates the same logical customer across independent regional Hiddify panels** by calling each panel's API v2 to create/update/disable the corresponding Hiddify user, and then **aggregates the per-region subscription bodies behind the UNSEEN subscription sidecar**. This is a clean, well-understood model (node entitlements + a sidecar that filters/aggregates) that keeps the business logic engine-agnostic. If/when Hiddify's native multi-server matures, it can be adopted later as an internal optimization without changing the customer-facing contract.

### 4.3 The subscription contract (engine-independent)

The customer always receives **one UNSEEN-branded subscription URL** (`https://sub.unseen.click/s/<opaque-token>`). The Master's sidecar resolves the token to the customer's entitled regions+protocols, fetches the relevant upstream Hiddify subscription content, filters it to the entitlement set, re-brands it, and serves it. The customer never sees a raw Hiddify panel URL, a panel secret path, or a node IP.

---

## 5. Master VPS architecture

The Master mirrors the current UNSEEN VPN master layout (proven), with engine-specific pieces renamed. Each service binds to `127.0.0.1` and is fronted by **nginx** (sole owner of public `:80/:443`, TLS via Let's Encrypt/Certbot). Suggested project root: **`/opt/unseen-proxy/`** with one subdir per service.

**Master server (current):** Germany, IP `88.214.56.96`, 4 vCPU / 16 GB RAM / 100 GB SSD, 30 TB/mo bandwidth (full inventory in Appendix F.7). This box runs the control plane **and** the co-located DE Hiddify node (Section 4.1 exception); its CPU/RAM/bandwidth headroom is monitored as first-class so proxy load cannot starve the control plane (Section 30.2.1). It is the **single management entry point** — operators and coding tools (e.g. Vibe Code) connect only to the Master, which orchestrates every node over API v2 (Section 6.1).

| Service | Purpose | Framework | Local port | Subdomain | systemd unit |
|---|---|---|---|---|---|
| `unseenproxy-bot` | Telegram bot (then Messenger/Viber adapters) | python-telegram-bot (async) | n/a (long-poll) or webhook | `bot.unseen.click` (webhooks if used) | `unseenproxy-bot.service` |
| `unseenproxy-sidecar` | Subscription delivery `/s/<token>` | stdlib WSGI (thin) | `127.0.0.1:8197` | `sub.unseen.click` | `unseenproxy-sidecar.service` |
| `unseenproxy-admin` | Web admin dashboard | FastAPI + Uvicorn | `127.0.0.1:8190` | `panel.unseen.click` | `unseenproxy-admin.service` |
| `unseenproxy-portal` | Customer self-service web portal | FastAPI + Uvicorn (server-rendered) | `127.0.0.1:8191` | `app.unseen.click` | `unseenproxy-portal.service` |
| `unseenproxy-api` | Internal/service API layer | FastAPI + Uvicorn | `127.0.0.1:8192` | `api.unseen.click` | `unseenproxy-api.service` |
| `unseenproxy-web` | Marketing site (static) | nginx static | n/a | `unseen.click` / `www` | (nginx) |
| Hiddify orchestrator | API v2 client + provisioner (a library + CLI scripts used by bot/admin) | python | n/a | n/a | invoked in-process / via scripts |

**Shared database:** a single SQLite file (e.g. `/opt/unseen-proxy/data/unseenproxy.sqlite3`) accessed by the services (bot/admin/portal/sidecar) using WAL-safe access patterns. (SQLite is sufficient for the current scale; Appendix A notes the Postgres migration path if/when concurrency demands it.)

**Timers (systemd):**

| Timer | Interval | Purpose |
|---|---|---|
| `unseenproxy-notify.timer` | ~60s | Flush queued notifications; run auto-issue/auto-delivery pass; usage sync |
| `unseenproxy-backup.timer` | daily | WAL-safe DB snapshot + `.env` + units backup |
| `unseenproxy-leak-watcher.timer` | ~30min | Subscription IP-diversity watcher; sanitized admin alerts |
| `unseenproxy-node-health.timer` | ~hourly | Per-node Hiddify health + bandwidth/capacity |
| `unseenproxy-payment-timeout.timer` | ~60s | Expire stale payment/screenshot sessions |

**Secrets at rest:** every service `.env` is `0600`, root-owned. The subscription-token encryption secret (`ACCESS_TOKEN_ENCRYPTION_SECRET`) lives in the bot/sidecar `.env` and is **backup-critical** (Section 30/31).

---

## 6. Multiple-node VPS architecture

Each region is **one or more independent node VPS**, each running a full **Hiddify Manager** install. Responsibilities are strictly limited:

- **On a node:** Hiddify Manager (panel + Hysteria2/SS/VLESS-Reality inbounds), TLS for the node's own domain(s), the node's local Hiddify SQLite/user store, and nothing else. **No customer business data, no bot, no payments.**
- **The Master never proxies traffic.** Customer VPN traffic goes customer → node directly. The Master only calls each node's Hiddify **API v2** to create/update/disable users and to read usage.

**Node provisioning standard (per node):**
1. Fresh VPS, hardened SSH (key-only, managed keys held on Master under `/root/.ssh/unseenproxy_<region>_ed25519`).
2. Install Hiddify Manager (official installer).
3. Configure the protocol inbounds the product needs: **Hysteria2 (FAST1)**, **Shadowsocks (FAST2)**, **VLESS-Reality (Secure)**. Keep the panel admin path secret; expose only the proxy ports + the sub domain publicly.
4. Create a dedicated **service admin UUID / API key** for the Master orchestrator (least privilege).
5. Record the node in the Master DB (`proxy_nodes` table — Appendix A): region, public hostname, panel API base (stored as a reference/handle, secret in `.env`), status (`test` / `standby` / `live`), capacity/bandwidth budget.
6. Validate with a **disposable test user** through the Master orchestrator before the node is marked `live`.

**Per-customer model across nodes:** for a customer entitled to N regions, the orchestrator creates the *same logical user* on each of the N regional panels (one Hiddify UUID per panel; a stable per-customer UUID can be reused across panels to keep things tidy). Quota and expiry are written to every regional user; the **Master is the authority** on the true cap/expiry and reconciles usage across panels for display and abuse detection.

**Node lifecycle ops** (all gated, dry-run-first): attach node, mark live, suspend a customer on a node, drain/retire a node, rebuild a node. Test nodes carry **no backup** and may be wiped freely; live nodes are treated as production data plane (but still rebuildable, because the Master holds the authoritative user set and can re-provision).

### 6.1 Dynamic, replaceable nodes (never hardcoded)

**Nodes are data, not code.** The set of nodes lives entirely in the `proxy_nodes` table (Appendix A) plus per-node secrets in `.env` referenced by handle. Nothing about a specific node — its IP, hostname, region, capacity, or even its existence — is ever hardcoded anywhere in the application. This is the same dynamic-config invariant that governs plans (Section 18), applied to infrastructure:

- **Add a node:** insert a `proxy_nodes` row + its secret handle, mark it `test`, validate with a disposable user, promote to `live`. No code change, no redeploy.
- **Replace a node** (cancelled service, migrating provider, moving DE off the Master): stand up the replacement, point the row's `public_hostname`/`panel_api_base_ref`/secret handle at it, re-provision the authoritative user set from the Master, promote, then retire the old row. The customer-facing subscription token is unchanged because the sidecar resolves regions/protocols dynamically, not fixed hosts.
- **Remove a node:** mark it `standby`/`retired`; the system continues on the remaining nodes (see 6.2).
- The Master is the **single control point**: all node management (add/replace/promote/drain/rebuild) happens through the Master's gated CLIs/admin surface. An operator (or a coding tool like Vibe Code) connects **only to the Master**, and the Master orchestrates every node over API v2. No tool ever talks to a node directly for management.

### 6.2 Graceful degradation when a node is unavailable (fail-soft, never fail-whole)

A single node being damaged, cancelled, overloaded, or unreachable **must never take down the whole system**. The system degrades to the healthy remainder:

- **Health-driven offering.** The node-health monitor (Section 30.2) marks each node `healthy` / `degraded` / `down`. The entitlement/offering logic already requires a region to have ≥1 healthy `live` node before it is offered (Section 25); when a node goes `down`, the Master simply stops offering it and serves the customer's other entitled regions/nodes.
- **Sidecar fail-soft.** When the sidecar builds a customer's subscription, an unreachable node's entries are **omitted** rather than failing the whole response — the customer still receives every working region/protocol they're entitled to. Fetches to nodes are time-boxed; a slow/dead node cannot hang the response (this builds on the per-region fetch+merge model in Section 17.1).
- **Customer-facing status.** If a customer selects (or is currently on) a region whose node is `down`, the bot/portal shows an honest status — e.g. **"DE is temporarily unavailable — please use SG/US, or try again shortly"** — instead of a silent failure. The "Regions & protocols available" view (Section 16) reflects live node health, not just static entitlement.
- **No single point of proxy failure for multi-region plans.** A PRO/MAX customer entitled to DE+US+SG keeps working on the survivors if one region drops. (Single-region plans on a downed node show the status message and an ETA/contact path; the Master can also fast-track provisioning them onto a temporary alternate region if policy allows.)
- **Master/DE caveat.** Because DE is co-located on the Master (Section 4.1), a Master outage affects both control plane and the DE node together; this is the one place the co-location trades isolation for cost. It is mitigated by the dashboard/alerts watching Master headroom and by DE being movable to its own VPS without code change if needed.

---

## 7. Supported regions

Regions are **DB-driven** (`proxy_regions` table) and **not all live by default**. A region progresses through explicit states: `planned → test → standby → live`. Only `live` regions are offered to customers, and only when (a) the plan entitles the region **and** (b) at least one node in that region is healthy and `live`.

Candidate regions (enable incrementally, never all at once):

| Region | Code | Priority rationale |
|---|---|---|
| Germany | `de` | **Default/entry region** — present on every plan; mature EU egress; the operator's existing operational familiarity and the location of the Master VPS |
| USA | `us` | Content access; added from CORE upward; higher latency |
| Singapore | `sg` | **Premium-only** (PRO/MAX) — closest low-latency hub to Myanmar; the top-tier differentiator rather than the baseline |
| Thailand | `th` | Regional proximity (evaluate routing/legal) |
| Vietnam | `vn` | Regional proximity |
| Japan | `jp` | Low-latency East-Asia alternative |
| Others | — | Add as demand/capacity justify |

**Region policy rules:**
- A region with entitlements but **no live node** must not be advertised as available (the "entitled but no node" gap must be explicitly avoided).
- **Germany (DE) is the default/primary region** and the only region guaranteed on every plan; **Singapore (SG) is premium-only** (PRO/MAX). This is a commercial decision (`Plan_Rules.md`), and it reverses v1.0's "Singapore as default" recommendation.
- **Latency caveat for the operator:** Myanmar↔Germany is ~8000 km and is a known cause of "slow VPN" perception on long-haul links. With DE as the entry region, **FAST1 (Hysteria2) is the mitigation** — its QUIC/UDP transport handles high-latency, lossy long-haul links far better than the previous TCP-bound stack, which is precisely why Hiddify was chosen (Section 3.3). Entry-tier customers on DE should be steered to FAST1 by default. Customers who need the lowest possible latency are the target market for the **SG premium tier**. Monitor real connect latency per region/protocol (Section 30) and revisit the default if DE latency proves unacceptable for the entry tier.

---

## 8. Domain and subdomain structure

Brand domain: **unseen.click**. UNSEEN PROXY uses its own fresh subdomains under `unseen.click`; it does not reuse any subdomain or endpoint from the retired UNSEEN VPN system.

| Subdomain | Service | Public? | Notes |
|---|---|---|---|
| `unseen.click`, `www.unseen.click` | Marketing site | yes | Static |
| `app.unseen.click` | Customer portal | yes | Self-service status/import-guide |
| `api.unseen.click` | API layer | yes (authenticated) | Service/integration API |
| `bot.unseen.click` | Bot webhooks | yes | Only if webhook mode is used |
| `panel.unseen.click` | Web admin | yes (auth) | Admin dashboard (consider IP allowlist) |
| `sub.unseen.click` | Subscription sidecar | yes | `https://sub.unseen.click/s/<token>` — the customer's subscription URL |
| `node-sg.unseen.click`, `node-de.unseen.click`, … | Per-node Hiddify domains | yes | Each node's own domain(s) for its proxy/sub endpoints; **never shown to customers directly** |

**TLS:** nginx + Certbot on the Master for Master subdomains; each node manages its own TLS for its node domain. **Reverse-proxy discipline:** all Master services bind loopback; nginx terminates TLS and routes by subdomain. The `/s/` location has `access_log off` (no token leakage to disk).

**DNS safety:** add new records only; do not alter existing `s`/`speed` records. Use a separate Certbot lineage per new subdomain.

---

## 9. Bot platform architecture (multi-platform identity)

The unified-identity design:

- **Canonical identity:** `customers.id` (`customer_id`) + `public_customer_code` (e.g. `UP0001`).
- **Platform identities:** a single `platform_accounts` table maps `(platform_name, platform_user_id) → customer_id` for `telegram`, `messenger`, `viber`, `whatsapp`, `web`.
- **Two service boundaries** (`account_service` / `notification_service`):
  - **AccountService** — `resolve_customer(platform_name, platform_user_id, profile fields) → customer_id`. Idempotent; creates the customer on first contact and back-fills the platform mapping. Every handler resolves identity through this, never by raw platform id.
  - **NotificationService** — `notify_customer(customer_id, message/asset, …)`. Resolves the customer's *active* platform account(s) and sends through the right channel, **channel-aware** of each platform's messaging policy (below).

**Channel adapter pattern:** the bot core is platform-agnostic. Each platform has a thin **adapter** that (1) receives inbound events and normalizes them to a common "incoming message/intent" shape, (2) renders outbound messages/buttons to that platform's API, and (3) declares its capabilities (buttons? deep-link buttons? file upload? proactive messaging window?). The business flows (register, plan, pay, deliver, support) are written once against the common shape.

**Platform messaging-policy matrix** (drives NotificationService behavior):

| Capability | Telegram | Messenger | Viber | WhatsApp |
|---|---|---|---|---|
| Proactive (unprompted) messages | Allowed | **Restricted** to 24h window + approved templates | Restricted (session/templated) | **Restricted** to approved templates |
| Rich buttons / inline keyboards | Yes | Yes (quick replies/buttons) | Yes (keyboards) | Limited (list/reply buttons) |
| Deep-link button (`hiddify://…`) | Yes (URL button) | Via URL button / fallback link | Via URL | Via link |
| File/image upload from user | Yes | Yes | Yes | Yes |

Implication: **expiry/renewal reminders are push on Telegram but must be queued/templated on Messenger/WhatsApp** (send on next user contact or via an approved template). NotificationService encapsulates this so business code stays unaware.

### 9.1 Platform-first compliance (non-negotiable principle)

**For every front-end platform, we plan to that platform's own rules and policies *first*, and the notification content, message types, and timing are built to comply with each platform's allowances *before* that channel launches.** A channel does not go live until its compliance plan is written and signed off (the per-phase gate below). This protects the business: a Meta Page ban, a rejected app review, or a WhatsApp number flagged for template misuse would take a whole channel offline. The principle applies to Telegram too (bot API terms, anti-spam), even though Telegram is the most permissive.

Concretely, each platform carries its own policy contract:

- **Telegram** — Bot API terms; avoid unsolicited bulk messaging; respect user block/stop. Most permissive, but not unlimited.
- **Facebook Messenger (Meta)** — the **24-hour standard messaging window**: free-form replies only within 24h of the user's last message. Outside it, only an **approved message tag / template** for permitted purposes (e.g. account update) may be sent — never marketing. Requires Page + App with `pages_messaging` and **Meta app review**; respect policy on promotional content and opt-out.
- **Viber** — Public Account / Bot rules: a user must have a session or be subscribed to receive messages; session/templated limits apply; respect Viber's commercial-message rules.
- **WhatsApp Business Platform (Meta/BSP)** — the **24-hour customer-service window** for free-form replies; outside it only **pre-approved templates** (categorized utility/authentication/marketing) may be sent; opt-in and opt-out handling is mandatory; template approval has lead time. Limited interactive messages (list/reply buttons).

These contracts are recorded per platform in **`docs/BOT_FLOWS.md`** (one section per platform) and surfaced to NotificationService as the **declared capability/policy of each adapter** (Section 9 adapter pattern, point 3). NotificationService is the **single enforcement point**: it classifies every outbound message by purpose (transactional reply vs. proactive reminder vs. promotional) and, per the destination channel's policy, either sends now, holds it in the `outbound_messages` queue (30A.3) until a valid window opens, sends it via an approved template, or **suppresses it** if no compliant path exists. Business code never decides this; it just asks to notify, and the policy layer does the compliant thing.

### 9.2 Per-channel launch compliance gate

Before any new channel is enabled (Messenger/Viber in Phase 9, WhatsApp in Phase 9+/13), its **launch compliance checklist** must be completed and signed off:
- Platform account/app created with the correct permissions; **app review submitted and approved** where required (Meta).
- The platform's messaging policy documented in `docs/BOT_FLOWS.md` and encoded in the adapter's declared capabilities.
- All **proactive message types** (expiry reminders, delivery notices, referral grants) mapped to a **compliant delivery path** on that platform (in-window free-form vs. approved template), with templates **submitted and approved** ahead of time.
- Opt-in/opt-out and block/stop handling verified.
- A test confirming NotificationService correctly **queues/templates/suppresses** out-of-window messages on that platform (not just sends them).

Review lead time (especially Meta/BSP template and app approval) is planned **before** the phase starts, not discovered during it.

### 9.3 Cross-platform account linking (one profile across all platforms)

**Goal:** a customer can use **any** front-end (Telegram, Messenger, Viber, later WhatsApp) and have it all resolve to **one profile** — one `customer_id`, one set of subscriptions, one usage/expiry view. A customer who started on Telegram and later wants to buy from Messenger must be able to land on the **same profile**, so the new purchase joins their existing keys rather than creating a stranger account. The feature is designed for **non-technical, often older users with no email** — linking must be as easy as typing a short code.

**No email, no password, ever.** Identity is the platform account itself (Telegram/Messenger/Viber id) plus a short link code. There is no email, no username/password, and no "web login with credentials." (The `web` platform row exists only for the bot-issued short-lived portal link of Section 16 — it is **not** an email/password account.)

**The link code flow (primary method — easy, oldies-friendly):**
1. On the platform the customer is **already** using (say Telegram), they tap **"အကောင့်ချိတ်ဆက်ရန် / Link my account."** The bot shows a **short link code** (e.g. a 6–8 character code, shown in a big `<code>` block, easy to read aloud or copy) and a plain-language instruction.
2. The customer opens the **other** platform (say Messenger), messages the bot, taps **"ကုဒ်ဖြင့်ချိတ်ဆက်ရန် / Link with a code,"** and **types or pastes the code.**
3. The backend matches the code to the original `customer_id`, links the new platform account to it, and confirms on both sides: **"အောင်မြင်ပါသည် — သင့်အကောင့်နှစ်ခု ပူးပေါင်းပြီးပါပြီ" ("Done — your two accounts are now one").**
4. Now any purchase, key, or usage is shared across both platforms.

- **Validity:** the code is valid for **24 hours** and is **one-time use** (consumed on first successful link), so a slow or offline user has plenty of time, while a used/expired code simply stops working. Codes are stored hashed; a reason-opaque "code not valid" message covers expired/used/unknown (no information leak).
- **Direction-agnostic:** linking works from any platform to any other; the customer generates the code on whichever side they're on and enters it on the other.
- **Quality-of-life:** the bot also offers the customer's `public_customer_code` (e.g. `UP0007`) as a human-readable identifier they can give to support, but the **link code is the secret** that performs the merge — the public code alone never links accounts.

**Merge semantics (what happens to existing purchases):** when two platform accounts link, the profiles **merge into one** — **all subscriptions, keys, usage, and history from both sides become visible and usable from every linked platform.** Implementation:
- If the platform entering the code was a **brand-new contact** (no purchases), its platform-account row is simply attached to the existing `customer_id`.
- If **both** sides already had purchases (the customer had unknowingly created two separate profiles), the system performs a **gated, audited, reversible merge**: one `customer_id` becomes canonical (the older, by `created_at`), all `platform_accounts`, `subscriptions`, `payment_orders`, `referral_credits`, tokens, and deliveries from the other are **re-pointed** to it, and the now-empty duplicate is marked `merged_into_customer_id`. The merge runs **dry-run-first**, is logged in `audit_logs`, and never deletes financial rows (it re-points them). A `customer_merges` record preserves the lineage so a mistaken merge can be traced.
- Subscriptions never silently combine their data caps; they remain distinct subscriptions, just owned by one profile and listed together in My Account.
- Self-merge and already-linked cases are detected and handled idempotently (re-entering a code for an already-linked pair is a friendly no-op).

**Schema:** `account_link_tokens(customer_id, code_hash, expires_at, used_at, created_at)` issues/validates codes; `platform_accounts` gains nothing new (linking just inserts/attaches a row); `customers` gains `merged_into_customer_id NULL` (set on the absorbed profile); a `customer_merges(id, canonical_customer_id, absorbed_customer_id, performed_by, summary_sanitized, created_at)` table records every merge for audit/rollback. All linking/merge writes are idempotent and gated.

**Surfaces:** a **"My Account → Link another app"** action on every platform (generate code), and a top-level **"Link with a code"** entry on first contact (enter code) so a returning customer on a new platform finds it immediately. Copy is Burmese-primary (Section 9.4). The support flow (Section 29) includes a "couldn't link my accounts" category.

### 9.4 Frontend language: Burmese-primary (≈90% Burmese / ≈10% English terminology)

**The end-user-facing frontend is Burmese (Myanmar) by default — roughly 90% Burmese — with English deliberately retained for the ~10% of terms that read more naturally or clearly in English.** This is a **product requirement**, not a per-user setting to be discovered. The aim is a frontend that feels native to a Burmese speaker, including non-technical and older users, while not forcing awkward Burmese translations of terms people already know in English.

- **Default language is `my` (Burmese)** for bot interaction across Telegram, Messenger, Viber, and (later) WhatsApp, plus the customer portal (`app.unseen.click`): greetings, instructions, prompts, errors, status text, reminders, menus, the account-linking copy, and onboarding/usage guides are all Burmese.
- **English is kept for specific terminology** where a Burmese translation would be more confusing than the borrowed English word. Examples: **"Plan"** (not "ပလန်"), and likely **FAST1 / FAST2 / Secure** profile labels, **GB**, **Hiddify**, **QR**, and **VPN**. Which exact terms stay English is a **content decision recorded in `docs/LOCALIZATION.md`**, not scattered through code — the localization layer holds the final per-string wording (a Burmese sentence may embed an English term, e.g. "သင့် **Plan** ကို ရွေးပါ").
- **Invoices and receipts are in English** (labels, headings, and field names). Only the bot/portal *interaction* layer is Burmese-primary; the financial documents are English. (This removes the Burmese-PDF-font concern from invoices, though the portal still renders Burmese.)
- All user-facing strings live in a **localization layer (files / DB `settings`)**, never hardcoded in code (consistent with the dynamic-config invariant), so wording — Burmese phrasing and which terms remain English — can be tuned without code changes.
- `customers.preferred_language` defaults to `my`. A fuller language toggle may be offered later; the shipped default and design target is Burmese-primary as above.
- **Admin-facing** surfaces (web admin, technical docs, protocol/engine names) remain in English — this requirement governs the **customer frontend** only.
- **Burmese rendering care:** use Unicode Burmese (not Zawgyi) consistently across bot and portal; verify that mixed Burmese+English button labels fit Messenger/Viber button-length limits during each channel's compliance gate (Section 9.2). (Invoices are English, so no Burmese font is required in the PDF.)

---

## 10. Telegram bot settings and flow

**Library:** `python-telegram-bot` (async), same as current. **Mode:** long-polling for the internal beta (simplest, no inbound port); switch to webhook on `bot.unseen.click` for production scale if desired.

**Top-level menu (Burmese-primary, English terminology where clearer — Section 9.4):** Plan များ (View Plans) · ကျွန်ုပ်အကောင့် (My Account) · အသုံးပြုပုံ (Usage/Setup guide) · အကောင့်ချိတ်ဆက်ရန် (Link account — Section 9.3) · အကူအညီ (Support). "Plan" stays English on purpose; all labels are localized strings, not hardcoded.

**Flows (all cloned, engine-swapped at delivery):**
1. `/start` → AccountService resolves/creates customer → welcome message with `public_customer_code` in a `<code>` block + main menu.
2. **View Plans** → render enabled, public plans from `plans` (dynamic; never hardcoded).
3. **Buy** → if existing active subs, ask Upgrade vs Additional; create pending order with **snapshot** of price/cap/duration; show enabled payment methods.
4. **Pay** → show method instructions + a unique per-order payment note (`<code>`); accept wallet screenshot.
5. **Verify** → OCR (Tesseract) auto-verify; auto-approve on amount+note match, else admin review.
6. **Deliver** (Section 17) → create Hiddify users on entitled live nodes → mint per-customer token → send **deep-link import button + copy-link + QR fallback + setup guide + invoice/receipt PDFs**.
7. **My Account** → subscription cards (plan, usage, remaining, expiry, device recommendation); buttons to re-show the import button/QR and to download invoice/receipt.
8. **Support** → category form, optional speed-test mini-app, sanitized hand-off to admins.

**Admin mode (Telegram):** pending payments approve/reject, user lookup, bot/node status, manual key actions — all gated.

**Settings & secrets:** `TELEGRAM_BOT_TOKEN`, `ADMIN_TELEGRAM_IDS` in `.env` (0600). Bot username and copy live in `settings`/locale files, not hardcoded.

---

## 11. Facebook Messenger bot settings and flow

**Transport:** Messenger Platform via the Facebook Graph API; **webhook-based** on `bot.unseen.click` (verify token + app secret signature verification on every inbound). A Facebook Page + App with `pages_messaging` permission is required (Meta app review).

**Adapter responsibilities:** verify `X-Hub-Signature`, map PSID → `customer_id` via `platform_accounts` (`platform_name='messenger'`), translate the common message/button shape to Messenger **quick replies / button templates / generic templates**, and respect the **24-hour standard messaging window** (proactive messages outside it require an approved message tag/template).

**Flow parity:** the same register → plan → pay → deliver → support flow. Differences:
- **Payment screenshot:** users send an image attachment; the adapter downloads via the attachment URL and feeds the same OCR pipeline.
- **Delivery:** send a **URL button** with the `hiddify://import/<sub-link>` deep link plus a copy-able link and a "Open guide" button to the web portal; attach invoice/receipt PDFs as file attachments.
- **Reminders:** queued; sent on next inbound or via an approved template tag (e.g. account-update). NotificationService handles this.

**Settings/secrets:** `MESSENGER_PAGE_ACCESS_TOKEN`, `MESSENGER_APP_SECRET`, `MESSENGER_VERIFY_TOKEN` in `.env`.

---

## 12. Viber bot settings and flow

**Transport:** Viber Bot REST API; **webhook-based**, `set_webhook` to `bot.unseen.click`. Requires a Viber Public Account / Bot and an auth token.

**Adapter responsibilities:** validate the `X-Viber-Content-Signature`, map Viber user id → `customer_id`, render the common shape to Viber **keyboards** (rich media carousels for plans, URL buttons for the deep link), and handle Viber's session/subscription rules (a user must have messaged or subscribed to receive messages).

**Flow parity:** identical business flow. Viber supports keyboards and URL actions, so the deep-link import button works; screenshots arrive as media messages for OCR. Reminders follow Viber's messaging rules via NotificationService.

**Settings/secrets:** `VIBER_AUTH_TOKEN` in `.env`.

---

## 13. Future WhatsApp bot support

**Transport (future):** WhatsApp Business Platform (Cloud API) via Meta, or a BSP. **Constraints to design for now:** outside a 24-hour customer-service window, only **pre-approved message templates** may be sent; rich interactive messages are limited (list messages, reply buttons). Media (screenshots) and link buttons are supported.

**Plan:** add a `whatsapp` adapter implementing the common shape; map WhatsApp phone-number id → `customer_id`; route all proactive messaging through templated sends in NotificationService. No business-logic changes needed because of the adapter boundary. Treat as **Phase 9+ / post-launch**.

---

## 14. Hiddify Manager integration

This is the core engine swap. Build a **Hiddify orchestrator** library (`hiddify_client.py`) + a provisioner CLI (`hiddify_customer_provisioner.py`), the analog of the current `marzban_customer_provisioner.py`.

### 14.1 API surface (Hiddify Manager API v2)

- **Base:** `https://<node-domain>/<secret-proxy-path>/api/v2/admin/` (the `secret-proxy-path` is the panel's secret admin path; **store it in `.env`, never in the DB or logs**).
- **Auth:** header `Hiddify-API-Key: <admin-api-key-or-uuid>` (per the Hiddify recommendation to pass the key in the header, not the URL). **Always use API v2** (v1 is deprecation-prone).
- **Key operations** (confirm exact paths against each node's live `…/api/v2/` OpenAPI/Swagger during Phase 3):
  - Create user: `POST …/admin/user/` with fields `{uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date, mode, comment, telegram_id, enable}`.
  - Update user: `PATCH …/admin/user/<uuid>/` (change quota/expiry/enable).
  - Get user: `GET …/admin/user/<uuid>/`; list users: `GET …/admin/user/`.
  - Disable/suspend: `PATCH` with `enable=false` (preferred reversible action); delete only on teardown.
  - Read usage: from the user record (`current_usage_GB`) or the user-facing `…/api/v2/user/me/` endpoint.

> **Phase-3 audit requirement:** the exact field names, units (GB vs bytes), and endpoint paths **must be verified against the actual installed Hiddify version** before any code depends on them. Pin the Hiddify version per node and record the verified contract in `docs/HIDDIFY_API_CONTRACT.md`. Do **not** assume; the API changes between versions.

### 14.2 Provisioning model

- **One stable per-customer UUID** generated by the Master at first provision (store in `access_profiles.engine_account_ref`), reused across regional panels so the same person is the same UUID everywhere.
- **Quota/expiry authority is the Master** (`subscriptions.data_limit_gib`, `end_date`). The orchestrator writes these to each regional Hiddify user. A periodic reconcile job reads `current_usage_GB` per region and aggregates.
- **Protocol exposure** is controlled by which inbounds exist on the node **and** by the plan→protocol entitlement filter applied at the sidecar (Section 26). A node may run all three protocols; the sidecar decides which the customer's plan may see.

### 14.3 Provisioner CLI (mirror current safety patterns)

`hiddify_customer_provisioner.py` with subcommands: `audit | status | dry-run | provision-one --customer-id N --subscription-id N | suspend-one | reconcile-usage`. Live mutations require an env latch (`UNSEENPROXY_HIDDIFY_PROVISION_LIVE_ENABLED=1`) **and** explicit `--live --confirm`. Dry-run prints the exact node(s), UUID, quota, expiry, and which inbounds would be exposed — **no live call**. Refuses the admin/test customer for abuse-style actions.

---

## 15. Hiddify App user onboarding

This section directly answers the onboarding concern: **Hiddify App does not do gallery-QR import the way Happ does, so we lead with deep links and clipboard, and treat QR as a fallback.**

### 15.1 Primary method — one-tap deep link (recommended default)

The bot sends a **URL button** whose URL is a Hiddify deep link:

```
hiddify://import/https://sub.unseen.click/s/<token>#UNSEEN%20PROXY
```

Tapping it opens Hiddify App and imports the subscription automatically. Supported scheme variants (verify against the installed app version in Phase 3):

- `hiddify://import/<sub-link>#<name>`
- `hiddify://install-sub?url=<url-encoded sub-link>#<name>`
- `hiddify://install-config?url=<url-encoded config>#<name>`
- `hiddify://install-proxy?url=<url-encoded proxy share link>#<name>`

The bot message includes a short label: **"① Hiddify ဖွင့်ပြီး Import လုပ်ရန် ဤခလုတ်ကိုနှိပ်ပါ"** ("Tap this button to open Hiddify and import").

### 15.2 Secondary method — copy link + paste

Provide a **copyable plain text** of the subscription URL (in a `<code>` block on Telegram) and the instruction:

1. Copy the subscription link.
2. Open Hiddify App → **+ Add profile / New profile**.
3. Choose **Add from clipboard** (Hiddify reads the link from the clipboard).
4. Import → the profile appears with FAST1 / FAST2 / Secure servers.
5. Select a server and **Connect**.

### 15.3 Tertiary method — QR fallback

Send the subscription URL as a **QR image** (lossless `send_document`). Note in the caption that the QR is for users who prefer scanning **with Hiddify's in-app camera scanner** (not from the gallery). Keep this as a fallback; do not make it the headline.

### 15.4 Guided walkthrough + support template

- A **web portal page** (`app.unseen.click/import`) with screenshots for Android and iOS: install Hiddify (link to stores), tap the deep-link button or paste the link, select FAST1/FAST2/Secure, connect.
- A **"📖 အသုံးပြုပုံ" (usage guide)** button in the bot replicating the steps inline.
- A **support message template** for users who cannot import: collect device/OS, whether the deep-link button opened the app, and whether paste-from-clipboard worked, then hand off to a human.

### 15.5 Onboarding copy must reflect reality

- **Only works in the Hiddify App**, not a web browser (the subscription URL is UA-filtered and will 404 in a browser by design — this is expected, documented browser-block behavior).
- Recommend the **official Hiddify App** only, and the right store link per platform.

---

## 16. Web app / customer portal

A lightweight, server-rendered portal at **`app.unseen.click`** (FastAPI + Jinja or htmx; no heavy SPA). Auth via a short-lived link/code issued by the bot (no passwords for customers). Pages:

- **Status:** plan, subscription status, **data used / remaining**, expiry date.
- **Regions & protocols available** to this customer (derived from entitlements; honest about what's live).
- **Import:** the deep-link button, the copyable subscription link, the QR, and the step-by-step Hiddify guide (Section 15).
- **Invoices/receipts:** download PDFs.
- **Support:** contact options + the same support form.

**Rules:** the portal renders the subscription link/QR **in memory** from the durable encrypted token (never stores plaintext); pages with the link set `no-store`; the link is only shown to the authenticated owner. The portal is **read-mostly** — it does not mutate entitlements (admin-only).

---

## 17. Subscription URL and QR/link delivery

This is the cloned crown jewel, engine-swapped at the upstream fetch.

### 17.1 The sidecar (`sub.unseen.click/s/<token>`)

A thin WSGI service (clone of the current `subscription_sidecar_app.py`) that, on `GET /s/<token>`:

1. **UA-filter first** (before token resolution): off/report/enforce; allowlist of real clients (**must include `hiddify`, `hiddifynext`, sing-box, clash/mihomo/meta, v2ray, nekobox, streisand, shadowrocket, karing, etc.**); browsers/curl/empty → **reason-opaque 404**. Configured via the systemd unit `Environment=` (so it overrides any code default), with an internal health-check UA allowlisted and excluded from the leak-watcher.
2. SHA-256 the token; resolve via the presentation service to a customer + entitlement set; fail-closed (uniform 404) on unknown/revoked/expired.
3. **Decrypt** the per-customer token's stored upstream reference **in memory** (never logged).
4. **Fetch upstream** the entitled region(s)' Hiddify subscription content. Two viable shapes (decide in Phase 3/6):
   - **Per-region fetch + merge:** call each entitled node's `…/<uuid>/<format>/` sub endpoint with a fixed, known-good client UA, then merge entries.
   - **Single-node base + cross-region hosts:** if a future Hiddify multi-server setup exposes all regions in one sub, fetch once. (Not assumed for v1.)
5. **Filter by entitlement** (region **and** protocol) — fail-closed: drop any entry whose region or protocol the plan does not allow; drop unknown/unmappable entries.
6. **Re-brand**: set profile title `UNSEEN PROXY | <public_customer_code>`, support URL, sensible update interval, and (optionally) `hide-settings` style headers as deterrence — **never claimed as encryption**.
7. **Serve**; log only: token **fingerprint** (first 8 hex of hash), status, body length, UA class, **masked IP prefix** (/24, /48). Never the raw token, URL, body, or full IP.

### 17.2 Output format selection (`auto` is the friend here)

Hiddify supports multiple subscription output formats (`sub`, `sub64`, `singbox`, `clash`/`clashmeta`, `auto`, plus normal/xray). The **`auto`** format detects the client by User-Agent and returns the best format. Strategy: serve a format the **Hiddify App** consumes natively (the app's own sub format / `auto`), so a single token works for the app's deep-link import. Confirm the exact format and path suffix in Phase 3 and pin it.

### 17.3 Token model (cloned exactly)

Per-customer opaque token (`secrets.token_urlsafe(32)`), stored as: `token_hash` (SHA-256, unique lookup), `token_fingerprint` (8-hex, for logs), `encrypted_token_payload` (durable, decryptable only with `.env` `ACCESS_TOKEN_ENCRYPTION_SECRET`), plus `customer_id`/`profile_id`/`subscription_id`, `purpose`, `status (active|revoked|rotated|expired)`, `expires_at`, rotation lineage. **Raw token never stored plaintext; URL/QR built only in memory.** Manager CLI (`public_token_manager.py`): `issue | list | verify | rotate | revoke | preflight`, gated for live writes, protecting the admin token.

### 17.4 Delivery payload to the customer (per Section 15)

Deep-link button (primary) + copyable link (secondary) + QR document (fallback) + setup guide + invoice/receipt PDFs. On a successful first delivery, transition `subscription.key_status → delivered` and `customer.status → active` (a delivered/active state transition). Delivery records are metadata-only (`secret_payload_stored = 0` enforced by a CHECK constraint).

---

## 18. Plan structure

**Fully DB-driven** (`plans` table — Appendix A), admin-editable, **never hardcoded**. Each plan row carries: `plan_code` (unique), display names (incl. Burmese), `data_limit_gib`, `duration_days`/`duration_months`, `price_amount` + `currency_code`, `recommended_device_count` + text, `allowed_device_count` (NULL = unlimited), `is_public`, `admin_only`, `is_trial`, `is_enabled`, `plan_category`, sort order.

> **Dynamic-config invariant (applies to the whole project).** **Every plan allowance and limitation is a database value, mutated only through the admin web app (Section 28), never a code constant** — this includes data caps, durations, prices, currency, recommended/allowed device counts, region entitlements, profile entitlements, the trial flag, enable/disable, and sort/display order. The numbers seeded in this section and Appendix F are the **starting state**, not fixed values: an admin can change TRIAL from 7 days to 14, raise BASIC's cap, re-price MAX, add a region to CORE, or disable a plan entirely — all at runtime, with **no code change, no redeploy, and no edit to this document**. Code reads these values fresh from the DB on every use; a value appearing in this plan is documentation of the *initial seed*, not a hardcoded business rule. The only thing snapshotting protects is **historical orders** (each order/renewal freezes the price/cap/duration it was sold at, so later admin edits never retroactively change what a past customer bought).

### 18.1 Authoritative seed catalogue (from `Plan_Rules.md`)

These are the **launch values**, seeded into the DB at first init (Appendix F). They are the source of truth for the *initial state*, **not** fixed limits — they remain **fully editable at runtime** via the admin surface per the invariant above, and every order/renewal snapshots price/cap/duration so later edits never change historical orders. Currency is **MMK**; `allowed_devices` is **unlimited** on every public plan (a soft `recommended_devices` figure is advice only — Section 27).

| Code | Data | Duration | Price (MMK) | Rec. devices | Regions | Profiles (user-facing) |
|---|---|---|---|---|---|---|
| **TRIAL** | 10 GB | 7 days | 0 | 1 | DE | **Fast**, Secure |
| **BASIC** (1M) | 50 GB | 1 month | 3,000 | 2 | DE | **Fast**, Secure |
| **CORE** (1M) | 100 GB | 1 month | 5,000 | 3 | DE, US | **Fast**, Secure |
| **PLUS** (3M) | 360 GB | 3 months | 15,000 | 4 | DE, US | **Fast1, Fast2**, Secure |
| **PRO** (3M) | 600 GB | 3 months | 20,000 | 5 | DE, US, SG | **Fast1, Fast2**, Secure |
| **MAX** (6M) | 1500 GB | 6 months | 30,000 | 5 | DE, US, SG | **Fast1, Fast2**, Secure |
| **INFINITY** | (large) | (long) | 0 | — | all | all (hidden, admin-only test plan) |

### 18.2 Region rules

- **DE (Germany) is the default/entry region** and is present on every public plan. It is the region a customer connects to unless they choose otherwise.
- **US** is added from **CORE** upward.
- **SG (Singapore) is premium-only** — available **only on PRO and MAX**. (This reverses the v1.0 "SG as default" recommendation; SG is now the top-tier differentiator, not the baseline.)
- A region is only *offered* if the plan entitles it **AND** the region is `live` **AND** a healthy node exists in it (Section 25). Seeded entitlements may list a region before its node is live; the sidecar fails closed until the node is marked `live`.

### 18.3 Profile (protocol) rules and the "Fast" display rule

- **`Fast1` = Hysteria2**, **`Fast2` = Shadowsocks**, **`Secure` = VLESS-Reality** (Section 26). `Secure` (VLESS-Reality) is present on **every** plan.
- **TRIAL / BASIC / CORE** carry a **single Fast tier** (Hysteria2 only) plus Secure.
- **PLUS / PRO / MAX** carry **both** Fast tiers (Hysteria2 + Shadowsocks) plus Secure.
- **The "Fast" display rule (computed, not stored):** when a plan's entitlements include only one Fast tier, the user-facing label is rendered as **"Fast"** (no number). When a plan includes both Fast tiers, they render as **"Fast1"** and **"Fast2"**. This is derived at render time from `plan_profile_entitlements`; the DB stores the canonical `profile_code` (`FAST1`/`FAST2`) and a base label, and the bot/portal/sidecar-branding layer applies the drop-the-number rule. Re-labeling the base text (e.g. localizing "Fast") is still a DB field, so copy can change without code changes.
- **FAST2 (Shadowsocks) is fully wired** for PLUS/PRO/MAX from the start, but like every protocol it only goes **live after its inbound is node-tested** (Section 33 / Phase 3+). Until a node's Shadowsocks inbound passes the import-and-connect gate, the sidecar fails closed and FAST2 simply does not appear, even for entitled plans.

Order-time **snapshots** of price/cap/duration are written into the order row so later plan edits never change historical orders.

---

## 19. Customer registration flow

1. First contact on any platform → adapter normalizes → **AccountService.resolve_customer**.
2. If new: insert `customers` row, generate `public_customer_code = "UP" + zero-padded(max_numeric_id + 1)` (max-numeric-id + 1, **not** count + 1, so deletions never cause a code collision), insert the `platform_accounts` mapping.
3. Return `customer_id`; send a localized welcome with the code and the main menu.
4. Identity is **idempotent**: re-contact updates the mapping, never duplicates the customer. A bot error handler guards `/start` so a returning user after any reset never hits a crash.

---

## 20. Payment flow

Cloned end-to-end (engine-independent).

**Methods** (DB-driven `payment_methods`, admin-editable): Myanmar mobile wallets — **KBZPay, WavePay, AYAPay, CBPay, CTZPay, A+** — plus **Manual Payment** (admin-reviewed, no OCR). Disabled methods stay hidden until the admin provides real account details/QR.

**Wallet-screenshot path:**
1. Customer selects a plan → order created with snapshot + a unique payment note.
2. Customer pays in their wallet app, uploads the screenshot.
3. Bot records the screenshot (file id; **no raw image persisted beyond what's needed**), replies "received, please wait."
4. **OCR (Tesseract)** extracts text → verify expected **amount** (≥ expected, with sane upper bound to reject phone numbers, keyword-context aware) **and** the **payment note** (exact or compact match).
5. **Auto-approve** if both match → create subscription (`key_status = pending`) → trigger delivery (Section 17/21). Otherwise **flag for admin review** with a **sanitized** summary (no raw image dumped to logs).
6. **Admin review** path: approve (same as auto) or reject (cancel order, notify once).

**Manual Payment path:** no OCR; order marked admin-review; admin approves/rejects from the admin surface.

**Safety:** auto-verify must **allowlist the target before approval** if the abuse model requires it (approving before allowlisting can leak the wrong delivery). Pre-create the subscription/entitlement so "allowlist-before-approval" holds without runtime hacks.

---

## 20A. Referral system

A **double-sided, credit-ledger** referral program. Both the **referrer** (existing customer) and the **referee** (the person they invite) earn a reward, granted when the referee's **first payment is approved** — not at signup — so throwaway accounts cannot farm rewards. Like every other business value in this project, **all referral parameters are DB-driven and admin-editable** (Section 18 dynamic-config invariant); nothing below is hardcoded.

### 20A.1 Reward model — bonus subscription days, via an append-only ledger

- The reward is **bonus subscription days** (admin-configurable count). "A free month" is simply the admin setting the value to `30`. Days are chosen over "a free month of your current tier" because days are unambiguous when a customer has multiple, mixed, or changing subscriptions, and they **stack cleanly** onto an existing subscription's `end_date`.
- Rewards accrue in an **append-only `referral_credits` ledger** (one row per grant, never mutated — corrections are new offsetting rows, mirroring accounting discipline and the project's audit culture). A customer's available balance is the sum of unspent credit rows. Modeling rewards as a ledger (rather than directly bumping `end_date`) keeps the system **future-proof**: the same ledger can later express MMK account credit, plan discounts, or campaign bonuses by adding a `credit_type`, without re-architecting.
- **Redemption (v1):** a `bonus_days` credit is applied by extending the chosen subscription's `end_date` by the granted days (and pushing the matching expiry to each regional Hiddify user via the orchestrator, reversible like any expiry write — Section 23). Redemption is its own ledger event (`status: granted → redeemed`), so the balance and the audit trail stay exact.

### 20A.2 Referral codes and attribution

- Each customer gets a **stable referral code** derived from their `public_customer_code` (e.g. `UP0007`) plus a shareable deep link per platform (Telegram `https://t.me/<bot>?start=ref_UP0007`; Messenger `m.me/<page>?ref=ref_UP0007`; Viber/portal equivalents). The bot's `/start` parser already handles a payload, so attribution is captured at first contact and stored on the new `customers.referred_by_customer_id` (set once, immutable).
- Attribution is **first-touch and one-time**: the first valid referral payload on a brand-new customer wins; a returning/existing customer cannot be "re-referred." Self-referral (referrer == referee, same `customer_id`, or a linked platform identity of the same person) is rejected.

### 20A.3 Trigger, grant, and fraud controls

1. Referee signs up via a referral link → `referred_by_customer_id` recorded (no reward yet).
2. Referee completes their **first approved payment** (Section 20). On approval, the activation flow (Section 21) calls `ReferralService.on_first_paid_conversion(referee_customer_id)`.
3. `ReferralService` validates: referee has a recorded referrer; referee `has_used_referral_reward = 0`; the payment is a **real, approved, non-trial** order (TRIAL/0-MMK orders do **not** trigger rewards — set by an admin flag `referral_requires_paid_order`, default on); anti-fraud checks pass (not self-referral; referrer not over the per-period cap; no shared-identity signal).
4. On success: write **two ledger rows** — one `bonus_days` credit to the referrer, one to the referee — each for the admin-set day counts (`referral_referrer_bonus_days`, `referral_referee_bonus_days`). Mark `has_used_referral_reward = 1` on the referee. Notify both (channel-aware, Section 9).
5. **Fraud/abuse controls (all DB-driven):** per-referrer reward **cap per rolling period** (`referral_max_rewards_per_period`, `referral_period_days`); optional minimum referee spend; self/again-referral blocks; shared masked-IP-prefix or device-overlap signals feed the existing **leak-watcher/audit** path as a **report-only** abuse flag (never auto-punishes — an admin reviews, consistent with Section 30). The **admin/test customer is excluded** from earning or triggering rewards.

### 20A.4 Surfaces

- **Bot "Refer a friend":** shows the customer's referral link + a copy button, their current bonus-day balance, how many successful referrals they've made, and the current reward terms (read from settings, so copy reflects live values).
- **Customer portal (`app.unseen.click/referrals`):** same data, plus a simple history of granted/redeemed credits (sanitized — no other customer's identity revealed; show only "a referral converted," not who).
- **Admin (`panel.unseen.click`):** tune all referral settings, view the ledger (masked), see flagged abuse, manually grant/revoke a credit (gated + audited), and pause the whole program with one flag (`referral_enabled`).

### 20A.5 Honesty and limits

- Reward terms shown to customers always reflect the live admin settings; if the program is paused, the surfaces say so rather than showing stale promises.
- Bonus days extend an existing subscription; they are **not** cash and are **not** withdrawable in v1 (the ledger leaves that door open for later without promising it now).

---

## 21. Subscription activation flow

On approval (auto or admin):
1. Create/locate the `subscriptions` row from the order snapshot (`key_status = pending`).
2. Compute the **entitlement set**: allowed regions (plan→region ∩ live nodes) and allowed protocols (plan→protocol ∩ active profiles).
3. **Provision** via the Hiddify orchestrator: ensure a per-customer UUID exists on each entitled live node with the correct quota/expiry/enabled state (idempotent).
4. **Mint** (or reuse) the per-customer subscription token; store durably (encrypted).
5. **Deliver** (Section 17): deep-link + link + QR + guide + PDFs.
6. Transition `key_status → delivered`, `customer.status → active`; write the delivery record (metadata-only).
7. **Auto-delivery sweeper** (timer, gated by `UNSEENPROXY_AUTO_DELIVERY_ENABLED`) handles approved-but-not-yet-delivered subscriptions, with the same entitlement checks, so delivery is reliable even if the inline trigger is missed.
8. **Referral conversion check** (Section 20A): if this is the customer's **first approved, paid** order, call `ReferralService.on_first_paid_conversion(customer_id)`, which grants the double-sided bonus-day credits when validation/anti-fraud passes. This runs **after** delivery succeeds so a reward is never granted for an order that failed to provision; it is idempotent (guarded by `has_used_referral_reward`).

---

## 22. Renewal flow

- A renewal creates a **new subscription** linked to the prior one (`renewal_of_subscription_id`), reusing the same per-customer UUID where possible and **extending** quota/expiry on the existing Hiddify users rather than re-onboarding the customer (so the import they already did keeps working).
- Renewal can be initiated by the customer (My Account → Renew) or surfaced proactively (Section 23).
- Price/cap/duration are snapshotted again at renewal.
- The subscription token can be **kept** (continuity) or **rotated** (if abuse is suspected) — operator choice.

---

## 23. Expiry handling

- The Master is the authority on `end_date`. A timer evaluates approaching/lapsed expiry.
- **Reminders:** Telegram push at e.g. T-3 days / T-1 day / on-expiry; on Messenger/Viber/WhatsApp these are **queued/templated** per Section 9.
- **On expiry:** orchestrator sets the regional Hiddify users to `enable=false` (or expired) — reversible; the subscription becomes `expired`; the subscription token is left resolvable but the upstream is disabled (so the customer sees no servers / cannot connect) or the token 404s, per policy. Prefer disable-not-delete so renewal is instant.
- Hiddify also enforces `package_days` natively as a backstop; the Master's expiry is the source of truth and reconciles.

---

## 24. Data / bandwidth allowance handling

- Per-subscription cap (`data_limit_gib`) is the authority; written to each regional Hiddify user as `usage_limit_GB`.
- **Quota is shared across regions** (one logical allowance), not per-region. A reconcile job sums `current_usage_GB` across the customer's regional users to compute true usage; the larger of (sum, max) policy is decided in Phase 7 and documented (be explicit to avoid double-counting).
- Hiddify disables a user when `usage_limit_GB` is reached (native backstop). The Master surfaces "used / remaining" in My Account and the portal.
- **Node bandwidth budgets** (per-VPS monthly transfer) are tracked separately by the node-health monitor; a node nearing its budget can be drained (stop offering it to new customers) without affecting customer caps.

---

## 25. Region entitlement handling

- `plan_region_entitlements`: which regions each plan may use (DB-driven).
- A region is **offered** to a customer only if: plan entitles it **AND** the region is `live` **AND** ≥1 node in it is healthy/live.
- The sidecar filter enforces this at delivery time (fail-closed): non-entitled or non-live regions never appear in the served subscription.
- **Region switching** (if offered) is entitlement-gated and rate-limited (e.g. N switches/day); with the multi-region-in-one-subscription model the customer simply selects a different server in Hiddify, so "switching" is mostly a client action plus optional default-region preference.

---

## 26. Protocol entitlement handling

**User-facing names (simple, non-technical):**

| User label | Protocol (admin only) | Role | Hiddify support |
|---|---|---|---|
| **FAST1** | **Hysteria2** | Default, fastest, best on lossy links | **Native** ✅ |
| **FAST2** | **Shadowsocks** | Secondary fast | Native ✅ |
| **Secure** | **VLESS-Reality** | Stealth/secure; may be plan-gated | Native ✅ |

- `profiles` table maps `profile_code (FAST1/FAST2/SECURE) → protocol_code`, with `is_active`, `is_default`, `status`, and a `base_display_label`.
- `plan_profile_entitlements`: which profiles each plan may use.
- `profile_region_availability` / `plan_profile_region_availability`: which profile is available on which region/node.
- The sidecar classifies each upstream entry by its protocol and keeps it **only if** entitled **and** active **and** available on that node — fail-closed for unknown protocols.
- **The "Fast" display rule (computed at render time).** The DB stores canonical codes (`FAST1`, `FAST2`) and a base label. The presentation layer (bot menus, portal, and the sidecar's profile-title branding) applies one rule: **if the customer's plan entitles only one Fast tier, render it as "Fast" (drop the number); if it entitles both, render "Fast1" and "Fast2".** Secure always renders as "Secure". This keeps TRIAL/BASIC/CORE showing a clean **Fast + Secure**, while PLUS/PRO/MAX show **Fast1 + Fast2 + Secure**, all from the same data. Re-labeling the base text (e.g. localizing) is a DB field; the drop-the-number behavior is logic, not data.
- **Per-plan entitlement seed (from `Plan_Rules.md`):**

  | Plan | FAST1 (Hysteria2) | FAST2 (Shadowsocks) | Secure (VLESS-Reality) | Renders as |
  |---|---|---|---|---|
  | TRIAL | ✅ | — | ✅ | Fast, Secure |
  | BASIC | ✅ | — | ✅ | Fast, Secure |
  | CORE | ✅ | — | ✅ | Fast, Secure |
  | PLUS | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |
  | PRO | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |
  | MAX | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |

- **Default exposure for v1:** **FAST1 (Hysteria2) is the default profile on every plan**, with Secure (VLESS-Reality) always available. **FAST2 (Shadowsocks) is fully wired for PLUS/PRO/MAX** and becomes live as soon as its inbound passes the node test gate. **Do not enable a protocol on the sidecar before its inbound is live and tested on the node** (Section 33 / Phase 3+) — until then the sidecar fails closed and the profile does not appear even for entitled plans.
- Naming is dynamic: a profile's base user-facing label is a DB field, so "Fast"/"Secure" can be re-labeled without code changes; the number-dropping rule and the technical protocol names stay in `docs/PROTOCOLS.md` only.

---

## 27. Device recommendation policy

- `plans.recommended_device_count` + `recommended_devices_text` (DB-driven; default e.g. 5).
- Shown as **advice** in My Account / portal ("Use on at most N devices"), **not hard-enforced**. (Hiddify/Hysteria2 do not give a reliable hard device cap; honesty over false promises.)
- Real protection against over-sharing is the **server side**: per-user token, shared data cap, expiry, token rotation, and the **IP-leak watcher** (Section 30). The plan must **never** promise that configs cannot be copied/shared.

---

## 28. Admin control requirements

Two surfaces (cloned):

**Web admin (`panel.unseen.click`, FastAPI):** auth-gated (session login, optional IP allowlist), CSRF-protected, read-mostly with explicit write actions:
- Pending payments: view (sanitized), approve, reject.
- Plans: create/edit/enable/disable (codes, prices, caps, durations, device rec, currency).
- Payment methods: create/edit, upload QR (size/type limited).
- Entitlements: view/edit plan→region, plan→protocol, region/node status.
- Nodes dashboard: a visual performance view of **all nodes** — status (healthy/degraded/down), CPU/RAM/disk, bandwidth used vs. budget, active users, reachability, connect-success/latency (30A.4) — plus write actions: mark test/standby/live, drain, attach/replace/retire. Backed by Section 30.2.1.
- Usage/abuse: read-only used/remaining + abuse flags.
- Launch controls: feature-flag toggles (auto-delivery, live provisioning, protocol enablement) behind confirmation text.
- **Customer data export / deletion:** a gated admin action to (a) **export** one customer's data (identity, subscriptions, orders, deliveries — sanitized of secrets) as a single file on request, and (b) **delete/anonymize** a customer on request — removing or scrambling personal fields while preserving the financial/audit records that must be retained, and disabling their Hiddify users. Both actions are gated, dry-run-first, and audited. This is cheap to have now and covers customer disputes and any future platform requirement (e.g. Meta/WhatsApp review in Phase 9 may ask for a data-handling story).
- Audit log: read-only, masked.

**Telegram admin mode:** approve/reject payments, user lookup, bot/node status, manual delivery/rotation actions — all gated.

**Hard rules:** every admin write is audited (no secrets in the audit); destructive actions are gated + dry-run-first; the **admin/test customer and admin token are protected** from abuse-response tooling.

---

## 29. Support flow

Cloned: a multi-step support form (category → details → optional device/speed-test) reachable from every platform. Categories mirror the current set (can't connect, payment issue, didn't receive subscription, slow line, other). Optional **speed-test mini-app** (a small web page) for connection-quality reports. Each ticket is handed to admins **sanitized** (no tokens/URLs/IPs), with the customer's `public_customer_code` and active-subscription summary. Include the **Hiddify import support template** (Section 15.4) as a category, since import help will be common early on.

---

## 30. Logging, monitoring, backup, and rollback procedures

### 30.1 Logging (sanitized by construction)
- Subscription/sidecar logs: fingerprint + status + body length + UA class + masked IP prefix only. **Never** raw token/URL/body/full IP/PII.
- Bot/admin logs: no secrets, no screenshots dumped, no payment images logged.
- `/s/` nginx location: `access_log off`.

### 30.2 Monitoring
- **IP-leak watcher** (`subscription_leak_watcher.py`, timer ~30min): parses sanitized sidecar logs; flags per-token masked-prefix diversity (OK/WARN/CRITICAL e.g. 3/5 prefixes); maps fingerprint→customer for the admin; **report-only** (never auto-mutates); sanitized Telegram admin alerts with **dedup/snooze** (WARN 6h, CRITICAL 2h, escalation immediate, recovery silent); emits a **copy-paste** gated suspend command (never runs it); refuses the admin profile.
- **Node-health/capacity monitor** (timer ~hourly): per-node Hiddify reachability, inbound listening, CPU/RAM/disk, monthly bandwidth budget; sanitized matrix; alert on degraded/over-budget nodes.
- **Service liveness:** `systemctl is-active` checks for bot/admin/portal/sidecar; alert on failure.

#### 30.2.1 Node performance dashboard & threshold alerting

A **visual dashboard on the web admin** (`panel.unseen.click`, Section 28) renders the health and performance of **all nodes** (and the Master itself), backed by a `node_metrics` time-series table fed by the node-health timer. It shows, per node:

- **Status:** healthy / degraded / down (drives graceful degradation, Section 6.2).
- **Resources:** CPU %, RAM %, disk % — against that node's known size (the four servers' specs are recorded in Appendix F.7, so % is computed against real capacity).
- **Bandwidth:** used vs. the node's monthly **bandwidth budget** (`proxy_nodes.bandwidth_budget_gb`), shown as a % and a remaining figure.
- **Load:** active Hiddify users / connections, reachability, inbound-listening checks.
- **Connection quality:** connect-success rate and latency per protocol (30A.4).

A small set of **history charts** (e.g. last 24h / 7d) visualizes trends so the operator can see a node trending toward its limits before it hits them.

**Threshold alerting (the 75% rule).** The monitor raises a **sanitized admin alert** (Telegram + dashboard banner) when **any** tracked usage on **any** node reaches an estimated **75%** of its limit — CPU, RAM, disk, or monthly bandwidth — with escalation at higher thresholds:

- **WARN at ≥75%** of any limit → "node SG1 bandwidth at 76% of 10 TB budget."
- **CRITICAL at ≥90%** → louder, shorter dedup window; suggest draining the node (gated, copy-paste — never auto-run).
- **DOWN/unreachable** → immediate alert; the node is marked `down` and graceful degradation engages (Section 6.2).
- **Recovery** is silent (clears the banner). Alerts reuse the existing **dedup/snooze** discipline (WARN ~6h, CRITICAL ~2h, escalation immediate) and the **report-only** rule — the system **alerts and suggests** (e.g. drain/replace), it never auto-destroys or auto-mutates a node.
- All thresholds are **DB-driven settings** (Appendix F.7 / `settings`), so 75/90 can be retuned per the dynamic-config invariant without code changes; budgets per node are `proxy_nodes` fields. The **Master's own headroom** (CPU/RAM/bandwidth) is monitored the same way, with extra weight because it co-hosts the DE node (Section 4.1).

### 30.3 Backup (WAL-safe; DB + secrets together)
- Daily timer runs a Python backup using **`sqlite3.Connection.backup()`** — **never `cp` the WAL DB** (copying the WAL file yields a stale/corrupt snapshot).
- Back up **the DB and the `.env`(s) together**, because durable subscription tokens decrypt **only** with `.env`'s `ACCESS_TOKEN_ENCRYPTION_SECRET`; a DB-only restore cannot decrypt them.
- Also back up systemd units + nginx site configs + the verified Hiddify API contract doc.
- Root-only backup dir, mode 700, with a retention window (e.g. 14 days). Run `PRAGMA integrity_check` on each snapshot. After any restore, run a no-send token-decrypt smoke test.

### 30.4 Rollback
- **Dry-run before every live mutation**; every destructive tool has `dry-run`/`status`/`audit` subcommands.
- **Pre-apply DB backup** before any schema change or bulk mutation.
- Live actions are **double-gated**: env latch + explicit `--live --confirm` flags.
- Prefer **reversible** actions: disable (not delete) Hiddify users; rotate (not just revoke) tokens; mark node test/standby (not destroy) to drain.
- **Test on non-live nodes first.** New protocols/regions are validated with disposable users before any customer is routed there.

---

## 30A. Data integrity & resilience primitives

These are foundational mechanisms that protect the money path, the data, and the customer experience. They are cheap to build in now and expensive to retrofit later, so they are specified as part of the core build (Phase 4 for the schema-level ones; the telemetry view by Phase 6–7).

### 30A.1 Schema migrations registry ("the logbook")

- A `schema_migrations` table records **every** ordered change to the database structure: `version` (sequential), `name`, `applied_at`, `checksum`. Before applying a migration, the runner checks whether that version is already recorded and **skips it if so** — so re-running the migration step is safe and never duplicates or errors.
- Migrations are **ordered, forward-only, and reversible-by-design**: each ships with an `up` (apply) and, where feasible, a `down` (undo) step. A pre-apply DB backup (Section 30.3) is taken automatically before any migration runs.
- The same registry guarantees the **test node's DB and the live Master's DB evolve identically and in the same order** — no drift, no "was that change applied here?" guesswork. This is also the mechanism that makes the documented **SQLite → Postgres** path (Appendix A scale note) orderly rather than a risky one-off.

### 30A.2 Idempotency on the money & provisioning path ("the elevator button")

- The two operations where a duplicate is costly — **payment approval** and **Hiddify user provisioning** — are made **idempotent**: doing them twice has the same effect as doing them once.
- Mechanism: an `idempotency_keys` table (`key UNIQUE, operation, target_ref, status, result_ref, created_at, expires_at`). Each payment order and each provisioning call carries a stable key (e.g. derived from `payment_order_id` + operation). Before acting, the handler checks the key: if it's already `completed`, it returns the prior result instead of re-doing the work; if `in_progress`, it refuses the duplicate.
- This neutralizes the classic bot failure: a customer double-taps "confirm," a webhook is re-delivered, or a retry fires — and the system creates **one** subscription / grants **one** referral reward, never two. (The referral path keeps its `has_used_referral_reward` guard as well; defense in depth.)

### 30A.3 Outbound notification queue with retry ("a to-do list for messages")

- All customer-facing messages (delivery, expiry reminders, referral grants, admin notices) are written to an **`outbound_messages` queue** rather than sent inline-and-forgotten: `id, customer_id, channel[telegram|messenger|viber|whatsapp|web], payload_ref, status[pending|sending|sent|failed|dead], attempts, next_retry_at, last_error_sanitized, created_at, sent_at`.
- A worker (driven by the existing `unseenproxy-notify.timer`) processes `pending` rows, marks `sent` on success, and on transient failure schedules a retry with **exponential backoff** (e.g. 1m, 5m, 30m, 2h). After a capped number of attempts a message moves to `dead` (a "couldn't deliver" pile) for admin review — it is never silently lost.
- This also cleanly encapsulates the **Messenger/WhatsApp 24-hour-window and template rules** (Section 9): a reminder that can't be pushed now is held in the queue and sent on the next valid window or via an approved template, with no business code aware of the difference.
- **Sanitized by construction:** the queue stores a reference to the message content/asset, never secrets; `last_error_sanitized` follows the same no-secret rule as all logging (Section 30.1 / 31).

### 30A.4 Connect-success & latency telemetry ("the delivery-route logbook")

- The central product bet is that **FAST1 (Hysteria2) performs well on the Myanmar↔DE long haul** (Section 7). To make that an evidence-based decision rather than anecdote, the node-health monitor records lightweight, **anonymous** connection-quality samples per `region_code` + `profile_code`: a `connect_samples` table (`id, region_code, profile_code, sample_source[node_probe|health_check], success BOOL, latency_ms NULL, captured_at`) — **no customer identity, no IP, no PII**.
- Samples come from **the Master's own synthetic probes / node health checks**, not from surveilling customer traffic (which the nodes do not report to the Master anyway). An admin dashboard view rolls these up into a simple matrix — e.g. *"DE+FAST1: 95% success / fast; DE+Secure: 80% / slow; US+FAST1: 60%"* — to drive decisions: when to promote SG, whether to push FAST2, which region/protocol to default to.
- This stays firmly inside the privacy rules: it measures **the service**, not **the people** using it.

### 30A.5 Secret rotation runbook (no-downtime)

- A documented procedure (`docs/SECRET_ROTATION.md`) for rotating the two classes of long-lived secret without taking the service down:
  - **`ACCESS_TOKEN_ENCRYPTION_SECRET`:** the schema already carries `token_storage_version` on `access_profile_public_tokens` for exactly this. Rotation re-encrypts each token payload from the old secret to the new one, bumping the version, in a gated, dry-run-first, backup-first batch; both secrets are held during the transition so nothing is unreadable mid-rotation.
  - **Node API keys:** issue a new least-privilege key on the node, update the node's `.env` handle on the Master, verify a read-only probe succeeds with the new key, then revoke the old key.
- Rotation is a **gated/latched** operation (env latch + `--live --confirm`), backed up before and verified after (a no-send token-decrypt smoke test), consistent with all other live mutations.

---

## 31. Security and secret-safety rules

These are **non-negotiable** and must be enforced in code review and in the agent's behavior:

1. **Never expose secrets.** No tokens, token hashes, subscription URLs, QR payloads, deep links containing tokens, API keys, panel admin paths, panel/admin credentials, Reality private keys/short-ids, or customer PII in logs, errors, audit entries, commits, chat output, or third-party calls. Print only **fingerprints** and **masked IPs**.
2. **Durable tokens are encrypted at rest** with `ACCESS_TOKEN_ENCRYPTION_SECRET`; raw tokens are never stored; URLs/QRs are built in memory and never persisted.
3. **No third-party exfiltration.** Do not submit subscription URLs/tokens to external services (submitting a sub URL to an external "crypt" service is treated as exfiltration and hard-blocked). Any crypto/obfuscation must be done locally or out-of-band.
4. **Do not hardcode business values** — plans, prices, caps, durations, device counts, region lists, protocol labels all come from the DB.
5. **Not all regions/protocols live by default** — each is enabled explicitly after a node test.
6. **No risky protocol/routing changes without testing** on a disposable target first.
7. **Honest promises only** — never tell users configs are impossible to copy/share. Lean on per-user tokens, caps, expiry, rotation, UA-filter, and leak monitoring.
8. **Least-privilege node API keys**; panel admin paths and ports are not public; consider IP-allowlisting the web admin.
9. **`.env` files are `0600`, root-owned**; **secrets never enter git** (enforced by `.gitignore` + a pre-commit secret scan, Section 31A). Use `.env.example` with placeholder keys.
10. **Never fabricate a PASS.** Always verify artifacts exist on disk / endpoints actually return the expected status before reporting success. Fail closed and say so honestly when blocked.

---

## 31A. Source control & deployment (GitHub)

UNSEEN PROXY uses **GitHub as the authorized home for code and documentation**, with **manual pull-to-deploy** onto the Master. This gives version history, rollback, and a clean off-server backup of the *code*, while keeping the **operational secrets and live data on the Master only**.

### 31A.1 Repository

- **Repo (private):** `https://github.com/CharlesThawnpi/proxy.unseen.click.git`. Private so the architecture, configs, and component layout are not public.
- **This is the one authorized repository.** It does **not** violate the clean-build isolation rule (Section "most important rule") — that rule forbids referencing the *retired UNSEEN VPN* repos/artifacts. This fresh repo *is* the UNSEEN PROXY project; the coding tool builds into it and pushes to it, and never pulls from or matches against any legacy repo.
- The local working tree lives at the project root `/opt/unseen-proxy/` (a git repo whose remote `origin` is the URL above).

### 31A.2 What is tracked vs. never tracked

**Tracked (in git):** application code, the migration files, `docs/`, this plan, `.env.example` files (placeholders only), systemd unit *templates*, nginx site *templates*, `requirements.txt`/lockfiles, and `seed_catalogue.py` (which seeds **structure and starting values only**, no secrets).

**NEVER tracked (enforced by `.gitignore` + pre-commit scan):**
- `.env` and any real secret (bot token, `ACCESS_TOKEN_ENCRYPTION_SECRET`, node API keys, panel admin paths, Reality private keys/short-ids).
- The database (`*.sqlite3`, WAL/SHM files) and all backups.
- Anything under `data/`, `backups/`, `logs/`, `tmp/`, generated QR images, or any file that could contain tokens, subscription URLs, screenshots, or PII.
- A committed-secret is treated as a **security incident**: rotate the exposed secret (Section 30A.5), don't just delete the commit.

### 31A.3 `.gitignore` + pre-commit guard

The repo ships a `.gitignore` covering the above, **plus a pre-commit hook that scans staged changes** for secret-shaped strings (token/key patterns, `hiddify://`/`vless://`/`ss://`/`hy2://`, `/s/<token>` URLs, long UUID payloads, full IPs) and **blocks the commit** if found. This operationalizes the standing rule "secrets never enter git / no secrets in commits" (Section 31, rule 1 & 9) so it can't be violated by accident.

### 31A.4 Branching & history

- **`main`** is always deployable. Day-to-day work happens on short-lived feature branches merged into `main`; small solo commits directly to `main` are acceptable early on.
- Commits are **descriptive and reference the phase/section** (e.g. "Phase 5: Telegram bot register flow"). Every change still updates `docs/` + `CHANGELOG.md` (Section 32) — the changelog is the human-readable history, git is the precise one.
- Git history is a **rollback tool**: a bad code change is reverted by checking out the previous commit/tag and re-pulling on the Master (it does **not** touch the DB, which has its own backup/rollback in Section 30).
- Tag releases at meaningful milestones (e.g. `v-internal-beta`, `v-soft-launch`) so a known-good code state can be re-deployed quickly.

### 31A.5 Deployment: manual pull onto the Master (SSH key)

- The Master holds a **read-only deploy key** (or a fine-scoped deploy token) for the private repo — a least-privilege key whose **private half stays on the Master, never in the repo**. Generated/stored per the secret rules (`0600`, root-owned).
- **Deploy = pull, not push-to-server:** on the Master, `git pull` (or checkout a tag) into `/opt/unseen-proxy/`, then run migrations (Section 30A.1), then restart the affected systemd units. A short `scripts/deploy.sh` documents the exact, gated steps (pull → backup DB+`.env` → migrate → restart → verify), dry-run-first where it mutates anything.
- **Secrets and DB are *not* delivered by git** — they already live on the Master (`.env`, the SQLite DB). A fresh clone therefore needs the operator to place `.env` (from `.env.example`) before services start. This is documented in `docs/DEPLOYMENT.md`.
- **Nodes are not deployed from git.** Node VPS run stock Hiddify Manager; only the Master pulls the project code (Sections 4–6). A node is configured/orchestrated by the Master over API v2, not by a git checkout.

### 31A.6 CI (deferred, optional)

Automated CI/CD is **intentionally not enabled at start** (manual pull is simpler and lower-risk). A later, optional step may add **GitHub Actions for checks only** (lint + unit tests on push — the tests in Section 33), with **deployment staying manual**. Auto-deploy from CI to the Master is **out of scope** unless explicitly chosen later, because it would put deploy credentials in GitHub and risks an unattended change to a live system.

---

## 32. Documentation requirements

Every major change updates docs under `/opt/unseen-proxy/docs/`. Maintain at least:

- `ARCHITECTURE.md`, `SYSTEM_OVERVIEW.md` — services, ports, subdomains, data flow.
- `DATABASE.md` — schema + migrations + identity model.
- `SERVICES.md`, `SERVERS.md`, `NETWORK.md`, `PORTS.md`, `DOMAINS.md` — infra map.
- `REGIONS.md`, `NODES.md` — region/node inventory + status.
- `PROTOCOLS.md` — FAST1/FAST2/Secure ↔ Hysteria2/SS/VLESS-Reality mapping (the only place technical names appear).
- `HIDDIFY_API_CONTRACT.md` — the **verified** API v2 fields/endpoints/units per pinned Hiddify version.
- `SUBSCRIPTION_ACCESS_POLICY.md` — token model, UA-filter, sidecar behavior.
- `PAYMENT_FLOW.md`, `INVOICE_RECEIPT.md`, `BOT_FLOWS.md` (per platform), `ADMIN_OPERATIONS.md`, `ACCOUNT_LINKING.md` (Section 9.3 link-code + merge flow), `LOCALIZATION.md` (Burmese-primary frontend + the list of terms kept in English, Section 9.4).
- `SECURITY.md`, `BACKUPS.md`, `SECRET_ROTATION.md` (Section 30A.5), `ABUSE_AND_LEAK_RESPONSE_RUNBOOK.md`, `ROLLBACK.md`.
- `DEPLOYMENT.md` (Section 31A — repo, `.gitignore`/secret-scan, pull-to-deploy steps, deploy key, placing `.env` on a fresh clone) and `VERSION_CONTROL.md` (branching, tags, what's tracked vs. never tracked).
- `CHANGELOG.md` + a per-phase status doc (`CURRENT_STATUS.md`).
- A short **`AGENT_START_HERE.md`** that points an agent at this plan, the current phase, and the safety rules.

---

## 33. Testing and verification procedures

- **Unit tests** for: identity resolution, plan snapshotting, OCR verify logic, entitlement filtering (region + protocol, fail-closed), token mint/rotate/revoke, sidecar UA-filter decisions, deep-link/QR builders.
- **Sidecar contract tests:** Hiddify-App UA → 200 + correct format; browser/curl/empty UA → reason-opaque 404; revoked/expired/unknown token → uniform 404; entitlement filter drops non-entitled region/protocol.
- **Hiddify integration tests (against a disposable test node):** create user → fetch sub → import into a real Hiddify App on a real device → connect on FAST1, FAST2, Secure → verify egress region. This is the **gate** before any protocol/region is marked live.
- **End-to-end rehearsal (internal beta):** fresh test customer → pay (test method) → OCR/approve → provision → deliver deep-link → import → connect → My Account shows usage → renew → expiry disables access. Verify **on disk / on endpoint**, never assume.
- **Disposable-target pattern:** every live-path validation uses a throwaway customer/node that is torn down afterward (disposable-test discipline).
- **Isolation guard:** after each phase, confirm **no legacy UNSEEN VPN artifact** has appeared on any target VPS (no old code, paths, repos, services, or DB) and that the build remains scoped to the UNSEEN PROXY root only.

---

## 34. Deployment phases

Each phase has **deliverables**, **exit criteria**, and is **reversible**. Do not start a phase before the previous one's exit criteria are met. Customer-facing capability is gated behind feature flags until Phase 11/12.

### Phase 0 — Clean-VPS verification (gate before any build)
- **Deliverables:** confirm every target VPS (Master + nodes) is **clean** — no UNSEEN VPN code, repositories, file paths (`/opt/services/unseenvpn-*` or any legacy root), databases, systemd units, nginx sites, cron/timers, or backups present. Record a short `CLEAN_VPS_CHECKLIST.md` evidencing the checks per server. Scope the coding tool (Vibe Code) to the UNSEEN PROXY project root **only**, with instructions to build from this plan and never search for or reference prior-project artifacts.
- **Exit:** each server verified clean (checklist signed); the tool is confirmed scoped to the UNSEEN PROXY root; if **any** legacy artifact is found, it is removed (or the VPS re-imaged) **before** proceeding. No build step runs until this gate passes.

### Phase 1 — Documentation, repo & architecture planning
- **Deliverables:** project root `/opt/unseen-proxy/` initialized as a **git repo** with `origin = https://github.com/CharlesThawnpi/proxy.unseen.click.git` (private); this plan committed; the full `docs/` skeleton (Section 32) incl. `DEPLOYMENT.md`; `AGENT_START_HERE.md`; `.env.example` files; a **`.gitignore` + pre-commit secret-scan hook** (Section 31A.3); naming/subdomain decisions recorded.
- **Exit:** docs reviewed; the clean-build isolation rule restated in `AGENT_START_HERE.md`; the repo's **first commit + push to `main` contains no secrets** (verified by the pre-commit scan and a manual check that `.env`/DB/backups are git-ignored); subdomain/DNS plan agreed.

### Phase 2 — Hiddify test VPS setup
- **Deliverables:** one **disposable** Hiddify Manager node (**DE recommended** — it is the default/entry region every plan depends on, so it must be the first to prove out) with FAST1/FAST2/Secure inbounds; a dedicated least-privilege API key; node recorded as `test`. **No backup; wipe freely.**
- **Exit:** panel reachable over API v2 from the Master; manual test user connects in the Hiddify App on a real device on all three protocols.

### Phase 3 — Hiddify API & subscription compatibility audit
- **Deliverables:** `HIDDIFY_API_CONTRACT.md` (verified endpoints/fields/units, pinned version); confirmed subscription URL format + best output format for Hiddify App; confirmed deep-link scheme variants; a read-only `hiddify_api_probe.py`.
- **Exit:** a documented, version-pinned contract the code can depend on; deep-link import verified on a real device.

### Phase 4 — Database & backend clone design
- **Deliverables:** the cloned schema (Appendix A) with the engine layer swapped to Hiddify; the **schema migrations registry** (30A.1) and migration runner; the **idempotency-key** mechanism wired into the payment-approval and provisioning paths (30A.2); the **outbound notification queue** with retry/dead-letter behind NotificationService (30A.3); AccountService/NotificationService boundaries; the Hiddify orchestrator library (dry-run only); WAL-safe backup script. (The `connect_samples` telemetry view (30A.4) lands with node-health work in Phase 6–7; the secret-rotation runbook (30A.5) is written by Phase 10.)
- **Exit:** DB initializes via the migration runner (re-running it is a safe no-op); identity/plan/entitlement/token unit tests pass; idempotency and notification-queue unit tests pass; **no live provisioning yet**.

### Phase 5 — Telegram bot implementation (Burmese-primary)
- **Deliverables:** bot with register → plans → pay (OCR + manual) → admin review → My Account → support, against the new DB; invoice/receipt PDFs (English, pre-live watermark); **customer-facing copy ≈90% Burmese with English terminology where clearer** from a localization layer (Section 9.4); the **account-linking link-code flow** (generate code + enter code) and the **profile-merge** logic, gated and dry-run-first (Section 9.3).
- **Exit:** full flow works in an internal chat to the point of "approved", **delivery stubbed** (no real provisioning); **Burmese renders correctly** in all messages/buttons (Unicode, not Zawgyi) with English terms intact; **generating a link code on one Telegram account and entering it from a second resolves both to one profile** (link verified; a simulated two-purchase merge re-points rows and is audited).

### Phase 6 — Hiddify subscription delivery integration
- **Deliverables:** orchestrator live-provisioning (gated), sidecar serving `/s/<token>` with UA-filter + entitlement filter, deep-link/link/QR delivery, auto-delivery sweeper; **sidecar fail-soft** (time-boxed per-node fetch; an unreachable node's entries are omitted, never failing the whole response — Section 6.2).
- **Exit:** one disposable internal customer goes pay → provision → deliver → **import → connect** end-to-end on a real device; leak-watcher running; **a simulated node-down still returns the customer's other entitled regions** (fail-soft verified); all behind flags.

### Phase 7 — Plan-based region/protocol entitlement + node resilience
- **Deliverables:** plan→region and plan→protocol entitlement enforcement end-to-end; usage reconcile across regions; region/protocol enablement workflow (test→live); **graceful degradation** (Section 6.2) — health-driven offering, customer-facing "region temporarily unavailable" status, multi-region survivors keep working; **dynamic node management** (Section 6.1) — add/replace/retire a node via the Master as a data operation (gated CLI/admin), proven by adding the SG1/SG2/US nodes from the seed.
- **Exit:** a multi-region plan serves only entitled regions/protocols (verified, fail-closed); a single-region plan is correctly limited; **a node marked `down` is dropped from offerings and the rest of the system keeps serving** (verified); **replacing a node's address is a row update with no code change** (verified on a test node).

### Phase 8 — Web app / customer portal
- **Deliverables:** `app.unseen.click` status/import/invoices/support pages with bot-issued login.
- **Exit:** a customer can self-serve status + re-import without contacting support.

### Phase 9 — Messenger and Viber bot integration
- **Prerequisite (compliance-first):** complete the **per-channel launch compliance gate** (Section 9.2) for each platform *before* enabling it — platform account/app + required approvals (Meta app review for Messenger), policy documented in `docs/BOT_FLOWS.md` and encoded in the adapter, all proactive message types mapped to a compliant path (in-window vs. approved template) with templates pre-approved, and opt-in/opt-out handling. Plan Meta/BSP review lead time before the phase starts.
- **Deliverables:** Messenger + Viber adapters on the common shape; webhook security; channel-aware NotificationService; flow parity.
- **Exit:** a customer completes the full flow on Messenger and on Viber **in Burmese (with English terms where defined)**; reminders respect each platform's policy; a test confirms NotificationService correctly **queues/templates/suppresses** out-of-window proactive messages (not just sends them); **a customer who bought on Telegram links Messenger with a code and sees the same subscriptions** (cross-platform one-profile verified); the compliance checklist for each launched channel is signed off.

### Phase 10 — Monitoring, backup, security, production hardening
- **Deliverables:** all timers (notify/backup/leak-watcher/node-health/payment-timeout); **node performance dashboard + threshold alerting** (Section 30.2.1 — per-node CPU/RAM/disk/bandwidth/users/connect-quality, history charts, 75% WARN / 90% CRITICAL / down alerts, all DB-driven thresholds); abuse-response runbook + gated suspender; security review; rate limits; admin IP-allowlist; restore drill.
- **Exit:** a restore drill succeeds (DB+`.env` → token decrypts); leak-watcher alerts verified sanitized; **the node dashboard shows all four servers with live metrics and a forced 75% threshold raises a sanitized admin alert** (verified); security checklist signed off.

### Phase 11 — Internal beta testing
- **Deliverables:** 5–10 internal/disposable customers across plans/regions/protocols; full rehearsals incl. renewal/expiry; bug fixes.
- **Exit:** no Sev-1 issues; all E2E rehearsals pass on real devices; docs current.

### Phase 12 — Controlled public soft launch
- **Deliverables:** real payment methods enabled (real account details/QRs); pre-live watermark removed at cutover; admit real customers **one cohort at a time** with Charles approval; monitoring watched closely.
- **Exit:** first real cohort delivered + validated; rollback path proven; steady-state ops handed to the runbooks.

---

## 35. Clean-build strategy (no legacy reference)

**Principle:** build UNSEEN PROXY **fresh, from this plan alone**, on cleaned VPS. The retired UNSEEN VPN system is never referenced, imported, cloned, or matched against.

1. **Build from this specification.** Every component — identity (`account_service`/`notification_service`), plan/payment/OCR/invoice services, sidecar + UA-filter, token manager, leak-watcher, suspender, backup script, admin app, docs — is written new, to the requirements in this plan. No file, repo, or path from the prior project is copied or consulted.
2. **Engine layer is Hiddify-native from the start.** `hiddify_customer_provisioner.py` + `hiddify_client.py` (API v2); the sidecar fetches Hiddify sub bodies; the protocol classifier maps **Hysteria2/SS/VLESS-Reality → FAST1/FAST2/Secure**. There is no Marzban code to remove because none is ever introduced.
3. **Fresh database.** Start from an empty `unseenproxy.sqlite3`, created via the migration runner (30A.1) and seeded with plans/methods/regions/profiles/nodes/settings (Appendix F). There are no legacy customer rows to import — UNSEEN PROXY begins with zero customers.
4. **Fresh infra.** Cleaned VPS (Master + nodes per Appendix F.7), new subdomains under `unseen.click`, new systemd units, new `.env` secrets (new bot token, new encryption secret, new node API keys). Nothing points at any retired system.
5. **Operational culture, applied from day one:** dry-run/gated/latched live actions, disposable-target validation, WAL-safe backups, sanitized logging, allowlist-before-approval, dynamic config, graceful degradation, and "verify on disk, never fabricate a PASS."
6. **Clean-build isolation is enforced continuously:** Phase 0 verifies each VPS is clean before any build; the tool is scoped to the UNSEEN PROXY root; each phase re-checks that no legacy artifact has appeared (Section 33 isolation guard).

---

## 36. Risks, limitations, and follow-up tasks

| # | Risk / limitation | Mitigation / follow-up |
|---|---|---|
| 1 | **Hiddify API drifts between versions** | Pin version per node; verify + record `HIDDIFY_API_CONTRACT.md` in Phase 3; re-verify on any upgrade; wrap all API calls behind `hiddify_client.py` so a contract change is one-file. |
| 2 | **Hiddify native multi-server is immature** | Use independent per-region panels + Master orchestration + sidecar aggregation (Section 4.2); revisit native multi-server only as a later optimization. |
| 3 | **Hysteria2 (UDP/QUIC) may be throttled/blocked on some Myanmar ISPs** | Keep Secure (VLESS-Reality, TCP/443) and FAST2 (SS) as fallbacks; let users switch servers in-app; monitor which protocol connects per region. |
| 4 | **Deep-link scheme differences across Hiddify App versions/OSes** | Always provide all three onboarding methods (deep link + copy-paste + QR); test the scheme on real Android + iOS in Phase 3; document the working variant. |
| 5 | **Subscription URL 404 in browser confuses users** | This is expected (UA-filter); the onboarding copy and support template must state "works in Hiddify App, not browser." |
| 6 | **Usage double-counting across regional panels** | Decide and document the aggregation policy (sum vs max) in Phase 7; reconcile job authoritative; show one "remaining" number. |
| 7 | **Cross-region quota/expiry desync** | Master is authority; reconcile job repairs drift; expiry disables (not deletes) for instant renewal. |
| 8 | **Messenger/WhatsApp proactive-messaging limits / platform-policy violations** | Platform-first compliance principle + per-channel launch compliance gate (Section 9.1/9.2); channel-aware NotificationService (send-now/queue/template/suppress); Meta/BSP app + template review lead time planned before Phase 9/13. |
| 9 | **Device sharing / leaks** | Per-user token + shared cap + expiry + rotation + UA-filter + leak-watcher; never promise un-copyable configs. |
| 10 | **SQLite concurrency at scale** | Adequate for beta; Appendix A notes the Postgres migration path; keep all DB access behind a data layer to ease the move. |
| 11 | **Legacy UNSEEN VPN artifacts contaminating the clean build** | Phase 0 clean-VPS verification; tool scoped to the UNSEEN PROXY root; per-phase isolation guard (Section 33); build from this plan only — no legacy code/paths/repos referenced. |
| 12 | **Operator secret handling** | All secrets in `0600` `.env`; backup DB+`.env` together; restore drill in Phase 10; no secrets in chat/commits/logs. |
| 13 | **A node fails (damaged / cancelled / unreachable) and takes the service down** | Graceful degradation (Section 6.2): health-driven offering, sidecar fail-soft, multi-region survivors keep working, honest "region unavailable" status to the customer; the system never fails as a whole for one node. |
| 14 | **DE node co-located on the Master (shared failure / resource contention)** | Documented single exception (Section 4.1); Master headroom monitored first-class with 75% alerts (30.2.1); DE node is movable to its own VPS with no code change (Section 6.1) if load or risk demands. |
| 15 | **Small SG nodes / low bandwidth budgets hit limits under load** | Dashboard + 75% threshold alerts surface it early (F.7 note); add SG capacity by inserting another node row (dynamic, Section 6.1); drain near-budget nodes (gated). |
| 16 | **Node details hardcoded → brittle infra** | Nodes are pure data (`proxy_nodes`, Section 6.1); add/replace/retire is a row update through the Master; no node IP/host/spec ever in code. |
| 17 | **Wrong/abusive account linking (linking someone else's profile)** | Link code is a 24h one-time secret stored hashed; reason-opaque "not valid" on expired/used/unknown; merge is gated, dry-run-first, audited, and reversible via `customer_merges`; self/already-linked cases are idempotent no-ops (Section 9.3). |
| 18 | **Profile merge loses or double-counts purchases** | Merge re-points financial rows (never deletes), keeps subscriptions distinct under one owner, preserves lineage in `customer_merges`; dry-run shows exactly what will move before it moves (Section 9.3). |
| 19 | **Burmese text renders wrongly (Zawgyi vs Unicode) or mixed Burmese+English labels overflow platform buttons** | Use Unicode Burmese consistently across bot + portal; record which terms stay English in `docs/LOCALIZATION.md`; verify mixed-label rendering inside Messenger/Viber button limits during each channel's compliance gate. (Invoices/receipts are English, so no Burmese PDF font is needed — Section 9.4.) |
| 20 | **A secret accidentally pushed to GitHub** | `.gitignore` excludes `.env`/DB/backups/secrets; a pre-commit secret-scan hook blocks secret-shaped commits (Section 31A.3); private repo; if it ever happens, treat as an incident and **rotate** the secret (Section 30A.5), not just delete the commit. |
| 21 | **GitHub/repo unavailable or deploy key compromised** | Repo is a convenience for code history/deploy, not a runtime dependency — the Master keeps running from its checked-out code regardless; deploy key is read-only, least-privilege, Master-only, and rotatable (Section 31A.5). |

**Decisions resolved in v1.1 (via `Plan_Rules.md`):**
- ✅ **Default region: Germany (DE).** SG is premium-only (PRO/MAX). DE node is tested first (Phase 2).
- ✅ **Secure (VLESS-Reality) is on every plan** (TRIAL→MAX).
- ✅ **FAST2 (Shadowsocks) ships at launch** for PLUS/PRO/MAX, going live once node-tested.
- ✅ **Prices, caps, durations, recommended-device counts, per-plan regions/profiles** are all seeded per Section 18.

**Open decisions for Charles (still genuinely open; commercial/policy, not technical blockers):**
- **Launch region order beyond DE:** DE is first and mandatory. When do US (CORE+) and SG (PRO/MAX) nodes come live? Recommended: DE at soft launch, US shortly after CORE has customers, SG before admitting the first PRO/MAX cohort.
- **Region-switch UX:** in-app server pick (simplest — the multi-region subscription already lets the user choose a server in Hiddify) vs a managed "switch default region" preference. Recommended: start with in-app pick, add a managed default later if support load justifies it.
- **TRIAL abuse policy:** one TRIAL per customer is already designed (`has_used_trial`); decide whether to also gate by device/payment-history signals before enabling TRIAL publicly.
- **Pricing review cadence:** MMK prices are seeded but volatile market-wise; decide who reviews them and how often (they are runtime-editable, so no code change needed).
- **WhatsApp timing** (post-launch, Phase 9+).

---

# Appendix A — Proposed database schema (cloned + adapted)

SQLite (WAL). The engine layer is generalized to "engine/node" so Hiddify slots in cleanly. **All business values are rows, not constants.**

**Identity**
- `customers(id PK, public_customer_code UNIQUE, display_name, shortname, status[lead|active|suspended], preferred_language DEFAULT 'my', has_used_trial, referred_by_customer_id FK NULL, referral_code UNIQUE, has_used_referral_reward DEFAULT 0, merged_into_customer_id FK NULL, created_at, updated_at)` — `referred_by_customer_id` is set once at first contact and immutable; `referral_code` is derived from `public_customer_code`; `preferred_language` defaults to Burmese (`my`, Section 9.4); `merged_into_customer_id` is set on a profile absorbed by a cross-platform merge (Section 9.3).
- `platform_accounts(id PK, customer_id FK, platform_name[telegram|messenger|viber|whatsapp|web], platform_user_id, username, display_name, status, linked_at, metadata_json)` — UNIQUE(platform_name, platform_user_id)
- `account_link_tokens(id PK, customer_id FK, code_hash UNIQUE, expires_at, used_at, created_at)` — short link codes for cross-platform linking (Section 9.3); 24h validity, one-time use, stored hashed.
- `customer_merges(id PK, canonical_customer_id FK, absorbed_customer_id FK, performed_by, summary_sanitized, created_at)` — audit/rollback lineage for profile merges (Section 9.3).

**Plans & entitlements**
- `plans(id PK, plan_code UNIQUE, plan_name, display_name_mm, data_limit_gib, duration_days, duration_months, price_amount, currency_code, recommended_device_count, recommended_devices_text, allowed_device_count NULL=unlimited, is_public, admin_only, is_trial, is_enabled, plan_category, sort_order, created_at, updated_at)`
- `profiles(profile_code PK[FAST1|FAST2|SECURE], base_display_label, display_label_mm, protocol_code[hysteria2|shadowsocks|vless_reality], is_default, is_active, status, sort_order)` — the user-facing "Fast" vs "Fast1"/"Fast2" rendering is **computed** from a plan's entitlements (Section 18.3/26), not stored here.
- `proxy_regions(id PK, region_code UNIQUE, region_name, status[planned|test|standby|live], display_order)`
- `proxy_nodes(id PK, region_code FK, node_code UNIQUE, public_hostname, public_ip, panel_api_base_ref, status[planned|test|standby|live|degraded|down|retired], is_master_colocated DEFAULT 0, vcpu_count, ram_mb, disk_gb, bandwidth_budget_gb, bandwidth_period[monthly], capacity_note, sort_order, created_at, updated_at)` — secrets (api key, secret path) live in `.env`, referenced by handle only. Hardware spec fields let the dashboard compute % against real capacity (Section 30.2.1). `is_master_colocated=1` only for the DE node on the Master (Section 4.1). **Everything here is data** — replacing a node is a row update, never a code change (Section 6.1).
- `plan_region_entitlements(id PK, plan_code FK, region_code FK, is_enabled, is_default, display_label, sort_order)`
- `plan_profile_entitlements(plan_code, profile_code, is_enabled, sort_order)` — PK(plan_code, profile_code)
- `profile_region_availability(profile_code, region_code, node_code, is_available, status, sort_order)`
- `plan_profile_region_availability(plan_code, profile_code, region_code, node_code, is_available, status)` — fine-grained override

**Subscriptions & engine accounts**
- `subscriptions(id PK, customer_id FK, plan_code FK, status[active|paused|expired|revoked], key_status[none|pending|prepared|delivered|failed|revoked], payment_status, data_limit_gib, used_bytes, start_date, end_date, key_label, renewal_of_subscription_id, abuse_flag, created_at, updated_at)`
- `access_profiles(id PK, customer_id FK, subscription_id FK, engine_code[hiddify], engine_account_ref[per-customer UUID], region_code, profile_scope, status[active|suspended|expired|revoked], quota_bytes, used_bytes, last_synced_at, created_at, updated_at, metadata_json)` — one per (customer, region) Hiddify user.

**Subscription tokens (durable, encrypted)**
- `access_profile_public_tokens(id PK, customer_id FK, profile_id FK, subscription_id FK, token_hash UNIQUE, token_fingerprint, encrypted_token_payload, token_storage_version, purpose, status[active|revoked|rotated|expired], expires_at, rotated_from_token_id, last_seen_at, created_at, updated_at)`

**Payments & deliveries**
- `payment_methods(id PK, method_code UNIQUE, method_name, account_name, account_number, qr_image_path, enabled, sort_order, instructions_mm)`
- `payment_orders(id PK, customer_id FK, plan_code, payment_method_code, status[pending|proof_uploaded|approved|rejected|timed_out], subscription_id FK, plan_price_snapshot, currency_snapshot, data_limit_gib_snapshot, duration_days_snapshot, duration_months_snapshot, payment_note, screenshot_file_id, detected_amount, amount_match_status, note_match_status, auto_verification_status, requires_admin_review, approved_by_admin_id, approved_at, invoice_doc_status, notify_status, created_at, updated_at)`
- `subscription_deliveries(id PK, customer_id FK, platform_account_id FK, platform, profile_id FK, token_id FK, token_fingerprint, delivery_method[deeplink|copy_link|qr], delivery_status[prepared|delivered|failed|revoked], secret_payload_stored CHECK(=0), delivered_at, error_note_sanitized, created_at, updated_at)`

**Referral (append-only ledger)**
- `referral_credits(id PK, customer_id FK, role[referrer|referee], counterpart_customer_id FK, source_payment_order_id FK, credit_type[bonus_days], credit_amount, status[granted|redeemed|revoked|expired], redeemed_subscription_id FK NULL, redeemed_at NULL, granted_by[system|admin], note_sanitized, expires_at NULL, created_at)` — never mutated in place; corrections/redemptions are new rows or a status transition with its own timestamp. Balance = sum of `granted` rows minus `redeemed`/`revoked`/`expired`. `credit_type` is an enum so future MMK-credit/discount types slot in without a new table.

**Ops**
- `settings(setting_key PK, setting_value, description, updated_at)` — feature flags, bot username, policy markers, **and all referral parameters** (Appendix F.6).
- `audit_logs(id PK, actor_type, actor_id, action, target_type, target_id, summary_sanitized, created_at)`
- `usage_snapshots(id PK, subscription_id FK, region_code, used_bytes, captured_at)`
- `node_metrics(id PK, node_code FK, captured_at, cpu_pct, ram_pct, disk_pct, bandwidth_used_gb, active_users, reachable BOOL, inbound_ok BOOL)` — time-series feed for the dashboard + threshold alerts (Section 30.2.1); retained on a rolling window (e.g. 30 days), older rows pruned.
- `node_alerts(id PK, node_code FK, metric[cpu|ram|disk|bandwidth|reachability], level[warn|critical|down|recovery], value_pct, threshold_pct, message_sanitized, status[open|snoozed|cleared], created_at, cleared_at)` — alert state with dedup/snooze (Section 30.2.1).
- `leak_watcher_suspects(...)`, `node_health(...)` as needed.

**Integrity & resilience (Section 30A)**
- `schema_migrations(version PK, name, applied_at, checksum)` — the migrations logbook; forward-only, skip-if-applied (30A.1).
- `idempotency_keys(key PK, operation, target_ref, status[in_progress|completed|failed], result_ref, created_at, expires_at)` — guards payment approval & provisioning against duplicates (30A.2).
- `outbound_messages(id PK, customer_id FK, channel[telegram|messenger|viber|whatsapp|web], payload_ref, status[pending|sending|sent|failed|dead], attempts, next_retry_at, last_error_sanitized, created_at, sent_at)` — retrying notification queue (30A.3).
- `connect_samples(id PK, region_code, profile_code, sample_source[node_probe|health_check], success, latency_ms NULL, captured_at)` — anonymous service telemetry; **no customer identity/IP/PII** (30A.4).

**Scale note:** every table is accessed through a thin data layer; if concurrency outgrows SQLite, migrate to Postgres by swapping the data layer + a one-time export/import. The schema above is Postgres-compatible.

---

# Appendix B — Canonical component list (build fresh)

> The modules UNSEEN PROXY comprises, defined here as **new components to build from this plan**. There is intentionally **no "old→new" mapping** — the retired UNSEEN VPN system is not a reference. Names are suggestions; what matters is the responsibility.

| Component | Responsibility |
|---|---|
| `unseenproxy-bot` | Telegram bot (+ Messenger/Viber adapters later) on the common message shape |
| `subscription_sidecar_app.py` | Serves `sub.unseen.click/s/<token>`: UA-filter → entitlement filter → Hiddify upstream fetch (fail-soft) → rebrand |
| `hiddify_client.py` | Hiddify Manager **API v2** client (create/update/disable users, read usage) |
| `hiddify_customer_provisioner.py` | Gated provisioner CLI (audit/status/dry-run/provision/suspend/reconcile) over `hiddify_client` |
| `public_token_manager.py` | Per-customer opaque token issue/list/verify/rotate/revoke (encrypted at rest) |
| `subscription_leak_watcher.py` | Report-only IP-diversity watcher; sanitized admin alerts |
| `customer_access_suspender.py` | Gated suspend = Hiddify `enable=false`; refuses the admin profile |
| `auto_delivery_sweeper.py` | Timer-driven delivery of approved-but-undelivered subscriptions |
| `deliver_subscription.py` | Builds the delivery payload: deep-link button + copy link + QR + guide + PDFs |
| `account_service` / `notification_service` | Identity resolution; channel-aware, policy-compliant notifications (queue/template/suppress) |
| `referral_service` | Double-sided referral conversion + ledger (Section 20A) |
| Node monitor + dashboard | `node_metrics`/`node_alerts`, 75% threshold alerting, graceful degradation (Sections 6.2, 30.2.1) |
| Migration runner | Applies/records `schema_migrations` (Section 30A.1) |
| `scripts/deploy.sh` | Gated pull-to-deploy on the Master: pull/checkout → backup DB+`.env` → migrate → restart units → verify (Section 31A.5) |

Key env handles (all in `0600` `.env`, never the DB): `TELEGRAM_BOT_TOKEN`, `ACCESS_TOKEN_ENCRYPTION_SECRET` (backup-critical), per-node API key + secret admin path, `SUB_UA_FILTER_MODE`, feature-flag latches.

---

# Appendix C — Hiddify technical reference (verify in Phase 3)

> Treat everything here as **to-be-verified against the installed version** before code depends on it. Record the verified contract in `docs/HIDDIFY_API_CONTRACT.md`.

**Subscription link (per-user):** `https://<node-domain>/<secret-proxy-path>/<user-uuid>/` with format suffixes such as `/sub/`, `/sub64/`, `/singbox/`, `/clash/`, `/clashmeta/`, `/auto/` (and normal/xray). **`auto`** detects the client by User-Agent and returns the best format. A single Hiddify user link returns **all** enabled protocols/domains on that panel. UNSEEN PROXY never hands this raw link to customers — it is fetched by the Master sidecar and re-served as `https://sub.unseen.click/s/<token>`.

**Hiddify App import / URL scheme (the onboarding key):**
- `hiddify://import/<sub-link>#<name>`
- `hiddify://install-sub?url=<url-encoded sub-link>#<name>`
- `hiddify://install-config?url=<url-encoded config>#<name>`
- `hiddify://install-proxy?url=<url-encoded proxy share link>#<name>`
- The app also parses `clash://`, `clashmeta://`, `sing-box://` links. Add-profile supports **clipboard** and **in-app QR scan**. (Gallery-QR import is **not** a reliable Hiddify feature — lead with deep link + clipboard.)

**Hiddify Manager API v2 (admin):**
- Base `https://<node-domain>/<secret-proxy-path>/api/v2/admin/`; auth header `Hiddify-API-Key: <key>`; **use v2**.
- User fields seen in the API: `uuid, name, usage_limit_GB, package_days, current_usage_GB, start_date, mode, comment, telegram_id, enable, last_online, last_reset_time`.
- The Swagger/OpenAPI for the exact endpoints is available in the panel under **Settings → API**; generate the verified contract from there per node.

**Protocols:** Hiddify natively supports **Hysteria2**, **Shadowsocks**, **VLESS-Reality**, Trojan, VMESS, TUIC, WireGuard, SSH, and more — selectable per panel. (Hysteria2 support is the key capability an Xray-core-only stack lacks.)

**Sources (web, June 2026):**
- Hiddify App usage & URL scheme: <https://hiddify.com/app/URL-Scheme/>, <https://github.com/hiddify/hiddify-app/wiki/URL-Scheme>, <https://deepwiki.com/hiddify/hiddify-app/4.4-link-parsing>
- Deep-link feature/issue context: <https://github.com/hiddify/hiddify-app/issues/2074>, <https://github.com/hiddify/hiddify-app/issues/1411>
- Subscription link concept: <https://hiddify.com/manager/domain-worker-cdn-and-tunneling/How-to-create-subscription-link-on-Hiddify/>
- API usage: <https://hiddify.com/manager/contribution/How-to-use-API-in-HiddifyManager-project/>, <https://github.com/hiddify/Hiddify-Manager/discussions/3062>, <https://github.com/orgs/hiddify/discussions/3209>
- Multi-server status (feature requests): <https://github.com/hiddify/Hiddify-Manager/issues/3640>, <https://github.com/hiddify/Hiddify-Manager/issues/3318>
- Manager overview: <https://deepwiki.com/hiddify/Hiddify-Manager>, <https://hiddify.com/manager/>

---

# Appendix D — Coding-agent task checklist ("definition of done")

For **every** task, before reporting success:
- [ ] No secret printed/committed/logged (only fingerprints + masked IPs).
- [ ] No business value hardcoded (read from DB/settings).
- [ ] Dry-run added/passing before any live mutation; live action double-gated (env latch + `--live --confirm`).
- [ ] DB+`.env` backed up before schema/bulk changes (WAL-safe `conn.backup()`).
- [ ] No legacy UNSEEN VPN artifact present or referenced (build scoped to the UNSEEN PROXY root; this plan is the only source).
- [ ] Artifacts verified **on disk / on endpoint** (status codes, files, rows) — never assumed.
- [ ] Docs updated (the relevant `docs/*.md` + `CHANGELOG.md` + phase status).
- [ ] Tests added/passing for the changed behavior.
- [ ] Committed to the project's GitHub repo with a clear, phase-referenced message; pre-commit secret-scan passed (no `.env`/DB/secret tracked); pushed to `main` (Section 31A).
- [ ] Honest status: if blocked or partial, say so and fail closed.

---

# Appendix E — Glossary

- **Master VPS** — the control-plane server (DB, bots, payments, admin, sidecar, monitoring). Carries no proxy traffic.
- **Node VPS** — a regional server running Hiddify Manager; carries proxy traffic only.
- **Hiddify Manager** — the multi-protocol proxy panel (sing-box + Hysteria2 core).
- **Hiddify App** — the client app customers import their subscription into.
- **FAST1 / FAST2 / Secure** — user-facing names for Hysteria2 / Shadowsocks / VLESS-Reality.
- **Subscription token** — per-customer opaque secret resolving to entitled configs; served from `sub.unseen.click`.
- **Sidecar** — the thin service that serves `/s/<token>` with UA-filter + entitlement filtering + rebranding.
- **Entitlement** — DB-driven mapping of which regions/protocols a plan may use.
- **Gated / latched** — a live action requires an explicit env flag and confirmation flags.
- **Reason-opaque 404** — invalid/revoked/expired/blocked all return an identical 404 (no information leak).
- **Dry-run** — print intended changes without mutating anything.

---

---

# Appendix F — Authoritative seed data (plans, regions, profiles, entitlements)

> This appendix is the **machine-readable source of truth** for the launch catalogue, derived from `Plan_Rules.md` and the decisions recorded in v1.1. The seed script (`seed_catalogue.py`, idempotent, run once at init and re-runnable to upsert) writes exactly these rows. **All values remain editable at runtime via the admin surface** — seeding sets the starting state, it does not hardcode behavior. Currency is **MMK** throughout; `allowed_device_count = NULL` means unlimited.

### F.1 `plans`

| plan_code | data_limit_gib | duration_months | duration_days | price_amount | currency | recommended_device_count | allowed_device_count | is_public | is_trial | admin_only | is_enabled |
|---|---|---|---|---|---|---|---|---|---|---|---|
| TRIAL | 10 | 0 | 7 | 0 | MMK | 1 | NULL | 1 | 1 | 0 | 1 |
| BASIC | 50 | 1 | 30 | 3000 | MMK | 2 | NULL | 1 | 0 | 0 | 1 |
| CORE | 100 | 1 | 30 | 5000 | MMK | 3 | NULL | 1 | 0 | 0 | 1 |
| PLUS | 360 | 3 | 90 | 15000 | MMK | 4 | NULL | 1 | 0 | 0 | 1 |
| PRO | 600 | 3 | 90 | 20000 | MMK | 5 | NULL | 1 | 0 | 0 | 1 |
| MAX | 1500 | 6 | 180 | 30000 | MMK | 5 | NULL | 1 | 0 | 0 | 1 |
| INFINITY | 100000 | 120 | 3650 | 0 | MMK | NULL | NULL | 0 | 0 | 1 | 1 |

*(INFINITY values are placeholders for a hidden admin/test plan; tune freely — it is never public.)*

> **Duration authority.** `duration_days` is the **single authoritative** duration field used for all expiry math (`end_date = start_date + duration_days`). `duration_months` is a **display/labeling convenience only** (e.g. "1M", "3M", "6M" badges) and must never be used in date calculations. For TRIAL, `duration_months = 0` and `duration_days = 7`. Code computes expiry from `duration_days` exclusively; if the two ever disagree, `duration_days` wins. (This avoids the classic "is a month 30 days or a calendar month?" ambiguity and makes a 7-day trial unambiguous.)

### F.2 `proxy_regions`

| region_code | region_name | status | display_order | notes |
|---|---|---|---|---|
| de | Germany | live\* | 1 | Default/entry region; first node tested (Phase 2) |
| us | USA | planned | 2 | Goes live around CORE adoption |
| sg | Singapore | planned | 3 | Premium-only; live before first PRO/MAX cohort |

*\* `de` is `test` until its Phase-2 node passes the import-and-connect gate, then promoted to `live`. Seed it as `planned`/`test` and promote explicitly — never seed a region as `live` before its node is verified.*

### F.3 `profiles`

| profile_code | protocol_code | base_display_label | is_default | is_active | status |
|---|---|---|---|---|---|
| FAST1 | hysteria2 | Fast | 1 | 1 | enabled |
| FAST2 | shadowsocks | Fast | 0 | 1 | enabled |
| SECURE | vless_reality | Secure | 0 | 1 | enabled |

*Note: both Fast tiers share the base label "Fast"; the number is appended by the display rule (Section 18.3) only when a plan carries both. `is_default=1` on FAST1 means Hysteria2 is the default profile offered.*

### F.4 `plan_region_entitlements`

| plan_code | de | us | sg |
|---|---|---|---|
| TRIAL | ✅ (default) | — | — |
| BASIC | ✅ (default) | — | — |
| CORE | ✅ (default) | ✅ | — |
| PLUS | ✅ (default) | ✅ | — |
| PRO | ✅ (default) | ✅ | ✅ |
| MAX | ✅ (default) | ✅ | ✅ |
| INFINITY | ✅ | ✅ | ✅ |

*Each ✅ is a row `(plan_code, region_code, is_enabled=1)`; `is_default=1` on the `de` rows. A region only becomes visible to the customer once its node is `live` (fail-closed).*

### F.5 `plan_profile_entitlements`

| plan_code | FAST1 | FAST2 | SECURE | Renders as |
|---|---|---|---|---|
| TRIAL | ✅ | — | ✅ | Fast, Secure |
| BASIC | ✅ | — | ✅ | Fast, Secure |
| CORE | ✅ | — | ✅ | Fast, Secure |
| PLUS | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |
| PRO | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |
| MAX | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |
| INFINITY | ✅ | ✅ | ✅ | Fast1, Fast2, Secure |

*Each ✅ is a row `(plan_code, profile_code, is_enabled=1)`. FAST2 rows exist for PLUS/PRO/MAX from launch but only surface once the node's Shadowsocks inbound passes the test gate (Section 26).*

### F.6 Referral settings (`settings` rows — Section 20A)

All referral behavior is governed by these `settings` rows; the admin edits them at runtime. Seed values below are sensible defaults — **tune freely, no code change**.

| setting_key | seed value | meaning |
|---|---|---|
| `referral_enabled` | `0` (off) | Master switch; seeded **off**, turn on at/after Phase 11. |
| `referral_referrer_bonus_days` | `30` | Bonus days granted to the referrer on a successful conversion ("a free month"). |
| `referral_referee_bonus_days` | `7` | Bonus days granted to the new customer (the referee). |
| `referral_requires_paid_order` | `1` (true) | Only a real, approved, **non-trial/non-zero** first order triggers rewards. |
| `referral_max_rewards_per_period` | `10` | Max rewards one referrer can earn per rolling window (anti-farming). |
| `referral_period_days` | `30` | Length of that rolling window. |
| `referral_credit_expiry_days` | `0` (never) | Optional expiry for unredeemed credits; `0` = no expiry. |
| `referral_min_referee_spend_mmk` | `0` (none) | Optional minimum referee order value to qualify. |

### F.7 Node inventory (current servers) & alert thresholds

> Recorded from the operator's current infrastructure (2026-06-15). These seed the `proxy_nodes` rows. **Specs and addresses are data, not code** — replacing or moving any node is a row update (Section 6.1). IPs/secrets are operational data: the public IP is stored in `proxy_nodes.public_ip`; the **panel API key and secret admin path live only in `.env`**, referenced by handle (Section 31). Nodes are seeded `planned`/`test` and promoted to `live` only after the node-verification gate (Sections 6, 33).

**Master VPS (control plane + co-located DE node):**

| Field | Value |
|---|---|
| Role | **Master** (brain) **+ DE Hiddify node** co-located (Section 4.1 exception) |
| Region | Germany (DE) — default/entry region |
| Public IP | `88.214.56.96` |
| Spec | 4 vCPU, 16 GB RAM, 100 GB SSD |
| Bandwidth budget | 30 TB / month |
| `proxy_nodes` row | `node_code=de-master`, `region_code=de`, `is_master_colocated=1`, `vcpu_count=4`, `ram_mb=16384`, `disk_gb=100`, `bandwidth_budget_gb=30000` |

**Proxy nodes (data plane):**

| node_code | region | Public IP | vCPU | RAM | Disk | Bandwidth budget |
|---|---|---|---|---|---|---|
| `sg1` | SG | `64.56.71.64` | 1 | 2 GB | 60 GB SSD | 10 TB/mo |
| `sg2` | SG | `104.250.118.37` | 1 | 2 GB | 20 GB SSD | 2 TB/mo |
| `us1` | US | `172.245.110.130` | 5 | 6 GB | 100 GB SSD | 9.8 TB/mo |

Seed values: `ram_mb` = 2048/2048/6144; `disk_gb` = 60/20/100; `bandwidth_budget_gb` = 10000/2000/9800. (SG has two nodes — the offering/sidecar logic already supports multiple nodes per region, and graceful degradation means if `sg1` is down, `sg2` still serves SG — Section 6.2.)

**Capacity note for the operator:** the SG nodes are small (1 vCPU / 2 GB) and `sg2`'s **2 TB/month** budget is modest — these will hit the 75% bandwidth alert sooner than the others under load; the dashboard makes that visible early so SG capacity can be added (a third SG node is just another row). The US node is the largest by CPU; the Master has the most bandwidth headroom (30 TB) which is appropriate since it also carries DE proxy traffic.

**Alert-threshold `settings` (DB-driven, retunable — Section 30.2.1):**

| setting_key | seed value | meaning |
|---|---|---|
| `node_alert_warn_pct` | `75` | WARN when any resource/bandwidth reaches this % of its limit. |
| `node_alert_critical_pct` | `90` | CRITICAL threshold. |
| `node_alert_warn_snooze_hours` | `6` | Dedup window for WARN. |
| `node_alert_critical_snooze_hours` | `2` | Dedup window for CRITICAL. |
| `node_metrics_retention_days` | `30` | Rolling window for `node_metrics` history. |

### F.8 Seeding rules (non-negotiable)

- The seed is **idempotent** (upsert by unique code); re-running it must not duplicate rows or clobber admin edits to mutable fields beyond what the operator intends — prefer "insert if absent" for catalogue rows and leave a documented `--force-update` path for deliberate re-seeds.
- **No region is seeded as `live`.** Regions start `planned`/`test`; promotion to `live` is an explicit, node-verified admin action (Sections 6, 7, 33).
- **No node is seeded as `live`.** The four servers in F.7 seed as `planned`/`test`; each is promoted only after its verification gate (Sections 6, 33).
- **No protocol is exposed before its inbound is node-tested**, regardless of entitlement rows (Section 26).
- Seed `payment_methods` **disabled** with placeholder account details; the operator fills real KBZPay/WavePay/etc. details and enables them only at Phase 12 (Section 20).
- The seed writes the `settings` feature flags **off** (auto-delivery, live provisioning, **`referral_enabled`**) so a fresh install is inert until deliberately enabled.
- **Node secrets never seed into the DB.** F.7 seeds specs + public IP only; each node's API key and secret admin path go in `.env` (`0600`), referenced by handle.

---

*End of plan. Build it one phase at a time, from this plan only; verify on disk; keep the build clean of any legacy artifact; never expose a secret.*
