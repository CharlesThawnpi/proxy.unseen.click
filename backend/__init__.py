"""UNSEEN PROXY backend package (Phase 4A foundation).

Stdlib-only (sqlite3 / urllib / unittest) so it runs on the control-plane Master with
no extra dependencies. No business values are hardcoded here — plans/regions/protocols/
nodes live in the DB (see backend.seed); secrets come from the environment by handle
(see backend.config), never from source.
"""
__all__ = [
    "config", "db", "migrate", "seed", "units", "customer_code", "display",
    # Phase 4B service boundaries (backend-foundation only; no live sends/mutations):
    "account_service", "account_linking", "notification_service",
    "idempotency", "payment_flow", "backup",
    # Phase 4C dry-run provisioning orchestration (no live Hiddify, no sends):
    "audit", "provisioning_plan", "subscription_service", "access_profile_service",
    "payment_approval_service", "provisioning_service", "compensation",
    # Phase 5 Telegram bot foundation (dry-run; no polling/webhook/API/sends):
    "bot_context", "telegram_adapter", "telegram_messages", "telegram_commands",
    "bot_flows", "telegram_router",
    # Phase 5 transport foundation (gated; dry-run default; no network/daemon):
    "runtime_gates", "telegram_transport", "telegram_polling",
    "notification_sender", "outbound_worker",
    # Phase 6 subscription delivery foundation (dry-run; no raw links persisted/logged):
    "link_renderer", "qr_renderer", "hiddify_subscription_output",
    "delivery_payloads", "subscription_delivery",
]
