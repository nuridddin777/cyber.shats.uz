# ============================================================
# CYBER SHATS — Autentifikatsiya yordamchilari (session asosida)
# ============================================================
from functools import wraps
from flask import session, redirect, url_for, request, flash, jsonify
from db import query_one, execute


def get_current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        return None
    # XAVFSIZLIK (MUHIM TUZATISH): bu funksiya HAR BIR sahifada (hatto
    # bosh sahifada ham, agar tizimga kirgan bo'lsangiz) chaqiriladi —
    # chunki app.py'dagi global context_processor shuni qiladi. Agar
    # server hali eski bazada ishlab tursa (login_streak, last_login_date
    # kabi ustunlar hali qo'shilmagan bo'lsa — masalan migratsiya hali
    # ishga tushmagan bo'lsa), bu yerdagi xato BUTUN SAYTNI (har bir
    # tizimga kirgan foydalanuvchi uchun HAR bir sahifani) "500 Server
    # xatosi"ga olib kelardi. Endi bu ikkala tekshiruv try/except bilan
    # o'ralgan — muvaffaqiyatsiz bo'lsa, funksiya shunchaki bu
    # "bezak" imkoniyatlarini o'tkazib yuboradi, lekin asosiy
    # foydalanuvchi ma'lumotini baribir qaytaradi, sayt ISHLASHDA DAVOM
    # ETADI.
    try:
        needs_refetch = False
        if _expire_plan_if_needed(user):
            needs_refetch = True
        if _update_login_streak(user):
            needs_refetch = True
        if needs_refetch:
            user = query_one("SELECT * FROM users WHERE id=?", (uid,))  # yangilangan holatni qayta o'qish
    except Exception as e:
        import logging
        logging.getLogger("cybershats").error(
            f"get_current_user() qo'shimcha tekshiruvlarida xato (sayt baribir ishlayveradi): {e}")
    return user


def _update_login_streak(user) -> bool:
    """Kunlik faollik ketma-ketligi (streak) — har KUN birinchi marta
    saytga kirganda +1 qo'shiladi. Agar bir kun o'tkazib yuborilsa —
    streak 1ga qaytadi (yangidan boshlanadi). Qaytaradi: True — agar
    bazada haqiqatan ham yangilangan bo'lsa (chaqiruvchi qayta o'qishi kerak)."""
    import datetime as _dt
    today = _dt.date.today().isoformat()
    if user["last_login_date"] == today:
        return False  # bugun allaqachon hisoblangan
    yesterday = (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    if user["last_login_date"] == yesterday:
        new_streak = (user["login_streak"] or 0) + 1
    else:
        new_streak = 1
    execute("UPDATE users SET login_streak=?, last_login_date=? WHERE id=?", (new_streak, today, user["id"]))
    return True


def _expire_plan_if_needed(user) -> bool:
    """HAQIQIY sana/vaqt asosida — foydalanuvchi tarifi (Pro/Cyber Pro/VIP/
    MAXSUS) muddati o'tgan bo'lsa, DARHOL (foydalanuvchi saytga har safar
    kirganda, shu funksiya orqali) 'free'ga avtomatik tushiriladi. Avval
    plan_expires_at faqat YOZILAR edi, lekin HECH QAYERDA tekshirilmasdi —
    shuning uchun 1 oy o'tsa ham tarif "abadiy" qolib ketardi.
    Qaytaradi: True — agar tarif haqiqatan ham tugatilgan bo'lsa (chaqiruvchi
    foydalanuvchi ma'lumotini qayta o'qishi kerak)."""
    if user["plan"] in ("free", None):
        return False
    if not user["plan_expires_at"]:
        return False
    row = query_one(
        "SELECT 1 AS expired FROM users WHERE id=? AND datetime(plan_expires_at) < datetime('now')",
        (user["id"],)
    )
    if row:
        old_plan = user["plan"]
        execute("UPDATE users SET plan='free', plan_expires_at=NULL WHERE id=?", (user["id"],))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "Tarif muddati tugadi",
                 f"{old_plan.upper()} tarifingiz muddati tugadi, hisobingiz FREE tarifga o'tkazildi. "
                 f"Davom etish uchun qayta sotib oling.", "warn"))
        return True
    return False


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Davom etish uchun avval tizimga kiring.", "warn")
            return redirect(url_for("login", next=request.path))
        user = get_current_user()
        if not user or user["is_blocked"]:
            session.clear()
            flash("Hisobingiz bloklangan yoki topilmadi.", "error")
            return redirect(url_for("login"))
        if not user.get("email_verified") and request.endpoint not in (
            "verify_email", "verify_email_resend", "logout"
        ):
            flash("Davom etishdan oldin emailingizni tasdiqlang.", "warn")
            return redirect(url_for("verify_email"))
        # O'quvchi (student) hali o'ziga IT yo'nalishini tanlamagan bo'lsa —
        # platformaning qolgan qismiga (kurslar, dashboard va h.k.) kirish
        # yopiq: avval /choose-direction orqali BITTA asosiy yo'nalish
        # tanlashi shart. Admin/mentor/o'qituvchi/g'aznachi kabi rollarga
        # tegmaydi — faqat oddiy o'quvchilar uchun.
        if (user.get("role") == "student" and not user.get("primary_direction_id")
                and request.endpoint not in (
                    "choose_direction", "verify_email", "verify_email_resend", "logout"
                )):
            flash("Davom etishdan oldin o'zingizga mos IT yo'nalishini tanlang.", "warn")
            return redirect(url_for("choose_direction"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = get_current_user()
        if not user or user["role"] not in ("admin", "mentor", "super_admin"):
            flash("Bu sahifa faqat administratorlar uchun.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def super_admin_required(view):
    """Faqat super_admin kira oladigan sahifalar/amallar uchun (masalan: admin_id o'zgartirish)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        user = get_current_user()
        if not user or user["role"] != "super_admin":
            flash("Bu amal faqat Super Admin uchun ruxsat etilgan.", "error")
            return redirect(url_for("admindash_bp.admin_dashboard"))
        return view(*args, **kwargs)
    return wrapped


def api_login_required(view):
    """API endpointlar uchun — JSON xato qaytaradi, redirect qilmaydi."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify(success=False, data=None, error="Avtorizatsiya talab qilinadi", ts=None), 401
        return view(*args, **kwargs)
    return wrapped
