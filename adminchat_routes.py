# ============================================================
# CYBER SHATS — Admin Chat bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required, admin_required
from db import query_one, query_all, execute

adminchat_bp = Blueprint("adminchat_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


# =================================================================

# ADMIN CHAT — MAXSUS
# =================================================================
@adminchat_bp.route("/admin-chat", methods=["GET", "POST"])
@login_required
def admin_chat_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            execute("INSERT INTO admin_chat_messages (user_id, sender, message) VALUES (?,?,?)",
                    (user["id"], "user", message))
        return redirect(url_for(".admin_chat_page"))
    messages = query_all("SELECT * FROM admin_chat_messages WHERE user_id=? ORDER BY created_at", (user["id"],))
    return render_template("admin_chat.html", messages=messages)


@adminchat_bp.route("/admin/admin-chat")
@admin_required
def admin_chat_inbox():
    """Admin uchun barcha MAXSUS foydalanuvchilar murojaatlari ro'yxati."""
    threads = query_all(
        """SELECT u.id as user_id, u.ism, u.familiya, u.custom_id,
                  MAX(m.created_at) as last_at,
                  SUM(CASE WHEN m.sender='user' AND m.read_at IS NULL THEN 1 ELSE 0 END) as unread
           FROM admin_chat_messages m JOIN users u ON u.id = m.user_id
           GROUP BY u.id ORDER BY last_at DESC"""
    )
    return render_template("admin_chat_inbox.html", threads=threads)


@adminchat_bp.route("/admin/admin-chat/<int:user_id>", methods=["GET", "POST"])
@admin_required
def admin_chat_thread(user_id):
    admin_user = get_current_user()
    target = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target:
        abort(404)
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            execute("INSERT INTO admin_chat_messages (user_id, sender, message) VALUES (?,'admin',?)",
                    (user_id, message))
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (user_id, "Admin javob berdi", "Admin chat'da yangi xabar bor.", "info"))
        return redirect(url_for(".admin_chat_thread", user_id=user_id))
    execute("UPDATE admin_chat_messages SET read_at=datetime('now') WHERE user_id=? AND sender='user' AND read_at IS NULL",
            (user_id,))
    messages = query_all("SELECT * FROM admin_chat_messages WHERE user_id=? ORDER BY created_at", (user_id,))
    return render_template("admin_chat_thread.html", messages=messages, target=target)
