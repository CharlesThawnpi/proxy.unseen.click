# ABUSE & LEAK RESPONSE RUNBOOK

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §30.2
> **Status:** Phase 1 skeleton — stub; verified in Phase 10

§30.2 defines the **IP-leak watcher** (`subscription_leak_watcher.py`, ~30min timer): it parses sanitized sidecar logs and flags per-token **masked-prefix diversity** (OK/WARN/CRITICAL, e.g. 3/5 prefixes), mapping fingerprint→customer for the admin.

It is **report-only** — it never auto-mutates. Alerts are sanitized Telegram messages with **dedup/snooze** (WARN 6h, CRITICAL 2h, escalation immediate, recovery silent), and it emits a **copy-paste gated suspend command** that it never runs itself. The suspender **refuses the admin profile**.

> Verified in Phase 10
