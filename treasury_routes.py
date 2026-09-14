# ============================================================
# CYBER SHATS — G'azna (Treasury) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user
from db import query_one, query_all, execute, get_db
from utils import api_response, resolve_user_id
from ids import (get_premium_ids_list, get_vip_ids_list, admin_create_premium_id,
                 admin_delete_premium_id, admin_set_alphanumeric_id, admin_close_all_bidding_auctions,
                 admin_counter_offer, admin_accept_offer_at_asking, admin_reject_offer,
                 get_pending_sell_offers)
import certificates as cert_mod
from config import Config
import treasury as treasury_mod
import treasury_email_verify
import webpush_mod as push_mod
import trading_stub as trading_mod  # V2: stub
import os
import datetime
import hashlib
import time

treasury_bp = Blueprint("treasury_bp", __name__)


# G'AZNA (Code Panel) — foydalanuvchilar/admin tizimidan BUTUNLAY MUSTAQIL.
# Alohida login (email+parol), alohida sessiya, alohida jamg'arma balansi.
# Pro yoqish/o'chirish ENDI ADMIN PANELDA ("Foydalanuvchilar" bo'limida) qoladi —
# G'azna faqat jamg'armadan coin chiqarish bilan shug'ullanadi.
# =================================================================

def _credential_fingerprint(account) -> str:
    """Hisobning email+parol_hash'idan hosila 'iz' (fingerprint) — sessiyada
    saqlanadi va har so'rovda joriy hisob holati bilan solishtiriladi.

    MUHIM (tuzatilgan xavfsizlik xatosi): avval parol/email o'zgartirilganda
    ALLAQACHON OCHIQ sessiyalar (masalan eski, zaif parol bilan kirib
    olingan sessiya) HECH QACHON bekor qilinmasdi — chunki sessiya faqat
    `treasury_account_id`ni saqlaydi, u esa hisob o'chirilmagan ekan doim
    haqiqiy bo'lib qolaveradi. Endi login vaqtida hisobning email+parol_hash
    combinatsiyasidan bir tomonlama iz olinib sessiyaga yoziladi; har
    so'rovda bu iz joriy bazadagi qiymat bilan solishtiriladi — mos
    kelmasa (parol/email o'zgargan bo'lsa) sessiya DARHOL bekor qilinadi,
    hisob egasi qaytadan (YANGI ma'lumotlar bilan) kirishga majbur bo'ladi.
    Xom parol_hash'ning o'zi cookie'ga yozilmaydi (u faqat imzolangan,
    shifrlanmagan — mijozga o'qilishi mumkin), faqat undan olingan
    qaytarib bo'lmaydigan hash saqlanadi."""
    raw = f"{account['email']}:{account['password_hash']}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def treasury_login_required(view):
    """G'azna xodimi sifatida kirilganligini tekshiradi (foydalanuvchi sessiyasidan mustaqil)."""
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("treasury_account_id"):
            return redirect(url_for(".treasury_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@treasury_bp.route("/treasury/login", methods=["GET", "POST"])
def treasury_login():
    """G'azna xodimlari uchun mustaqil login sahifasi (foydalanuvchi/admin login'idan butunlay alohida)."""
    next_url = request.args.get("next") or request.form.get("next") or url_for(".treasury_dashboard")
    no_accounts_yet = treasury_mod.treasury_accounts_count() == 0

    if request.method == "POST":
        if no_accounts_yet:
            # Birinchi G'azna hisobini shu yerda yaratamiz (bootstrap)
            ism = request.form.get("ism", "")
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            if password != confirm:
                flash("Parollar mos kelmadi.", "error")
                return redirect(url_for(".treasury_login"))
            ok, msg = treasury_mod.create_treasury_account(ism, email, password)
            if not ok:
                flash(msg, "error")
                return redirect(url_for(".treasury_login"))
            account = treasury_mod.get_treasury_account_by_email(email)
            session["treasury_account_id"] = account["id"]
            session["treasury_account_ism"] = account["ism"]
            session["treasury_cred_fingerprint"] = _credential_fingerprint(account)
            session["treasury_login_at"] = time.time()
            session.permanent = False
            treasury_email_verify.send_verification_code(account["id"], account["email"], account["ism"])
            flash("G'azna hisobi yaratildi. Davom etish uchun emailingizni tasdiqlang.", "success")
            return redirect(url_for(".treasury_verify_email"))
        else:
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            account = treasury_mod.verify_treasury_login(email, password)
            if not account:
                flash("Email yoki parol noto'g'ri.", "error")
                return redirect(url_for(".treasury_login", next=next_url))
            session["treasury_account_id"] = account["id"]
            session["treasury_account_ism"] = account["ism"]
            session["treasury_cred_fingerprint"] = _credential_fingerprint(account)
            session["treasury_login_at"] = time.time()
            if not account.get("email_verified"):
                session.permanent = False
                treasury_email_verify.send_verification_code(account["id"], account["email"], account["ism"])
                return redirect(url_for(".treasury_verify_email"))
            session.permanent = True
            return redirect(next_url)

    return render_template("treasury_login.html", no_accounts_yet=no_accounts_yet, next_url=next_url)


@treasury_bp.route("/treasury/logout", methods=["GET", "POST"])
def treasury_logout():
    session.pop("treasury_account_id", None)
    session.pop("treasury_account_ism", None)
    session.pop("treasury_cred_fingerprint", None)
    session.pop("treasury_login_at", None)
    flash("G'aznadan chiqdingiz.", "success")
    return redirect(url_for(".treasury_login"))


_TREASURY_VERIFY_EXEMPT_ENDPOINTS = {
    "treasury_bp.treasury_verify_email", "treasury_bp.treasury_verify_email_resend",
    "treasury_bp.treasury_logout", "treasury_bp.treasury_login",
}

# Emaili hali tasdiqlanmagan G'azna xodimi uchun sessiya shu vaqtdan keyin
# AVTOMATIK bekor qilinadi (login+parolni qaytadan so'raydi) — muhim
# (tuzatilgan xato): avval bu oraliq sessiya `session.permanent = True`
# bilan CHEKSIZ (bir necha hafta) saqlanardi, ya'ni brauzerni yopib qayta
# ochsa ham tasdiqlash sahifasiga TO'G'RIDAN-TO'G'RI (parol so'ramasdan)
# kirib qolar edi.
_PENDING_VERIFY_TTL_SECONDS = 600  # 10 daqiqa


def _pending_login_expired() -> bool:
    login_at = session.get("treasury_login_at")
    return not login_at or (time.time() - login_at) > _PENDING_VERIFY_TTL_SECONDS


def _clear_treasury_session():
    session.pop("treasury_account_id", None)
    session.pop("treasury_account_ism", None)
    session.pop("treasury_cred_fingerprint", None)
    session.pop("treasury_login_at", None)


@treasury_bp.before_request
def _check_treasury_email_verified():
    """Har so'rovda: (1) hisob ma'lumotlari (email/parol) o'zgarganini
    tekshiradi — o'zgargan bo'lsa sessiya DARHOL bekor qilinadi (qarang:
    _credential_fingerprint() docstring); (2) Email tasdiqlanmagan G'azna
    xodimini /treasury/verify-email sahifasiga yo'naltiradi, VA bu holat
    _PENDING_VERIFY_TTL_SECONDS'dan uzoqqa cho'zilsa sessiyani bekor
    qilib qaytadan login/parol so'raydi."""
    account_id = session.get("treasury_account_id")
    if not account_id:
        return
    if request.endpoint in _TREASURY_VERIFY_EXEMPT_ENDPOINTS:
        return

    account = treasury_mod.get_treasury_account(account_id)
    if not account or _credential_fingerprint(account) != session.get("treasury_cred_fingerprint"):
        _clear_treasury_session()
        flash("Hisobingiz ma'lumotlari yangilangan — xavfsizlik uchun qaytadan tizimga kiring.", "error")
        return redirect(url_for(".treasury_login"))

    if not account.get("email_verified"):
        if _pending_login_expired():
            _clear_treasury_session()
            flash("Sessiya muddati tugadi — qaytadan tizimga kiring.", "error")
            return redirect(url_for(".treasury_login"))
        return redirect(url_for(".treasury_verify_email"))


@treasury_bp.route("/treasury/verify-email", methods=["GET", "POST"])
def treasury_verify_email():
    account_id = session.get("treasury_account_id")
    if not account_id:
        return redirect(url_for(".treasury_login"))
    account = treasury_mod.get_treasury_account(account_id)
    if not account:
        session.clear()
        return redirect(url_for(".treasury_login"))
    if account.get("email_verified"):
        return redirect(url_for(".treasury_dashboard"))
    if _pending_login_expired():
        _clear_treasury_session()
        flash("Sessiya muddati tugadi — qaytadan tizimga kiring.", "error")
        return redirect(url_for(".treasury_login"))

    if request.method == "GET":
        return render_template("treasury_verify_email.html", account=account, error=None)

    code = request.form.get("code", "").strip()
    ok, msg = treasury_email_verify.verify_code(account_id, code)
    if ok:
        flash(msg, "success")
        session["treasury_login_at"] = time.time()
        session.permanent = True
        return redirect(url_for(".treasury_dashboard"))
    return render_template("treasury_verify_email.html", account=account, error=msg)


@treasury_bp.route("/treasury/verify-email/resend", methods=["POST"])
def treasury_verify_email_resend():
    account_id = session.get("treasury_account_id")
    if not account_id:
        return redirect(url_for(".treasury_login"))
    account = treasury_mod.get_treasury_account(account_id)
    if not account:
        session.clear()
        return redirect(url_for(".treasury_login"))
    if account.get("email_verified"):
        return redirect(url_for(".treasury_dashboard"))
    if _pending_login_expired():
        _clear_treasury_session()
        flash("Sessiya muddati tugadi — qaytadan tizimga kiring.", "error")
        return redirect(url_for(".treasury_login"))
    ok, msg = treasury_email_verify.send_verification_code(account_id, account["email"], account["ism"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_verify_email"))


@treasury_bp.route("/treasury/")
@treasury_login_required
def treasury_dashboard():
    stats = treasury_mod.get_fund_stats()
    fund_log = treasury_mod.get_fund_log(60)
    q = request.args.get("q", "").strip()
    search_results = []
    if q:
        search_results = query_all(
            """SELECT id, ism, familiya, email, plan, code_balance, is_blocked, custom_id
               FROM users WHERE ism LIKE ? OR familiya LIKE ? OR email LIKE ? OR custom_id LIKE ?
               ORDER BY id DESC LIMIT 30""",
            (f"%{q}%", f"%{q}%", f"%{q}%", f"%{q}%")
        )
    pricing = {r["key"]: r["value"] for r in query_all("SELECT key, value FROM pricing_settings")}
    trading_current = trading_mod.get_current_price()

    # --- EDU BO'LIMI: Edu qismi uchun ALOHIDA jamg'arma (asosiy jamg'armadan
    # mustaqil) — shu yerdan tashkilotlarga CODE chiqarish va 9 xonali
    # faollashtirish kaliti berish mumkin.
    from edu_treasury_bridge import get_edu_fund_balance
    edu_fund_balance = get_edu_fund_balance()
    edu_fund_log = query_all(
        """SELECT l.*, o.name as org_name FROM edu_treasury_fund_log l
           LEFT JOIN edu_organizations o ON o.id = l.edu_org_id
           ORDER BY l.created_at DESC LIMIT 40"""
    )
    edu_orgs = query_all("""
        SELECT o.id, o.name, o.org_number, o.org_type, o.is_active, o.coin_balance, o.tarif_code, o.username
        FROM edu_organizations o ORDER BY o.created_at DESC
    """)
    edu_tariffs = query_all("SELECT * FROM edu_tariffs ORDER BY org_type, code")
    from edu_treasury_bridge import get_purchase_requests
    edu_purchase_requests = get_purchase_requests("pending")

    # Markazni ID (org_number), nomi yoki @username orqali qidirish —
    # shu orqali aniq markaz topilib, unga to'g'ridan-to'g'ri CODE chiqariladi.
    org_q = request.args.get("org_q", "").strip()
    org_search_results = []
    if org_q:
        org_search_results = query_all(
            """SELECT * FROM edu_organizations
               WHERE org_number LIKE ? OR name LIKE ? OR username LIKE ?
               ORDER BY created_at DESC LIMIT 30""",
            (f"%{org_q}%", f"%{org_q}%", f"%{org_q}%")
        )

    return render_template(
        "treasury_dashboard.html",
        stats=stats, fund_log=fund_log, search_q=q, search_results=search_results,
        treasury_ism=session.get("treasury_account_ism"),
        pricing=pricing, trading_current=trading_current,
        edu_fund_balance=edu_fund_balance, edu_fund_log=edu_fund_log,
        edu_orgs=edu_orgs, edu_tariffs=edu_tariffs, edu_purchase_requests=edu_purchase_requests,
        org_search_q=org_q, org_search_results=org_search_results,
        code_to_som_rate=int(pricing.get("code_to_som_rate", 10000)),
    )


@treasury_bp.route("/treasury/design-orders")
@treasury_login_required
def treasury_design_orders():
    orders = query_all(
        """SELECT o.*, u.ism, u.familiya, u.custom_id
           FROM design_orders o JOIN users u ON u.id=o.user_id
           WHERE o.status IN ('pending','quoted') ORDER BY o.created_at DESC""")
    return render_template("treasury_design_orders.html", orders=orders)


@treasury_bp.route("/treasury/design-orders/<int:order_id>/quote", methods=["POST"])
@treasury_login_required
def treasury_design_order_quote(order_id):
    try:
        price = int(request.form.get("quoted_price", 0))
    except ValueError:
        price = 0
    if price < 1:
        flash("Narx kamida 1 CODE bo'lishi kerak.", "error")
        return redirect(url_for(".treasury_design_orders"))
    order = query_one("SELECT * FROM design_orders WHERE id=? AND status='pending'", (order_id,))
    if not order:
        flash("Buyurtma topilmadi.", "error")
        return redirect(url_for(".treasury_design_orders"))
    execute("UPDATE design_orders SET status='quoted', quoted_price=?, updated_at=datetime('now') WHERE id=?",
            (price, order_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (order["user_id"], "Dizayn zakazingizga narx belgilandi! 🎨",
             f"So'ragan dizayiningiz uchun narx: ⚡ {price:,} CODE. To'lash uchun 'Dizayn zakaz' sahifasiga o'ting.",
             "info"))
    flash(f"Narx belgilandi: {price:,} CODE. Foydalanuvchiga xabar yuborildi.", "success")
    return redirect(url_for(".treasury_design_orders"))


@treasury_bp.route("/treasury/design-orders/<int:order_id>/reject", methods=["POST"])
@treasury_login_required
def treasury_design_order_reject(order_id):
    order = query_one("SELECT * FROM design_orders WHERE id=? AND status IN ('pending','quoted')", (order_id,))
    if not order:
        flash("Buyurtma topilmadi.", "error")
        return redirect(url_for(".treasury_design_orders"))
    execute("UPDATE design_orders SET status='rejected', updated_at=datetime('now') WHERE id=?", (order_id,))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (order["user_id"], "Dizayn zakazi rad etildi", "So'ragan dizayin buyurtmangiz rad etildi.", "info"))
    flash("Buyurtma rad etildi.", "success")
    return redirect(url_for(".treasury_design_orders"))


@treasury_bp.route("/treasury/ids")
@treasury_login_required
def treasury_ids_page():
    """G'azna uchun ID boshqaruvi — huddi Super Admindagi kabi (premium
    IDlar, VIP 0-9 IDlar, maxsus harfli ID berish, auksionni yopish)."""
    premium_ids = get_premium_ids_list()
    vip_ids = get_vip_ids_list()
    pending_sell_offers = get_pending_sell_offers()
    return render_template("treasury_ids.html", premium_ids=premium_ids, vip_ids=vip_ids,
                           pending_sell_offers=pending_sell_offers)


@treasury_bp.route("/treasury/ids/create", methods=["POST"])
@treasury_login_required
def treasury_ids_create():
    custom_id = request.form.get("custom_id", "").strip()
    try:
        price = int(request.form.get("price", 0))
    except ValueError:
        price = 0
    ok, msg = admin_create_premium_id(custom_id, price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/<custom_id>/delete", methods=["POST"])
@treasury_login_required
def treasury_ids_delete(custom_id):
    ok, msg = admin_delete_premium_id(custom_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/grant-special", methods=["POST"])
@treasury_login_required
def treasury_grant_special_id():
    target_identifier = request.form.get("target_identifier", "").strip()
    new_id = request.form.get("new_id", "").strip()
    treasury_marker_id = -(session.get("treasury_account_id") or 0)
    ok, msg = admin_set_alphanumeric_id(treasury_marker_id, target_identifier, new_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/close-auctions", methods=["POST"])
@treasury_login_required
def treasury_close_auctions():
    ok, msg = admin_close_all_bidding_auctions()
    flash(msg, "success")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/sell-offers/<int:offer_id>/counter", methods=["POST"])
@treasury_login_required
def treasury_id_sell_counter(offer_id):
    try:
        counter_price = int(request.form.get("counter_price", 0))
    except ValueError:
        counter_price = 0
    treasury_marker_id = -(session.get("treasury_account_id") or 0)
    ok, msg = admin_counter_offer(treasury_marker_id, offer_id, counter_price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/sell-offers/<int:offer_id>/accept", methods=["POST"])
@treasury_login_required
def treasury_id_sell_accept(offer_id):
    treasury_marker_id = -(session.get("treasury_account_id") or 0)
    disposition = request.form.get("disposition", "random_pool")
    try:
        marketplace_price = int(request.form.get("marketplace_price", 0)) or None
    except ValueError:
        marketplace_price = None
    ok, msg = admin_accept_offer_at_asking(treasury_marker_id, offer_id, disposition, marketplace_price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/ids/sell-offers/<int:offer_id>/reject", methods=["POST"])
@treasury_login_required
def treasury_id_sell_reject(offer_id):
    treasury_marker_id = -(session.get("treasury_account_id") or 0)
    ok, msg = admin_reject_offer(treasury_marker_id, offer_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_ids_page"))


@treasury_bp.route("/treasury/edu/orgs/<int:org_id>/issue-coins", methods=["POST"])
@treasury_login_required
def treasury_edu_issue_coins(org_id):
    """G'azna xodimi Edu jamg'armasidan tashkilotga CODE chiqaradi."""
    from edu_treasury_bridge import issue_coins_to_org
    from edu_orgs import EduOrgError
    amount = request.form.get("amount", type=int) or 0
    org_q = request.form.get("org_q", "")
    try:
        issue_coins_to_org(get_db(), session["treasury_account_id"], org_id, amount)
        flash(f"{amount} CODE Edu tashkilotiga chiqarildi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    if org_q:
        dest = url_for(".treasury_dashboard", org_q=org_q)
    else:
        dest = url_for(".treasury_dashboard")
    return redirect(dest + "#edu")


@treasury_bp.route("/treasury/edu/keys/generate", methods=["POST"])
@treasury_login_required
def treasury_edu_generate_key():
    """G'azna xodimi coin talab qilmaydigan 9 xonali faollashtirish kaliti chiqaradi."""
    from edu_treasury_bridge import generate_activation_key
    from edu_orgs import EduOrgError
    tarif_code = request.form.get("tarif_code", "")
    months = request.form.get("months", type=int) or 1
    try:
        key_code = generate_activation_key(get_db(), tarif_code, months)
        flash(f"Yangi faollashtirish kaliti: {key_code} (tarif: {tarif_code}, {months} oy)", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for(".treasury_dashboard") + "#edu")


@treasury_bp.route("/treasury/edu/purchases/<int:req_id>/approve", methods=["POST"])
@treasury_login_required
def treasury_edu_purchase_approve(req_id):
    """G'azna xodimi tashkilotning (markazning) haqiqiy pul evaziga CODE
    sotib olish so'rovini tasdiqlaydi — Edu jamg'armasidan CODE chiqariladi."""
    from edu_treasury_bridge import approve_purchase_request
    from edu_orgs import EduOrgError
    try:
        req = approve_purchase_request(get_db(), req_id, session["treasury_account_id"])
        flash(f"✅ {req['code_amount']:,} CODE tashkilotga chiqarildi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for(".treasury_dashboard") + "#edu")


@treasury_bp.route("/treasury/edu/purchases/<int:req_id>/reject", methods=["POST"])
@treasury_login_required
def treasury_edu_purchase_reject(req_id):
    """G'azna xodimi so'rovni rad etadi (masalan chek noto'g'ri/soxta bo'lsa)."""
    from edu_treasury_bridge import reject_purchase_request
    from edu_orgs import EduOrgError
    reason = request.form.get("reason", "").strip()
    try:
        reject_purchase_request(get_db(), req_id, session["treasury_account_id"], reason)
        flash("So'rov rad etildi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for(".treasury_dashboard") + "#edu")


@treasury_bp.route("/treasury/edu/deposit", methods=["POST"])
@treasury_login_required
def treasury_edu_deposit():
    """G'azna xodimi Edu jamg'armasiga to'g'ridan-to'g'ri CODE qo'shadi
    (asosiy sayt jamg'armasiga depozit qilish bilan bir xil mantiq)."""
    from edu_treasury_bridge import deposit_to_edu_fund
    from edu_orgs import EduOrgError
    amount = request.form.get("amount", type=int) or 0
    note = request.form.get("note", "").strip()
    try:
        deposit_to_edu_fund(amount, note, session["treasury_account_id"])
        flash(f"{amount:,} CODE Edu jamg'armasiga qo'shildi.", "success")
    except EduOrgError as e:
        flash(str(e), "error")
    return redirect(url_for(".treasury_dashboard") + "#edu")


@treasury_bp.route("/treasury/edu/purchases/<int:req_id>/receipt")
@treasury_login_required
def treasury_edu_purchase_receipt(req_id):
    """Markaz yuklagan to'lov chekini ko'rsatish."""
    req = query_one("SELECT receipt_file_path FROM edu_purchase_requests WHERE id=?", (req_id,))
    if not req or not req["receipt_file_path"]:
        abort(404)
    return redirect(req["receipt_file_path"])


@treasury_bp.route("/treasury/update-packages", methods=["POST"])
@treasury_login_required
def treasury_update_packages():
    """G'azna tomonidan CODE paket narxlarini yangilash."""
    packs = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    for amt in packs:
        val = request.form.get(f"code_pack_{amt}", "").strip()
        if val and val.isdigit() and int(val) > 0:
            execute(
                "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"code_pack_{amt}", val)
            )
    flash("Paket narxlari yangilandi!", "success")
    return redirect(url_for(".treasury_dashboard"))


@treasury_bp.route("/treasury/update-pricing", methods=["POST"])
@treasury_login_required
def treasury_update_pricing():
    """G'azna tomonidan CODE narxlarini yangilash."""
    keys = [
        "pro_price_code", "cyber_pro_price_code", "vip_price_code",
        "welcome_bonus_code", "paid_course_code_default",
        "bot_tariff_price_pro", "bot_tariff_price_cyber_pro",
        "bot_tariff_price_vip", "bot_tariff_price_hacker",
    ]
    for k in keys:
        val = request.form.get(k, "").strip()
        if val and val.isdigit():
            execute(
                "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (k, val)
            )
    flash("Narxlar yangilandi!", "success")
    return redirect(url_for(".treasury_dashboard"))


@treasury_bp.route("/treasury/issue/<int:user_id>", methods=["POST"])
@treasury_login_required
def treasury_issue_coins(user_id):
    """G'azna jamg'armasidan foydalanuvchiga coin chiqaradi. Mablag' yetmasa rad etiladi."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = treasury_mod.issue_coins_to_user(session["treasury_account_id"], user_id, amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_dashboard", q=request.form.get("q", "")))


@treasury_bp.route("/treasury/accounts")
@treasury_login_required
def treasury_accounts_page():
    """G'azna xodimlari ro'yxati (faqat boshqa G'azna xodimi ko'ra oladi)."""
    accounts = treasury_mod.list_treasury_accounts()
    return render_template("treasury_accounts.html", accounts=accounts)


@treasury_bp.route("/treasury/accounts/create", methods=["POST"])
@treasury_login_required
def treasury_accounts_create():
    """Yangi G'azna xodimi qo'shish — faqat tizimga kirgan G'azna xodimi qo'sha oladi."""
    ism = request.form.get("ism", "")
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    ok, msg = treasury_mod.create_treasury_account(ism, email, password)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_accounts_page"))


@treasury_bp.route("/treasury/accounts/<int:account_id>/toggle", methods=["POST"])
@treasury_login_required
def treasury_accounts_toggle(account_id):
    if account_id == session.get("treasury_account_id"):
        flash("O'zingizning hisobingizni faolsizlantira olmaysiz.", "error")
        return redirect(url_for(".treasury_accounts_page"))
    treasury_mod.toggle_treasury_account(account_id)
    flash("Hisob holati o'zgartirildi.", "success")
    return redirect(url_for(".treasury_accounts_page"))


@treasury_bp.route("/treasury/accounts/<int:account_id>/reset-password", methods=["POST"])
@treasury_login_required
def treasury_accounts_reset_password(account_id):
    new_password = request.form.get("new_password", "")
    ok, msg = treasury_mod.reset_treasury_account_password(account_id, new_password)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".treasury_accounts_page"))
# G'aznachi — sertifikat arizalari (faqat ko'rish, statistika)
@treasury_bp.route("/treasury/certificates")
@treasury_login_required
def treasury_certificates():
    applications = cert_mod.get_all_applications()
    return render_template("treasury_certificates.html", applications=applications)


# =================================================================
# G'AZNA — Telegram bot orqali sotuv so'rovlari
# =================================================================
@treasury_bp.route("/api/treasury/notifications/pending")
@treasury_login_required
def api_treasury_notifications_pending():
    """G'azna paneli uchun ovozli bildirishnoma: yangi kutilayotgan bot to'lov so'rovlari.
    Sessiyada ko'rilgan ID'lar ro'yxati saqlanadi — qayta ko'rsatilmasin."""
    seen_ids = session.get("treasury_seen_purchase_ids", [])
    pending = query_all(
        "SELECT id, request_type, code_amount, target_custom_id, created_at "
        "FROM bot_purchase_requests WHERE status='pending' ORDER BY id DESC LIMIT 20"
    )
    items = []
    new_seen = list(seen_ids)
    for r in pending:
        if r["id"] in seen_ids:
            continue
        new_seen.append(r["id"])
        if r["request_type"] == "code":
            body = f"⚡ {r['code_amount']:,} CODE so'rovi — ID #{r['target_custom_id']}"
        else:
            body = f"📚 Kurs sotib olish so'rovi — ID #{r['target_custom_id']}"
        items.append({
            "id": r["id"],
            "title": "Yangi to'lov so'rovi",
            "body": body,
        })
    # Sessiyada faqat oxirgi 200 tasini saqlaymiz (cheksiz o'smasin)
    session["treasury_seen_purchase_ids"] = new_seen[-200:]
    return api_response(True, data={"items": items})


@treasury_bp.route("/treasury/bot-purchases")
@treasury_login_required
def treasury_bot_purchases():
    """Bot orqali kelgan to'lov so'rovlari ro'yxati."""
    status = request.args.get("status", "pending")
    if status == "all":
        rows = query_all(
            "SELECT * FROM bot_purchase_requests ORDER BY id DESC LIMIT 200"
        )
    else:
        rows = query_all(
            "SELECT * FROM bot_purchase_requests WHERE status=? ORDER BY id DESC LIMIT 200",
            (status,)
        )
    return render_template("treasury_bot_purchases.html", rows=rows, status=status,
                           bot_token=Config.TELEGRAM_BOT_TOKEN)


@treasury_bp.route("/treasury/bot-purchases/<int:req_id>/approve", methods=["POST"])
@treasury_login_required
def treasury_bot_approve(req_id):
    """So'rovni tasdiqlash: g'azna jamg'armasidan code chiqaradi yoki kurs ochadi.
    Foydalanuvchi botda xabar oladi."""
    import json as _json
    req = query_one("SELECT * FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        flash("So'rov topilmadi.", "error")
        return redirect(url_for(".treasury_bot_purchases"))
    if req["status"] != "pending":
        flash(f"Bu so'rov allaqachon ko'rib chiqilgan ({req['status']}).", "error")
        return redirect(url_for(".treasury_bot_purchases"))

    site_user_id = req["site_user_id"]
    if not site_user_id:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for(".treasury_bot_purchases"))

    treasury_id = session["treasury_account_id"]

    if req["request_type"] == "code":
        # G'azna jamg'armasidan code chiqarish
        amount = req["code_amount"]
        ok, msg = treasury_mod.issue_coins_to_user(treasury_id, site_user_id, amount)
        if not ok:
            flash(msg, "error")
            return redirect(url_for(".treasury_bot_purchases"))
        # So'rovni tasdiqlash
        execute(
            """UPDATE bot_purchase_requests SET status='completed', reviewed_by=?,
               reviewed_at=datetime('now'), admin_note='approved via treasury'
               WHERE id=?""",
            (treasury_id, req_id)
        )
        # Saytda notification
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (site_user_id, "CODE qo'shildi!",
             f"{'Saytdan' if req['source']=='site' else 'Telegram bot orqali'} sotib olingan {amount:,} CODE hisobingizga qo'shildi.",
             "success")
        )
        try:
            push_mod.send_push_to_user(
                site_user_id, "CODE qo'shildi! ⚡",
                f"{amount:,} CODE hisobingizga qo'shildi.", "/coins"
            )
        except Exception:
            pass
        # Botga xabar (faqat bot orqali kelgan bo'lsa)
        _notify_bot_user(req["chat_id"], "code", req)
        flash(f"⚡ {amount:,} CODE foydalanuvchiga chiqarildi.", "success")

    elif req["request_type"] == "course":
        try:
            courses = _json.loads(req["courses_json"] or "[]")
        except Exception:
            courses = []
        for c in courses:
            existing = query_one(
                "SELECT id FROM enrollments WHERE user_id=? AND course_id=?",
                (site_user_id, c["id"])
            )
            if not existing:
                execute(
                    "INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                    (site_user_id, c["id"])
                )
        execute(
            """UPDATE bot_purchase_requests SET status='completed', reviewed_by=?,
               reviewed_at=datetime('now'), admin_note='courses unlocked'
               WHERE id=?""",
            (treasury_id, req_id)
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (site_user_id, "Kurslar ochildi!",
             f"Telegram bot orqali sotib olingan {len(courses)} ta kurs hisobingizga qo'shildi.",
             "success")
        )
        try:
            push_mod.send_push_to_user(
                site_user_id, "Kurslar ochildi! 📚",
                f"{len(courses)} ta kurs hisobingizga qo'shildi.", "/courses"
            )
        except Exception:
            pass
        _notify_bot_user(req["chat_id"], "course", req)
        flash(f"📚 {len(courses)} ta kurs foydalanuvchiga ochildi.", "success")

    elif req["request_type"] == "tariff":
        from datetime import datetime, timedelta
        plan = req["plan"]
        if plan not in ("pro", "cyber_pro", "vip", "hacker"):
            flash("Noto'g'ri tarif turi.", "error")
            return redirect(url_for(".treasury_bot_purchases"))

        expires_at = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan, expires_at, site_user_id))
        execute(
            """UPDATE bot_purchase_requests SET status='completed', reviewed_by=?,
               reviewed_at=datetime('now'), admin_note='tariff activated'
               WHERE id=?""",
            (treasury_id, req_id)
        )
        execute(
            "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (site_user_id, "Tarif faollashtirildi!",
             f"Telegram bot orqali sotib olingan {plan.upper()} tarifi 30 kunga faollashtirildi.",
             "success")
        )
        try:
            push_mod.send_push_to_user(
                site_user_id, "Tarif faollashtirildi! 🎓",
                f"{plan.upper()} tarifi 30 kunga faollashtirildi.", "/dashboard"
            )
        except Exception:
            pass
        _notify_bot_user(req["chat_id"], "tariff", req)
        flash(f"🎓 {plan.upper()} tarifi foydalanuvchiga 30 kunga faollashtirildi.", "success")

    return redirect(url_for(".treasury_bot_purchases"))


@treasury_bp.route("/treasury/bot-purchases/<int:req_id>/reject", methods=["POST"])
@treasury_login_required
def treasury_bot_reject(req_id):
    """So'rovni rad etish."""
    req = query_one("SELECT * FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        flash("So'rov topilmadi.", "error")
        return redirect(url_for(".treasury_bot_purchases"))
    if req["status"] != "pending":
        flash("Allaqachon ko'rib chiqilgan.", "error")
        return redirect(url_for(".treasury_bot_purchases"))

    reason = request.form.get("reason", "Chek soxta yoki ma'lumotlar mos kelmaydi")
    treasury_id = session["treasury_account_id"]
    execute(
        """UPDATE bot_purchase_requests SET status='rejected', reviewed_by=?,
           reviewed_at=datetime('now'), admin_note=? WHERE id=?""",
        (treasury_id, reason, req_id)
    )
    _notify_bot_user(req["chat_id"], "rejected", req, reason=reason)
    flash("So'rov rad etildi va foydalanuvchiga xabar yuborildi.", "success")
    return redirect(url_for(".treasury_bot_purchases"))


def _notify_bot_user(chat_id, kind, req, reason=""):
    """Telegram bot orqali foydalanuvchiga natija xabari yuborish."""
    token = Config.TELEGRAM_BOT_TOKEN
    if not token or not chat_id:
        return
    try:
        # Foydalanuvchining tili
        tg_user = query_one("SELECT language FROM telegram_users WHERE chat_id=?", (chat_id,))
        lang = tg_user["language"] if tg_user else "uz"

        # Telegram bot tarjimalarini import qilamiz
        import telegram_bot as bot_mod
        if kind == "code":
            text = bot_mod.t(lang, "purchase_approved_code",
                             code=req["code_amount"], cid=req["target_custom_id"])
            # CODE miqdoriga mos tayyor rasm bor bo'lsa (masalan "50 CODE
            # tushdi!"), matn o'rniga O'SHA rasmni (izoh sifatida matn bilan)
            # yuboramiz — mos rasm bo'lmasa oddiy matn bilan davom etamiz.
            image_path = bot_mod.get_code_result_image(req["code_amount"])
            if image_path:
                bot_mod.tg_send_photo(chat_id, image_path, caption=text)
                return
        elif kind == "course":
            import json as _json
            try:
                cnt = len(_json.loads(req["courses_json"] or "[]"))
            except Exception:
                cnt = 0
            text = bot_mod.t(lang, "purchase_approved_course",
                             n=cnt, cid=req["target_custom_id"])
        elif kind == "tariff":
            plan_labels = dict(bot_mod.TARIFF_PLANS)
            text = bot_mod.t(lang, "purchase_approved_tariff",
                             name=plan_labels.get(req["plan"], req["plan"]),
                             cid=req["target_custom_id"])
        else:  # rejected
            text = bot_mod.t(lang, "purchase_rejected", reason=reason)

        bot_mod.tg_send_message(chat_id, text)
    except Exception as e:
        log_action(None, "bot_notify_error", details=str(e)[:200])


@treasury_bp.route("/treasury/bot-purchases/<int:req_id>/receipt")
@treasury_login_required
def treasury_bot_receipt(req_id):
    """Chek skrinini ko'rsatish — botdan kelgan bo'lsa Telegram CDN'dan,
    saytdan kelgan bo'lsa to'g'ridan-to'g'ri statik fayldan."""
    req = query_one("SELECT receipt_file_id, receipt_file_path, source FROM bot_purchase_requests WHERE id=?", (req_id,))
    if not req:
        abort(404)

    # Saytdan yuklangan fayl — to'g'ridan-to'g'ri yo'naltirish
    if req["receipt_file_path"]:
        return redirect(req["receipt_file_path"])

    if not req["receipt_file_id"]:
        abort(404)
    token = Config.TELEGRAM_BOT_TOKEN
    if not token:
        flash("Bot token sozlanmagan.", "error")
        return redirect(url_for(".treasury_bot_purchases"))
    try:
        import requests as _req
        r = _req.get(f"https://api.telegram.org/bot{token}/getFile",
                     params={"file_id": req["receipt_file_id"]}, timeout=10)
        d = r.json()
        if d.get("ok"):
            file_path = d["result"]["file_path"]
            return redirect(f"https://api.telegram.org/file/bot{token}/{file_path}")
    except Exception as e:
        log_action(None, "bot_receipt_error", details=str(e)[:200])
    flash("Chek olib bo'lmadi.", "error")
    return redirect(url_for(".treasury_bot_purchases"))


@treasury_bp.route("/treasury/history")
@treasury_login_required
def treasury_history():
    """G'azna to'liq kirim-chiqim tarixi — loyiha boshlanganidan barcha harakatlar.
    Filtrlar: yo'nalish (in/out/all), sabab, sana oraliq."""
    direction_filter = request.args.get("direction", "")
    reason_filter = request.args.get("reason", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")
    page = max(1, int(request.args.get("page", 1) or 1))
    per_page = 100

    where = ["1=1"]
    params = []
    if direction_filter in ("in", "out"):
        where.append("direction = ?")
        params.append(direction_filter)
    if reason_filter:
        # 'id_sale' -> shu prefix bilan boshlanadigan ham olinadi
        if reason_filter in ("id_sale", "admin_deposit"):
            where.append("(reason = ? OR reason LIKE ?)")
            params.extend([reason_filter, reason_filter + ":%"])
        else:
            where.append("reason = ?")
            params.append(reason_filter)
    if date_from:
        where.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        where.append("created_at <= ?")
        params.append(date_to + " 23:59:59")

    where_sql = " AND ".join(where)
    total_row = query_one(
        f"SELECT COUNT(*) c FROM treasury_fund_log WHERE {where_sql}", tuple(params)
    )
    total = total_row["c"] if total_row else 0
    offset = (page - 1) * per_page
    pages = max(1, (total + per_page - 1) // per_page)

    rows = query_all(
        f"""SELECT l.*, u.ism as user_ism, u.familiya as user_familiya, u.custom_id as user_custom_id,
                   ta.ism as treasury_ism
            FROM treasury_fund_log l
            LEFT JOIN users u ON u.id = l.user_id
            LEFT JOIN treasury_accounts ta ON ta.id = l.treasury_account_id
            WHERE {where_sql}
            ORDER BY l.id DESC
            LIMIT ? OFFSET ?""",
        tuple(params + [per_page, offset])
    )

    # Filtrdagi yig'indi
    sum_in = query_one(
        f"SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='in' AND {where_sql}",
        tuple(params)
    )["s"]
    sum_out = query_one(
        f"SELECT COALESCE(SUM(amount),0) s FROM treasury_fund_log WHERE direction='out' AND {where_sql}",
        tuple(params)
    )["s"]

    # Reasonlar ro'yxati (filtr dropdown uchun)
    reasons = query_all(
        """SELECT DISTINCT CASE
              WHEN reason LIKE 'id_sale:%' THEN 'id_sale'
              WHEN reason LIKE 'admin_deposit:%' THEN 'admin_deposit'
              ELSE reason
           END as r FROM treasury_fund_log ORDER BY r"""
    )

    return render_template(
        "treasury_history.html",
        rows=rows,
        total=total, page=page, pages=pages,
        sum_in=sum_in, sum_out=sum_out,
        balance=treasury_mod.get_fund_balance(),
        reasons=[r["r"] for r in reasons],
        filters={
            "direction": direction_filter,
            "reason": reason_filter,
            "date_from": date_from,
            "date_to": date_to,
        }
    )


