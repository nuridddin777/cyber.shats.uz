# ============================================================
# CYBER SHATS — CODE (Coins), Promo, Dizayn zakaz bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app, jsonify
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response, resolve_user_id
from coins import (get_balance, add_coins, spend_coins, award_course_completion,
                   buy_pro_with_coins, buy_cyber_pro_with_coins, buy_vip_with_coins,
                   buy_course_with_coins, get_transactions, transfer_coins)
from pricing import get_price, get_pricing
import coins_purchase
import friends as friends_mod
import chests as chests_mod
import group_reports
from config import Config
import os
import datetime

coins_bp = Blueprint("coins_bp", __name__)


@coins_bp.route("/coins")
@login_required
def coins_page():
    user = get_current_user()
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/coins: get_balance xato: {e}")
        balance = 0
    try:
        txns = get_transactions(user["id"], 30)
    except Exception as e:
        current_app.logger.error(f"/coins: get_transactions xato: {e}")
        txns = []
    p = get_pricing()
    is_pro = user.get("plan") in ("pro", "cyber_pro", "vip", "enterprise")
    try:
        ticket_prices = chests_mod.TICKET_PRICES
    except Exception as e:
        current_app.logger.error(f"/coins: TICKET_PRICES xato: {e}")
        ticket_prices = {"tariff": {"1": 1, "10": 8}, "id": {"1": 3, "10": 27}, "mystery": {"1": 5, "10": 45}}
    return render_template("coins.html", balance=balance, txns=txns,
                           pro_cost=p["pro_price_code"],
                           cyber_pro_cost=p["cyber_pro_price_code"],
                           vip_cost=p["vip_price_code"],
                           hacker_cost=p["hacker_price_code"],
                           vip_enabled=p["vip_enabled"] in (1, "1", True),
                           ai_cost=p["ai_weekly_price_code"],
                           course_reward=p["course_reward_code"],
                           paid_course_code=p["paid_course_code_default"],
                           transfer_fee_percent=0 if is_pro else p["coin_transfer_fee_percent"],
                           code_to_som_rate=p.get("code_to_som_rate", 10000),
                           ticket_prices=ticket_prices,
                           is_pro=is_pro)


@coins_bp.route("/coins/transfer", methods=["POST"])
@login_required
def coins_transfer():
    user = get_current_user()
    recipient_raw = request.form.get("recipient", "").strip()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    target_id = resolve_user_id(recipient_raw.lstrip("#")) if recipient_raw else None

    if not target_id:
        flash("Qabul qiluvchi topilmadi. ID (#0000) yoki email kiriting.", "error")
        return redirect(url_for(".coins_page"))

    ok, msg = transfer_coins(user["id"], target_id, amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".coins_page"))


# =================================================================
# SAYTDAN TO'G'RIDAN-TO'G'RI CODE SOTIB OLISH (botsiz, ID+karta+chek)
# =================================================================
CODE_PURCHASE_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}
CODE_PURCHASE_UPLOAD_DIR = os.path.join("static", "uploads", "receipts")


def _save_receipt_file(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in CODE_PURCHASE_ALLOWED_EXT:
        return None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(CODE_PURCHASE_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(CODE_PURCHASE_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    return f"/static/uploads/receipts/{safe_name}"


@coins_bp.route("/coins/buy")
@login_required
def coins_buy_page():
    user = get_current_user()
    requests_list = coins_purchase.get_user_purchase_requests(user["id"])
    packages = coins_purchase.get_packages_with_prices()
    from pricing import get_price
    import payment_gateway
    return render_template(
        "coins_buy.html",
        cards=coins_purchase.PAYMENT_CARDS,
        card_holder=coins_purchase.CARD_HOLDER,
        packages=packages,
        min_amount=coins_purchase.MIN_AMOUNT,
        requests_list=requests_list,
        my_custom_id=user.get("custom_id"),
        code_to_som_rate=get_price("code_to_som_rate"),
        card_providers=payment_gateway.get_available_providers(),
        oneid_verified=bool(user.get("oneid_verified")),
        oneid_required_above=Config.ONEID_REQUIRED_ABOVE_UZS,
    )


@coins_bp.route("/coins/buy/card", methods=["POST"])
@login_required
def coins_buy_card():
    """Karta orqali (Click/Payme/Uzum) real-vaqtli to'lov — avtomatik CODE beriladi."""
    import payment_gateway
    user = get_current_user()
    provider = request.form.get("provider", "")

    if not payment_gateway._provider_configured(provider):
        flash("Karta orqali tezkor to'lov hozircha vaqtincha yopiq. Iltimos, \"Chek yuklab so'rov yuborish\" "
              "bo'limidan foydalaning.", "error")
        return redirect(url_for(".coins_buy_page"))

    card_type = request.form.get("card_type", "")
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    if amount < coins_purchase.MIN_AMOUNT:
        flash(f"Minimal miqdor: {coins_purchase.MIN_AMOUNT:,} CODE.", "error")
        return redirect(url_for(".coins_buy_page"))

    # Katta summalarda OneID tasdiqlash majburiy (firibgarlikka qarshi)
    if amount >= Config.ONEID_REQUIRED_ABOVE_UZS and not user.get("oneid_verified"):
        flash("Bu summada CODE sotib olish uchun avval OneID orqali shaxsingizni tasdiqlang.", "error")
        return redirect(url_for(".coins_buy_page"))

    packages = coins_purchase.get_packages_with_prices()
    price_uzs = amount
    for p in packages:
        if p["amount"] == amount:
            price_uzs = p["price"]
            break

    ok, msg, data = payment_gateway.create_payment_order(
        user["id"], price_uzs, amount, provider, card_type
    )
    if not ok:
        flash(msg, "error")
        return redirect(url_for(".coins_buy_page"))
    return redirect(data["checkout_url"])


@coins_bp.route("/api/promo/check", methods=["POST"])
@api_login_required
def api_promo_check():
    """DIQQAT: bu endi xariddan CHEGIRMA berish emas — promo kod endi
    mustaqil, to'g'ridan-to'g'ri CODE bonusi (xarid shart emas). Shu
    sabab bu eski AJAX-tekshiruv endpointi endi ishlatilmaydi; promo
    kodni faollashtirish uchun /promo/redeem ishlatiladi."""
    return api_response(False, error="Promo kod endi xariddan chegirma bermaydi — /promo sahifasidan faollashtiring.")


@coins_bp.route("/coins/buy/submit", methods=["POST"])
@login_required
def coins_buy_submit():
    user = get_current_user()
    custom_id = request.form.get("custom_id", "").strip().lstrip("#")
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    receipt_path = None
    if "receipt" in request.files:
        receipt_path = _save_receipt_file(request.files["receipt"])
        if request.files["receipt"].filename and not receipt_path:
            flash("Fayl turi noto'g'ri. Faqat rasm (png/jpg) yoki PDF qabul qilinadi.", "error")
            return redirect(url_for(".coins_buy_page"))

    ok, msg, rid = coins_purchase.create_site_purchase_request(
        user["id"], custom_id, amount, receipt_path
    )
    if ok:
        import group_reports
        p = get_pricing()
        group_reports.report_code_purchase(user["id"], amount, amount * p.get("code_to_som_rate", 10000))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".coins_buy_page"))


@coins_bp.route("/promo", methods=["GET", "POST"])
@login_required
def promo_page():
    """Promo kod faollashtirish — mustaqil CODE bonusi (xarid shart emas)."""
    if request.method == "POST":
        user = get_current_user()
        code = request.form.get("code", "")
        ok, msg = coins_purchase.redeem_promo_code(code, user["id"])
        flash(msg, "success" if ok else "error")
        return redirect(url_for(".promo_page"))
    return render_template("promo.html")


# =================================================================
# DIZAYN ZAKAZ BERISH — G'aznaga yuboriladi, G'azna narx belgilaydi
# =================================================================
@coins_bp.route("/design-order", methods=["GET", "POST"])
@login_required
def design_order_page():
    user = get_current_user()
    if request.method == "POST":
        description = request.form.get("description", "").strip()
        if not description or len(description) < 10:
            flash("Iltimos, xohlagan dizayiningizni batafsilroq tasvirlab bering (kamida 10 belgi).", "error")
            return redirect(url_for(".design_order_page"))
        try:
            execute("INSERT INTO design_orders (user_id, description, status) VALUES (?,?,'pending')",
                    (user["id"], description))
            flash("Dizayn zakazingiz G'aznaga yuborildi. Ular ko'rib chiqib, narx belgilaydi.", "success")
        except Exception as e:
            current_app.logger.error(f"/design-order POST: INSERT xato: {e}")
            flash("Vaqtinchalik xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.", "error")
        return redirect(url_for(".design_order_page"))
    try:
        my_orders = query_all(
            "SELECT * FROM design_orders WHERE user_id=? ORDER BY created_at DESC", (user["id"],))
    except Exception as e:
        current_app.logger.error(f"/design-order: my_orders xato: {e}")
        my_orders = []
    return render_template("design_order.html", my_orders=my_orders)


@coins_bp.route("/design-order/<int:order_id>/pay", methods=["POST"])
@login_required
def design_order_pay(order_id):
    """Foydalanuvchi G'azna belgilagan narxni to'laydi — dizayn buyurtmasi tasdiqlanadi."""
    user = get_current_user()
    order = query_one("SELECT * FROM design_orders WHERE id=? AND user_id=?", (order_id, user["id"]))
    if not order or order["status"] != "quoted":
        flash("Bu buyurtma to'lovga tayyor emas.", "error")
        return redirect(url_for(".design_order_page"))
    ok, msg = spend_coins(user["id"], order["quoted_price"], "design_order_payment", order_id)
    if not ok:
        flash(f"{order['quoted_price']} CODE kerak, balansingiz yetarli emas.", "error")
        return redirect(url_for(".design_order_page"))
    execute("UPDATE design_orders SET status='paid', updated_at=datetime('now') WHERE id=?", (order_id,))
    execute("UPDATE treasury_fund SET balance=balance+?, updated_at=datetime('now') WHERE id=1",
            (order["quoted_price"],))
    execute("INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
            (order["quoted_price"], f"Dizayn zakazi to'landi #{order_id}", user["id"]))
    flash("To'lov qabul qilindi! Dizaynchilarimiz tez orada siz bilan bog'lanishadi.", "success")
    return redirect(url_for(".design_order_page"))


@coins_bp.route("/api/coins/buy")
@api_login_required
def api_coins_buy_requests():
    """Foydalanuvchi o'z so'rovlari holatini tekshirishi uchun (real-vaqt yangilanish)."""
    user = get_current_user()
    rows = coins_purchase.get_user_purchase_requests(user["id"], 10)
    return api_response(True, data={"requests": rows})


@coins_bp.route("/api/coins/transfer", methods=["POST"])
@api_login_required
def api_coins_transfer():
    """Chat ichidan tanga jo'natish uchun JSON endpoint."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    try:
        to_user_id = int(data.get("to_user_id", 0))
        amount = int(data.get("amount", 0))
    except (TypeError, ValueError):
        return api_response(False, error="Noto'g'ri ma'lumot")
    ok, msg = transfer_coins(user["id"], to_user_id, amount)
    if ok:
        return api_response(True, data={"message": msg, "new_balance": get_balance(user["id"])})
    return api_response(False, error=msg)


@coins_bp.route("/coins/buy-pro", methods=["POST"])
@login_required
def coins_buy_pro():
    user = get_current_user()
    ok, msg = buy_pro_with_coins(user["id"])
    if ok:
        import group_reports
        p = get_pricing()
        group_reports.report_plan_purchase(user["id"], "PRO", p["pro_price_code"])
        flash(msg, "success")
    else:
        flash(msg, "error")
    return redirect(url_for(".coins_page"))


@coins_bp.route("/coins/buy-cyber-pro", methods=["POST"])
@login_required
def coins_buy_cyber_pro():
    """Cyber Pro versiyasini sotib olish — Pro'dan kuchliroq."""
    user = get_current_user()
    ok, msg = buy_cyber_pro_with_coins(user["id"])
    if ok:
        import group_reports
        p = get_pricing()
        group_reports.report_plan_purchase(user["id"], "CYBER PRO", p["cyber_pro_price_code"])
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "Cyber Pro!",
                 "Cyber Pro faollashtirildi! Endi Office yo'nalishi ochildi. "
                 "Har bir kurs bitirishda 1,000 CODE bonus olasiz, P2P o'tkazmalar komissiyasiz.", "success"))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".coins_page"))


@coins_bp.route("/coins/buy-vip", methods=["POST"])
@login_required
def coins_buy_vip():
    """SHATS CYBER PRO — eng kuchli versiya."""
    user = get_current_user()
    ok, msg = buy_vip_with_coins(user["id"])
    if ok:
        import group_reports
        p = get_pricing()
        group_reports.report_plan_purchase(user["id"], "VIP (SHATS CYBER PRO)", p["vip_price_code"])
        friends_mod.log_activity(user["id"], "plan_upgrade", "VIP")
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "🔥 SHATS CYBER PRO!",
                 "SHATS CYBER PRO versiyasi faollashtirildi! Eng yuqori darajadagi imkoniyatlar ochildi.", "success"))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".coins_page"))


@coins_bp.route("/coins/buy-hacker", methods=["POST"])
@login_required
def coins_buy_hacker():
    """MAXSUS versiya — binafsha-haker uslubi."""
    from coins import buy_hacker_with_coins
    user = get_current_user()
    ok, msg = buy_hacker_with_coins(user["id"])
    if ok:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user["id"], "⚡ MAXSUS versiya!",
                 "MAXSUS versiyasi faollashtirildi! Yon menyuda yangi bo'limlarni ko'ring.", "success"))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".coins_page"))


@coins_bp.route("/redeem", methods=["GET", "POST"])
@login_required
def redeem_page():
    """MAXSUS tarifni kod orqali faollashtirish sahifasi."""
    import redeem_codes
    if request.method == "POST":
        user = get_current_user()
        code = request.form.get("code", "")
        ok, msg = redeem_codes.redeem(user["id"], code)
        flash(msg, "success" if ok else "error")
        return redirect(url_for(".redeem_page"))
    return render_template("redeem.html")

