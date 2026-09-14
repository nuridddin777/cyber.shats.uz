# ============================================================
# CYBER SHATS — Shaxsiy xabarlar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
from messaging import (get_conversations, get_thread, send_message, mark_thread_read,
                       get_unread_total, search_users)
from pricing import get_price

messages_bp = Blueprint("messages_bp", __name__)


# =================================================================
# SHAXSIY XABARLAR — Telegram uslubidagi foydalanuvchidan-foydalanuvchiga chat
# =================================================================

@messages_bp.route("/messages")
@login_required
def messages_page():
    user = get_current_user()
    q = request.args.get("q", "").strip()
    conversations = get_conversations(user["id"])
    search_results = search_users(q, user["id"]) if q else []
    return render_template("messages.html", conversations=conversations,
                           search_results=search_results, search_q=q)


@messages_bp.route("/messages/<int:peer_id>")
@login_required
def messages_thread(peer_id):
    user = get_current_user()
    peer = query_one("SELECT id, ism, familiya, avatar, plan, role, custom_id FROM users WHERE id=?", (peer_id,))
    if not peer:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for(".messages_page"))
    thread = get_thread(user["id"], peer_id, 200)
    mark_thread_read(user["id"], peer_id)
    conversations = get_conversations(user["id"])
    return render_template("messages_thread.html", peer=peer, thread=thread,
                           conversations=conversations,
                           transfer_fee_percent=0 if user.get("plan") in ("pro", "cyber_pro", "vip", "enterprise") else get_price("coin_transfer_fee_percent"))


@messages_bp.route("/messages/<int:peer_id>/send", methods=["POST"])
@login_required
def messages_send(peer_id):
    user = get_current_user()
    body = request.form.get("body", "")
    ok, msg = send_message(user["id"], peer_id, body)
    if not ok:
        flash(msg, "error")
    return redirect(url_for(".messages_thread", peer_id=peer_id))


@messages_bp.route("/api/messages/<int:peer_id>/poll")
@api_login_required
def api_messages_poll(peer_id):
    """Real-vaqtda yangilanish uchun polling endpoint: oxirgi xabarlardan keyingilarini qaytaradi."""
    user = get_current_user()
    try:
        after_id = int(request.args.get("after_id", 0))
    except ValueError:
        after_id = 0
    rows = query_all(
        """SELECT * FROM private_messages
           WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)) AND id > ?
           ORDER BY id ASC""",
        (user["id"], peer_id, peer_id, user["id"], after_id)
    )
    if rows:
        mark_thread_read(user["id"], peer_id)
    return api_response(True, data={"messages": rows, "unread_total": get_unread_total(user["id"])})


@messages_bp.route("/api/messages/<int:peer_id>/send", methods=["POST"])
@api_login_required
def api_messages_send(peer_id):
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    ok, msg = send_message(user["id"], peer_id, data.get("body", ""))
    if not ok:
        return api_response(False, error=msg)
    return api_response(True, data={"message": msg})
