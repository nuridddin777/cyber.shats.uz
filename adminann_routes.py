# ============================================================
# CYBER SHATS — Admin E'lonlar va Yangiliklar (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required, api_login_required
from db import query_one, query_all, execute, log_action
from utils import api_response
import announcements as ann_mod

adminann_bp = Blueprint("adminann_bp", __name__)



# =================================================================
# ANNOUNCEMENTS (admin e'lonlari) — ovozli broadcast
# =================================================================
@adminann_bp.route("/admin/announcements")
@admin_required
def admin_announcements():
    announcements_list = ann_mod.list_all_announcements()
    return render_template("admin_announcements.html", announcements=announcements_list)


@adminann_bp.route("/admin/announcements/create", methods=["POST"])
@admin_required
def admin_announcements_create():
    title = request.form.get("title", "")
    body = request.form.get("body", "")
    priority = request.form.get("priority", "normal")
    target_plans = request.form.get("target_plans", "all")
    voice_enabled = request.form.get("voice_enabled") == "on"
    ok, msg, ann_id = ann_mod.create_announcement(
        session["user_id"], title, body, priority, target_plans, voice_enabled
    )
    log_action(session["user_id"], "announcement_created",
               details=f"id:{ann_id},target:{target_plans}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_announcements"))


@adminann_bp.route("/admin/announcements/<int:ann_id>/toggle", methods=["POST"])
@admin_required
def admin_announcements_toggle(ann_id):
    ann_mod.toggle_announcement(ann_id)
    flash("E'lon holati o'zgartirildi.", "success")
    return redirect(url_for(".admin_announcements"))


@adminann_bp.route("/admin/announcements/<int:ann_id>/delete", methods=["POST"])
@admin_required
def admin_announcements_delete(ann_id):
    ann_mod.delete_announcement(ann_id)
    flash("E'lon o'chirildi.", "success")
    return redirect(url_for(".admin_announcements"))


@adminann_bp.route("/api/announcements/pending")
@api_login_required
def api_announcements_pending():
    """Foydalanuvchi hali ko'rmagan faol e'lonlar (front-end real-vaqtda chaqiradi)."""
    user = get_current_user()
    pending = ann_mod.get_active_announcements_for_user(user["id"])
    return api_response(True, data={"announcements": pending})


# =================================================================
# YANGILIKLAR (bosh sahifadagi "Yangiliklar" bo'limi) — admin CRUD
# =================================================================
@adminann_bp.route("/admin/news")
@admin_required
def admin_news():
    news_list = query_all("SELECT * FROM news ORDER BY published_at DESC")
    return render_template("admin_news.html", news_list=news_list)


@adminann_bp.route("/admin/news/create", methods=["POST"])
@admin_required
def admin_news_create():
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary", "").strip()
    source = request.form.get("source", "CYBER SHATS").strip()
    category = request.form.get("category", "umumiy").strip()
    url_ = request.form.get("url", "").strip()
    if not title:
        flash("Sarlavha majburiy.", "error")
        return redirect(url_for(".admin_news"))
    execute("INSERT INTO news (title, summary, source, category, published_at, url) VALUES (?,?,?,?,date('now'),?)",
            (title, summary, source, category, url_ or None))
    log_action(session["user_id"], "news_created", details=title[:80], ip=request.remote_addr)
    flash("Yangilik qo'shildi.", "success")
    return redirect(url_for(".admin_news"))


@adminann_bp.route("/admin/news/<int:news_id>/edit", methods=["POST"])
@admin_required
def admin_news_edit(news_id):
    title = request.form.get("title", "").strip()
    summary = request.form.get("summary", "").strip()
    source = request.form.get("source", "").strip()
    category = request.form.get("category", "").strip()
    url_ = request.form.get("url", "").strip()
    if not title:
        flash("Sarlavha bo'sh bo'lishi mumkin emas.", "error")
        return redirect(url_for(".admin_news"))
    execute("UPDATE news SET title=?, summary=?, source=?, category=?, url=? WHERE id=?",
            (title, summary, source, category, url_ or None, news_id))
    log_action(session["user_id"], "news_edited", details=f"news:{news_id}", ip=request.remote_addr)
    flash("Yangilik yangilandi.", "success")
    return redirect(url_for(".admin_news"))


@adminann_bp.route("/admin/news/<int:news_id>/delete", methods=["POST"])
@admin_required
def admin_news_delete(news_id):
    execute("DELETE FROM news WHERE id=?", (news_id,))
    log_action(session["user_id"], "news_deleted", details=f"news:{news_id}", ip=request.remote_addr)
    flash("Yangilik o'chirildi.", "success")
    return redirect(url_for(".admin_news"))


@adminann_bp.route("/api/announcements/<int:ann_id>/seen", methods=["POST"])
@api_login_required
def api_announcements_seen(ann_id):
    user = get_current_user()
    ann_mod.mark_announcement_viewed(user["id"], ann_id)
    return api_response(True)

