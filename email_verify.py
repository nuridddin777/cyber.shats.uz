# ============================================================
# CYBER SHATS — Ro'yxatdan o'tishda EMAIL tasdiqlash kodi
# ============================================================
# Foydalanuvchi ro'yxatdan o'tganda (yoki email o'zgartirganda) unga
# 6 xonali kod yuboriladi. Kodni to'g'ri kiritmaguncha hisobi
# "tasdiqlanmagan" (email_verified=0) holatda qoladi va login_required
# uni /verify-email sahifasiga yo'naltiradi.
#
# YUBORISH: utils.py dagi send_email() orqali (SMTP). .env faylda
# SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD sozlanishi shart.
# Sozlanmagan bo'lsa, send_email jim False qaytaradi — bu holda
# DEV rejimda kod terminalga (konsolga) chiqariladi, sayt qulflanib
# qolmasligi uchun.
# ============================================================
import random
import datetime

from db import query_one, execute
from utils import send_email

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15          # Kod amal qilish muddati
RESEND_COOLDOWN_SECONDS = 60   # Qayta yuborish uchun kutish vaqti
MAX_ATTEMPTS = 5               # Noto'g'ri urinishlar limiti


def _generate_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


def _latest_record(user_id: int):
    return query_one(
        "SELECT * FROM email_verifications WHERE user_id=? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )


def send_verification_code(user_id: int, email: str, ism: str = "") -> tuple[bool, str]:
    """Yangi tasdiqlash kodi yaratadi va emailga yuboradi.
    Juda tez-tez so'ralsa (cooldown ichida), eski kodni qayta yubormaydi."""
    existing = _latest_record(user_id)
    if existing:
        last_sent = datetime.datetime.fromisoformat(existing["last_sent_at"])
        elapsed = (datetime.datetime.now() - last_sent).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            return False, f"Iltimos {wait} soniyadan so'ng qayta urinib ko'ring."

    code = _generate_code()
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=CODE_TTL_MINUTES)).isoformat()

    execute(
        "INSERT INTO email_verifications (user_id, code, expires_at) VALUES (?,?,?)",
        (user_id, code, expires_at),
    )

    subject = "SHATS CYBER — Emailni tasdiqlash kodi"
    body = (
        f"Assalomu alaykum{', ' + ism if ism else ''}!\n\n"
        f"SHATS CYBER platformasida ro'yxatdan o'tishni yakunlash uchun quyidagi "
        f"tasdiqlash kodini kiriting:\n\n"
        f"    {code}\n\n"
        f"Kod {CODE_TTL_MINUTES} daqiqa davomida amal qiladi.\n"
        f"Agar bu so'rovni siz yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring.\n\n"
        f"— SHATS CYBER jamoasi"
    )

    sent = send_email(email, subject, body)

    if not sent:
        # SMTP sozlanmagan (DEV/sandbox) — kodni terminalga chiqaramiz,
        # shunda ishlab chiquvchi test qila oladi, foydalanuvchi qulflanib qolmaydi.
        print(f"[EMAIL VERIFY - SMTP SOZLANMAGAN] {email} uchun kod: {code}")
        return True, "SMTP sozlanmagan (sandbox rejim) — kod server konsoliga chiqarildi."

    return True, "Tasdiqlash kodi emailingizga yuborildi."


def verify_code(user_id: int, submitted_code: str) -> tuple[bool, str]:
    """Foydalanuvchi kiritgan kodni tekshiradi. To'g'ri bo'lsa, hisobni tasdiqlaydi."""
    record = _latest_record(user_id)
    if not record:
        return False, "Avval tasdiqlash kodi so'ralmagan. Kodni qayta yuboring."

    if record["attempts"] >= MAX_ATTEMPTS:
        return False, "Juda ko'p noto'g'ri urinish. Yangi kod so'rang."

    expires_at = datetime.datetime.fromisoformat(record["expires_at"])
    if datetime.datetime.now() > expires_at:
        return False, "Kodning amal qilish muddati tugagan. Yangi kod so'rang."

    submitted_code = (submitted_code or "").strip()
    if submitted_code != record["code"]:
        execute(
            "UPDATE email_verifications SET attempts = attempts + 1 WHERE id=?",
            (record["id"],),
        )
        qoldi = MAX_ATTEMPTS - (record["attempts"] + 1)
        return False, f"Kod noto'g'ri. Qolgan urinishlar: {max(qoldi, 0)}"

    execute("UPDATE users SET email_verified=1 WHERE id=?", (user_id,))
    return True, "Email muvaffaqiyatli tasdiqlandi!"


def is_verified(user_id: int) -> bool:
    row = query_one("SELECT email_verified FROM users WHERE id=?", (user_id,))
    return bool(row and row["email_verified"])
