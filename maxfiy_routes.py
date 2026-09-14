# ============================================================
# CYBER SHATS — Maxfiy chat bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from utils import resolve_user_id
import secret_chat

maxfiy_bp = Blueprint("maxfiy_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


# MAXFIY CHAT (MAXSUS)
# =================================================================
@maxfiy_bp.route("/maxfiy-chat")
@login_required
def secret_chat_list_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import secret_chat
    user = get_current_user()
    chats = secret_chat.get_user_chats(user["id"])
    return render_template("secret_chat_list.html", chats=chats)


@maxfiy_bp.route("/maxfiy-chat/start", methods=["POST"])
@login_required
def secret_chat_start():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import secret_chat
    user = get_current_user()
    recipient_raw = request.form.get("recipient", "").strip()
    target_id = resolve_user_id(recipient_raw.lstrip("#")) if recipient_raw else None
    if not target_id:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(url_for(".secret_chat_list_page"))
    chat = secret_chat.get_or_create_chat(user["id"], target_id)
    return redirect(url_for(".secret_chat_thread", chat_id=chat["id"]))


@maxfiy_bp.route("/maxfiy-chat/<int:chat_id>", methods=["GET", "POST"])
@login_required
def secret_chat_thread(chat_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    import secret_chat
    user = get_current_user()
    chat = query_one("SELECT * FROM secret_chats WHERE id=? AND (user_a_id=? OR user_b_id=?)",
                      (chat_id, user["id"], user["id"]))
    if not chat:
        abort(404)
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        ttl = int(request.form.get("ttl_seconds", 60))
        if content:
            secret_chat.send_message(chat_id, user["id"], content, ttl)
        return redirect(url_for(".secret_chat_thread", chat_id=chat_id))
    peer_id = chat["user_b_id"] if chat["user_a_id"] == user["id"] else chat["user_a_id"]
    peer = query_one("SELECT * FROM users WHERE id=?", (peer_id,))
    messages = secret_chat.get_messages(chat_id, user["id"])
    return render_template("secret_chat_thread.html", chat=chat, peer=peer, messages=messages)


