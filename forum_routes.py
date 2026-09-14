# ============================================================
# CYBER SHATS — Forum bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute, log_action

forum_bp = Blueprint("forum_bp", __name__)


def award_xp(user_id, amount):
    """app.py'dagi bilan bir xil — aylanma import'dan qochish uchun
    kechiktirilgan (lazy) import ishlatiladi."""
    from app import award_xp as _real_award_xp
    return _real_award_xp(user_id, amount)


# =================================================================
# FORUM
# =================================================================
@forum_bp.route("/forum")
@login_required
def forum():
    category = request.args.get("cat", "")
    sql = ("SELECT p.*, u.ism, u.familiya, u.avatar FROM forum_posts p JOIN users u ON u.id=p.user_id")
    args = ()
    if category:
        sql += " WHERE p.category=?"
        args = (category,)
    sql += " ORDER BY p.created_at DESC LIMIT 50"
    posts = query_all(sql, args)
    categories = query_all("SELECT category, COUNT(*) as c FROM forum_posts GROUP BY category")
    return render_template("forum.html", posts=posts, categories=categories, active_cat=category)


@forum_bp.route("/forum/new", methods=["POST"])
@login_required
def forum_new():
    user = get_current_user()
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    category = request.form.get("category", "umumiy")
    if not title or not body:
        flash("Sarlavha va matn to'ldirilishi shart.", "error")
        return redirect(url_for(".forum"))
    pid = execute("INSERT INTO forum_posts (user_id, title, body, category) VALUES (?,?,?,?)",
                  (user["id"], title, body, category))
    award_xp(user["id"], 10)
    log_action(user["id"], "forum_new", details=title, ip=request.remote_addr)
    flash("Mavzu muvaffaqiyatli yaratildi.", "success")
    return redirect(url_for(".forum_post", post_id=pid))


@forum_bp.route("/forum/<int:post_id>")
@login_required
def forum_post(post_id):
    post = query_one(
        "SELECT p.*, u.ism, u.familiya, u.avatar FROM forum_posts p JOIN users u ON u.id=p.user_id WHERE p.id=?",
        (post_id,))
    if not post:
        abort(404)
    execute("UPDATE forum_posts SET views = views + 1 WHERE id=?", (post_id,))
    replies = query_all(
        "SELECT r.*, u.ism, u.familiya, u.avatar, u.role FROM forum_replies r JOIN users u ON u.id=r.user_id "
        "WHERE r.post_id=? ORDER BY r.created_at ASC", (post_id,))
    return render_template("forum_post.html", post=post, replies=replies)


@forum_bp.route("/forum/<int:post_id>/reply", methods=["POST"])
@login_required
def forum_reply(post_id):
    user = get_current_user()
    body = request.form.get("body", "").strip()
    if body:
        execute("INSERT INTO forum_replies (post_id, user_id, body) VALUES (?,?,?)", (post_id, user["id"], body))
        execute("UPDATE forum_posts SET replies_count = replies_count + 1 WHERE id=?", (post_id,))
        award_xp(user["id"], 5)
        log_action(user["id"], "forum_reply", details=f"post:{post_id}", ip=request.remote_addr)
    return redirect(url_for(".forum_post", post_id=post_id))

