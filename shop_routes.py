# ============================================================
# CYBER SHATS — Do'kon bo'limi (Blueprint)
# ============================================================
# Bu fayl — "0dan qayta yozish" so'ralganda men taklif qilgan
# YECHIM: kodning ISH MANTIG'I (sinalgan, ishlaydigan) SAQLANADI,
# lekin FAYL TUZILMASI professional, mantiqiy modullarga ajratiladi.
# Bu — 8600+ qatorli bitta app.py o'rniga, har bir domen (Do'kon,
# Do'stlik, Admin va h.k.) o'z faylida — bu HAQIQIY qayta qurish,
# lekin xavfsiz: har bir marshrut ko'chirilgandan keyin qayta sinaladi.
#
# Qamrab oladi: Sandiqlar (chests), Galichkalar (checkmarks),
# Ramkalar (frames), Koleksiya (collection).
import os
from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file, current_app
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
import chests as chests_mod
import collection as collection_mod
import frames_shop as frames_mod
import friends as friends_mod
from coins import get_balance

shop_bp = Blueprint("shop", __name__)


# =================================================================
# SANDIQLAR (loot box) TIZIMI
# =================================================================
@shop_bp.route("/chests")
@login_required
def chests_page():
    user = get_current_user()
    try:
        state = chests_mod.get_user_chest_state(user["id"])
    except Exception as e:
        current_app.logger.error(f"/chests: get_user_chest_state xato: {e}")
        state = {}
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/chests: get_balance xato: {e}")
        balance = 0
    try:
        my_friends = friends_mod.get_friends_list(user["id"])
    except Exception as e:
        current_app.logger.error(f"/chests: get_friends_list xato: {e}")
        my_friends = []
    return render_template("chests.html", state=state, balance=balance,
                           tariff_milestones=chests_mod.TARIFF_MILESTONES,
                           ticket_prices=chests_mod.TICKET_PRICES, my_friends=my_friends)


@shop_bp.route("/chests/buy-tickets", methods=["POST"])
@login_required
def chests_buy_tickets():
    user = get_current_user()
    chest_type = request.form.get("chest_type", "")
    qty = request.form.get("qty", "1")
    ok, msg = chests_mod.buy_tickets(user["id"], chest_type, qty)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".chests_page", highlight=chest_type))


@shop_bp.route("/api/chests/open/tariff", methods=["POST"])
@api_login_required
def api_chests_open_tariff():
    user = get_current_user()
    
    qty = 1
    if request.is_json:
        qty = int(request.json.get("qty", 1))
    else:
        qty = int(request.form.get("qty", 1) or 1)
        
    if qty not in (1, 5):
        qty = 1
        
    results = []
    total_keys = 0
    
    for _ in range(qty):
        res = chests_mod.open_tariff_chest(user["id"])
        if not res.get("ok"):
            if not results:
                return api_response(False, error=res.get("error"))
            break
        results.append(res)
        total_keys += res.get("keys_won", 0)
        
    if qty == 1 or len(results) == 1:
        return api_response(True, data=results[0])
        
    return api_response(True, data={
        "results": results,
        "total_keys": total_keys,
        "opened": len(results),
        "multiple": True
    })


@shop_bp.route("/api/chests/open/id", methods=["POST"])
@api_login_required
def api_chests_open_id():
    user = get_current_user()
    
    qty = 1
    if request.is_json:
        qty = int(request.json.get("qty", 1))
    else:
        qty = int(request.form.get("qty", 1) or 1)
        
    if qty not in (1, 5):
        qty = 1
        
    results = []
    total_keys = 0
    
    for _ in range(qty):
        res = chests_mod.open_id_chest(user["id"])
        if not res.get("ok"):
            if not results:
                return api_response(False, error=res.get("error"))
            break
        results.append(res)
        total_keys += res.get("keys_won", 0)
        
    if qty == 1 or len(results) == 1:
        return api_response(True, data=results[0])
        
    return api_response(True, data={
        "results": results,
        "total_keys": total_keys,
        "opened": len(results),
        "multiple": True
    })


@shop_bp.route("/chests/gift-tickets", methods=["POST"])
@login_required
def chests_gift_tickets():
    user = get_current_user()
    friend_identifier = request.form.get("friend_id", "").strip()
    chest_type = request.form.get("chest_type", "")
    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        qty = 0
    friend = query_one("SELECT id FROM users WHERE id=? OR custom_id=?", (friend_identifier, friend_identifier))
    if not friend:
        flash("Do'st topilmadi.", "error")
        return redirect(url_for(".chests_page"))
    ok, msg = chests_mod.gift_tickets(user["id"], friend["id"], chest_type, qty)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".chests_page"))


@shop_bp.route("/checkmarks")
@login_required
def checkmarks_shop_page():
    user = get_current_user()
    try:
        items = chests_mod.get_checkmark_shop()
    except Exception as e:
        current_app.logger.error(f"/checkmarks: get_checkmark_shop xato: {e}")
        items = []
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/checkmarks: get_balance xato: {e}")
        balance = 0
    try:
        keys_row = query_one("SELECT chest_keys FROM users WHERE id=?", (user["id"],))
        keys = keys_row["chest_keys"] if keys_row else 0
    except Exception as e:
        current_app.logger.error(f"/checkmarks: chest_keys xato: {e}")
        keys = 0
    return render_template("checkmarks_shop.html", items=items, balance=balance, keys=keys)


@shop_bp.route("/checkmarks/buy", methods=["POST"])
@login_required
def checkmarks_buy():
    user = get_current_user()
    badge_key = request.form.get("badge_key", "")
    pay_with = request.form.get("pay_with", "code")
    ok, msg = chests_mod.buy_checkmark(user["id"], badge_key, pay_with)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".checkmarks_shop_page"))


@shop_bp.route("/frames")
@login_required
def frames_shop_page():
    user = get_current_user()
    try:
        purchasable = frames_mod.get_purchasable_frames()
    except Exception as e:
        current_app.logger.error(f"/frames: get_purchasable_frames xato: {e}")
        purchasable = []
    try:
        tier_frames = frames_mod.get_tier_frames()
    except Exception as e:
        current_app.logger.error(f"/frames: get_tier_frames xato: {e}")
        tier_frames = []
    try:
        owned_keys = {r["frame_key"] for r in query_all(
            "SELECT frame_key FROM user_owned_frames WHERE user_id=?", (user["id"],))}
    except Exception as e:
        current_app.logger.error(f"/frames: owned_keys xato: {e}")
        owned_keys = set()
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/frames: get_balance xato: {e}")
        balance = 0
    try:
        active_frame_val = user["active_frame"]
    except (KeyError, IndexError):
        active_frame_val = None  # ustun hali bazada yo'q bo'lsa — sahifa baribir ochiladi
    return render_template("frames_shop.html", purchasable=purchasable, tier_frames=tier_frames,
                           owned_keys=owned_keys, balance=balance, my_plan=user["plan"],
                           active_frame=active_frame_val)


@shop_bp.route("/frames/buy", methods=["POST"])
@login_required
def frames_buy():
    user = get_current_user()
    frame_key = request.form.get("frame_key", "")
    ok, msg = frames_mod.buy_frame(user["id"], frame_key)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".frames_shop_page"))


@shop_bp.route("/frames/set-active", methods=["POST"])
@login_required
def frames_set_active():
    user = get_current_user()
    frame_key = request.form.get("frame_key", "")
    ok, msg = frames_mod.set_active_frame(user["id"], frame_key)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".frames_shop_page"))


# =================================================================
# KOLEKSIYA (100+5 haykalcha)
# =================================================================
@shop_bp.route("/collection")
@login_required
def collection_page():
    user = get_current_user()
    try:
        items = collection_mod.get_user_collection(user["id"])
    except Exception as e:
        current_app.logger.error(f"/collection: get_user_collection xato: {e}")
        items = []
    try:
        pinned_levels = {r["level"] for r in query_all(
            "SELECT level FROM user_pinned_statuettes WHERE user_id=?", (user["id"],))}
    except Exception as e:
        current_app.logger.error(f"/collection: pinned_levels xato: {e}")
        pinned_levels = set()
    unlocked_count = sum(1 for i in items if i.get("unlocked"))
    try:
        mystery_row = query_one("SELECT chest_tickets_mystery FROM users WHERE id=?", (user["id"],))
        mystery_tickets = mystery_row["chest_tickets_mystery"] if mystery_row else 0
    except Exception as e:
        current_app.logger.error(f"/collection: mystery_tickets xato: {e}")
        mystery_tickets = 0
    try:
        keys_row = query_one("SELECT chest_keys FROM users WHERE id=?", (user["id"],))
        keys = keys_row["chest_keys"] if keys_row else 0
    except Exception as e:
        current_app.logger.error(f"/collection: keys xato: {e}")
        keys = 0
    try:
        balance = get_balance(user["id"])
    except Exception as e:
        current_app.logger.error(f"/collection: get_balance xato: {e}")
        balance = 0
    return render_template("collection.html", items=items, pinned_levels=pinned_levels,
                           unlocked_count=unlocked_count, mystery_tickets=mystery_tickets,
                           keys=keys, balance=balance, key_redeem_cost=collection_mod.KEY_REDEEM_COST,
                           tier1_price=collection_mod.tier1_price)


@shop_bp.route("/collection/open-mystery", methods=["POST"])
@api_login_required
def api_collection_open_mystery():
    user = get_current_user()
    result = collection_mod.open_mystery_chest(user["id"])
    return api_response(result.get("ok", False), data=result if result.get("ok") else None,
                        error=result.get("error"))


@shop_bp.route("/collection/buy-tier1/<int:level>", methods=["POST"])
@login_required
def collection_buy_tier1(level):
    user = get_current_user()
    ok, msg = collection_mod.buy_tier1_statuette(user["id"], level)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".collection_page"))


@shop_bp.route("/collection/redeem-keys", methods=["POST"])
@api_login_required
def api_collection_redeem_keys():
    user = get_current_user()
    result = collection_mod.redeem_keys_for_statuette(user["id"])
    return api_response(result.get("ok", False), data=result if result.get("ok") else None,
                        error=result.get("error"))


@shop_bp.route("/collection/pin/<int:level>", methods=["POST"])
@login_required
def collection_pin(level):
    user = get_current_user()
    ok, msg = collection_mod.pin_statuette(user["id"], level)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".collection_page"))


@shop_bp.route("/collection/unpin/<int:level>", methods=["POST"])
@login_required
def collection_unpin(level):
    user = get_current_user()
    ok, msg = collection_mod.unpin_statuette(user["id"], level)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".collection_page"))


@shop_bp.route("/collection/statuette/<int:level>.svg")
def collection_statuette_svg(level):
    """DIQQAT: nomi tarixiy sabablarga ko'ra '.svg' bilan tugaydi, lekin
    endi bu yo'l HAQIQIY rasm (agar yuklangan bo'lsa) yoki SVG generatorni
    aqlli tarzda tanlaydi — shablonlarni o'zgartirish shart emas."""
    if collection_mod.has_real_image(level):
        img_path = os.path.join(collection_mod.STATUETTE_IMG_DIR, f"{level}.webp")
        return send_file(img_path, mimetype="image/webp",
                         max_age=604800)
    svg = collection_mod.generate_statuette_svg(level, size=200)
    return svg, 200, {"Content-Type": "image/svg+xml", "Cache-Control": "public, max-age=604800"}
