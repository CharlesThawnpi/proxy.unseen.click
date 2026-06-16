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


# Outbound notification templates, keyed by the payload_ref PREFIX (never the raw body/secret).
# The sender maps a queued message's payload_ref → one of these Burmese-primary strings. No
# subscription/proxy links or QR payloads are ever produced here.
DELIVERY_PREP = (
    "✅ သင့်ဝန်ဆောင်မှုကို ပြင်ဆင်နေပါသည်။ အသေးစိတ်ကို မကြာမီ အကြောင်းကြားပါမည်။ (dry-run)"
)
GENERIC_TRANSACTIONAL = "🔔 အသိပေးချက် — {brand}".format(brand=BRAND)


# Customer-facing availability copy (Burmese-primary). NO node IP / secret / link ever included —
# only region codes (DE/US/SG) and protocol display labels, which are public product facts.
def region_available(region_code: str) -> str:
    return f"✅ {region_code.upper()} ဒေသကို ယခု အသုံးပြုနိုင်ပါသည်။"


def region_unavailable(region_code: str) -> str:
    return (f"⚠️ {region_code.upper()} ဒေသကို ယခုအချိန် မရရှိနိုင်သေးပါ။ "
            "ခဏအကြာတွင် ပြန်လည်ကြိုးစားကြည့်ပါ — သို့မဟုတ် သင်ဝယ်ယူထားသော အခြားဒေသကို သုံးပါ။")


def region_test_only(region_code: str) -> str:
    return (f"🧪 {region_code.upper()} ဒေသသည် ယခုအဆင့်တွင် စမ်းသပ်ဆဲ (test) သာ ဖြစ်ပါသည် — "
            "တရားဝင် ဝန်ဆောင်မှု မဖွင့်ရသေးပါ။")


def protocol_unavailable(region_code: str, label: str) -> str:
    return f"⚠️ {label} protocol ကို {region_code.upper()} ဒေသတွင် ယခုအချိန် မရရှိနိုင်ပါ။"


def plan_excludes_region(region_code: str) -> str:
    return (f"ℹ️ သင့် Plan တွင် {region_code.upper()} ဒေသ မပါဝင်ပါ။ "
            "Pro/Max Plan များတွင် ပိုမိုသော ဒေသများ ပါဝင်ပါသည်။")


def delivery_preview(deep_link_available: bool, copy_link_available: bool,
                     qr_available: bool) -> str:
    """Safe Burmese-primary delivery preview — describes which delivery modes are available.
    Contains NO link/token/QR; the actual branded link is attached in memory only at send time."""
    lines = ["📦 သင့်ဝန်ဆောင်မှု Subscription ပြင်ဆင်ပြီးပါပြီ — ချိတ်ဆက်ရန် နည်းလမ်းများ:"]
    if deep_link_available:
        lines.append("• Hiddify App ဖြင့် တိုက်ရိုက်ဖွင့်ရန် (deep link) — အကြံပြုထားသည်")
    if copy_link_available:
        lines.append("• Subscription link ကို ကူးယူ၍ Hiddify App တွင် ထည့်ရန်")
    lines.append("• QR — မကြာမီ (ယခုအဆင့်တွင် မရသေးပါ)" if not qr_available
                 else "• QR ကုဒ်ဖြင့် scan ဖတ်၍ ထည့်ရန်")
    lines.append("🔒 လင့်ခ်ကို သီးသန့်ထားပါ — အများနှင့် မမျှဝေပါနှင့်။")
    return "\n".join(lines)


def render_payload(payload_ref: str) -> str:
    """Resolve a queued notification's payload_ref to Burmese-primary text. The payload_ref is a
    reference/template key (e.g. 'bot:welcome:7', 'delivery:sub:7') — never raw content."""
    ref = (payload_ref or "").strip()
    if ref.startswith("bot:welcome"):
        return WELCOME
    if ref.startswith("delivery:sub"):
        return DELIVERY_PREP
    return GENERIC_TRANSACTIONAL


def admin_summary(customers: int, subscriptions: int, queued_notifications: int,
                  dry_run_attempts: int) -> str:
    return (f"{ADMIN_SUMMARY_HEADER}\n"
            f"• customers: {customers}\n"
            f"• subscriptions: {subscriptions}\n"
            f"• queued notifications: {queued_notifications}\n"
            f"• provisioning attempts (dry-run): {dry_run_attempts}")
