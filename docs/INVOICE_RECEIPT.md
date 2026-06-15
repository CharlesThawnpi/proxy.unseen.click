# INVOICE & RECEIPT GENERATION

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §3.1, §20, §21
> **Status:** Phase 1 skeleton — decided from plan; code paths verified in Phase 5.

PDF invoice and receipt generation for customer orders, downloadable from "My Account" / the customer portal.

## What is generated

- **Invoice** and **receipt** PDFs are produced as part of the payment/activation flow and exposed via "My Account" (subscription/QR re-show, invoice/receipt download — §3.1).
- Documents reflect the **order-time snapshot** (price/cap/duration frozen at sale time), so a later plan edit never changes a past document.
- **Currency is MMK only** (no multi-currency, no cash-credit).

## Language

- **Invoices and receipts are in ENGLISH** — not Burmese.
- (Note: this is distinct from the customer-facing bot/portal copy, which is localized. The financial PDFs are English.)

## Pre-live watermark

- A **"pre-live / not final"** watermark is rendered on every invoice/receipt **until public launch**.
- The watermark is **removed at the Phase 12 cutover** to live/public.

## Notes

- Generated documents contain **no secrets** (no tokens, subscription URLs, or raw payment images). Treat PDFs as sanitized customer-facing artifacts.
- Exact template/layout, fonts, and the watermark toggle mechanism are implementation detail.

> Verified in Phase 5
