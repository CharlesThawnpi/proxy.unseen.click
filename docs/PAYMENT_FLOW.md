# PAYMENT FLOW

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §3.1, §18, §19, §20, §20A, §21
> **Status:** Phase 1 skeleton — decided from plan; code paths verified in Phase 5.

How a customer goes from picking a plan to a live, delivered subscription: plan selection, payment, OCR auto-verification, admin review, activation, and the referral rewards that ride on a first paid order.

## Currency and scope

- **MMK only.** No multi-currency, no cash-credit, no withdrawable balance in v1.
- Every plan allowance/price/cap/duration is **DB-driven and admin-editable** (§18 dynamic-config invariant); the launch seed values live in Appendix F of the plan, not in code or this doc.
- Each order/renewal **snapshots** the price/cap/duration it was sold at, so later admin edits never change historical orders.

## Registration prerequisite (§19)

First contact on any platform normalizes through the adapter to `AccountService.resolve_customer`. New customers get a `customers` row and a gap-safe `public_customer_code = "UP" + zero-padded(max_numeric_id + 1)`. Identity is idempotent — re-contact updates the mapping, never duplicates.

## Payment methods (§20)

DB-driven `payment_methods`, admin-editable. Myanmar mobile wallets — KBZPay, WavePay, AYAPay, CBPay, CTZPay, A+ — plus **Manual Payment** (admin-reviewed, no OCR). Disabled methods stay hidden until an admin supplies real account details/QR.

## Wallet-screenshot flow

1. Customer selects a plan → order created with the snapshot and a unique payment note.
2. Customer pays in their wallet app and uploads the screenshot.
3. Bot records the screenshot (file id only; no raw image persisted beyond what is needed) and replies "received, please wait."
4. **Tesseract OCR** extracts text and verifies the expected **amount** (≥ expected, with a sane upper bound to reject phone numbers, keyword-context aware) **and** the **payment note** (exact or compact match).
5. **Auto-approve** if both match → create subscription (`key_status = pending`) → trigger delivery (§21). Otherwise **flag for admin review** with a sanitized summary (no raw image in logs).
6. **Admin review:** approve (same as auto) or **reject** (cancel the order, notify once).

## Manual Payment flow

No OCR. Order is marked admin-review; an admin approves or rejects from the admin surface (§28).

## Safety

Auto-verify must **allowlist the target before approval** when the abuse model requires it (approving before allowlisting can leak the wrong delivery). The subscription/entitlement is pre-created so "allowlist-before-approval" holds without runtime hacks.

## Activation (§21, high level)

On approval (auto or admin):

1. Create/locate the `subscriptions` row from the order snapshot (`key_status = pending`).
2. Compute the **entitlement set**: allowed regions (plan→region ∩ live nodes) and allowed protocols (plan→protocol ∩ active profiles).
3. **Provision** via the Hiddify orchestrator — idempotent per-customer UUID on each entitled live node with correct quota/expiry/enabled state.
4. **Mint** (or reuse) the per-customer subscription token; store durably (encrypted).
5. **Deliver** (§17): deep-link + link + QR + guide + PDFs.
6. Transition `key_status → delivered`, `customer.status → active`; write a metadata-only delivery record.
7. An **auto-delivery sweeper** (timer, gated by a feature flag) catches approved-but-undelivered subscriptions with the same entitlement checks.
8. **Referral conversion check** runs after delivery succeeds (see below).

## Referral system (§20A summary)

A **double-sided, append-only credit-ledger** program. All parameters are DB-driven and admin-editable; nothing is hardcoded.

- **Reward:** bonus subscription **days** (admin-configurable count). Days stack cleanly onto an existing subscription's `end_date` and are unambiguous across mixed subscriptions. Granted via an **append-only `referral_credits` ledger** (one row per grant, never mutated; corrections are new offsetting rows). Balance = sum of unspent rows. Redemption extends a chosen subscription's `end_date` and pushes the new expiry to each regional Hiddify user (reversible), recorded as its own ledger event (`granted → redeemed`).
- **Attribution:** stable referral code derived from `public_customer_code` plus per-platform deep links; captured at first contact on `customers.referred_by_customer_id` (set once, immutable). **First-touch, one-time**; self-referral and re-referral of an existing customer are rejected.
- **Trigger:** granted on the referee's **first approved, paid, non-trial order** — not at signup. Activation (§21) calls `ReferralService.on_first_paid_conversion(...)` after delivery succeeds; idempotent, guarded by `has_used_referral_reward`. On success, two ledger rows are written (referrer + referee, each for the admin-set day counts) and both are notified.
- **Fraud controls (all DB-driven):** TRIAL/0-MMK orders do not trigger (admin flag `referral_requires_paid_order`, default on); per-referrer reward cap per rolling period; optional minimum referee spend; self/again-referral blocks; shared masked-IP-prefix or device-overlap signals feed the **report-only** leak-watcher/audit path (never auto-punishes — an admin reviews). The admin/test customer is excluded from earning or triggering rewards. The whole program can be paused with one flag (`referral_enabled`).

> Verified in Phase 5
