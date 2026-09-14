# ============================================================
# CYBER SHATS — Freelance bozori bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

freelance_bp = Blueprint("freelance_bp", __name__)


def _require_hacker_plan():
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _require_hacker_plan as _real_fn
    return _real_fn()



# =================================================================
# FREELANCE BOZORI (MAXSUS)
# =================================================================
@freelance_bp.route("/freelance")
@login_required
def freelance_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    gigs = query_all(
        """SELECT g.*, u.ism, u.familiya, u.custom_id FROM freelance_gigs g
           JOIN users u ON u.id = g.user_id WHERE g.status='open' ORDER BY g.created_at DESC LIMIT 50"""
    )
    return render_template("freelance.html", gigs=gigs)


@freelance_bp.route("/freelance/create", methods=["POST"])
@login_required
def freelance_create():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    gig_type = request.form.get("gig_type", "offer")
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    try:
        price = int(request.form.get("price_code", 0))
    except ValueError:
        price = 0
    if title and description:
        execute("INSERT INTO freelance_gigs (user_id, gig_type, title, description, price_code) VALUES (?,?,?,?,?)",
                (user["id"], gig_type, title, description, price))
        flash("E'lon joylandi!", "success")
    return redirect(url_for(".freelance_page"))


@freelance_bp.route("/freelance/<int:gig_id>/respond", methods=["POST"])
@login_required
def freelance_respond(gig_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    message = request.form.get("message", "").strip()
    if message:
        execute("INSERT INTO freelance_responses (gig_id, user_id, message) VALUES (?,?,?)",
                (gig_id, user["id"], message))
        gig = query_one("SELECT * FROM freelance_gigs WHERE id=?", (gig_id,))
        if gig:
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (gig["user_id"], "Yangi javob!", f"E'loningizga '{gig['title']}' javob keldi.", "info"))
        flash("Javobingiz yuborildi!", "success")
    return redirect(url_for(".freelance_page"))
