# TIMEZONE POLICY

> **Decision date:** 2026-06-16 MMT
> **Status:** ACCEPTED — project-wide business/customer time rule.

## Myanmar Time Rule

All project, system, and product business dates/times use **Myanmar Time**.

- **Project timezone:** Myanmar Time
- **Abbreviation:** MMT
- **Offset:** UTC+06:30
- **IANA timezone:** `Asia/Yangon`

## Business / Customer Dates

Customer-visible dates and times must be shown in MMT. This includes portal, bot, support, admin, reports, and status
surfaces unless the value is explicitly a technical/external UTC timestamp.

## Subscription Lifecycle

Subscription start/end dates use MMT.

Example:

- Start: `2026-06-16 09:00:00 MMT`
- End for a 30-day Plan: `2026-07-16 09:00:00 MMT`

If a node/API expects a different timezone or UTC-derived value later, convert at the integration boundary and keep the
business source value in MMT.

## Payments / Invoices

Payment/order approval timestamps, invoice dates, and receipt dates use MMT. Financial documents remain English, but
their dates are Myanmar Time dates.

## Bot / Portal / Admin Displays

Telegram bot copy, customer portal pages, future admin pages, support summaries, and report examples must label or
otherwise clearly imply MMT for customer/business dates.

## External UTC Conversion Rule

If an external API returns UTC, convert it to MMT before customer/business use. Do not store or display an external UTC
timestamp as a subscription/payment/customer-facing date without conversion.

## Technical Log Exception

Technical logs may use UTC later when that is operationally useful, but those fields must be explicitly labeled as UTC
and must not be confused with business dates. Customer-facing and product lifecycle dates remain MMT.

## Implementation Helpers

`backend/timezone.py` provides:

- `now_mmt()`
- `to_mmt(dt)`
- `format_mmt(dt)`
- `today_mmt()`
- `parse_mmt(value)`
- `storage_mmt(dt)`

New code should use timezone-aware datetimes and reject/avoid naive datetimes.

## Current App-Write Coverage

As of the Phase 8B MMT timestamp foundation, current app-created dry-run business writes route through
`backend.timezone` helpers instead of SQLite clock fallbacks for:

- Subscription `start_date` / `expiry_date`.
- Payment-order `approved_at`.
- Outbound-message `created_at`, `sent_at`, and `next_attempt_at`.
- Audit-log `created_at`.
- Idempotency-key `created_at` / `updated_at`.
- Account-link token `expires_at` / `consumed_at`.
- Node-alert `raised_at` / `cleared_at`.
- Portal access-token/session `created_at`, `expires_at`, `last_verified_at`, and `revoked_at`.

Legacy SQLite `datetime('now')` defaults remain in historical migrations as documented fallbacks only; they should not
be the primary app-created business timestamp path.

## Known Follow-Ups Before Live Launch

- Keep auditing legacy SQLite defaults and technical timestamp paths; do not destructively rewrite historical
  migrations.
- Review backup, health-monitor, and other purely technical timestamp paths and explicitly label or convert them before
  they reach customer/business surfaces.
- Review invoices/receipts before launch so every generated financial date is MMT.
- Review bot/portal/admin display paths and add explicit MMT labels wherever ambiguity remains.
- Decide whether purely technical logs should remain UTC; if so, label them clearly as UTC.
