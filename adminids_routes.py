# ============================================================
# CYBER SHATS — Admin ID va Auktsion boshqaruvi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import admin_required, super_admin_required
from db import query_one, query_all, execute, log_action
from utils import resolve_user_id
from ids import (get_premium_ids_list, get_vip_ids_list, admin_create_premium_id,
                 admin_delete_premium_id, admin_set_alphanumeric_id, admin_close_all_bidding_auctions,
                 admin_counter_offer, admin_accept_offer_at_asking, admin_reject_offer,
                 get_pending_sell_offers, finalize_auction, assign_vip_id, revoke_vip_id,
                 admin_update_premium_id_price)
import group_reports
import datetime

adminids_bp = Blueprint("adminids_bp", __name__)


@adminids_bp.route("/admin/ids")
@admin_required
def admin_ids():
    premium_ids = get_premium_ids_list()
    auctions = query_all("SELECT a.*, p.id_type FROM id_auctions a JOIN premium_ids p ON p.id=a.premium_id_id ORDER BY a.created_at DESC LIMIT 50")
    vip_ids = get_vip_ids_list()
    pending_sell_offers = get_pending_sell_offers()
    return render_template("admin_ids.html", premium_ids=premium_ids, auctions=auctions, vip_ids=vip_ids,
                           pending_sell_offers=pending_sell_offers)


@adminids_bp.route("/admin/ids/vip/assign", methods=["POST"])
@admin_required
def admin_vip_assign():
    """VIP maxsus ID (0-9) ni foydalanuvchiga tayinlash."""
    digit = request.form.get("digit", "").strip()
    identifier = request.form.get("user_id", "").strip()
    user_id = resolve_user_id(identifier)
    if user_id is None:
        flash(f"Foydalanuvchi topilmadi: \"{identifier}\". Saytdagi ID (custom_id), email yoki ichki raqamni kiriting.", "error")
        return redirect(url_for(".admin_ids") + "#vip")
    ok, msg = assign_vip_id(session["user_id"], digit, user_id)
    if ok:
        log_action(session["user_id"], "vip_id_assigned", details=f"digit:{digit},user:{user_id}",
                   ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids") + "#vip")


@adminids_bp.route("/admin/ids/vip/<digit>/revoke", methods=["POST"])
@admin_required
def admin_vip_revoke(digit):
    """VIP ID'ni egasidan qaytarib olish."""
    ok, msg = revoke_vip_id(digit)
    if ok:
        log_action(session["user_id"], "vip_id_revoked", details=f"digit:{digit}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids") + "#vip")


@adminids_bp.route("/admin/ids/close-auctions", methods=["POST"])
@super_admin_required
def admin_close_auctions():
    """ID auksionini (taklif-berish uslubi) butunlay yopadi — faol
    auktsionlardagi puldor qatnashchilarga pul qaytariladi."""
    ok, msg = admin_close_all_bidding_auctions()
    log_action(session["user_id"], "admin_close_bidding_auctions", details=msg, ip=request.remote_addr)
    flash(msg, "success")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/sell-offers/<int:offer_id>/counter", methods=["POST"])
@super_admin_required
def admin_id_sell_counter(offer_id):
    try:
        counter_price = int(request.form.get("counter_price", 0))
    except ValueError:
        counter_price = 0
    ok, msg = admin_counter_offer(session["user_id"], offer_id, counter_price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/sell-offers/<int:offer_id>/accept", methods=["POST"])
@super_admin_required
def admin_id_sell_accept(offer_id):
    disposition = request.form.get("disposition", "random_pool")
    try:
        marketplace_price = int(request.form.get("marketplace_price", 0)) or None
    except ValueError:
        marketplace_price = None
    ok, msg = admin_accept_offer_at_asking(session["user_id"], offer_id, disposition, marketplace_price)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/sell-offers/<int:offer_id>/reject", methods=["POST"])
@super_admin_required
def admin_id_sell_reject(offer_id):
    ok, msg = admin_reject_offer(session["user_id"], offer_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/grant-special", methods=["POST"])
@admin_required
def admin_grant_special_id():
    """FAQAT admin — harflar aralash maxsus ID beradi (masalan 'SHATS-1')."""
    target_identifier = request.form.get("target_identifier", "").strip()
    new_id = request.form.get("new_id", "").strip()
    ok, msg = admin_set_alphanumeric_id(session["user_id"], target_identifier, new_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/create", methods=["POST"])
@admin_required
def admin_create_premium_id_route():
    """Admin yangi premium ID (istalgan 7 xonali raqam) + narx kiritib sotuvga qo'shadi."""
    custom_id = request.form.get("custom_id", "").strip()
    id_type = request.form.get("id_type", "custom").strip() or "custom"
    try:
        base_price = int(request.form.get("base_price", 0))
    except ValueError:
        base_price = 0
    ok, msg = admin_create_premium_id(custom_id, base_price, id_type)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_create_premium_id",
                   details=f"id:{custom_id},price:{base_price}", ip=request.remote_addr)
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/<custom_id>/set-price", methods=["POST"])
@admin_required
def admin_set_premium_id_price(custom_id):
    """Admin mavjud premium IDning narxini o'zgartiradi."""
    try:
        base_price = int(request.form.get("base_price", 0))
    except ValueError:
        base_price = 0
    ok, msg = admin_update_premium_id_price(custom_id, base_price)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_update_premium_id_price",
                   details=f"id:{custom_id},price:{base_price}", ip=request.remote_addr)
        import group_reports
        group_reports.report_price_change([(f"ID #{custom_id}", None, str(base_price))])
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/<custom_id>/delete", methods=["POST"])
@admin_required
def admin_delete_premium_id_route(custom_id):
    """Admin premium IDni ro'yxatdan o'chiradi (faqat sotilmagan bo'lsa)."""
    ok, msg = admin_delete_premium_id(custom_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_delete_premium_id",
                   details=f"id:{custom_id}", ip=request.remote_addr)
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/create-auction", methods=["POST"])
@admin_required
def admin_create_auction():
    custom_id = request.form.get("custom_id", "").strip()
    start_price = int(request.form.get("start_price", 40000))
    hours = int(request.form.get("hours", 24))
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=? AND status='available'", (custom_id,))
    if not pid:
        flash("Bu ID mavjud emas yoki band.", "error")
        return redirect(url_for(".admin_ids"))
    import datetime
    ends = (datetime.datetime.now() + datetime.timedelta(hours=hours)).isoformat()
    execute("UPDATE premium_ids SET status='auction' WHERE custom_id=?", (custom_id,))
    execute(
        "INSERT INTO id_auctions (premium_id_id, custom_id, start_price, starts_at, ends_at, created_by) VALUES (?,?,?,datetime('now'),?,?)",
        (pid["id"], custom_id, start_price, ends, session["user_id"])
    )
    log_action(session["user_id"], "admin_create_auction", details=f"id:{custom_id}", ip=request.remote_addr)
    flash(f"#{custom_id} ID auktsiyonga qo'yildi ({hours} soat).", "success")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/finalize/<int:auction_id>", methods=["POST"])
@admin_required
def admin_finalize_auction(auction_id):
    finalize_auction(auction_id)
    flash("Auktsion yakunlandi.", "success")
    return redirect(url_for(".admin_ids"))


@adminids_bp.route("/admin/ids/give-id", methods=["POST"])
@admin_required
def admin_give_id():
    """Admin foydalanuvchiga premium ID beradi (bepul)."""
    identifier = request.form.get("user_id", "").strip()
    user_id = resolve_user_id(identifier)
    custom_id = request.form.get("custom_id", "").strip()
    if user_id is None:
        flash(f"Foydalanuvchi topilmadi: \"{identifier}\". Saytdagi ID (custom_id), email yoki ichki raqamni kiriting.", "error")
        return redirect(url_for(".admin_ids"))
    pid = query_one("SELECT * FROM premium_ids WHERE custom_id=?", (custom_id,))
    if not pid or pid["status"] not in ("available",):
        flash("ID mavjud emas yoki band.", "error")
        return redirect(url_for(".admin_ids"))
    import datetime
    execute("UPDATE premium_ids SET status='sold', owner_user_id=?, sold_at=? WHERE custom_id=?",
            (user_id, datetime.datetime.now().isoformat(), custom_id))
    execute("UPDATE users SET custom_id=? WHERE id=?", (custom_id, user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (user_id, f"Premium ID #{custom_id}",
             f"Sizga admin tomonidan #{custom_id} premium ID berildi!", "success"))
    log_action(session["user_id"], "admin_give_id", details=f"user:{user_id},id:{custom_id}", ip=request.remote_addr)
    flash(f"#{custom_id} ID foydalanuvchiga berildi.", "success")
    return redirect(url_for(".admin_ids"))

