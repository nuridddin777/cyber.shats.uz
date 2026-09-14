# ============================================================
# EDU — Tashkilot ro'yxatdan o'tishida EMAIL tasdiqlash kodi
# ============================================================
# Asosiy saytdagi email_verify.py bilan bir xil naqsh, lekin
# `users` jadvali o'rniga `edu_organizations` / `edu_org_email_verifications`
# jadvallari ustida ishlaydi (Edu tashkilotlari alohida hisob turi,
# users jadvalida emas).
#
# YUBORISH: utils.py dagi send_email() orqali (SMTP). Sozlanmagan bo'lsa,
# kod terminalga (server konsoliga) chiqariladi — DEV rejimda sayt
# qulflanib qolmasligi uchun.
# ============================================================
import random
import datetime

from db import get_db
from utils import send_email

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5


def _generate_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


def _latest_record(conn, org_id: int):
    return conn.execute(
        "SELECT * FROM edu_org_email_verifications WHERE org_id=? ORDER BY id DESC LIMIT 1",
        (org_id,),
    ).fetchone()


def send_verification_code(org_id: int, email: str, org_name: str = "") -> tuple[bool, str]:
    """Yangi tasdiqlash kodi yaratadi va tashkilot emailiga yuboradi."""
    if not email:
        return False, "Tashkilotda email ko'rsatilmagan."

    conn = get_db()
    existing = _latest_record(conn, org_id)
    if existing:
        last_sent = datetime.datetime.fromisoformat(existing["last_sent_at"])
        elapsed = (datetime.datetime.now() - last_sent).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            return False, f"Iltimos {wait} soniyadan so'ng qayta urinib ko'ring."

    code = _generate_code()
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=CODE_TTL_MINUTES)).isoformat()

    conn.execute(
        "INSERT INTO edu_org_email_verifications (org_id, code, expires_at) VALUES (?,?,?)",
        (org_id, code, expires_at),
    )
    conn.commit()

    subject = "SHATS CYBER EDU — Emailni tasdiqlash kodi"
    body = (
        f"Assalomu alaykum{', ' + org_name if org_name else ''}!\n\n"
        f"SHATS CYBER EDU platformasida tashkilotingizni ro'yxatdan o'tkazishni "
        f"yakunlash uchun quyidagi tasdiqlash kodini kiriting:\n\n"
        f"    {code}\n\n"
        f"Kod {CODE_TTL_MINUTES} daqiqa davomida amal qiladi.\n"
        f"Agar bu so'rovni siz yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring.\n\n"
        f"— SHATS CYBER EDU jamoasi"
    )

    sent = send_email(email, subject, body)

    if not sent:
        print(f"[EDU EMAIL VERIFY - SMTP SOZLANMAGAN] {email} uchun kod: {code}")
        return True, "SMTP sozlanmagan (sandbox rejim) — kod server konsoliga chiqarildi."

    return True, "Tasdiqlash kodi emailingizga yuborildi."


def verify_code(org_id: int, submitted_code: str) -> tuple[bool, str]:
    conn = get_db()
    record = _latest_record(conn, org_id)
    if not record:
        return False, "Avval tasdiqlash kodi so'ralmagan. Kodni qayta yuboring."

    if record["attempts"] >= MAX_ATTEMPTS:
        return False, "Juda ko'p noto'g'ri urinish. Yangi kod so'rang."

    expires_at = datetime.datetime.fromisoformat(record["expires_at"])
    if datetime.datetime.now() > expires_at:
        return False, "Kodning amal qilish muddati tugagan. Yangi kod so'rang."

    submitted_code = (submitted_code or "").strip()
    if submitted_code != record["code"]:
        conn.execute(
            "UPDATE edu_org_email_verifications SET attempts = attempts + 1 WHERE id=?",
            (record["id"],),
        )
        conn.commit()
        qoldi = MAX_ATTEMPTS - (record["attempts"] + 1)
        return False, f"Kod noto'g'ri. Qolgan urinishlar: {max(qoldi, 0)}"

    conn.execute("UPDATE edu_organizations SET email_verified=1 WHERE id=?", (org_id,))
    conn.commit()
    return True, "Email muvaffaqiyatli tasdiqlandi!"


def is_verified(org_id: int) -> bool:
    conn = get_db()
    row = conn.execute("SELECT email_verified FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    return bool(row and row["email_verified"])
