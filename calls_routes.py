# ============================================================
# CYBER SHATS — Voice/Video qo'ng'iroqlar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, abort
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from utils import resolve_user_id
import secrets

calls_bp = Blueprint("calls_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


@calls_bp.route("/qongiroqlar")
@login_required
def calls_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    calls = query_all(
        """SELECT cr.*, u1.ism as req_ism, u1.familiya as req_familiya,
                  u2.ism as target_ism, u2.familiya as target_familiya
           FROM call_requests cr
           JOIN users u1 ON u1.id = cr.requester_id
           JOIN users u2 ON u2.id = cr.target_id
           WHERE cr.requester_id=? OR cr.target_id=?
           ORDER BY cr.created_at DESC LIMIT 30""",
        (user["id"], user["id"])
    )
    return render_template("calls.html", calls=calls)


@calls_bp.route("/qongiroqlar/request", methods=["POST"])
@login_required
def calls_request():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import secrets
    user = get_current_user()
    recipient_raw = request.form.get("recipient", "").strip()
    call_type = request.form.get("call_type", "voice")
    target_id = resolve_user_id(recipient_raw.lstrip("#")) if recipient_raw else None
    if not target_id:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for(".calls_page"))
    room_code = secrets.token_hex(6)
    execute("INSERT INTO call_requests (requester_id, target_id, call_type, room_code) VALUES (?,?,?,?)",
            (user["id"], target_id, call_type, room_code))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (target_id, "Qo'ng'iroq so'rovi!", f"{user['ism']} sizga {call_type} qo'ng'iroq qilmoqchi.", "info"))
    flash("Qo'ng'iroq so'rovi yuborildi!", "success")
    return redirect(url_for(".calls_page"))


@calls_bp.route("/qongiroqlar/<int:call_id>/respond", methods=["POST"])
@login_required
def calls_respond(call_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    call = query_one("SELECT * FROM call_requests WHERE id=? AND target_id=?", (call_id, user["id"]))
    if not call:
        abort(404)
    new_status = request.form.get("status", "declined")
    execute("UPDATE call_requests SET status=? WHERE id=?", (new_status, call_id))
    flash("Javob yuborildi!", "success")
    return redirect(url_for(".calls_page"))

