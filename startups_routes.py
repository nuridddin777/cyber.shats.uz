# ============================================================
# CYBER SHATS — Startaplar va Auksionlar (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from auth import get_current_user, login_required, admin_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
import startups as startups_mod
import os
import datetime

startups_bp = Blueprint("startups_bp", __name__)


def _require_hacker_plan():
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


def _check_panel(panel_key: str):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _check_panel as _real_check_panel
    return _real_check_panel(panel_key)


STARTUP_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
STARTUP_UPLOAD_DIR = os.path.join("static", "uploads", "startups")


def _startup_save_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in STARTUP_ALLOWED_EXT:
        return None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(STARTUP_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(STARTUP_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    return f"/static/uploads/startups/{safe_name}"


@startups_bp.route("/startups")
@login_required
def startups_list():
    check = _check_panel('startups')
    if check: return check
    user = get_current_user()
    approved = startups_mod.get_approved_startups()
    my_startups = startups_mod.get_user_startups(user["id"])
    liked_ids = set()
    if approved:
        ids = [s["id"] for s in approved]
        placeholders = ",".join("?" for _ in ids)
        liked_rows = query_all(
            f"SELECT startup_id FROM startup_likes WHERE user_id=? AND startup_id IN ({placeholders})",
            tuple([user["id"]] + ids)
        )
        liked_ids = {r["startup_id"] for r in liked_rows}
    return render_template("startups_list.html", approved=approved, my_startups=my_startups,
                           liked_ids=liked_ids, categories=startups_mod.CATEGORIES)


@startups_bp.route("/startups/create", methods=["POST"])
@login_required
def startups_create():
    user = get_current_user()
    image_path = None
    if "image" in request.files:
        image_path = _startup_save_image(request.files["image"])
    ok, msg, sid = startups_mod.create_startup(
        user["id"], request.form.get("name", ""), request.form.get("description", ""),
        image_path, request.form.get("link_url", ""), request.form.get("category", "boshqa")
    )
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".startups_list"))


@startups_bp.route("/startups/<int:startup_id>")
@login_required
def startup_detail(startup_id):
    startup = startups_mod.get_startup(startup_id)
    if not startup or (startup["status"] != "approved" and startup["user_id"] != get_current_user()["id"]):
        abort(404)
    startups_mod.increment_view(startup_id)
    like_count = startups_mod.get_like_count(startup_id)
    user_liked = startups_mod.is_liked(startup_id, get_current_user()["id"])
    return render_template("startup_detail.html", startup=startup, like_count=like_count, user_liked=user_liked)


@startups_bp.route("/startups/<int:startup_id>/toggle-help", methods=["POST"])
@login_required
def startup_toggle_help(startup_id):
    """MAXSUS: loyiha egasi 'yordam kerak / mentor so'rayapman' belgisini qo'yishi mumkin."""
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    startup = startups_mod.get_startup(startup_id)
    if not startup or startup["user_id"] != user["id"]:
        abort(404)
    field = request.form.get("field")
    if field not in ("needs_help", "mentor_requested"):
        abort(400)
    current = startup[field]
    execute(f"UPDATE startups SET {field}=? WHERE id=?", (0 if current else 1, startup_id))
    flash("Yangilandi!", "success")
    return redirect(url_for(".startup_detail", startup_id=startup_id))


@startups_bp.route("/api/startups/<int:startup_id>/like", methods=["POST"])
@api_login_required
def api_startup_like(startup_id):
    user = get_current_user()
    liked, count = startups_mod.toggle_like(startup_id, user["id"])
    return api_response(True, data={"liked": liked, "like_count": count})


@startups_bp.route("/startups/<int:startup_id>/delete", methods=["POST"])
@login_required
def startup_delete(startup_id):
    user = get_current_user()
    is_admin = user.get("role") in ("admin", "super_admin")
    ok, msg = startups_mod.delete_startup(startup_id, user["id"], is_admin)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".startups_list"))


# Admin — startaplarni tasdiqlash
@startups_bp.route("/admin/startups")
@admin_required
def admin_startups():
    status = request.args.get("status", "pending")
    startups_data = startups_mod.get_all_startups_admin(status if status != "all" else None)
    return render_template("admin_startups.html", startups=startups_data, status_filter=status)


@startups_bp.route("/admin/startups/<int:startup_id>/review", methods=["POST"])
@admin_required
def admin_startups_review(startup_id):
    decision = request.form.get("decision")
    ok, msg = startups_mod.review_startup(startup_id, session["user_id"], decision)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_startups"))


@startups_bp.route("/admin/startups/<int:startup_id>/auction", methods=["POST"])
@admin_required
def admin_startup_create_auction(startup_id):
    """Admin tasdiqlangan loyihani auksionga qo'yadi."""
    try:
        start_price = int(request.form.get("start_price") or 0) or None
    except ValueError:
        start_price = None
    try:
        duration_days = int(request.form.get("duration_days") or 0) or None
    except ValueError:
        duration_days = None
    ok, msg, aid = startups_mod.create_auction(startup_id, session["user_id"], start_price, duration_days)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_startups"))


@startups_bp.route("/admin/startup-auctions/<int:auction_id>/cancel", methods=["POST"])
@admin_required
def admin_startup_auction_cancel(auction_id):
    ok, msg = startups_mod.cancel_auction(auction_id, session["user_id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".startup_auctions_list"))


@startups_bp.route("/admin/startup-auctions/<int:auction_id>/extend", methods=["POST"])
@admin_required
def admin_startup_auction_extend(auction_id):
    """Auksion muddatini uzaytirish yoki qisqartirish (admin)."""
    import datetime
    try:
        hours = int(request.form.get("hours", 0))
    except ValueError:
        hours = 0
    if not hours:
        flash("Soat miqdori noto'g'ri.", "error")
        return redirect(url_for(".startup_auctions_list"))
    from db import execute as db_execute, query_one as db_q
    auction = db_q("SELECT ends_at FROM startup_auctions WHERE id=?", (auction_id,))
    if not auction:
        flash("Auksion topilmadi.", "error")
        return redirect(url_for(".startup_auctions_list"))
    try:
        old_end = datetime.datetime.fromisoformat(auction["ends_at"])
    except Exception:
        old_end = datetime.datetime.now()
    new_end = (old_end + datetime.timedelta(hours=hours)).isoformat()
    db_execute("UPDATE startup_auctions SET ends_at=? WHERE id=?", (new_end, auction_id))
    flash(f"Auksion muddati {'+' if hours>0 else ''}{hours} soat o'zgartirildi.", "success")
    return redirect(url_for(".startup_auctions_list"))


# =================================================================
# STARTAPLAR AUKSIONI — foydalanuvchi tomondan
# =================================================================
@startups_bp.route("/startup-auctions")
@login_required
def startup_auctions_list():
    startups_mod.check_and_finalize_expired_auctions()
    auctions = startups_mod.get_active_auctions()
    return render_template("startup_auctions_list.html", auctions=auctions)


@startups_bp.route("/startup-auctions/<int:auction_id>")
@login_required
def startup_auction_detail(auction_id):
    startups_mod.check_and_finalize_expired_auctions()
    auction = startups_mod.get_auction(auction_id)
    if not auction:
        abort(404)
    bids = startups_mod.get_auction_bids(auction_id)
    return render_template("startup_auction_detail.html", auction=auction, bids=bids)


@startups_bp.route("/startup-auctions/<int:auction_id>/bid", methods=["POST"])
@login_required
def startup_auction_bid(auction_id):
    user = get_current_user()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = startups_mod.place_bid(auction_id, user["id"], amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".startup_auction_detail", auction_id=auction_id))
