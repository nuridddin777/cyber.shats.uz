# ============================================================
# EDU ADMIN AUTH — Asosiy SHATS CYBER admin'dan BUTUNLAY MUSTAQIL
# ============================================================
# v33'dan boshlab: "Edu qismini butunlay Edu adminga yuklaymiz — hammasi
# alohida bo'ladi" talabiga ko'ra, Edu (tashkilotlar/tariflar/Edu G'aznasi)
# ENDI asosiy `users` jadvalidagi admin/super_admin orqali emas, alohida
# `edu_admins` jadvalidagi MUSTAQIL hisob orqali boshqariladi.
#
# Standart hisob: shatsadmin@edu / edu19199655
# (birinchi kirishdan keyin parolni albatta almashtirish tavsiya etiladi —
# qarang: /edu2/admin/change-password)

from functools import wraps
from flask import session, redirect, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash
from db import query_one, execute


def get_edu_admin_by_email(email: str):
    return query_one("SELECT * FROM edu_admins WHERE email=?", (email.strip().lower(),))


def get_edu_admin(admin_id: int):
    return query_one("SELECT * FROM edu_admins WHERE id=?", (admin_id,))


def verify_edu_admin_login(email: str, password: str):
    """Login+parolni tekshiradi. Muvaffaqiyatli bo'lsa admin qatorini,
    aks holda None qaytaradi."""
    admin = get_edu_admin_by_email(email)
    if not admin or not admin["is_active"]:
        return None
    if not check_password_hash(admin["password_hash"], password):
        return None
    execute("UPDATE edu_admins SET last_login_at=datetime('now') WHERE id=?", (admin["id"],))
    return admin


def change_edu_admin_password(admin_id: int, new_password: str):
    execute("UPDATE edu_admins SET password_hash=? WHERE id=?",
            (generate_password_hash(new_password), admin_id))


def edu_admin_required(f):
    """Faqat `edu_admins` jadvalidagi MUSTAQIL Edu admin hisobi (asosiy
    SHATS CYBER admin/super_admin EMAS) Edu boshqaruv panellariga
    (tashkilotlar, tariflar, Edu G'aznasi, faollashtirish kalitlari) kira oladi."""
    @wraps(f)
    def decorated(*args, **kwargs):
        admin_id = session.get("edu_admin_id")
        if not admin_id:
            return redirect(url_for("edu_orgs.edu_admin_login_page"))
        admin = get_edu_admin(admin_id)
        if not admin or not admin["is_active"]:
            session.pop("edu_admin_id", None)
            return redirect(url_for("edu_orgs.edu_admin_login_page"))
        return f(*args, **kwargs)
    return decorated


def is_unified_admin(user: dict) -> bool:
    """Eski shablonlar bilan moslik uchun saqlangan — endi Edu ruxsatini
    ANIQLASHDA ishlatilmaydi (buning o'rniga sessiyadagi edu_admin_id
    tekshiriladi), faqat boshqa umumiy ko'rsatish maqsadlari uchun qoldi."""
    return bool(user and user.get("role") in ("admin", "super_admin"))
