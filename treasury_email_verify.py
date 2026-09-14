# ============================================================
# G'AZNA (Treasury) — hisobni ochishda EMAIL tasdiqlash kodi
# ============================================================
# Asosiy saytdagi email_verify.py / edu_email_verify.py bilan bir xil
# naqsh, lekin `users`/`edu_organizations` jadvali o'rniga
# `treasury_accounts` / `treasury_email_verifications` jadvallari
# ustida ishlaydi (G'azna xodimlari alohida hisob turi, users
# jadvalida emas — treasury.py'ning boshida yozilganidek).
#
# YUBORISH: utils.py dagi send_email() orqali. Sozlanmagan bo'lsa,
# kod terminalga (server konsoliga) chiqariladi — DEV rejimda G'azna
# qulflanib qolmasligi uchun.
# ============================================================
import random
import datetime

from db import query_one, execute
from utils import send_email

CODE_LENGTH = 6
CODE_TTL_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5


def _generate_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(CODE_LENGTH))


def _latest_record(treasury_account_id: int):
    return query_one(
        "SELECT * FROM treasury_email_verifications WHERE treasury_account_id=? ORDER BY id DESC LIMIT 1",
        (treasury_account_id,),
    )


def send_verification_code(treasury_account_id: int, email: str, ism: str = "") -> tuple[bool, str]:
    """Yangi tasdiqlash kodi yaratadi va G'azna xodimining emailiga yuboradi."""
    if not email:
        return False, "G'azna hisobida email ko'rsatilmagan."

    existing = _latest_record(treasury_account_id)
    if existing:
        last_sent = datetime.datetime.fromisoformat(existing["last_sent_at"])
        elapsed = (datetime.datetime.now() - last_sent).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = int(RESEND_COOLDOWN_SECONDS - elapsed)
            return False, f"Iltimos {wait} soniyadan so'ng qayta urinib ko'ring."

    code = _generate_code()
    expires_at = (datetime.datetime.now() + datetime.timedelta(minutes=CODE_TTL_MINUTES)).isoformat()

    execute(
        "INSERT INTO treasury_email_verifications (treasury_account_id, code, expires_at) VALUES (?,?,?)",
        (treasury_account_id, code, expires_at),
    )

    subject = "SHATS CYBER G'AZNA — Emailni tasdiqlash kodi"
    body = (
        f"Assalomu alaykum{', ' + ism if ism else ''}!\n\n"
        f"SHATS CYBER G'azna paneliga kirishni yakunlash uchun quyidagi "
        f"tasdiqlash kodini kiriting:\n\n"
        f"    {code}\n\n"
        f"Kod {CODE_TTL_MINUTES} daqiqa davomida amal qiladi.\n"
        f"Agar bu so'rovni siz yubormagan bo'lsangiz, bu xabarni e'tiborsiz qoldiring "
        f"va G'azna parolingizni darhol almashtiring.\n\n"
        f"— SHATS CYBER jamoasi"
    )

    sent = send_email(email, subject, body)

    if not sent:
        print(f"[TREASURY EMAIL VERIFY - SMTP SOZLANMAGAN] {email} uchun kod: {code}")
        return True, "SMTP sozlanmagan (sandbox rejim) — kod server konsoliga chiqarildi."

    return True, "Tasdiqlash kodi emailingizga yuborildi."


def verify_code(treasury_account_id: int, submitted_code: str) -> tuple[bool, str]:
    """Kodni tekshiradi. To'g'ri bo'lsa, hisobni tasdiqlaydi."""
    record = _latest_record(treasury_account_id)
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
            "UPDATE treasury_email_verifications SET attempts = attempts + 1 WHERE id=?",
            (record["id"],),
        )
        qoldi = MAX_ATTEMPTS - (record["attempts"] + 1)
        return False, f"Kod noto'g'ri. Qolgan urinishlar: {max(qoldi, 0)}"

    execute("UPDATE treasury_accounts SET email_verified=1 WHERE id=?", (treasury_account_id,))
    return True, "Email muvaffaqiyatli tasdiqlandi!"


def is_verified(treasury_account_id: int) -> bool:
    row = query_one("SELECT email_verified FROM treasury_accounts WHERE id=?", (treasury_account_id,))
    return bool(row and row["email_verified"])
