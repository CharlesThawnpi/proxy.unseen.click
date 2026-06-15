# ADMIN OPERATIONS

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §22–§29, §28
> **Status:** Phase 1 skeleton — decided from plan; code paths verified in Phase 5 / 7 / 10 as noted per surface.

The admin surfaces and capabilities for running UNSEEN PROXY, plus the customer lifecycle those admins oversee. Every configurable business value is **DB-driven and admin-editable** (§18 dynamic-config invariant) — the seed values live in Appendix F, not in code.

## Surfaces (§28)

Two surfaces, both auth-gated and audited.

### Web admin (`panel.unseen.click`, FastAPI)

Session login (optional IP allowlist), CSRF-protected, read-mostly with explicit write actions:

- **Pending payments:** view (sanitized), approve, reject.
- **Plans:** create/edit/enable/disable — codes, prices, caps, durations, device recommendation, currency (all DB-driven).
- **Payment methods:** create/edit, upload QR (size/type limited).
- **Entitlements:** view/edit plan→region, plan→protocol, region/node status.
- **Nodes dashboard:** visual performance view of all nodes (status, CPU/RAM/disk, bandwidth used vs. budget, active users, reachability, connect-success/latency) plus write actions: mark test/standby/live, drain, attach/replace/retire.
- **Usage/abuse:** read-only used/remaining and abuse flags.
- **Launch controls:** feature-flag toggles (auto-delivery, live provisioning, protocol enablement) behind confirmation text.
- **Customer data export / deletion:** a gated action to (a) **export** one customer's data (identity, subscriptions, orders, deliveries — sanitized of secrets) as a single file, and (b) **delete/anonymize** a customer — scrubbing personal fields while preserving the financial/audit records that must be retained, and disabling their Hiddify users. Both are gated, dry-run-first, and audited.
- **Audit log:** read-only, masked.

> Nodes dashboard / health backing verified in Phase 7. Data export/deletion and platform-review story verified in Phase 9/10.

### Telegram admin mode

Approve/reject payments, user lookup, bot/node status, manual delivery/rotation actions — all gated.

## Hard rules (culture)

- Every admin write is **audited**, with **no secrets in the audit**.
- Destructive actions are **gated and dry-run-first**.
- The **gated suspender refuses the admin profile**; the admin/test customer and admin token are **protected** from abuse-response tooling.
- "Gated-latched" / dry-run-first is the default posture for anything destructive or live-affecting.

> Verified in Phase 5 (admin payment review) / Phase 7 (nodes, entitlements) / Phase 10 (launch controls, data export/deletion).

## Customer lifecycle the admin oversees

### Renewal (§22)

A renewal creates a **new subscription** linked to the prior one (`renewal_of_subscription_id`), reusing the same per-customer UUID where possible and **extending** quota/expiry on the existing Hiddify users (so a previously completed import keeps working). Customer-initiated (My Account → Renew) or surfaced proactively (§23). Price/cap/duration are snapshotted again. The subscription token can be **kept** (continuity) or **rotated** (suspected abuse) — operator choice.

### Expiry handling (§23)

The Master is the authority on `end_date`; a timer evaluates approaching/lapsed expiry. **Reminders** (e.g. T-3d / T-1d / on-expiry) push on Telegram, queued/templated on other platforms. **On expiry**, the orchestrator sets regional Hiddify users to `enable=false`/expired (reversible) — **prefer disable-not-delete** so renewal is instant. Hiddify's native `package_days` is a backstop; the Master reconciles.

### Data / bandwidth allowance (§24)

Per-subscription cap (`data_limit_gib`) is authoritative, written to each regional Hiddify user as `usage_limit_GB`. **Quota is shared across regions** (one logical allowance); a reconcile job sums usage across regional users (sum-vs-max policy decided in Phase 7). My Account/portal surface used/remaining. Per-VPS **node bandwidth budgets** are tracked separately — a node nearing budget can be drained without affecting customer caps.

### Region entitlement (§25)

`plan_region_entitlements` is DB-driven. A region is **offered** only if the plan entitles it AND the region is `live` AND ≥1 healthy node exists in it. The sidecar enforces this fail-closed at delivery time. Region switching (if offered) is entitlement-gated and rate-limited.

### Device recommendation (§27)

`recommended_device_count` / `recommended_devices_text` are DB-driven and shown as **advice only**, not hard-enforced (Hiddify/Hysteria2 give no reliable device cap). Real over-sharing protection is server-side: per-user token, shared data cap, expiry, token rotation, and the IP-leak watcher. The plan must **never** promise configs cannot be copied/shared.

### Support flow (§29)

A multi-step support form (category → details → optional device/speed-test) reachable from every platform. Categories: can't connect, payment issue, didn't receive subscription, slow line, other, plus a **Hiddify import** category. Tickets are handed to admins **sanitized** (no tokens/URLs/IPs) with the customer's `public_customer_code` and active-subscription summary. Optional speed-test mini-app for connection-quality reports.

> Lifecycle reconcile/policy details (quota sum-vs-max, expiry reconciliation) verified in Phase 7.
