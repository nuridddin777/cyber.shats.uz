# ============================================================
# CYBER SHATS — Telegram Mini App (WebApp) autentifikatsiyasi
# ============================================================
# Telegram bot Web App ochganda, foydalanuvchi brauzeriga (aslida
# Telegram'ning o'z ichki brauzeriga) `initData` degan satr beriladi.
# Bu satrni HAR SAFAR serverda TEKSHIRISH SHART — aks holda istalgan
# odam o'zini boshqa foydalanuvchi qilib ko'rsatib, uning balansini
# ko'rishi/sarflashi mumkin bo'lib qolardi. Tekshirish HMAC-SHA256
# orqali, bot tokenidan olingan maxfiy kalit bilan amalga oshiriladi
# — bu Telegram'ning rasmiy, hujjatlashtirilgan algoritmi.
import hashlib
import hmac
import json
import os
import time
from urllib.parse import parse_qsl

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
MAX_AUTH_AGE_SECONDS = 86400  # 24 soat — undan eski initData rad etiladi


def verify_init_data(init_data: str) -> dict | None:
    """initData satrini tekshiradi. To'g'ri bo'lsa — ichidagi foydalanuvchi
    ma'lumotini (dict) qaytaradi. Noto'g'ri/soxta/eskirgan bo'lsa — None."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > MAX_AUTH_AGE_SECONDS:
            return None

        user_json = parsed.get("user")
        if not user_json:
            return None
        return json.loads(user_json)
    except Exception:
        return None
