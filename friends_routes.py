# ============================================================
# CYBER SHATS — Do'stlik bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from auth import get_current_user, login_required
from db import query_one, query_all, execute
import friends as friends_mod
import datetime as _dt

friends_bp = Blueprint("friends", __name__)


@friends_bp.route("/friends")
@login_required
def friends_page():
    """MUHIM (tuzatilgan xato): xuddi /my-id, /chests va boshqa
    sahifalardagi kabi — bu yerda ham 6 ta turli ma'lumot manbai
    HIMOYASIZ chaqirilar edi. Endi har biri alohida himoyalangan."""
    user = get_current_user()

    try:
        friends = friends_mod.get_friends_list(user["id"])
    except Exception as e:
        current_app.logger.error(f"/friends: get_friends_list xato: {e}")
        friends = []
    try:
        received = friends_mod.get_pending_received(user["id"])
    except Exception as e:
        current_app.logger.error(f"/friends: get_pending_received xato: {e}")
        received = []
    try:
        sent = friends_mod.get_pending_sent(user["id"])
    except Exception as e:
        current_app.logger.error(f"/friends: get_pending_sent xato: {e}")
        sent = []

    search_q = request.args.get("q", "").strip()
    try:
        if search_q:
            discover = query_all(
                """SELECT id, ism, familiya, custom_id, avatar_path, plan, level, exclusive_theme, role
                   FROM users WHERE role IN ('student','admin','super_admin','mentor') AND id != ?
                   AND (custom_id LIKE ? OR ism LIKE ? OR familiya LIKE ?)
                   ORDER BY level DESC LIMIT 30""",
                (user["id"], f"%{search_q}%", f"%{search_q}%", f"%{search_q}%")
            )
        else:
            discover = query_all(
                """SELECT id, ism, familiya, custom_id, avatar_path, plan, level, exclusive_theme, role
                   FROM users WHERE role IN ('student','admin','super_admin','mentor') AND id != ?
                   ORDER BY xp DESC LIMIT 20""",
                (user["id"],)
            )
    except Exception as e:
        current_app.logger.error(f"/friends: discover xato: {e}")
        discover = []

    friend_ids = {f["id"] for f in friends}
    try:
        activity_feed = friends_mod.get_friends_activity_feed(user["id"], limit=25)
    except Exception as e:
        current_app.logger.error(f"/friends: get_friends_activity_feed xato: {e}")
        activity_feed = []
    try:
        friends_leaderboard = friends_mod.get_friends_leaderboard(user["id"])
    except Exception as e:
        current_app.logger.error(f"/friends: get_friends_leaderboard xato: {e}")
        friends_leaderboard = []
    import datetime as _dt
    return render_template("friends.html", friends=friends, received=received, sent=sent,
                           discover=discover, search_q=search_q, friend_ids=friend_ids,
                           activity_feed=activity_feed, friends_leaderboard=friends_leaderboard,
                           my_id=user["id"], today_str=_dt.date.today().isoformat())


@friends_bp.route("/friends/request/<int:target_id>", methods=["POST"])
@login_required
def friends_send_request(target_id):
    user = get_current_user()
    ok, msg = friends_mod.send_friend_request(user["id"], target_id)
    flash(msg, "success" if ok else "error")
    return redirect(request.referrer or url_for(".friends_page"))


@friends_bp.route("/friends/respond/<int:requester_id>", methods=["POST"])
@login_required
def friends_respond(requester_id):
    user = get_current_user()
    accept = request.form.get("decision") == "accept"
    ok, msg = friends_mod.respond_friend_request(user["id"], requester_id, accept)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".friends_page"))


@friends_bp.route("/friends/remove/<int:other_id>", methods=["POST"])
@login_required
def friends_remove(other_id):
    user = get_current_user()
    ok, msg = friends_mod.remove_friend(user["id"], other_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".friends_page"))


@friends_bp.route("/friends/compare/<int:other_id>")
@login_required
def friends_compare(other_id):
    user = get_current_user()
    if friends_mod.get_friendship_status(user["id"], other_id) != "friends":
        flash("Faqat do'stlaringiz bilan solishtirish mumkin.", "error")
        return redirect(url_for(".friends_page"))
    me_stats, other_stats = friends_mod.get_comparison_stats(user["id"], other_id)
    return render_template("friends_compare.html", me=me_stats, other=other_stats)
