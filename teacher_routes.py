# ============================================================
# CYBER SHATS — O'qituvchi paneli bo'limi (Blueprint)
# ============================================================
from functools import wraps as _wraps
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute, log_action
import social

teacher_bp = Blueprint("teacher_bp", __name__)


def teacher_required(view):
    @_wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user or not (user.get("is_teacher") or user.get("role") in ("admin", "super_admin")):
            flash("Bu bo'lim faqat tasdiqlangan o'qituvchilar uchun.", "error")
            return redirect(url_for("profile"))
        return view(*args, **kwargs)
    return wrapped


def _save_teacher_file(file_storage, allowed_ext, upload_dir, max_bytes=8 * 1024 * 1024):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _save_teacher_file as _real_fn
    return _real_fn(file_storage, allowed_ext, upload_dir, max_bytes)


@teacher_bp.route("/teacher")
@teacher_required
def teacher_dashboard():
    user = get_current_user()
    my_groups = query_all(
        "SELECT * FROM groups WHERE owner_id=? ORDER BY created_at DESC", (user["id"],))
    my_channels = query_all(
        "SELECT * FROM channels WHERE owner_id=? ORDER BY created_at DESC", (user["id"],))
    application = query_one(
        "SELECT * FROM teacher_applications WHERE user_id=? AND status='approved' ORDER BY id DESC LIMIT 1",
        (user["id"],))
    return render_template("teacher_dashboard.html", my_groups=my_groups, my_channels=my_channels,
                           application=application)


@teacher_bp.route("/teacher/groups/create", methods=["GET", "POST"])
@teacher_required
def teacher_create_group():
    user = get_current_user()
    if request.method == "POST":
        name = request.form.get("name", "")
        description = request.form.get("description", "")
        is_public = request.form.get("is_public") == "1"
        ok, msg, gid = social.teacher_create_group(user["id"], name, description, is_public)
        flash(msg, "success" if ok else "error")
        if ok:
            return redirect(url_for("groups_bp.group_detail", group_id=gid))
        return redirect(url_for(".teacher_create_group"))
    private_count = query_one("SELECT COUNT(*) c FROM groups WHERE owner_id=? AND is_public=0",
                              (user["id"],))["c"]
    next_tax = social.GROUP_TAX_BASE if private_count < 5 else social.GROUP_TAX_ABOVE_5
    return render_template("teacher_create_group.html", private_count=private_count, next_tax=next_tax)


@teacher_bp.route("/teacher/channels/create", methods=["GET", "POST"])
@teacher_required
def teacher_create_channel():
    user = get_current_user()
    if request.method == "POST":
        name = request.form.get("name", "")
        description = request.form.get("description", "")
        ok, msg, cid = social.teacher_create_channel(user["id"], name, description)
        flash(msg, "success" if ok else "error")
        if ok:
            return redirect(url_for("groups_bp.channel_detail", channel_id=cid))
        return redirect(url_for(".teacher_create_channel"))
    count = query_one("SELECT COUNT(*) c FROM channels WHERE owner_id=?", (user["id"],))["c"]
    next_tax = social.CHANNEL_TAX_BASE if count < 5 else social.CHANNEL_TAX_ABOVE_5
    return render_template("teacher_create_channel.html", count=count, next_tax=next_tax)


@teacher_bp.route("/teacher/courses/post", methods=["GET", "POST"])
@teacher_required
def teacher_post_course():
    """O'qituvchi tomonidan yangi kurs mavzusi joylashtirish — Word/PDF yuklab
    yoki to'g'ridan-to'g'ri yozib. Admin tomonidan ko'rib chiqiladi."""
    user = get_current_user()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content_text = request.form.get("content_text", "").strip()
        material_file = request.files.get("material_file")
        if not title:
            flash("Mavzu sarlavhasi majburiy.", "error")
            return redirect(url_for(".teacher_post_course"))
        material_path = None
        if material_file and material_file.filename:
            material_path, err = _save_teacher_file(
                material_file, {"pdf", "doc", "docx"}, os.path.join("static", "uploads", "teacher_materials"))
            if err:
                flash("Fayl PDF/DOC/DOCX bo'lishi va 8 MB dan oshmasligi kerak.", "error")
                return redirect(url_for(".teacher_post_course"))
        if not content_text and not material_path:
            flash("Matn yozing yoki fayl yuklang.", "error")
            return redirect(url_for(".teacher_post_course"))
        execute(
            """INSERT INTO notifications (user_id, title, body, type)
               SELECT id, ?, ?, 'admin' FROM users WHERE role IN ('admin','super_admin')""",
            (f"O'qituvchidan yangi mavzu: {title}",
             f"{user['familiya']} {user['ism']} \"{title}\" mavzusini joyladi." +
             (f" Fayl: {material_path}" if material_path else ""))
        )
        log_action(user["id"], "teacher_post_course", details=title)
        flash("Mavzu adminga yuborildi — tasdiqlangach kursga qo'shiladi.", "success")
        return redirect(url_for(".teacher_dashboard"))
    return render_template("teacher_post_course.html")

