# ============================================================
# CYBER SHATS — Guruhga avtomatik xisobot yuborish tizimi
# ============================================================
# Har bir moliyaviy/muhim voqea (CODE cheki, ID sotildi, tarif
# sotib olindi, yangi ro'yxatdan o'tish) avtomatik ravishda
# Telegram guruhiga (kerak bo'lsa — aniq BO'LIMga) yuboriladi.
#
# DIQQAT: bu FAQAT oddiy foydalanuvchi harakatlari uchun ishlaydi.
# Admin panelidan yoki Super Admin tomonidan bajarilgan amallar
# BU YERGA HECH QACHON kelmaydi (ataylab) — aks holda guruh juda
# "shovqinli" bo'lib ketardi.
import os
from db import query_one

ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "").strip()

# Bo'lim (topic) ID'lari — .env orqali sozlanadi. Agar bo'sh bo'lsa,
# xabar oddiy "General"ga (thread_id'siz) tushadi — hech qachon xato
# bermaydi, faqat kerakli bo'limga tushmaydi xolos.
TOPIC_FINANCE = os.environ.get("TG_TOPIC_FINANCE", "").strip()     # CODE xaridlari, tarif sotuvi
TOPIC_ID_SALES = os.environ.get("TG_TOPIC_ID_SALES", "").strip()   # ID savdolari
TOPIC_NEWS = os.environ.get("TG_TOPIC_NEWS", "").strip()           # Yangi ro'yxatdan o'tganlar


def _send_to_topic(text: str, topic_id: str):
    """Guruhga (kerak bo'lsa aniq bo'limga) xabar yuboradi. Bo'lim
    sozlanmagan bo'lsa — General'ga tushadi, hech qachon yiqilib
    qolmaydi."""
    if not ADMIN_CHAT_ID:
        return
    try:
        import telegram_bot as tg
        kwargs = {}
        if topic_id:
            try:
                kwargs["message_thread_id"] = int(topic_id)
            except ValueError:
                pass
        tg.tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=text,
                     parse_mode="Markdown", **kwargs)
    except Exception as e:
        import logging
        logging.getLogger("cybershats").warning(f"Guruhga xisobot yuborishda xato: {e}")


def report_code_purchase(user_id: int, amount_code: int, amount_som: int = None):
    user = query_one("SELECT ism, familiya, custom_id FROM users WHERE id=?", (user_id,))
    if not user:
        return
    text = (f"💳 *Yangi CODE xarid so'rovi*\n\n"
            f"👤 {user['familiya']} {user['ism']} (#{user['custom_id']})\n"
            f"⚡ {amount_code:,} CODE" + (f" ({amount_som:,} so'm)" if amount_som else ""))
    _send_to_topic(text, TOPIC_FINANCE)


def report_id_sale(user_id: int, custom_id: str, price_code: int, buyer_type: str = "admin"):
    user = query_one("SELECT ism, familiya FROM users WHERE id=?", (user_id,))
    if not user:
        return
    text = (f"🆔 *ID sotildi*\n\n"
            f"👤 {user['familiya']} {user['ism']}\n"
            f"#{custom_id} — ⚡ {price_code:,} CODE")
    _send_to_topic(text, TOPIC_ID_SALES)


def report_plan_purchase(user_id: int, plan_name: str, price_code: int):
    user = query_one("SELECT ism, familiya, custom_id FROM users WHERE id=?", (user_id,))
    if not user:
        return
    text = (f"👑 *Tarif sotib olindi*\n\n"
            f"👤 {user['familiya']} {user['ism']} (#{user['custom_id']})\n"
            f"📦 {plan_name} — ⚡ {price_code:,} CODE")
    _send_to_topic(text, TOPIC_FINANCE)


def report_new_registration(user_id: int):
    user = query_one("SELECT ism, familiya, custom_id, email FROM users WHERE id=?", (user_id,))
    if not user:
        return
    text = (f"🎉 *Yangi foydalanuvchi ro'yxatdan o'tdi*\n\n"
            f"👤 {user['familiya']} {user['ism']}\n"
            f"🆔 #{user['custom_id']}\n"
            f"📧 {user['email']}")
    _send_to_topic(text, TOPIC_NEWS)


PRICE_LABELS = {
    "pro_price_code": "PRO tarif narxi",
    "cyber_pro_price_code": "CYBER PRO tarif narxi",
    "vip_price_code": "VIP tarif narxi",
    "hacker_price_code": "MAXSUS tarif narxi",
    "welcome_bonus_code": "Xush kelibsiz bonusi",
    "paid_course_code_default": "Standart pulik kurs narxi",
    "code_to_som_rate": "1 CODE necha so'm",
    "tarif_basic_uzs": "BASIC tarif narxi (so'm)",
    "tarif_standard_uzs": "STANDARD tarif narxi (so'm)",
    "tarif_pro_uzs": "PRO tarif narxi (so'm)",
    "tarif_vip_uzs": "VIP tarif narxi (so'm)",
    "team_tax_free_code": "Bepul guruh solig'i",
    "team_tax_paid_code": "Pulik guruh solig'i",
    "team_tax_hacker_code": "MAXSUS guruh solig'i",
    "team_hacker_free_months": "MAXSUS bepul oylar soni",
}


def report_price_change(changes: list):
    """changes: [(key_or_label, old_value, new_value), ...]"""
    if not changes:
        return
    lines = ["💲 *Narxlar o'zgartirildi*\n"]
    for key, old, new in changes:
        label = PRICE_LABELS.get(key, key)
        if old is not None:
            lines.append(f"• {label}: ~{old}~ → *{new}*")
        else:
            lines.append(f"• {label}: *{new}*")
    _send_to_topic("\n".join(lines), TOPIC_FINANCE)
