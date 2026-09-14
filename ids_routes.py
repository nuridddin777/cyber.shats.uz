# ============================================================
# CYBER SHATS — ID va Random ID bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app, session
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from utils import api_response
from coins import get_balance
from ids import (set_user_id, get_premium_ids_list, buy_premium_id,
                 generate_random_id_offer, confirm_random_id,
                 REGULAR_ID_CHANGE_PRICE, create_sell_offer, get_user_sell_offer, cancel_sell_offer,
                 user_respond_to_counter, get_user_id_history,
                 reserve_random_id, get_active_reservation, cancel_reservation, buy_reserved_id,
                 RESERVATION_HOURS)
import group_reports

ids_bp = Blueprint("ids_bp", __name__)


@ids_bp.route("/my-id")
@login_required
def my_id_page():
    """MUHIM (tuzatilgan xato): avval bu sahifa 4-5 ta turli funksiyani
    (get_premium_ids_list, get_user_sell_offer, get_user_id_history va
    h.k.) HIMOYASIZ chaqirar edi. Agar ULARDAN BIRONTASI ishlatadigan
    jadval (masalan user_id_history yoki id_sell_offers) serverda biror
    sababdan (masalan migratsiya hali to'liq ishlamagan bo'lsa) mavjud
    bo'lmasa — BUTUN SAHIFA 500 xato berardi. Endi HAR BIR ma'lumot
    manbai ALOHIDA himoyalangan — bittasi ishlamasa ham, sahifa
    bo'sh/standart qiymat bilan baribir ochiladi."""
    user = get_current_user()

    try:
        premium_ids = get_premium_ids_list()
    except Exception as e:
        current_app.logger.error(f"/my-id: get_premium_ids_list xato: {e}")
        premium_ids = []

    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/my-id: get_balance xato: {e}")
        balance = 0

    next_id_change_cost = REGULAR_ID_CHANGE_PRICE

    try:
        my_sell_offer = get_user_sell_offer(user["id"])
    except Exception as e:
        current_app.logger.error(f"/my-id: get_user_sell_offer xato: {e}")
        my_sell_offer = None

    try:
        id_history = get_user_id_history(user["id"])
    except Exception as e:
        current_app.logger.error(f"/my-id: get_user_id_history xato: {e}")
        id_history = []

    return render_template("my_id.html", premium_ids=premium_ids, auctions=[],
                           balance=balance, user=user, next_id_change_cost=next_id_change_cost,
                           my_sell_offer=my_sell_offer, id_history=id_history)


@ids_bp.route("/my-id/sell", methods=["POST"])
@login_required
def my_id_sell():
    user = get_current_user()
    try:
        asking_price = int(request.form.get("asking_price", 0))
    except ValueError:
        asking_price = 0
    ok, msg = create_sell_offer(user["id"], asking_price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".my_id_page"))


@ids_bp.route("/my-id/sell/<int:offer_id>/cancel", methods=["POST"])
@login_required
def my_id_sell_cancel(offer_id):
    user = get_current_user()
    ok, msg = cancel_sell_offer(user["id"], offer_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".my_id_page"))


@ids_bp.route("/my-id/sell/<int:offer_id>/respond", methods=["POST"])
@login_required
def my_id_sell_respond(offer_id):
    user = get_current_user()
    accept = request.form.get("decision") == "accept"
    ok, msg = user_respond_to_counter(user["id"], offer_id, accept)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".my_id_page"))


@ids_bp.route("/my-id/change", methods=["POST"])
@login_required
def change_my_id():
    user = get_current_user()
    new_id = request.form.get("new_id", "").strip()
    if len(new_id) != 7 or not new_id.isdigit():
        flash("ID 7 ta raqamdan iborat bo'lishi kerak.", "error")
        return redirect(url_for(".my_id_page"))
    # Premium IDlarni tekshir (endi bazadan)
    is_premium = query_one("SELECT id FROM premium_ids WHERE custom_id=?", (new_id,))
    if is_premium:
        flash("Bu premium ID — uni sotib olish kerak.", "error")
        return redirect(url_for(".my_id_page"))
    ok, msg = set_user_id(user["id"], new_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".my_id_page"))


@ids_bp.route("/my-id/buy/<custom_id>", methods=["POST"])
@login_required
def buy_premium_id_route(custom_id):
    user = get_current_user()
    pid = query_one("SELECT base_price FROM premium_ids WHERE custom_id=?", (custom_id,))
    ok, msg = buy_premium_id(user["id"], custom_id)
    if ok:
        import group_reports
        group_reports.report_id_sale(user["id"], custom_id, pid["base_price"] if pid else 0)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".my_id_page"))


@ids_bp.route("/auction")
@login_required
def auction_page():
    # DIQQAT: ID auksioni (taklif-berish uslubi) YOPILDI, o'rniga Random ID
    # tizimi keldi — endi bu yerga kirgan foydalanuvchi yangi sahifaga
    # yo'naltiriladi.
    return redirect(url_for(".random_id_page"))


@ids_bp.route("/id-random")
@login_required
def random_id_page():
    user = get_current_user()
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/id-random: get_balance xato: {e}")
        balance = 0
    try:
        active_reservation = get_active_reservation(user["id"])
    except Exception as e:
        current_app.logger.error(f"/id-random: get_active_reservation xato: {e}")
        active_reservation = None
    return render_template("random_id.html", balance=balance, active_reservation=active_reservation,
                           reservation_hours=RESERVATION_HOURS)


@ids_bp.route("/id-random/spin", methods=["POST"])
@login_required
def random_id_spin():
    """Foydalanuvchi 'aylantirish' tugmasini bosganda — tasodifiy ID +
    narx hisoblab, sessiyaga vaqtincha saqlaymiz (tasdiqlashda qayta
    tekshiriladi, sessiya orqali "narxni almashtirish" imkonsiz)."""
    offer = generate_random_id_offer()
    session["random_id_offer"] = offer
    return api_response(True, data=offer)


@ids_bp.route("/id-random/confirm", methods=["POST"])
@login_required
def random_id_confirm():
    user = get_current_user()
    offer = session.get("random_id_offer")
    if not offer:
        flash("Avval 'Aylantirish' tugmasini bosing.", "error")
        return redirect(url_for(".random_id_page"))
    ok, msg = confirm_random_id(user["id"], offer["custom_id"], offer["price"])
    if ok:
        session.pop("random_id_offer", None)
        import group_reports
        group_reports.report_id_sale(user["id"], offer["custom_id"], offer["price"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".random_id_page"))


@ids_bp.route("/id-random/reserve", methods=["POST"])
@login_required
def random_id_reserve():
    user = get_current_user()
    offer = session.get("random_id_offer")
    if not offer:
        flash("Avval 'Aylantirish' tugmasini bosing.", "error")
        return redirect(url_for(".random_id_page"))
    ok, msg = reserve_random_id(user["id"], offer["custom_id"], offer["price"])
    if ok:
        session.pop("random_id_offer", None)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".random_id_page"))


@ids_bp.route("/id-random/reservation/<int:reservation_id>/buy", methods=["POST"])
@login_required
def random_id_reservation_buy(reservation_id):
    user = get_current_user()
    ok, msg = buy_reserved_id(user["id"], reservation_id)
    if ok:
        import group_reports
        res = query_one("SELECT custom_id, price FROM id_reservations WHERE id=?", (reservation_id,))
        if res:
            group_reports.report_id_sale(user["id"], res["custom_id"], res["price"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".random_id_page"))


@ids_bp.route("/id-random/reservation/<int:reservation_id>/cancel", methods=["POST"])
@login_required
def random_id_reservation_cancel(reservation_id):
    user = get_current_user()
    ok, msg = cancel_reservation(user["id"], reservation_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".random_id_page"))
