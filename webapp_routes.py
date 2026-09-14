# ============================================================
# CYBER SHATS — Telegram Mini App (WebApp) API
# ============================================================
# DIQQAT: bu — botning O'ZINI (chat orqali CODE/tarif/kurs sotib
# olish, chek yuklash, profil ulash va h.k.) ILOVA SIFATIDA qayta
# quradi. Saytga (asosiy Flask sahifalariga) HECH QANDAY yo'naltirish
# YO'Q — barcha amallar shu ilova ICHIDA, o'z API'lari orqali sodir
# bo'ladi. Har bir so'rov initData orqali tekshiriladi.
import os
import time
import uuid
from flask import Blueprint, request, jsonify, render_template
from db import query_one, query_all, execute
from webapp_auth import verify_init_data

webapp_bp = Blueprint("webapp", __name__)

PAYMENT_CARD = "4916 9903 5863 3797 (Q.TEMUROV)"
RECEIPT_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "static", "webapp_receipts")


def _get_tg_user():
    """initData'ni tekshiradi, ICHIDAGI Telegram foydalanuvchi ma'lumotini
    (id, first_name va h.k.) qaytaradi — sayt akkauntiga ulanmagan bo'lsa
    ham qaytaradi (profil ulash ekrani uchun kerak)."""
    init_data = request.headers.get("X-Telegram-Init-Data") or request.args.get("initData") or ""
    return verify_init_data(init_data)


def _get_linked_site_user():
    """initData tekshirilgach, ULANGAN sayt foydalanuvchisini qaytaradi.
    Ulanmagan bo'lsa None."""
    tg_user = _get_tg_user()
    if not tg_user:
        return None
    link = query_one(
        "SELECT linked_user_id FROM telegram_users WHERE chat_id=? AND linked_user_id IS NOT NULL",
        (tg_user["id"],)
    )
    if not link:
        return None
    return query_one("SELECT * FROM users WHERE id=?", (link["linked_user_id"],))


def _ensure_tg_user_row(tg_user):
    """telegram_users jadvalida shu foydalanuvchi uchun qator borligini
    kafolatlaydi (bot orqali /start bosmagan, lekin to'g'ridan-to'g'ri
    ilovani ochgan odam uchun ham kerak)."""
    existing = query_one("SELECT id FROM telegram_users WHERE chat_id=?", (tg_user["id"],))
    if not existing:
        execute(
            "INSERT INTO telegram_users (chat_id, first_name, last_name, username, language) "
            "VALUES (?,?,?,?,?)",
            (tg_user["id"], tg_user.get("first_name", ""), tg_user.get("last_name", ""),
             tg_user.get("username", ""), tg_user.get("language_code", "uz"))
        )


@webapp_bp.route("/webapp")
def webapp_shell():
    return render_template("webapp/shell.html")


# =================================================================
# PROFIL
# =================================================================
@webapp_bp.route("/api/webapp/profile")
def webapp_profile():
    user = _get_linked_site_user()
    if not user:
        return jsonify({"ok": False, "error": "not_linked",
                        "message": "Profilingiz ulanmagan."}), 401
    plan_labels = {"pro": "PRO", "cyber_pro": "CYBER PRO", "vip": "SHATS VIP", "hacker": "MAXSUS", "admin": "ADMIN", "free": "FREE"}
    rate_row = query_one("SELECT value FROM pricing_settings WHERE key='code_to_som_rate'")
    rate = int(rate_row["value"]) if rate_row else 10000
    return jsonify({
        "ok": True,
        "user": {
            "ism": user["ism"], "familiya": user["familiya"], "custom_id": user["custom_id"],
            "code_balance": user["code_balance"], "code_balance_som": user["code_balance"] * rate,
            "plan": plan_labels.get(user["plan"], "FREE"), "level": user["level"], "xp": user["xp"],
        }
    })


@webapp_bp.route("/api/webapp/link-profile", methods=["POST"])
def webapp_link_profile():
    """Bot'dagi 'Profil ulash' (ID+email) oqimining ILOVA versiyasi —
    bitta so'rovda ikkalasini ham tekshiradi.

    XAVFSIZLIK: bot tarafidagi bilan BIR XIL urinishlar cheklovi —
    15 daqiqada 5 tadan ortiq noto'g'ri urinish bloklanadi."""
    tg_user = _get_tg_user()
    if not tg_user:
        return jsonify({"ok": False, "message": "Telegram autentifikatsiyasi muvaffaqiyatsiz."}), 401

    import time as _time
    import json as _json
    attempt_key = f"link_attempts_{tg_user['id']}"
    raw = query_one("SELECT value FROM bot_state WHERE key=?", (attempt_key,))
    now = _time.time()
    if raw:
        try:
            saved = _json.loads(raw["value"])
            count, since = saved["count"], saved["since"]
            if now - since > 900:
                count, since = 0, now
        except Exception:
            count, since = 0, now
    else:
        count, since = 0, now

    if count >= 5:
        wait_min = max(1, int((900 - (now - since)) / 60))
        return jsonify({"ok": False, "message": f"Juda ko'p noto'g'ri urinish. {wait_min} daqiqadan so'ng qayta urinib ko'ring."}), 429

    def _bump_attempt(new_count, new_since):
        execute("INSERT INTO bot_state (key,value,updated_at) VALUES (?,?,datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
                (attempt_key, _json.dumps({"count": new_count, "since": new_since})))

    data = request.json or {}
    custom_id = (data.get("custom_id") or "").strip().lstrip("#")
    email = (data.get("email") or "").strip().lower()
    if not custom_id or not email:
        return jsonify({"ok": False, "message": "ID va email kiritilishi shart."})

    site_user = query_one("SELECT id, email, custom_id FROM users WHERE custom_id=?", (custom_id,))
    if not site_user and custom_id.isdigit():
        site_user = query_one("SELECT id, email, custom_id FROM users WHERE id=?", (int(custom_id),))
    if not site_user:
        _bump_attempt(count + 1, since)
        return jsonify({"ok": False, "message": "Bu ID saytda topilmadi."})
    if (site_user["email"] or "").strip().lower() != email:
        _bump_attempt(count + 1, since)
        return jsonify({"ok": False, "message": "Email mos kelmadi."})

    _bump_attempt(0, now)

    _ensure_tg_user_row(tg_user)
    execute(
        "UPDATE telegram_users SET linked_user_id=?, linked_custom_id=? WHERE chat_id=?",
        (site_user["id"], site_user["custom_id"], tg_user["id"])
    )
    return jsonify({"ok": True, "message": "Profil muvaffaqiyatli ulandi!"})


# =================================================================
# CODE SOTIB OLISH
# =================================================================
@webapp_bp.route("/api/webapp/code-packages")
def webapp_code_packages():
    rows = query_all("SELECT key, value FROM pricing_settings WHERE key LIKE 'bot_code_pkg_%'")
    rate_row = query_one("SELECT value FROM pricing_settings WHERE key='code_to_som_rate'")
    rate = int(rate_row["value"]) if rate_row else 10000
    defaults = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
    packages = [{"code": n, "price_som": n * rate} for n in defaults]
    return jsonify({"ok": True, "packages": packages})


@webapp_bp.route("/api/webapp/purchase/code", methods=["POST"])
def webapp_purchase_code():
    return _create_request_with_receipt("code")


# =================================================================
# TARIF SOTIB OLISH
# =================================================================
@webapp_bp.route("/api/webapp/pricing")
def webapp_pricing():
    """DIQQAT (tuzatilgan xato): avval bu yerda 'tarif_{plan}_uzs' degan
    KALITLAR ishlatilgan edi — lekin bular bazada UMUMAN mavjud emas edi
    (bot esa 'bot_tariff_price_{plan}' kalitini ishlatadi)! Natijada
    Mini App har doim o'zining standart (hardcoded) qiymatlarini
    ko'rsatib, BOT bilan har xil narx chiqarardi. Endi ikkalasi ham
    AYNAN BIR XIL kalitdan o'qiydi — narxlar hech qachon farqlanmaydi."""
    rows = {r["key"]: r["value"] for r in query_all(
        "SELECT key, value FROM pricing_settings WHERE key LIKE '%_price_code' OR key LIKE 'bot_tariff_price_%'")}
    plans = [
        {"key": "pro", "label": "PRO", "price_code": int(rows.get("pro_price_code", 3)),
         "price_uzs": int(rows.get("bot_tariff_price_pro", 30000)), "icon": "⭐"},
        {"key": "cyber_pro", "label": "CYBER PRO", "price_code": int(rows.get("cyber_pro_price_code", 7)),
         "price_uzs": int(rows.get("bot_tariff_price_cyber_pro", 70000)), "icon": "👑"},
        {"key": "vip", "label": "SHATS VIP", "price_code": int(rows.get("vip_price_code", 15)),
         "price_uzs": int(rows.get("bot_tariff_price_vip", 150000)), "icon": "🔥"},
        {"key": "hacker", "label": "MAXSUS", "price_code": int(rows.get("hacker_price_code", 27)),
         "price_uzs": int(rows.get("bot_tariff_price_hacker", 270000)), "icon": "⚡"},
    ]
    return jsonify({"ok": True, "plans": plans})


@webapp_bp.route("/api/webapp/purchase/tariff", methods=["POST"])
def webapp_purchase_tariff():
    return _create_request_with_receipt("tariff")


# =================================================================
# KURS SOTIB OLISH
# =================================================================
@webapp_bp.route("/api/webapp/courses")
def webapp_courses():
    rows = query_all(
        """SELECT c.id, c.title, c.subtitle, c.code_price, d.name_uz as direction_name
           FROM courses c JOIN directions d ON d.id = c.direction_id
           WHERE c.is_active=1 AND c.code_price > 0
           ORDER BY d.sort_order, c.id LIMIT 60"""
    )
    return jsonify({"ok": True, "courses": [dict(r) for r in rows]})


@webapp_bp.route("/api/webapp/purchase/course", methods=["POST"])
def webapp_purchase_course():
    return _create_request_with_receipt("course")


# =================================================================
# UMUMIY: SO'ROV YARATISH + CHEK YUKLASH (barcha xarid turlari uchun)
# =================================================================
def _create_request_with_receipt(request_type):
    """CODE/tarif/kurs — barchasi uchun bitta umumiy funksiya: sayt
    foydalanuvchisi tekshiriladi, chek rasmi (agar bo'lsa) saqlanadi,
    bot_purchase_requests jadvaliga yoziladi — XUDDI bot orqali chek
    yuklanganidagi kabi, G'azna/Admin panelida ko'rinadi."""
    user = _get_linked_site_user()
    if not user:
        return jsonify({"ok": False, "message": "Profilingiz ulanmagan."}), 401
    tg_user = _get_tg_user()

    code_amount = int(request.form.get("code_amount", 0) or 0)
    price_uzs = int(request.form.get("price_uzs", 0) or 0)
    plan = request.form.get("plan", "")
    course_ids = request.form.get("course_ids", "")

    receipt_path = None
    file = request.files.get("receipt")
    if file and file.filename:
        os.makedirs(RECEIPT_UPLOAD_DIR, exist_ok=True)
        ext = os.path.splitext(file.filename)[1] or ".jpg"
        fname = f"{user['id']}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
        full_path = os.path.join(RECEIPT_UPLOAD_DIR, fname)
        file.save(full_path)
        receipt_path = f"/static/webapp_receipts/{fname}"
    else:
        return jsonify({"ok": False, "message": "Chek rasmi yuklanmadi."})

    rid = execute(
        """INSERT INTO bot_purchase_requests
           (chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json, plan,
            target_custom_id, site_user_id, receipt_file_path, source, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'webapp','pending')""",
        (tg_user["id"] if tg_user else None, tg_user["id"] if tg_user else None,
         request_type, code_amount, price_uzs, course_ids, plan,
         user["custom_id"], user["id"], receipt_path)
    )

    try:
        import group_reports
        if request_type == "code":
            group_reports.report_code_purchase(user["id"], code_amount, price_uzs)
    except Exception:
        pass

    return jsonify({"ok": True, "message": "So'rovingiz yuborildi! G'azna tekshirib, tasdiqlaydi.",
                    "request_id": rid})


# =================================================================
# BONUS (PROMO) KOD
# =================================================================
@webapp_bp.route("/api/webapp/redeem-promo", methods=["POST"])
def webapp_redeem_promo():
    user = _get_linked_site_user()
    if not user:
        return jsonify({"ok": False, "message": "Profilingiz ulanmagan."}), 401
    code = (request.json or {}).get("code", "").strip()
    if not code:
        return jsonify({"ok": False, "message": "Kod kiritilmagan."})
    import coins_purchase
    ok, msg = coins_purchase.redeem_promo_code(code, user["id"])
    return jsonify({"ok": ok, "message": msg})


# =================================================================
# REYTING (LEADERBOARD)
# =================================================================
@webapp_bp.route("/api/webapp/leaderboard")
def webapp_leaderboard():
    rows = query_all(
        """SELECT familiya, ism, level, xp FROM users
           WHERE role='student' ORDER BY xp DESC LIMIT 10""")
    return jsonify({"ok": True, "leaders": [dict(r) for r in rows]})


# =================================================================
# MENING SO'ROVLARIM (xarid tarixi holati)
# =================================================================
@webapp_bp.route("/api/webapp/my-requests")
def webapp_my_requests():
    user = _get_linked_site_user()
    if not user:
        return jsonify({"ok": False, "message": "Profilingiz ulanmagan."}), 401
    rows = query_all(
        """SELECT id, request_type, code_amount, price_uzs, plan, status, created_at
           FROM bot_purchase_requests WHERE site_user_id=? ORDER BY created_at DESC LIMIT 15""",
        (user["id"],)
    )
    return jsonify({"ok": True, "requests": [dict(r) for r in rows]})
