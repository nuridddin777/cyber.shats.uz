"""
CYBER SHATS — MAXSUS versiya uchun aktivatsiya kodlari (redeem code).

Admin turli muddatli (1 soat yoki 30 kun) kodlar generatsiya qiladi.
Foydalanuvchi kodni kiritib MAXSUS tarifni faollashtiradi — bepul emas,
chunki kodning o'zi (odatda) sotiladi/tarqatiladi, lekin saytda kod
kiritilishi shart, xuddi kurs faollashtirish kodlariga o'xshab.
"""
import secrets
import string
from datetime import datetime, timedelta
from db import query_one, execute


def _gen_code() -> str:
    # XAVFSIZLIK: bu kodlar to'g'ridan-to'g'ri pullik (MAXSUS/hacker) tarifni
    # ochadi — shuning uchun oddiy `random` (taxmin qilinishi mumkin bo'lgan
    # Mersenne Twister) EMAS, kriptografik jihatdan xavfsiz `secrets` moduli
    # ishlatiladi.
    chars = string.ascii_uppercase + string.digits
    return "MAX-" + "".join(secrets.choice(chars) for _ in range(8))


def generate_codes(created_by: int, duration_type: str, count: int = 1, plan: str = "hacker") -> list[str]:
    """duration_type: '1h' yoki '30d'"""
    if duration_type not in ("1h", "30d"):
        duration_type = "30d"
    codes = []
    for _ in range(max(1, min(count, 200))):
        code = _gen_code()
        execute(
            "INSERT INTO redeem_codes (code, plan, duration_type, created_by) VALUES (?,?,?,?)",
            (code, plan, duration_type, created_by)
        )
        codes.append(code)
    return codes


def redeem(user_id: int, code_str: str) -> tuple[bool, str]:
    code_str = (code_str or "").strip().upper()
    if not code_str:
        return False, "Kodni kiriting."
    row = query_one("SELECT * FROM redeem_codes WHERE code=?", (code_str,))
    if not row:
        return False, "Kod topilmadi."
    if row["used_by"]:
        return False, "Bu kod allaqachon ishlatilgan."

    now = datetime.now()
    duration = timedelta(hours=1) if row["duration_type"] == "1h" else timedelta(days=30)
    expires_at = now + duration

    execute("UPDATE redeem_codes SET used_by=?, used_at=? WHERE code=?",
            (user_id, now.strftime("%Y-%m-%d %H:%M:%S"), code_str))
    execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?",
            (row["plan"], expires_at.strftime("%Y-%m-%d %H:%M:%S"), user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (user_id, "MAXSUS versiya faollashtirildi!",
             f"Kod orqali {row['plan'].upper()} tarifi faollashtirildi. Amal qilish muddati: "
             f"{'1 soat' if row['duration_type'] == '1h' else '30 kun'}.", "success"))
    return True, f"Muvaffaqiyatli! {row['plan'].upper()} tarifi {'1 soatga' if row['duration_type']=='1h' else '30 kunga'} faollashdi."


def list_recent_codes(limit: int = 50):
    from db import query_all
    return query_all(
        """SELECT rc.*, u1.ism as creator_ism, u2.ism as user_ism, u2.familiya as user_familiya
           FROM redeem_codes rc
           LEFT JOIN users u1 ON u1.id = rc.created_by
           LEFT JOIN users u2 ON u2.id = rc.used_by
           ORDER BY rc.id DESC LIMIT ?""",
        (limit,)
    )
