# ============================================================
# CYBER SHATS — Umumiy yordamchi funksiyalar
# ============================================================
import datetime
from flask import jsonify


# O'zbekiston (Toshkent) vaqt zonasi — UTC+5, yil davomida o'zgarmaydi (DST yo'q)
TASHKENT_OFFSET = datetime.timedelta(hours=5)


def to_tashkent(iso_str, fmt="%d.%m.%Y %H:%M"):
    """
    Bazadagi UTC vaqtni (datetime('now') SQLite UTC qaytaradi) O'zbekiston
    mahalliy vaqtiga (UTC+5) o'tkazib, berilgan formatda matn qaytaradi.
    Bo'sh yoki noto'g'ri qiymat uchun bo'sh satr qaytaradi.
    """
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(str(iso_str).replace("Z", ""))
    except Exception:
        return str(iso_str)
    local_dt = dt + TASHKENT_OFFSET
    return local_dt.strftime(fmt)


def api_response(success=True, data=None, error=None, status=200):
    """Loyihaning standart API javob formati: {success, data, error, ts}"""
    body = {
        "success": success,
        "data": data,
        "error": error,
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
    }
    return jsonify(body), status


def time_ago_uz(iso_str):
    """ISO vaqtni 'N daqiqa oldin' kabi o'zbekcha formatga o'tkazadi."""
    try:
        dt = datetime.datetime.fromisoformat(str(iso_str).replace("Z", ""))
    except Exception:
        return ""
    now = datetime.datetime.now()
    diff = now - dt
    secs = diff.total_seconds()
    if secs < 60:
        return "hozir"
    if secs < 3600:
        return f"{int(secs // 60)} daqiqa oldin"
    if secs < 86400:
        return f"{int(secs // 3600)} soat oldin"
    if secs < 86400 * 30:
        return f"{int(secs // 86400)} kun oldin"
    return dt.strftime("%d.%m.%Y")


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    m = seconds // 60
    s = seconds % 60
    if m >= 60:
        return f"{m // 60} soat {m % 60} daq"
    return f"{m} daq {s} sek" if s else f"{m} daq"


def resolve_user_id(identifier: str):
    """
    Admin panellarida "User ID" maydoniga odamlar ko'pincha saytdagi ko'rinadigan
    ID'ni (custom_id, 7 xonali yoki VIP bitta raqamli) yozadi, ba'zan email yoki
    ichki bazaviy raqamli id (users.id) yozadi. Bu funksiya HAMMASINI qabul qiladi:

      1) avval custom_id bo'yicha aniq moslik qidiradi (saytda ko'rinadigan ID)
      2) topilmasa va matn email ko'rinishida bo'lsa — email bo'yicha qidiradi
      3) topilmasa va matn butun son bo'lsa — users.id (ichki asosiy kalit) bo'yicha qidiradi

    Topilsa users.id (int) qaytaradi, aks holda None.
    Avvalgi xato: forma faqat (3)-variantni qo'llab-quvvatlar edi, shu sabab
    admin "TAYINLASH/Ber" tugmasini bossa ham "foydalanuvchi topilmadi" xatosi
    doimiy chiqar edi — chunki admin odatda saytda ko'rinadigan custom_id'ni kiritardi.
    """
    from db import query_one
    if identifier is None:
        return None
    identifier = str(identifier).strip()
    if not identifier:
        return None

    row = query_one("SELECT id FROM users WHERE custom_id=?", (identifier,))
    if row:
        return row["id"]

    if "@" in identifier:
        row = query_one("SELECT id FROM users WHERE email=?", (identifier.lower(),))
        if row:
            return row["id"]

    if identifier.isdigit():
        row = query_one("SELECT id FROM users WHERE id=?", (int(identifier),))
        if row:
            return row["id"]

    return None


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    HTTP API (Resend) orqali email yuboradi. 
    Xosting/Railway SMTP portlarini bloklagani sababli TCP/SMTP dan voz kechildi.
    """
    import os
    import requests

    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    
    # Resend API faqat tasdiqlangan domendan (yoki test uchun onboarding@resend.dev) xat yuborishga ruxsat beradi.
    # Shuning uchun agar @gmail.com kiritilgan bo'lsa, uni avtomatik onboarding ga o'zgartiramiz, 
    # chunki Gmail domenidan xat yuborishni Resend bloklaydi.
    smtp_user = os.environ.get("SMTP_USER", "onboarding@resend.dev").strip()
    if "gmail.com" in smtp_user.lower() or not smtp_user:
        sender = "onboarding@resend.dev"
    else:
        sender = smtp_user

    if not to_email:
        print("[EMAIL] Yuborilmadi: qabul qiluvchi email manzili bo'sh.")
        return False

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {resend_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": body
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            return True
        else:
            print(f"[EMAIL] Resend API xatosi: HTTP {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[EMAIL] Resend tarmog'iga ulanishda xato: {e}")
        return False
