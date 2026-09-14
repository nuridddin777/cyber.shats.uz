# ============================================================
# CYBER SHATS — SHATS LIVE bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

shatslive_bp = Blueprint("shatslive_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()



# =================================================================
# SHATS LIVE — MAXSUS
# =================================================================
@shatslive_bp.route("/shats-live")
@login_required
def shats_live_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    streams = query_all(
        """SELECT ls.*, u.ism, u.familiya FROM live_streams ls
           JOIN users u ON u.id = ls.host_id
           ORDER BY (ls.status='live') DESC, ls.scheduled_at DESC LIMIT 30"""
    )
    return render_template("shats_live.html", streams=streams)


@shatslive_bp.route("/shats-live/schedule", methods=["POST"])
@login_required
def shats_live_schedule():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    scheduled_at = request.form.get("scheduled_at", "").strip()
    if not title or not scheduled_at:
        flash("Sarlavha va sana kiritilishi shart.", "error")
        return redirect(url_for(".shats_live_page"))
    execute(
        "INSERT INTO live_streams (title, description, host_id, scheduled_at) VALUES (?,?,?,?)",
        (title, description, user["id"], scheduled_at)
    )
    flash("Efir rejalashtirildi!", "success")
    return redirect(url_for(".shats_live_page"))


@shatslive_bp.route("/shats-live/<int:stream_id>/go-live", methods=["POST"])
@login_required
def shats_live_go_live(stream_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    stream = query_one("SELECT * FROM live_streams WHERE id=?", (stream_id,))
    if not stream or stream["host_id"] != user["id"]:
        flash("Ruxsat yo'q.", "error")
        return redirect(url_for(".shats_live_page"))
    execute("UPDATE live_streams SET status='live' WHERE id=?", (stream_id,))
    flash("Efir boshlandi!", "success")
    return redirect(url_for(".shats_live_page"))


@shatslive_bp.route("/shats-live/<int:stream_id>/end", methods=["POST"])
@login_required
def shats_live_end(stream_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    stream = query_one("SELECT * FROM live_streams WHERE id=?", (stream_id,))
    if not stream or stream["host_id"] != user["id"]:
        flash("Ruxsat yo'q.", "error")
        return redirect(url_for(".shats_live_page"))
    execute("UPDATE live_streams SET status='ended' WHERE id=?", (stream_id,))
    flash("Efir yakunlandi.", "success")
    return redirect(url_for(".shats_live_page"))


# =================================================================
