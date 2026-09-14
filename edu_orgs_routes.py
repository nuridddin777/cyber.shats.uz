# ============================================================
# EDU ORGS ROUTES — Edu 2.0 uchun TO'LIQ ISHLAYDIGAN Flask route'lari
# ============================================================
# Bu blueprint edu_orgs.py / advanced_labs.py / edu_treasury_bridge.py
# ichidagi biznes-logikani haqiqiy sahifalarga ulaydi:
#   - Tashkilot (Maktab/Texnikum/Markaz) ro'yxatdan o'tishi
#   - Tarif tanlash va (DEMO) faollashtirish
#   - Tashkilot/O'qituvchi/O'quvchi kirishi (bitta forma, avtomatik aniqlaydi)
#   - Tashkilot admin paneli: o'qituvchi/o'quvchi/guruh qo'shish
#   - O'qituvchi va o'quvchi shaxsiy panellari
#   - Platforma admin (SHATS CYBER admin/super_admin) — barcha tashkilotlar
#     ro'yxati va G'aznadan coin chiqarish
#
# DIQQAT (DEMO cheklovlar, aniq belgilangan):
#   - Tarifni sotib olish HAQIQIY: narx (edu_tariffs.price_coins) tashkilot
#     coin balansidan yechiladi (yoki G'aznadan berilgan 9 xonali faollashtirish
#     kaliti bilan bepul ochiladi). Qarang: edu_orgs.py -> activate_organization_tariff.
#   - Coin top-up hozircha DEMO tugma orqali (haqiqiy to'lov integratsiyasi
#     keyingi bosqich) — G'azna admin panelidan CODE chiqarish esa haqiqiy.

from functools import wraps
import hmac
import os
import re
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, current_app

from db import get_db
from auth import get_current_user
from edu_orgs import (
    EduOrgError, register_organization, activate_organization_tariff,
    register_teacher, register_student, get_org_tariff, check_can_add_teacher,
    check_can_add_student, can_send_free_gift, check_and_expire_subscription,
    create_school_classes, create_texnikum_course, resolve_class_code, list_org_classes,
)
import edu_email_verify
from edu_treasury_bridge import (
    get_unified_fund_balance, issue_coins_to_org, execute_coin_transfer,
    create_org_purchase_request, get_org_purchase_requests,
)
from advanced_labs import list_labs_for_org
from edu_admin_auth import edu_admin_required
import coins_purchase
from pricing import get_price
import edu_curriculum

EDU_RECEIPT_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
EDU_RECEIPT_UPLOAD_DIR = os.path.join("static", "uploads", "receipts")


def _save_receipt_file(file_storage):
    """Chek rasmi/faylini xavfsiz saqlaydi: kengaytma whitelist + tasodifiy
    (UUID) fayl nomi — path-traversal va zararli fayl yuklashning oldini oladi
    (asosiy saytdagi _save_receipt_file bilan bir xil xavfsizlik naqshi)."""
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in EDU_RECEIPT_ALLOWED_EXT:
        return None
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(EDU_RECEIPT_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(EDU_RECEIPT_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    return f"/static/uploads/receipts/{safe_name}"

edu_orgs_bp = Blueprint("edu_orgs", __name__, url_prefix="/edu2")


# ------------------------------------------------------------------
# CSRF HIMOYASI
# ------------------------------------------------------------------
# XAVFSIZLIK: bu blueprintdagi barcha amallar (o'qituvchi/o'quvchi qo'shish,
# coin o'tkazish, tarif faollashtirish va h.k.) holatni o'zgartiradigan
# POST so'rovlar. CSRF tokensiz, boshqa saytdan yashirin forma orqali
# tashkilot adminining sessiyasidan foydalanib beixtiyor amal
# bajartirilishi mumkin edi. Shu sabab har bir sessiya uchun tasodifiy
# token generatsiya qilinadi va har bir POST so'rovda tekshiriladi.
def _get_csrf_token():
    if "edu2_csrf" not in session:
        import secrets
        session["edu2_csrf"] = secrets.token_hex(24)
    return session["edu2_csrf"]


@edu_orgs_bp.context_processor
def _inject_csrf():
    return {"csrf_token": _get_csrf_token()}


# ------------------------------------------------------------------
# PWA — "Ilovani telefonga o'rnatish" (manifest + service worker)
# ------------------------------------------------------------------
# sw.js ATAYLAB /edu2/sw.js manzilida beriladi (static/ ichida emas) —
# Service Worker qamrovi (scope) fayl joylashgan manzilga bog'liq bo'lgani
# uchun shunda avtomatik butun /edu2/ bo'limini qamraydi.
@edu_orgs_bp.route("/sw.js")
def edu_service_worker():
    from flask import send_file, Response
    resp = send_file(os.path.join(current_app.root_path, "static", "edu-sw.js"))
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/edu2/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@edu_orgs_bp.route("/manifest.json")
def edu_manifest():
    from flask import send_file
    resp = send_file(os.path.join(current_app.root_path, "static", "edu-manifest.json"))
    resp.headers["Content-Type"] = "application/manifest+json"
    return resp


# ------------------------------------------------------------------
# XAVFSIZLIK SARLAVHALARI (barcha Edu javoblariga qo'llanadi)
# ------------------------------------------------------------------
@edu_orgs_bp.after_request
def _security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return resp


@edu_orgs_bp.before_request
def _check_csrf():
    if request.method == "POST":
        sent = request.form.get("csrf_token", "")
        expected = session.get("edu2_csrf", "")
        if not expected or not sent or not hmac.compare_digest(sent, expected):
            from flask import abort
            abort(403)


@edu_orgs_bp.before_request
def _check_subscription_expiry():
    """1 oylik/1 yillik (yoki istalgan necha oylik) tarif muddati tugagan
    tashkilotni avtomatik 'Faol emas' holatiga o'tkazadi."""
    org_id = session.get("edu_org_id")
    if org_id:
        check_and_expire_subscription(get_db(), org_id)


_EMAIL_VERIFY_EXEMPT_ENDPOINTS = {
    "edu_orgs.verify_email_page", "edu_orgs.verify_email_resend",
    "edu_orgs.logout", "edu_orgs.login_page",
}


@edu_orgs_bp.before_request
def _check_org_email_verified():
    """Email tasdiqlanmagan tashkilotni /verify-email sahifasiga yo'naltiradi."""
    if session.get("edu_role") != "org" or not session.get("edu_org_id"):
        return
    if request.endpoint in _EMAIL_VERIFY_EXEMPT_ENDPOINTS:
        return
    conn = get_db()
    org = conn.execute(
        "SELECT email_verified FROM edu_organizations WHERE id=?", (session["edu_org_id"],)
    ).fetchone()
    if org and not org["email_verified"]:
        return redirect(url_for("edu_orgs.verify_email_page"))


# ------------------------------------------------------------------
# Session yordamchilari (edu_organizations/teachers/students `users`
# jadvalida emas, shuning uchun ALOHIDA session kalitlari ishlatiladi)
# ------------------------------------------------------------------
def _current_org_id():
    return session.get("edu_org_id")


def _current_role():
    return session.get("edu_role")  # 'org' | 'teacher' | 'student'


def edu2_login_required(f):
    @wraps(f)
    def decorated(*a, **kw):
        if not session.get("edu_org_id"):
            return redirect(url_for("edu_orgs.login_page"))
        return f(*a, **kw)
    return decorated


def edu2_org_only(f):
    @wraps(f)
    def decorated(*a, **kw):
        if session.get("edu_role") != "org":
            flash("Bu sahifa faqat tashkilot admini uchun.", "error")
            return redirect(url_for("edu_orgs.dashboard"))
        return f(*a, **kw)
    return decorated


# ------------------------------------------------------------------
# 1) Tashkilot ro'yxatdan o'tishi
# ------------------------------------------------------------------
@edu_orgs_bp.route("/api/districts/<int:region_id>")
def api_districts_by_region(region_id):
    """Ro'yxatdan o'tish formasidagi 'Viloyat -> Tuman' kaskad tanlovi uchun
    JSON qaytaradi. Faqat o'qish (GET, ma'lumot o'zgartirmaydi) — login talab
    qilinmaydi, chunki ro'yxatdan o'tishdan OLDIN chaqiriladi."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name FROM districts WHERE region_id=? ORDER BY name", (region_id,)
    ).fetchall()
    return jsonify([{"id": r["id"], "name": r["name"]} for r in rows])


@edu_orgs_bp.route("/register-org", methods=["GET", "POST"])
def register_org_page():
    conn = get_db()
    regions = conn.execute("SELECT id, name FROM regions ORDER BY name").fetchall()
    districts = conn.execute(
        "SELECT d.id, d.name, r.name as region_name FROM districts d "
        "JOIN regions r ON r.id=d.region_id ORDER BY r.name, d.name"
    ).fetchall()

    if request.method == "GET":
        return render_template("edu_orgs/register_org.html", regions=regions, districts=districts, error=None)

    try:
        org_type = request.form.get("org_type", "").strip()
        name = request.form.get("name", "").strip()
        region_id = request.form.get("region_id", type=int)
        district_id = request.form.get("district_id", type=int)
        phone = request.form.get("phone", "").strip()
        login = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip()
        telegram_user = request.form.get("telegram_user", "").strip()

        if not name or not login or not password:
            raise EduOrgError("Nomi, login va parol majburiy")
        if len(password) < 6:
            raise EduOrgError("Parol kamida 6 ta belgidan iborat bo'lishi kerak")
        if not region_id or not district_id:
            raise EduOrgError("Viloyat va tumanni tanlash majburiy")
        if not phone or not phone.startswith("+998") or len(phone) != 13 or not phone[1:].isdigit():
            raise EduOrgError("Telefon raqam +998XXXXXXXXX formatida bo'lishi shart (9 ta raqam)")
        if not email or "@" not in email:
            raise EduOrgError("Email majburiy — unga tasdiqlash kodi yuboriladi")

        org_id = register_organization(
            conn, org_type, name, region_id, district_id, phone, login, password,
            email=email, telegram_user=telegram_user,
        )
        org = conn.execute("SELECT username FROM edu_organizations WHERE id=?", (org_id,)).fetchone()

        session.clear()
        session["edu_org_id"] = org_id
        session["edu_role"] = "org"

        edu_email_verify.send_verification_code(org_id, email, name)
        flash(f"Ro'yxatdan muvaffaqiyatli o'tdingiz! Tashkilot manzili: @{org['username']}. "
              f"Emailingizga tasdiqlash kodi yuborildi.", "success")
        return redirect(url_for("edu_orgs.verify_email_page"))

    except EduOrgError as e:
        return render_template("edu_orgs/register_org.html", regions=regions, districts=districts, error=str(e))


# ------------------------------------------------------------------
# 2) Tarif tanlash va (DEMO) faollashtirish
# ------------------------------------------------------------------
@edu_orgs_bp.route("/tariffs", methods=["GET"])
@edu2_login_required
@edu2_org_only
def tariffs_page():
    conn = get_db()
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (_current_org_id(),)).fetchone()
    tariffs = conn.execute("SELECT * FROM edu_tariffs WHERE org_type=?", (org["org_type"],)).fetchall()
    return render_template("edu_orgs/tariffs.html", org=org, tariffs=tariffs)


@edu_orgs_bp.route("/tariffs/activate", methods=["POST"])
@edu2_login_required
@edu2_org_only
def activate_tariff():
    conn = get_db()
    tarif_code = request.form.get("tarif_code")
    months = request.form.get("months", "1")
    try:
        months = int(months)
    except ValueError:
        months = 1
    months = max(1, min(months, 60))
    try:
        activate_organization_tariff(conn, _current_org_id(), tarif_code, months=months)
        flash(f"'{tarif_code}' tarifi {months} oyga muvaffaqiyatli sotib olindi va faollashtirildi!", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for("edu_orgs.dashboard"))


# ------------------------------------------------------------------
# 3) Kirish (Tashkilot / O'qituvchi / O'quvchi — bitta forma)
# ------------------------------------------------------------------
@edu_orgs_bp.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template("edu_orgs/login.html", error=None)

    from werkzeug.security import check_password_hash
    from security import is_ip_blocked, block_ip, log_security_event
    from db import query_one

    ip = request.remote_addr or "unknown"
    ua = request.headers.get("User-Agent", "")

    # --- Brute-force himoyasi: mavjud SHATS CYBER IP-bloklash tizimidan
    # foydalanamiz (blocked_ips/security_events jadvallari — butun sayt
    # uchun umumiy, shuning uchun edu login ham asosiy login bilan bir xil
    # himoyaga ega bo'ladi).
    if is_ip_blocked(ip):
        return render_template("edu_orgs/login.html", error="Bu IP manzil bloklangan. Keyinroq urinib ko'ring.")

    conn = get_db()
    login_input = request.form.get("login", "").strip().lower()
    password = request.form.get("password", "")

    def _fail():
        log_security_event(None, "edu_failed_login", ip, ua, f"login:{login_input}", "medium")
        recent = query_one(
            "SELECT COUNT(*) c FROM security_events WHERE event_type='edu_failed_login' "
            "AND ip=? AND created_at > datetime('now', '-15 minutes')",
            (ip,)
        )
        if recent and recent["c"] >= 5:
            block_ip(ip, "edu_brute_force", duration_hours=1)
        return render_template("edu_orgs/login.html", error="Login yoki parol noto'g'ri")

    # Avval tashkilot logini (o'z login maydoni, @ belgisisiz) sifatida tekshiramiz
    org = conn.execute("SELECT * FROM edu_organizations WHERE login=?", (login_input,)).fetchone()
    if org and check_password_hash(org["password_hash"], password):
        session.clear()
        session["edu_org_id"] = org["id"]
        session["edu_role"] = "org"
        return redirect(url_for("edu_orgs.dashboard"))

    # Bo'lmasa, o'qituvchi yoki o'quvchi full_login (login@tashkilot) sifatida tekshiramiz
    teacher = conn.execute("SELECT * FROM edu_teachers WHERE full_login=?", (login_input,)).fetchone()
    if teacher and check_password_hash(teacher["password_hash"], password):
        session.clear()
        session["edu_org_id"] = teacher["org_id"]
        session["edu_role"] = "teacher"
        session["edu_teacher_id"] = teacher["id"]
        return redirect(url_for("edu_orgs.dashboard"))

    student = conn.execute("SELECT * FROM edu_students WHERE full_login=?", (login_input,)).fetchone()
    if student and check_password_hash(student["password_hash"], password):
        session.clear()
        session["edu_org_id"] = student["org_id"]
        session["edu_role"] = "student"
        session["edu_student_id"] = student["id"]
        return redirect(url_for("edu_orgs.dashboard"))

    return _fail()


@edu_orgs_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("edu_orgs.login_page"))


# ------------------------------------------------------------------
# 3.1) Tashkilot email tasdiqlash (ro'yxatdan o'tgach)
# ------------------------------------------------------------------
@edu_orgs_bp.route("/verify-email", methods=["GET", "POST"])
def verify_email_page():
    if session.get("edu_role") != "org" or not session.get("edu_org_id"):
        return redirect(url_for("edu_orgs.login_page"))

    conn = get_db()
    org_id = session["edu_org_id"]
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        session.clear()
        return redirect(url_for("edu_orgs.login_page"))
    if org["email_verified"]:
        return redirect(url_for("edu_orgs.org_dashboard"))

    if request.method == "GET":
        return render_template("edu_orgs/verify_email.html", org=org, error=None)

    code = request.form.get("code", "").strip()
    ok, msg = edu_email_verify.verify_code(org_id, code)
    if ok:
        flash(msg, "success")
        return redirect(url_for("edu_orgs.org_dashboard"))
    return render_template("edu_orgs/verify_email.html", org=org, error=msg)


@edu_orgs_bp.route("/verify-email/resend", methods=["POST"])
def verify_email_resend():
    if session.get("edu_role") != "org" or not session.get("edu_org_id"):
        return redirect(url_for("edu_orgs.login_page"))

    conn = get_db()
    org_id = session["edu_org_id"]
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (org_id,)).fetchone()
    if not org:
        session.clear()
        return redirect(url_for("edu_orgs.login_page"))
    if org["email_verified"]:
        return redirect(url_for("edu_orgs.org_dashboard"))

    ok, msg = edu_email_verify.send_verification_code(org_id, org["email"], org["name"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("edu_orgs.verify_email_page"))


# ------------------------------------------------------------------
# 4) Umumiy dashboard — rolga qarab tegishli panelga yo'naltiradi
# ------------------------------------------------------------------
@edu_orgs_bp.route("/dashboard")
@edu2_login_required
def dashboard():
    role = _current_role()
    if role == "org":
        return redirect(url_for("edu_orgs.org_dashboard"))
    if role == "teacher":
        return redirect(url_for("edu_orgs.teacher_dashboard"))
    if role == "student":
        return redirect(url_for("edu_orgs.student_dashboard"))
    return redirect(url_for("edu_orgs.login_page"))


# ------------------------------------------------------------------
# 5) Tashkilot admin paneli
# ------------------------------------------------------------------
@edu_orgs_bp.route("/org/dashboard")
@edu2_login_required
@edu2_org_only
def org_dashboard():
    conn = get_db()
    org_id = _current_org_id()
    org = conn.execute("""
        SELECT o.*, r.name as region_name, d.name as district_name
        FROM edu_organizations o
        LEFT JOIN regions r ON r.id=o.region_id
        LEFT JOIN districts d ON d.id=o.district_id
        WHERE o.id=?
    """, (org_id,)).fetchone()
    teachers = conn.execute("SELECT * FROM edu_teachers WHERE org_id=? ORDER BY teacher_number", (org_id,)).fetchall()
    students = conn.execute("SELECT * FROM edu_students WHERE org_id=? ORDER BY student_number", (org_id,)).fetchall()
    groups = conn.execute("SELECT * FROM edu_org_groups WHERE org_id=?", (org_id,)).fetchall()
    classes = list_org_classes(conn, org_id)
    subjects = conn.execute("SELECT * FROM edu_subjects WHERE org_type=? ORDER BY sort_order", (org["org_type"],)).fetchall()

    teacher_status = tarif_error = None
    student_status = None
    try:
        can_t, cost_t, reason_t = check_can_add_teacher(conn, org_id)
        teacher_status = {"can_add": can_t, "cost": cost_t, "reason": reason_t}
        can_s, cost_s, reason_s = check_can_add_student(conn, org_id, count=1)
        student_status = {"can_add": can_s, "cost": cost_s, "reason": reason_s}
    except EduOrgError as e:
        tarif_error = str(e)

    labs, labs_reason = ([], "")
    if not tarif_error:
        try:
            labs, labs_reason = list_labs_for_org(conn, org_id)
        except EduOrgError as e:
            labs_reason = str(e)

    return render_template(
        "edu_orgs/org_dashboard.html", org=org, teachers=teachers, students=students,
        groups=groups, classes=classes, subjects=subjects, teacher_status=teacher_status,
        student_status=student_status, tarif_error=tarif_error,
        labs=labs, labs_reason=labs_reason,
        fund_balance=get_unified_fund_balance(),
    )


# ------------------------------------------------------------------
# 5.1) O'qituvchi/O'quvchi O'ZI ro'yxatdan o'tishi
# ------------------------------------------------------------------
# Texnik topshiriqqa muvofiq: O'qituvchi ham, O'quvchi ham ADMIN TOMONIDAN
# emas, O'ZI ro'yxatdan o'tadi — familiya/ism, tashkilot, fan/guruh
# tanlaydi va LOGIN/PAROLNI O'ZI kiritadi (@gmail.com emas, tizim
# @tashkilot_username qo'shadi). Shuning uchun bu yerda standart/avto
# parol MUTLAQO ishlatilmaydi — parol maydoni har doim majburiy va
# foydalanuvchining o'zi kiritgan qiymati ishlatiladi.

@edu_orgs_bp.route("/join")
def join_picker():
    """Ro'yxatdan o'tishni boshlash: o'qituvchi/o'quvchi ANIQ markazning
    ULANISH KODINI kiritadi (markaz nomini ro'yxatdan tanlash EMAS —
    shunda aniq markaz topiladi va faqat o'sha markazga ulanadi).
    Markaz hali tarif/kalit orqali faollashtirilmagan bo'lsa, bu kod
    mavjud emas — demak hech kim ulana olmaydi."""
    role = request.args.get("role", "teacher")
    if role not in ("teacher", "student"):
        role = "teacher"
    if role == "student":
        return redirect(url_for("edu_orgs.join_class_page"))
    return render_template("edu_orgs/join_picker.html", role=role, error=None)


@edu_orgs_bp.route("/join/resolve", methods=["POST"])
def join_resolve():
    """Kiritilgan ulanish kodi bo'yicha ANIQ tashkilotni topadi va
    o'qituvchi ro'yxatdan o'tish sahifasiga yo'naltiradi.
    (O'quvchilar endi /join-class orqali, sinf/kurs kodi bilan o'tadi.)"""
    conn = get_db()
    role = "teacher"
    code = request.form.get("connect_code", "").strip().upper()

    if not code:
        return render_template("edu_orgs/join_picker.html", role=role,
                                error="Ulanish kodini kiriting.")

    org = conn.execute(
        "SELECT id FROM edu_organizations WHERE connect_code=? AND is_active=1", (code,)
    ).fetchone()
    if not org:
        # Xavfsizlik: kod noto'g'ri yoki markaz hali faol emasligini bir xil
        # xabar bilan qaytaramiz — shunda tashqi odam "kod to'g'ri, faqat
        # markaz faol emas" kabi ma'lumotni kod bo'yicha qidirib bila olmaydi.
        return render_template("edu_orgs/join_picker.html", role=role,
                                error="Bunday ulanish kodi topilmadi yoki markaz hali faol emas.")

    return redirect(url_for("edu_orgs.register_teacher_page", org_id=org["id"], code=code))


@edu_orgs_bp.route("/register-teacher", methods=["GET", "POST"])
def register_teacher_page():
    conn = get_db()

    if request.method == "GET":
        org_id = request.args.get("org_id", type=int)
        code = request.args.get("code", "").strip().upper()
        if not org_id or not code:
            return redirect(url_for("edu_orgs.join_picker", role="teacher"))
        org = conn.execute(
            "SELECT * FROM edu_organizations WHERE id=? AND is_active=1 AND connect_code=?", (org_id, code)
        ).fetchone()
        if not org:
            flash("Ulanish kodi noto'g'ri yoki markaz hali faol emas (tarif sotib olinmagan).", "error")
            return redirect(url_for("edu_orgs.join_picker", role="teacher"))
        subjects = conn.execute(
            "SELECT * FROM edu_subjects WHERE org_type=? ORDER BY sort_order", (org["org_type"],)
        ).fetchall()
        regions = conn.execute("SELECT id, name FROM regions ORDER BY name").fetchall()
        districts = conn.execute(
            "SELECT d.id, d.name, r.name as region_name FROM districts d "
            "JOIN regions r ON r.id=d.region_id ORDER BY r.name, d.name"
        ).fetchall()
        return render_template("edu_orgs/register_teacher.html", org=org, subjects=subjects,
                                regions=regions, districts=districts, connect_code=code, error=None)

    # POST — o'qituvchi o'zi kiritgan ma'lumotlar bilan ro'yxatdan o'tadi.
    # DIQQAT: ulanish kodi POST'da ham QAYTA tekshiriladi — shunda org_id'ni
    # taxmin qilib (kodni bilmasdan) hech kim ro'yxatdan o'ta olmaydi.
    org_id = request.form.get("org_id", type=int)
    submitted_code = request.form.get("connect_code", "").strip().upper()
    org = conn.execute(
        "SELECT * FROM edu_organizations WHERE id=? AND is_active=1 AND connect_code=?",
        (org_id, submitted_code)
    ).fetchone()
    if not org:
        flash("Ulanish kodi noto'g'ri yoki markaz faol emas.", "error")
        return redirect(url_for("edu_orgs.join_picker", role="teacher"))

    try:
        password = request.form.get("password", "")
        if len(password) < 6:
            raise EduOrgError("Parol kamida 6 ta belgidan iborat bo'lishi kerak")
        if password != request.form.get("password_confirm", ""):
            raise EduOrgError("Parollar mos kelmadi")

        result = register_teacher(
            conn, org_id,
            request.form.get("familiya", ""), request.form.get("ism", ""),
            request.form.get("subject_id", type=int),
            request.form.get("login", ""), password,
            request.form.get("region_id", type=int), request.form.get("district_id", type=int),
        )
        flash(f"Ro'yxatdan muvaffaqiyatli o'tdingiz! Login: {result['full_login']} | ID: {result['teacher_number']}. "
              f"Endi shu login va o'zingiz kiritgan parol bilan kiring.", "success")
        return redirect(url_for("edu_orgs.login_page"))
    except EduOrgError as e:
        subjects = conn.execute(
            "SELECT * FROM edu_subjects WHERE org_type=? ORDER BY sort_order", (org["org_type"],)
        ).fetchall()
        regions = conn.execute("SELECT id, name FROM regions ORDER BY name").fetchall()
        districts = conn.execute(
            "SELECT d.id, d.name, r.name as region_name FROM districts d "
            "JOIN regions r ON r.id=d.region_id ORDER BY r.name, d.name"
        ).fetchall()
        return render_template("edu_orgs/register_teacher.html", org=org, subjects=subjects,
                                regions=regions, districts=districts, connect_code=submitted_code, error=str(e))


@edu_orgs_bp.route("/register-student", methods=["GET", "POST"])
def register_student_page():
    conn = get_db()

    if request.method == "GET":
        class_code = request.args.get("class_code", "").strip().upper()
        if class_code:
            try:
                org, group = resolve_class_code(conn, class_code)
            except EduOrgError as e:
                flash(str(e), "error")
                return redirect(url_for("edu_orgs.join_class_page"))
            regions = conn.execute("SELECT id, name FROM regions ORDER BY name").fetchall()
            districts = conn.execute(
                "SELECT d.id, d.name, r.name as region_name FROM districts d "
                "JOIN regions r ON r.id=d.region_id ORDER BY r.name, d.name"
            ).fetchall()
            return render_template("edu_orgs/register_student.html", org=org, group=group,
                                    regions=regions, districts=districts, class_code=class_code, error=None)

        # Eskicha (org-level) havola hali ham qo'llab-quvvatlanadi — lekin
        # endi guruh tanlash dropdown emas, sinf/kurs kodi kiritish talab qilinadi.
        return redirect(url_for("edu_orgs.join_class_page"))

    # POST — o'quvchi o'zi kiritgan ma'lumotlar bilan ro'yxatdan o'tadi.
    # DIQQAT: sinf/kurs kodi POST'da ham QAYTA tekshiriladi.
    class_code = request.form.get("class_code", "").strip().upper()
    try:
        org, group = resolve_class_code(conn, class_code)
    except EduOrgError as e:
        flash(str(e), "error")
        return redirect(url_for("edu_orgs.join_class_page"))

    try:
        password = request.form.get("password", "")
        if len(password) < 6:
            raise EduOrgError("Parol kamida 6 ta belgidan iborat bo'lishi kerak")
        if password != request.form.get("password_confirm", ""):
            raise EduOrgError("Parollar mos kelmadi")

        result = register_student(
            conn, org["id"],
            request.form.get("familiya", ""), request.form.get("ism", ""),
            group["id"],
            request.form.get("login", ""), password,
            request.form.get("region_id", type=int), request.form.get("district_id", type=int),
        )
        flash(f"Ro'yxatdan muvaffaqiyatli o'tdingiz! Login: {result['full_login']} | ID: {result['student_number']}. "
              f"Endi shu login va o'zingiz kiritgan parol bilan kiring.", "success")
        return redirect(url_for("edu_orgs.login_page"))
    except EduOrgError as e:
        regions = conn.execute("SELECT id, name FROM regions ORDER BY name").fetchall()
        districts = conn.execute(
            "SELECT d.id, d.name, r.name as region_name FROM districts d "
            "JOIN regions r ON r.id=d.region_id ORDER BY r.name, d.name"
        ).fetchall()
        return render_template("edu_orgs/register_student.html", org=org, group=group,
                                regions=regions, districts=districts, class_code=class_code, error=str(e))


@edu_orgs_bp.route("/org/groups/add", methods=["POST"])
@edu2_login_required
@edu2_org_only
def add_group_route():
    """Endi guruh ochish = sinf/bo'lim (maktab) yoki kurs (texnikum) tanlash.
    Har biri o'zining alohida ulanish kodiga ega bo'ladi — bu kod tashkilot
    tarifni sotib olib faollashtirgandan KEYINGINA ishlaydi (resolve_class_code)."""
    conn = get_db()
    org = _current_org_row(conn)
    subject_id = request.form.get("subject_id", type=int)

    try:
        if org["org_type"] == "texnikum":
            kurs_no = request.form.get("kurs_no", type=int)
            if not kurs_no:
                raise EduOrgError("Kursni tanlang (1 yoki 2)")
            result = create_texnikum_course(conn, org["id"], kurs_no, subject_id)
            flash(f"'{result['name']}' yaratildi! Ulanish kodi: {result['join_code']}", "success")
        else:
            grade_no = request.form.get("grade_no", type=int)
            letters_raw = request.form.get("section_letters", "").strip()
            letters = [x for x in re.split(r"[,\s]+", letters_raw) if x]
            if not grade_no:
                raise EduOrgError("Sinfni tanlang (5-11)")
            if not letters:
                raise EduOrgError("Kamida bitta bo'lim kiriting (masalan: A yoki A,B,V)")
            results = create_school_classes(conn, org["id"], grade_no, letters, subject_id)
            codes_str = ", ".join(f"{r['name']}={r['join_code']}" for r in results)
            flash(f"Yaratildi: {codes_str}", "success")
    except EduOrgError as e:
        flash(str(e), "error")

    return redirect(url_for("edu_orgs.org_dashboard"))


# ------------------------------------------------------------------
# 3.2) O'quvchi uchun SINF/KURS kodi orqali qo'shilish (yangi asosiy yo'l)
# ------------------------------------------------------------------
@edu_orgs_bp.route("/join-class", methods=["GET", "POST"])
def join_class_page():
    if request.method == "GET":
        return render_template("edu_orgs/join_class.html", error=None)

    code = request.form.get("class_code", "").strip().upper()
    try:
        org, group = resolve_class_code(get_db(), code)
    except EduOrgError as e:
        return render_template("edu_orgs/join_class.html", error=str(e))

    return redirect(url_for("edu_orgs.register_student_page", class_code=code))


@edu_orgs_bp.route("/org/treasury")
@edu2_login_required
@edu2_org_only
def org_treasury_page():
    """Markaz uchun G'azna paneli — coin balans, CODE sotib olish tarixi va
    tarif faollashtirish tarixi bir joyda ko'rsatiladi."""
    conn = get_db()
    org = _current_org_row(conn)
    purchase_requests = get_org_purchase_requests(org["id"], limit=50)
    tarif = None
    try:
        _, tarif = get_org_tariff(conn, org["id"])
    except EduOrgError:
        pass
    return render_template("edu_orgs/treasury.html", org=org, purchase_requests=purchase_requests,
                            tarif=tarif, fund_balance=get_unified_fund_balance())



@edu_orgs_bp.route("/org/buy-code", methods=["GET"])
@edu2_login_required
@edu2_org_only
def buy_code_page():
    """Markaz haqiqiy pul evaziga CODE sotib olish sahifasi: miqdor kiritadi,
    narx SHATS CYBER'dagi bilan bir xil kursda avtomatik hisoblanadi, karta
    raqamlari va admin bilan aloqa (Telegram/telefon) ko'rsatiladi, chek
    yuklanadi."""
    conn = get_db()
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (_current_org_id(),)).fetchone()
    rate = get_price("code_to_som_rate") or 10_000
    my_requests = get_org_purchase_requests(_current_org_id())
    return render_template(
        "edu_orgs/buy_code.html", org=org, rate=rate, my_requests=my_requests,
        cards=coins_purchase.PAYMENT_CARDS, card_holder=coins_purchase.CARD_HOLDER,
        admin_telegram="shedow_777", admin_phone="+998976699655",
    )


@edu_orgs_bp.route("/org/buy-code/submit", methods=["POST"])
@edu2_login_required
@edu2_org_only
def buy_code_submit():
    conn = get_db()
    org_id = _current_org_id()
    amount = request.form.get("amount", type=int) or 0
    rate = get_price("code_to_som_rate") or 10_000
    price_uzs = amount * rate

    receipt_path = None
    if "receipt" in request.files:
        receipt_path = _save_receipt_file(request.files["receipt"])
        if request.files["receipt"].filename and not receipt_path:
            flash("Fayl turi noto'g'ri. Faqat rasm (png/jpg/webp) yoki PDF qabul qilinadi.", "error")
            return redirect(url_for("edu_orgs.buy_code_page"))

    try:
        create_org_purchase_request(org_id, amount, price_uzs, receipt_path)
        flash(f"So'rov yuborildi! {amount:,} CODE ({price_uzs:,} so'm) — "
              f"G'azna tekshirib, tez orada tasdiqlaydi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for("edu_orgs.buy_code_page"))


# ------------------------------------------------------------------
# 6) O'qituvchi paneli
# ------------------------------------------------------------------
@edu_orgs_bp.route("/teacher/dashboard")
@edu2_login_required
def teacher_dashboard():
    if _current_role() != "teacher":
        return redirect(url_for("edu_orgs.dashboard"))
    conn = get_db()
    tid = session["edu_teacher_id"]
    teacher = conn.execute("""
        SELECT t.*, r.name as region_name, d.name as district_name
        FROM edu_teachers t
        LEFT JOIN regions r ON r.id=t.region_id
        LEFT JOIN districts d ON d.id=t.district_id
        WHERE t.id=?
    """, (tid,)).fetchone()
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (teacher["org_id"],)).fetchone()
    groups = conn.execute("SELECT * FROM edu_org_groups WHERE org_id=?", (teacher["org_id"],)).fetchall()
    can_gift = can_send_free_gift(conn, "teacher", tid)
    is_pro, _, _ = edu_curriculum.is_org_pro(conn, teacher["org_id"])
    return render_template("edu_orgs/teacher_dashboard.html", teacher=teacher, org=org, groups=groups,
                            can_gift=can_gift, is_pro=is_pro)


# ------------------------------------------------------------------
# 7) O'quvchi paneli
# ------------------------------------------------------------------
@edu_orgs_bp.route("/student/dashboard")
@edu2_login_required
def student_dashboard():
    if _current_role() != "student":
        return redirect(url_for("edu_orgs.dashboard"))
    conn = get_db()
    sid = session["edu_student_id"]
    student = conn.execute("""
        SELECT s.*, r.name as region_name, d.name as district_name
        FROM edu_students s
        LEFT JOIN regions r ON r.id=s.region_id
        LEFT JOIN districts d ON d.id=s.district_id
        WHERE s.id=?
    """, (sid,)).fetchone()
    org = conn.execute("SELECT * FROM edu_organizations WHERE id=?", (student["org_id"],)).fetchone()
    group = None
    if student["group_id"]:
        group = conn.execute("SELECT * FROM edu_org_groups WHERE id=?", (student["group_id"],)).fetchone()
    can_gift = can_send_free_gift(conn, "student", sid)
    is_pro, _, _ = edu_curriculum.is_org_pro(conn, student["org_id"])
    return render_template("edu_orgs/student_dashboard.html", student=student, org=org, group=group,
                            can_gift=can_gift, is_pro=is_pro)


# ------------------------------------------------------------------
# 8) Coin o'tkazmasi (o'qituvchi/o'quvchi bir-biriga, tashkilot ichida)
# ------------------------------------------------------------------
@edu_orgs_bp.route("/transfer", methods=["POST"])
@edu2_login_required
def transfer_route():
    role = _current_role()
    if role not in ("teacher", "student"):
        flash("Faqat o'qituvchi yoki o'quvchi coin o'tkaza oladi.", "error")
        return redirect(url_for("edu_orgs.dashboard"))

    conn = get_db()
    sender_id = session.get("edu_teacher_id") if role == "teacher" else session.get("edu_student_id")
    receiver_type = request.form.get("receiver_type")
    receiver_id = request.form.get("receiver_id", type=int)
    amount = request.form.get("amount", type=int) or 0
    is_gift = request.form.get("is_gift") == "1"

    try:
        result = execute_coin_transfer(
            conn, _current_org_id(), role, sender_id, receiver_type, receiver_id, amount, is_free_gift=is_gift
        )
        flash(f"{result['amount']} coin yuborildi (komissiya: {result['commission']})", "success")
    except EduOrgError as e:
        flash(str(e), "error")

    return redirect(url_for(f"edu_orgs.{role}_dashboard"))


# ------------------------------------------------------------------
# 8.1) O'quv dasturi (mundarija) — sinf/kurs mavzulari va amaliylar
# ------------------------------------------------------------------
# DIQQAT: kirish nazorati BUTUNLAY tashkilot (org) tarifiga bog'liq —
# rol (org/teacher/student) emas. Shu sababli "Markaz Pro" bo'lsa,
# shu tashkilotdagi HAMMA (o'qituvchi ham, o'quvchi ham) avtomatik
# Pro darajadagi mazmunni (5 amaliy + rasm tavsiyalari) ko'radi.
def _current_org_row(conn):
    return conn.execute("SELECT * FROM edu_organizations WHERE id=?", (_current_org_id(),)).fetchone()


@edu_orgs_bp.route("/curriculum")
@edu2_login_required
def curriculum_grades():
    conn = get_db()
    org = _current_org_row(conn)
    grades = edu_curriculum.list_grades_for_org_type(conn, org["org_type"])
    is_pro, _, tarif = edu_curriculum.is_org_pro(conn, org["id"])
    return render_template("edu_orgs/curriculum_grades.html", org=org, grades=grades,
                            is_pro=is_pro, role=_current_role())


@edu_orgs_bp.route("/curriculum/<path:grade_label>")
@edu2_login_required
def curriculum_topics(grade_label):
    conn = get_db()
    org = _current_org_row(conn)
    topics = edu_curriculum.list_topics(conn, org["org_type"], grade_label)
    is_pro, _, tarif = edu_curriculum.is_org_pro(conn, org["id"])
    return render_template("edu_orgs/curriculum_topics.html", org=org, grade_label=grade_label,
                            topics=topics, is_pro=is_pro, role=_current_role())


@edu_orgs_bp.route("/curriculum/topic/<int:topic_id>")
@edu2_login_required
def curriculum_topic_detail(topic_id):
    conn = get_db()
    org = _current_org_row(conn)
    try:
        topic, practicals, is_pro, locked_count = edu_curriculum.list_practicals_for_topic(
            conn, org["id"], topic_id
        )
    except EduOrgError as e:
        flash(str(e), "error")
        return redirect(url_for("edu_orgs.curriculum_grades"))
    return render_template("edu_orgs/curriculum_topic.html", org=org, topic=topic,
                            practicals=practicals, is_pro=is_pro, locked_count=locked_count,
                            role=_current_role(), ai_question=None, ai_reply=None, ai_is_live=False)


# ------------------------------------------------------------------
# 8.2) PRO — SUN'IY INTELLEKT YORDAMCHISI (haqiqiy AI, ai.py orqali)
# ------------------------------------------------------------------
# DIQQAT: bu funksiya asosiy saytdagi AI yordamchi bilan bir xil real
# tizimdan (Gemini asosiy, Anthropic zaxira) foydalanadi — .env faylida
# GEMINI_API_KEY yoki ANTHROPIC_API_KEY sozlangan bo'lsa HAQIQIY javob
# beradi; sozlanmagan bo'lsa buni ochiq aytadigan demo javob qaytaradi
# (soxta "ishlayotgandek ko'rsatish" yo'q).
@edu_orgs_bp.route("/curriculum/topic/<int:topic_id>/ai-ask", methods=["POST"])
@edu2_login_required
def curriculum_ai_ask(topic_id):
    conn = get_db()
    org = _current_org_row(conn)
    try:
        topic, practicals, is_pro, locked_count = edu_curriculum.list_practicals_for_topic(
            conn, org["id"], topic_id
        )
    except EduOrgError as e:
        flash(str(e), "error")
        return redirect(url_for("edu_orgs.curriculum_grades"))

    if not is_pro:
        flash("AI yordamchi faqat Pro tarifda mavjud.", "error")
        return redirect(url_for("edu_orgs.curriculum_topic_detail", topic_id=topic_id))

    question = request.form.get("question", "").strip()
    ai_reply, ai_is_live = None, False
    if question:
        import ai
        system_prompt = (
            f"Sen SHATS CYBER EDU platformasining Informatika fani bo'yicha AI yordamchisisan. "
            f"O'quvchi/o'qituvchi hozir '{topic['grade_label']}' bosqichida '{topic['title']}' mavzusini "
            f"o'rganmoqda (qisqacha: {topic['summary']}). Ushbu mavzuga oid savollarga va amaliy "
            f"topshiriqlarni bajarishga yordam ber. O'zbek tilida, sodda, aniq va qisqa javob ber. "
            f"To'g'ridan-to'g'ri tayyor javobni yozib bermasdan, fikrlashga yo'naltiruvchi tushuntirish ber."
        )
        ai_reply, ai_is_live = ai.call_ai_assistant("umumiy", question, system_override=system_prompt)
    else:
        flash("Savol kiritilmadi.", "error")

    return render_template("edu_orgs/curriculum_topic.html", org=org, topic=topic,
                            practicals=practicals, is_pro=is_pro, locked_count=locked_count,
                            role=_current_role(), ai_question=question, ai_reply=ai_reply, ai_is_live=ai_is_live)


# ------------------------------------------------------------------
# 9) Edu admin — asosiy SHATS CYBER admindan MUSTAQIL, faqat Edu qismiga
#    javobgar alohida hisob (standart: shatsadmin@edu / edu19199655)
# ------------------------------------------------------------------
@edu_orgs_bp.route("/admin/login", methods=["GET", "POST"])
def edu_admin_login_page():
    if request.method == "GET":
        return render_template("edu_orgs/edu_admin_login.html", error=None)

    from security import is_ip_blocked, block_ip, log_security_event
    from db import query_one as _query_one
    from edu_admin_auth import verify_edu_admin_login

    ip = request.remote_addr or "unknown"
    if is_ip_blocked(ip):
        return render_template("edu_orgs/edu_admin_login.html",
                                error="Bu IP manzil bloklangan. Keyinroq urinib ko'ring.")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    admin = verify_edu_admin_login(email, password)
    if not admin:
        log_security_event(None, "edu_admin_failed_login", ip, request.headers.get("User-Agent", ""),
                            f"email:{email}", "high")
        recent = _query_one(
            "SELECT COUNT(*) c FROM security_events WHERE event_type='edu_admin_failed_login' "
            "AND ip=? AND created_at > datetime('now', '-15 minutes')", (ip,)
        )
        if recent and recent["c"] >= 5:
            block_ip(ip, "edu_admin_brute_force", duration_hours=2)
        return render_template("edu_orgs/edu_admin_login.html", error="Email yoki parol noto'g'ri")

    session.clear()
    session["edu_admin_id"] = admin["id"]
    return redirect(url_for("edu_orgs.admin_orgs_page"))


@edu_orgs_bp.route("/admin/logout", methods=["POST"])
def edu_admin_logout():
    session.pop("edu_admin_id", None)
    return redirect(url_for("edu_orgs.edu_admin_login_page"))


@edu_orgs_bp.route("/admin/change-password", methods=["POST"])
@edu_admin_required
def edu_admin_change_password():
    from edu_admin_auth import get_edu_admin, change_edu_admin_password
    from werkzeug.security import check_password_hash

    admin = get_edu_admin(session["edu_admin_id"])
    old_pw = request.form.get("old_password", "")
    new_pw = request.form.get("new_password", "")
    if not check_password_hash(admin["password_hash"], old_pw):
        flash("Joriy parol noto'g'ri.", "error")
    elif len(new_pw) < 8:
        flash("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak.", "error")
    else:
        change_edu_admin_password(admin["id"], new_pw)
        flash("Parol muvaffaqiyatli o'zgartirildi.", "success")
    return redirect(url_for("edu_orgs.admin_orgs_page"))


@edu_orgs_bp.route("/admin/orgs")
@edu_admin_required
def admin_orgs_page():
    conn = get_db()
    orgs = conn.execute("""
        SELECT o.*,
            (SELECT COUNT(*) FROM edu_teachers WHERE org_id=o.id) as teacher_count,
            (SELECT COUNT(*) FROM edu_students WHERE org_id=o.id) as student_count
        FROM edu_organizations o ORDER BY o.created_at DESC
    """).fetchall()
    tariffs = conn.execute("SELECT * FROM edu_tariffs ORDER BY org_type, code").fetchall()
    keys = conn.execute("""
        SELECT k.*, o.name as used_by_org_name FROM edu_activation_keys k
        LEFT JOIN edu_organizations o ON o.id = k.used_by_org_id
        ORDER BY k.created_at DESC LIMIT 50
    """).fetchall()
    system_status = _check_system_status()
    return render_template("edu_orgs/admin_orgs.html", orgs=orgs, tariffs=tariffs, keys=keys,
                           fund_balance=get_unified_fund_balance(), system_status=system_status)


def _check_system_status():
    """Email (SMTP) va AI (Gemini/Anthropic) sozlanganmi — tekshirib, admin
    panelida ko'rsatish uchun. Bu logga tushib qolgan xatolarni qidirish
    o'rniga, bir qarashda holatni ko'rish imkonini beradi."""
    smtp_ok = bool(os.environ.get("SMTP_HOST", "").strip() and
                   os.environ.get("SMTP_USER", "").strip() and
                   os.environ.get("SMTP_PASSWORD", "").strip())
    gemini_ok = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    anthropic_ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    return {
        "smtp": smtp_ok,
        "gemini": gemini_ok,
        "anthropic": anthropic_ok,
        "ai_any": gemini_ok or anthropic_ok,
    }


@edu_orgs_bp.route("/admin/orgs/tariffs/<string:tarif_code>/set-price", methods=["POST"])
@edu_admin_required
def admin_update_tariff_price(tarif_code):
    """Edu admin Edu tashkilot tariflarining narxini (necha CODE turishini)
    shu yerdan o'zgartiradi. Narx darhol kuchga kiradi — YANGI sotib
    olishlarga ta'sir qiladi, allaqachon faollashtirilgan tariflarga tegmaydi."""
    conn = get_db()
    price = request.form.get("price_coins", type=int)
    if price is None or price < 0:
        flash("Narx 0 yoki undan katta butun son bo'lishi kerak.", "error")
        return redirect(url_for("edu_orgs.admin_orgs_page"))

    tarif = conn.execute("SELECT * FROM edu_tariffs WHERE code=?", (tarif_code,)).fetchone()
    if not tarif:
        flash("Bunday tarif topilmadi.", "error")
        return redirect(url_for("edu_orgs.admin_orgs_page"))

    conn.execute("UPDATE edu_tariffs SET price_coins=? WHERE code=?", (price, tarif_code))
    conn.commit()
    flash(f"'{tarif['display_name']}' narxi {price} CODE ga o'zgartirildi.", "success")
    return redirect(url_for("edu_orgs.admin_orgs_page"))


@edu_orgs_bp.route("/admin/orgs/<int:org_id>/issue-coins", methods=["POST"])
@edu_admin_required
def admin_issue_coins(org_id):
    conn = get_db()
    amount = request.form.get("amount", type=int) or 0
    try:
        # AUDIT: edu_admin_id orqali "kim chiqardi" Edu G'azna logida saqlanadi
        issue_coins_to_org(conn, None, org_id, amount, edu_admin_id=session.get("edu_admin_id"))
        flash(f"{amount} CODE tashkilotga Edu G'aznadan chiqarildi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for("edu_orgs.admin_orgs_page"))


@edu_orgs_bp.route("/admin/keys/generate", methods=["POST"])
@edu_admin_required
def admin_generate_key():
    """Edu admin coin talab qilmaydigan, 9 xonali, bir martalik
    faollashtirish kaliti chiqaradi (Edu G'aznasi orqali nazorat qilinadi)."""
    from edu_treasury_bridge import generate_activation_key
    conn = get_db()
    tarif_code = request.form.get("tarif_code", "")
    months = request.form.get("months", type=int) or 1
    try:
        key_code = generate_activation_key(conn, tarif_code, months, edu_admin_id=session.get("edu_admin_id"))
        flash(f"Yangi faollashtirish kaliti: {key_code} (tarif: {tarif_code}, {months} oy)", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for("edu_orgs.admin_orgs_page"))


@edu_orgs_bp.route("/tariffs/activate-with-key", methods=["POST"])
@edu2_login_required
@edu2_org_only
def activate_tariff_with_key_route():
    """Tashkilot coin sarflamasdan, G'azna bergan 9 xonali kalit orqali
    tarifni faollashtiradi."""
    from edu_orgs import activate_tariff_with_key
    conn = get_db()
    key_code = request.form.get("key_code", "").strip()
    try:
        tarif = activate_tariff_with_key(conn, _current_org_id(), key_code)
        flash(f"'{tarif['display_name']}' tarifi faollashtirish kaliti orqali muvaffaqiyatli ochildi!", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for("edu_orgs.dashboard"))
