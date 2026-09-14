"""
CYBER SHATS — MAXSUS: Do'stlar Taklif (referral) moduli.

MUHIM: Bu modul faqat kuzatuv/statistika uchun — HECH QANDAY avtomatik CODE
bonusi bermaydi. Agar kerak bo'lsa, admin "Bonus berish" paneli orqali
o'zi qo'lda beradi.
"""
import random
import string
from db import query_one, query_all, execute


def ensure_referral_code(user_id: int) -> str:
    row = query_one("SELECT referral_code FROM users WHERE id=?", (user_id,))
    if row and row.get("referral_code"):
        return row["referral_code"]
    code = _gen_code()
    execute("UPDATE users SET referral_code=? WHERE id=?", (code, user_id))
    return code


def _gen_code() -> str:
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choice(chars) for _ in range(7))
        if not query_one("SELECT 1 FROM users WHERE referral_code=?", (code,)):
            return code


def apply_referral(new_user_id: int, referral_code: str) -> bool:
    """Yangi ro'yxatdan o'tgan foydalanuvchi taklif kodini kiritganda chaqiriladi.
    Faqat kim kimni taklif qilganini yozib qo'yadi — bonus bermaydi."""
    if not referral_code:
        return False
    referrer = query_one("SELECT * FROM users WHERE referral_code=?", (referral_code.strip().upper(),))
    if not referrer or referrer["id"] == new_user_id:
        return False
    existing = query_one("SELECT 1 FROM referrals WHERE referred_id=?", (new_user_id,))
    if existing:
        return False
    execute("UPDATE users SET referred_by=? WHERE id=?", (referrer["id"], new_user_id))
    execute("INSERT INTO referrals (referrer_id, referred_id) VALUES (?,?)", (referrer["id"], new_user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (referrer["id"], "Yangi taklif!",
             "Sizning taklif havolangiz orqali yangi foydalanuvchi ro'yxatdan o'tdi.", "success"))
    return True


def get_referral_stats(user_id: int) -> dict:
    total = query_one("SELECT COUNT(*) c FROM referrals WHERE referrer_id=?", (user_id,))["c"]
    referred_users = query_all(
        """SELECT u.ism, u.familiya, u.custom_id, r.created_at
           FROM referrals r JOIN users u ON u.id = r.referred_id
           WHERE r.referrer_id=? ORDER BY r.created_at DESC""",
        (user_id,)
    )
    # Reyting (top elchi)
    leaderboard = query_all(
        """SELECT u.ism, u.familiya, u.custom_id, COUNT(r.id) as total_invites
           FROM referrals r JOIN users u ON u.id = r.referrer_id
           GROUP BY u.id ORDER BY total_invites DESC LIMIT 10"""
    )
    return {"total": total, "referred_users": referred_users, "leaderboard": leaderboard}
