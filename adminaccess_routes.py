# ============================================================
# CYBER SHATS — Page Access Management
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import admin_required
from db import execute, query_all, query_one, log_action

adminaccess_bp = Blueprint("adminaccess_bp", __name__)

@adminaccess_bp.route("/admin/page-access")
@admin_required
def admin_page_access():
    pages = query_all("SELECT * FROM page_access ORDER BY id DESC")
    return render_template("admin_page_access.html", pages=pages)

@adminaccess_bp.route("/admin/page-access/add", methods=["POST"])
@admin_required
def admin_page_access_add():
    path = request.form.get("path", "").strip()
    title = request.form.get("title", "").strip()
    is_active = 1 if request.form.get("is_active") == "1" else 0
    
    if not path or not title:
        flash("Yo'l va sarlavha kiritilishi shart.", "error")
        return redirect(url_for("adminaccess_bp.admin_page_access"))
        
    if not path.startswith("/"):
        path = "/" + path
        
    existing = query_one("SELECT id FROM page_access WHERE path=?", (path,))
    if existing:
        flash("Bu yo'l allaqachon qo'shilgan.", "error")
    else:
        execute("INSERT INTO page_access (path, title, is_active) VALUES (?, ?, ?)", (path, title, is_active))
        log_action(session.get("user_id"), "add_page_access", details=f"path:{path},active:{is_active}", ip=request.remote_addr)
        flash("Sahifa ruxsatnomasi qo'shildi.", "success")
        
    return redirect(url_for("adminaccess_bp.admin_page_access"))

@adminaccess_bp.route("/admin/page-access/toggle/<int:page_id>", methods=["POST"])
@admin_required
def admin_page_access_toggle(page_id):
    page = query_one("SELECT * FROM page_access WHERE id=?", (page_id,))
    if not page:
        flash("Sahifa topilmadi.", "error")
        return redirect(url_for("adminaccess_bp.admin_page_access"))
        
    new_status = 1 if page["is_active"] == 0 else 0
    execute("UPDATE page_access SET is_active=? WHERE id=?", (new_status, page_id))
    log_action(session.get("user_id"), "toggle_page_access", details=f"id:{page_id},new_status:{new_status}", ip=request.remote_addr)
    status_str = "Faol" if new_status else "Nofaol"
    flash(f"'{page['title']}' sahifasi holati o'zgartirildi.", "success")
    return redirect(url_for("adminaccess_bp.admin_page_access"))

@adminaccess_bp.route("/admin/page-access/delete/<int:page_id>", methods=["POST"])
@admin_required
def admin_page_access_delete(page_id):
    page = query_one("SELECT * FROM page_access WHERE id=?", (page_id,))
    if page:
        execute("DELETE FROM page_access WHERE id=?", (page_id,))
        log_action(session.get("user_id"), "delete_page_access", details=f"id:{page_id}", ip=request.remote_addr)
        flash("Sahifa ruxsatnomasi o'chirildi.", "success")
    return redirect(url_for("adminaccess_bp.admin_page_access"))
