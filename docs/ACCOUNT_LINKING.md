# ACCOUNT LINKING — One profile across all platforms

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9.3
> **Status:** **Phase 4B — backend boundary IMPLEMENTED (no bot UI yet).** Identity resolution + link-code
> issue/validate/consume exist and are tested; the bot surfaces and the full profile merge land in Phase 5.
> **Verified in Phase 5** (UI lands with the Telegram bot).

## Phase 4B backend boundary (implemented, no UI)

The server-side foundation now exists ([PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md](PHASE4B_ACCOUNT_NOTIFICATION_BACKUP.md)):

- **`backend/account_service.py`** — `resolve_customer(platform_name, platform_user_id, profile=None)` maps a
  platform identity to ONE canonical `customers.id` (idempotent create + gap-safe `public_customer_code`). The raw
  platform id is **never** the identity. Validates `{telegram, messenger, viber, whatsapp, web}`.
- **`backend/account_linking.py`** — `issue_link_code` (8 chars, one-time, 24h, **hash-only** storage),
  `validate_link_code` (**reason-opaque**: unknown/expired/used are indistinguishable), `consume_link_code`
  (attach-new / already-linked idempotent no-op / **`merge_required_dry_run`**).
- **Merge is a DRY-RUN placeholder this slice:** when a code's customer differs from one that already owns the target
  platform account, nothing is mutated (no re-point, no delete, no `merged_into`) and the code is not consumed. The
  gated/audited/reversible merge (older `customer_id` canonical; re-point financial rows; `customer_merges` lineage)
  lands in Phase 5. The raw code is never logged.

How a customer on any front-end (Telegram, Messenger, Viber, later WhatsApp) ends up on **one** profile — one `customer_id`, one set of subscriptions, one usage/expiry view — without any email or password.

## Goal

A customer who started on Telegram and later buys from Messenger must land on the **same profile** so the new purchase joins their existing keys rather than creating a stranger account. Designed for **non-technical, often older users with no email** — linking must be as easy as typing a short code.

## No email, no password, ever

Identity is the platform account itself (Telegram/Messenger/Viber id) plus a short link code. There is **no email, no username/password, no "web login with credentials."** The `web` platform row exists **only** for the bot-issued short-lived portal link (§16) — it is not an email/password account.

## The link-code flow (primary method)

1. On the platform the customer is **already** using (say Telegram), they tap **"အကောင့်ချိတ်ဆက်ရန် / Link my account."** The bot shows a **short link code** (6–8 chars, big `<code>` block, easy to read aloud or copy) + plain-language instruction.
2. On the **other** platform (say Messenger), they message the bot, tap **"ကုဒ်ဖြင့်ချိတ်ဆက်ရန် / Link with a code,"** and type/paste the code.
3. Backend matches the code to the original `customer_id`, links the new platform account, confirms on both sides: **"အောင်မြင်ပါသည် — သင့်အကောင့်နှစ်ခု ပူးပေါင်းပြီးပါပြီ"** ("Done — your two accounts are now one").
4. Any purchase, key, or usage is now shared across both platforms.

**Code rules:**
- **Valid 24 hours**, **one-time use** (consumed on first successful link).
- Stored **hashed**; a **reason-opaque** "code not valid" message covers expired/used/unknown (no information leak).
- **Direction-agnostic** — generate on whichever side you're on, enter on the other.
- The **link code is the secret** that performs the merge; the `public_customer_code` (e.g. `UP0007`) is only a human-readable id for support and **never links accounts** by itself.

## Merge semantics

When two platform accounts link, the profiles **merge into one** — all subscriptions, keys, usage, and history from both sides become visible and usable from every linked platform.

- **New contact (no purchases):** its `platform_accounts` row is simply attached to the existing `customer_id`.
- **Both sides had purchases:** a **gated, audited, reversible** merge. The **older** `customer_id` (by `created_at`) becomes canonical; all `platform_accounts`, `subscriptions`, `payment_orders`, `referral_credits`, tokens, and deliveries from the other are **re-pointed** to it; the now-empty duplicate is marked `merged_into_customer_id`. Merge runs **dry-run-first**, is logged in `audit_logs`, and **never deletes financial rows** (re-points them). A `customer_merges` record preserves lineage so a mistaken merge can be traced/reversed.
- **Data caps never silently combine** — subscriptions stay distinct, just owned by one profile and listed together in My Account.
- **Self-merge / already-linked** cases are detected and handled **idempotently** (re-entering a code for an already-linked pair is a friendly no-op).

## Supporting tables

- `account_link_tokens(customer_id, code_hash, expires_at, used_at, created_at)` — issues/validates codes (code stored **hashed** as `code_hash`).
- `platform_accounts` — gains nothing new; linking just inserts/attaches a row.
- `customers.merged_into_customer_id NULL` — set on the absorbed profile.
- `customer_merges(id, canonical_customer_id, absorbed_customer_id, performed_by, summary_sanitized, created_at)` — records every merge for audit/rollback.

All linking/merge writes are idempotent and gated.

## Surfaces

- **"My Account → Link another app"** on every platform (generate code).
- Top-level **"Link with a code"** on first contact (enter code) so a returning customer on a new platform finds it immediately.
- Copy is Burmese-primary (see [LOCALIZATION.md](LOCALIZATION.md)). The support flow (§29) includes a "couldn't link my accounts" category.
