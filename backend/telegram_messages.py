"""Burmese-primary Telegram message catalogue (§9, LOCALIZATION, BOT_FLOWS).

All user-facing copy lives here (not scattered through handlers). Copy is ~90% Burmese with
standard English product terms kept verbatim: Plan, Trial, Basic, Core, Plus, Pro, Max, Fast,
Fast1, Fast2, Secure, UNSEEN PROXY. No secrets, links, tokens, or QR payloads ever appear here.

Phase 5 is dry-run: copy below is RENDERED into the adapter outbox, never sent.
"""
from __future__ import annotations

from typing import Dict, List

BRAND = "UNSEEN PROXY"

# Stable keys so tests can assert presence without matching exact wording.
WELCOME = (
    f"🛡️ {BRAND} မှ ကြိုဆိုပါတယ်။\n"
    "လုံခြုံပြီး မြန်ဆန်တဲ့ အင်တာနက်ဝန်ဆောင်မှုကို ရိုးရှင်းစွာ အသုံးပြုနိုင်ပါပြီ။\n"
    "အောက်က မီနူးကို ရွေးချယ်ပြီး စတင်လိုက်ပါ။"
)

MAIN_MENU = (
    "📋 ပင်မမီနူး — ဘာလုပ်ချင်ပါသလဲ?\n"
    "• Plan များကြည့်ရန် — /plans\n"
    "• ကျွန်ုပ်၏အကောင့်/အခြေအနေ — /account\n"
    "• အကောင့်ချိတ်ဆက်ရန် (code) — /link\n"
    "• အကူအညီ — /help"
)

HELP = (
    "ℹ️ အကူအညီ — {brand}\n"
    "ဤနေရာတွင် Plan များ ရွေးချယ်ခြင်း၊ အကောင့်အခြေအနေ ကြည့်ခြင်းနှင့် အကောင့်ချိတ်ဆက်ခြင်းတို့ ပြုလုပ်နိုင်ပါသည်။\n"
    "ပြဿနာရှိပါက ဤနေရာတွင် မေးမြန်းနိုင်ပါသည်။ ငွေပေးချေမှုနှင့် ဝန်ဆောင်မှုဖွင့်ခြင်းမှာ မကြာမီ ဖွင့်လှစ်ပါမည်။"
).format(brand=BRAND)

PLANS_HEADER = "🗂️ ရရှိနိုင်သော Plan များ (DE ကို အခြေခံအဖြစ် အသုံးပြုပါသည်):"

ACCOUNT_STATUS_NONE = (
    "👤 ကျွန်ုပ်၏အကောင့်\n"
    "သင့်အကောင့် ({code}) အတွက် လက်ရှိ subscription မရှိသေးပါ။\n"
    "Plan တစ်ခုကို /plans တွင် ရွေးချယ်နိုင်ပါသည်။ (ဝန်ဆောင်မှုဖွင့်ခြင်း — မကြာမီ)"
)

ACCOUNT_STATUS_HEADER = "👤 ကျွန်ုပ်၏အကောင့် ({code}) — subscription အခြေအနေ:"

LINK_PROMPT = (
    "🔗 အကောင့်ချိတ်ဆက်ရန်\n"
    "အခြား platform (Telegram/Messenger/Viber) တွင် ရရှိထားသော ၆–၈ လုံး code ကို ဤနေရာတွင် ရိုက်ထည့်ပါ။\n"
    "Code သည် ၂၄ နာရီသာ သက်တမ်းရှိပြီး တစ်ကြိမ်သာ အသုံးပြုနိုင်ပါသည်။ (Phase 5: နမူနာအဆင့်)"
)

COMING_SOON = "🚧 ဤလုပ်ဆောင်ချက်ကို မကြာမီ ဖွင့်လှစ်ပါမည်။ (ယခုအဆင့်မှာ စမ်းသပ်/dry-run သာ ဖြစ်ပါသည်။)"

UNKNOWN = (
    "❓ တောင်းပန်ပါတယ်၊ ဤညွှန်ကြားချက်ကို နားမလည်ပါ။\n"
    "ပင်မမီနူးအတွက် /start ၊ အကူအညီအတွက် /help ကို သုံးပါ။"
)

INVALID_UPDATE = "⚠️ မမှန်ကန်သော တောင်းဆိုမှု — ဘာမှ မလုပ်ဆောင်ပါ။"

ADMIN_DENIED = "⛔ ဤနေရာသည် admin များအတွက်သာ ဖြစ်ပါသည်။"

ADMIN_SUMMARY_HEADER = "🛠️ Admin အကျဉ်းချုပ် (dry-run; DB မှသာ — လျှို့ဝှက်အချက်အလက် မပါ):"


def help_text() -> str:
    return HELP


def plan_line(display_name_en: str, plan_code: str, gib: int, days: int, price_mmk: int,
              regions: List[str], profile_labels: Dict[str, str], premium_regions: List[str]) -> str:
    """One sanitized Burmese-primary plan line. Values come from DB rows (caller resolves)."""
    profiles = "/".join(profile_labels.get(c, c) for c in ("FAST1", "FAST2", "SECURE")
                        if c in profile_labels)
    regions_txt = ", ".join(r.upper() for r in regions)
    premium_note = ""
    if premium_regions:
        premium_note = f" — {'/'.join(r.upper() for r in premium_regions)} သည် Pro/Max အတွက်သာ"
    price_txt = "အခမဲ့" if price_mmk == 0 else f"{price_mmk:,} MMK"
    return (f"• {display_name_en} ({plan_code}): {gib} GiB · {days} ရက် · {price_txt}\n"
            f"   regions: {regions_txt}{premium_note} · protocols: {profiles}")


def admin_summary(customers: int, subscriptions: int, queued_notifications: int,
                  dry_run_attempts: int) -> str:
    return (f"{ADMIN_SUMMARY_HEADER}\n"
            f"• customers: {customers}\n"
            f"• subscriptions: {subscriptions}\n"
            f"• queued notifications: {queued_notifications}\n"
            f"• provisioning attempts (dry-run): {dry_run_attempts}")
