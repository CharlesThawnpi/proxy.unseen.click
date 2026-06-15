# LOCALIZATION — Burmese-primary frontend

> **Source of truth:** [IMPLEMENTATION_PLAN.md](../IMPLEMENTATION_PLAN.md) §9.4
> **Status:** Phase 1 skeleton — decided from plan; final per-string wording held in the localization layer

The customer-facing frontend is **Burmese (Myanmar) by default — roughly 90% Burmese / 10% English** — with English deliberately retained for the small set of terms that read more clearly in English.

## Policy

- This is a **product requirement**, not a per-user setting to be discovered. The aim is a frontend that feels native to a Burmese speaker, including non-technical and older users, without forcing awkward Burmese translations of terms people already know in English.
- **Default language is `my` (Burmese)** across Telegram, Messenger, Viber, and (later) WhatsApp, plus the customer portal (`app.unseen.click`): greetings, instructions, prompts, errors, status text, reminders, menus, account-linking copy, and onboarding/usage guides are all Burmese.
- `customers.preferred_language` defaults to `my`. A fuller language toggle may come later; the shipped default and design target is Burmese-primary.
- **Admin-facing** surfaces (web admin, technical docs, protocol/engine names) remain in **English** — this requirement governs the **customer frontend** only.

## Terms deliberately kept in English

A Burmese sentence may embed an English term (e.g. "သင့် **Plan** ကို ရွေးပါ"). The terms kept in English:

- **Plan** (not "ပလန်")
- Profile labels: **FAST1**, **FAST2**, **Secure**
- **GB**
- **Hiddify**
- **QR**
- **VPN**

Which exact terms stay English is a **content decision recorded here**, not scattered through code. The localization layer holds the final per-string wording.

## Invoices and receipts — English

**Invoices and receipts are in English** (labels, headings, field names). Only the bot/portal **interaction** layer is Burmese-primary; the financial documents are English. (This removes the Burmese-PDF-font concern from invoices — though the portal itself still renders Burmese.)

## Implementation rules

- All user-facing strings live in a **localization layer (files / DB `settings`)**, **never hardcoded** (consistent with the dynamic-config invariant), so Burmese phrasing and which terms stay English can be tuned without code changes.
- **Use Unicode Burmese, not Zawgyi**, consistently across bot and portal.
- Designed for **non-technical and older users**.
- During each channel's compliance gate (§9.2), verify that mixed Burmese+English button labels fit Messenger/Viber button-length limits.
