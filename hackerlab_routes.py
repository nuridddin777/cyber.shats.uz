# ============================================================
# CYBER SHATS — HackerLab (Maxsus versiya) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required, admin_required, api_login_required
from db import query_one, query_all, execute, log_action
from utils import api_response
from pricing import get_price
from coins import get_balance
import hacker_lab as hacker_lab_mod
import terminal_sim
import os


def _check_panel(panel_key: str):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _check_panel as _real_check_panel
    return _real_check_panel(panel_key)


hackerlab_bp = Blueprint("hackerlab_bp", __name__)


@hackerlab_bp.route("/hacker-lab")
@login_required
def hacker_lab():
    check = _check_panel('hacker_lab')
    if check: return check
    user = get_current_user()

    can, reason = hacker_lab_mod.can_enter(user["id"])

    if reason == "consent_required":
        return redirect(url_for(".hacker_lab_consent"))
    if reason == "access_required":
        return redirect(url_for(".hacker_lab_access_page"))
    if not can:
        flash(reason, "error")
        return redirect(url_for("dashboard"))

    # Yo'nalish tanlanmagan bo'lsa — tanlash sahifasiga
    if not user.get("selected_direction_id"):
        return redirect(url_for(".hacker_lab_choose_direction"))

    direction = query_one("SELECT * FROM directions WHERE id=?", (user["selected_direction_id"],))
    if not direction:
        return redirect(url_for(".hacker_lab_choose_direction"))

    term_type = terminal_sim.get_terminal_type(direction["slug"])
    return render_template("hacker_lab.html", direction=direction, term_type=term_type)


@hackerlab_bp.route("/hacker-lab/choose-direction", methods=["GET", "POST"])
@login_required
def hacker_lab_choose_direction():
    """Foydalanuvchi Hacker Lab uchun asosiy yo'nalishini tanlaydi/o'zgartiradi.
    Panel shu yo'nalishga moslashadi."""
    user = get_current_user()
    if request.method == "POST":
        try:
            direction_id = int(request.form.get("direction_id", 0))
        except ValueError:
            direction_id = 0
        direction = query_one("SELECT id FROM directions WHERE id=?", (direction_id,))
        if not direction:
            flash("Yo'nalish topilmadi.", "error")
            return redirect(url_for(".hacker_lab_choose_direction"))
        execute("UPDATE users SET selected_direction_id=? WHERE id=?", (direction_id, user["id"]))
        log_action(user["id"], "hacker_lab_direction_selected", details=f"dir:{direction_id}")
        flash("Yo'nalish tanlandi! Panel shunga moslashtirildi.", "success")
        return redirect(url_for(".hacker_lab"))

    directions = query_all("SELECT * FROM directions WHERE slug NOT IN ('smm','targetolog','logistika') ORDER BY sort_order")
    return render_template("hacker_lab_choose_direction.html", directions=directions)


@hackerlab_bp.route("/hacker-lab/consent", methods=["GET", "POST"])
@login_required
def hacker_lab_consent():
    user = get_current_user()
    if hacker_lab_mod.has_consented(user["id"]):
        return redirect(url_for(".hacker_lab"))
    if request.method == "POST":
        if request.form.get("agree") == "1":
            hacker_lab_mod.record_consent(user["id"], request.remote_addr)
            return redirect(url_for(".hacker_lab"))
        flash("Davom etish uchun shartlarga rozilik bildirishingiz shart.", "error")
    return render_template("hacker_lab_consent.html")


@hackerlab_bp.route("/hacker-lab/access", methods=["GET", "POST"])
@login_required
def hacker_lab_access_page():
    user = get_current_user()
    if request.method == "POST":
        ok, msg = hacker_lab_mod.purchase_access(user["id"])
        flash(msg, "success" if ok else "error")
        if ok:
            return redirect(url_for(".hacker_lab"))
        return redirect(url_for(".hacker_lab_access_page"))
    price = get_price("hacker_lab_pro_price")
    return render_template("hacker_lab_access.html", price=price, balance=get_balance(user["id"]))


@hackerlab_bp.route("/api/hacker-lab/exec", methods=["POST"])
@api_login_required
def api_hacker_lab_exec():
    """Sandbox terminal buyrug'ini bajaradi (xavfsiz, statik javoblar)."""
    user = get_current_user()
    can, reason = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return api_response(False, error=reason)

    data = request.get_json(silent=True) or {}
    command = data.get("command", "")
    direction = query_one("SELECT id, slug FROM directions WHERE id=?", (user.get("selected_direction_id"),))
    direction_slug = direction["slug"] if direction else "generic"

    result = terminal_sim.execute_command(direction_slug, command)

    if result["is_dangerous"]:
        hacker_lab_mod.report_dangerous_command(
            user["id"], command, direction["id"] if direction else None
        )
        result["output"] += "\n\n⚠️ DIQQAT: Bu buyruq xavfsizlik tizimi tomonidan qayd etildi va administratorga yuborildi."

    return api_response(True, data=result)


# =================================================================
# ADMIN — Hacker Lab xavfsizlik monitoringi
# =================================================================
@hackerlab_bp.route("/admin/hacker-lab-security")
@admin_required
def admin_hacker_lab_security():
    status_filter = request.args.get("status", "pending")
    if status_filter == "all":
        events = hacker_lab_mod.get_all_security_events()
    elif status_filter == "pending":
        events = hacker_lab_mod.get_pending_security_events()
    else:
        events = query_all(
            """SELECT e.*, u.ism, u.familiya, u.email, d.name_uz as direction_name
               FROM hacker_lab_security_events e
               JOIN users u ON u.id = e.user_id
               LEFT JOIN directions d ON d.id = e.direction_id
               WHERE e.status=? ORDER BY e.id DESC""",
            (status_filter,)
        )
    blocked_users = query_all("SELECT id, ism, familiya, email, custom_id FROM users WHERE hacker_lab_blocked=1")
    return render_template("admin_hacker_lab_security.html", events=events, status_filter=status_filter,
                           blocked_users=blocked_users)


@hackerlab_bp.route("/admin/hacker-lab-security/<int:event_id>/block", methods=["POST"])
@admin_required
def admin_hacker_lab_block(event_id):
    ok, msg = hacker_lab_mod.block_user_for_violation(event_id, session["user_id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_hacker_lab_security"))


@hackerlab_bp.route("/admin/hacker-lab-security/<int:event_id>/dismiss", methods=["POST"])
@admin_required
def admin_hacker_lab_dismiss(event_id):
    hacker_lab_mod.dismiss_event(event_id, session["user_id"])
    flash("Signal e'tiborsiz qoldirildi.", "success")
    return redirect(url_for(".admin_hacker_lab_security"))


@hackerlab_bp.route("/admin/hacker-lab-security/unblock/<int:user_id>", methods=["POST"])
@admin_required
def admin_hacker_lab_unblock(user_id):
    hacker_lab_mod.unblock_user(user_id, session["user_id"])
    flash("Foydalanuvchi blokdan chiqarildi.", "success")
    return redirect(url_for(".admin_hacker_lab_security"))


# =================================================================
# HACKER LAB — JAMOA BO'LIB ISHLASH (yo'nalish ichidagi fikr almashish)
# =================================================================
HACKER_LAB_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "pdf", "doc", "docx", "zip", "txt", "mp4", "mov"}
HACKER_LAB_UPLOAD_DIR = os.path.join("static", "uploads", "hacker_lab")


def _hacker_lab_save_file(file_storage):
    """Xavfsiz fayl saqlash: kengaytmani tekshiradi, tasodifiy nom beradi."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in HACKER_LAB_ALLOWED_EXT:
        return None, None
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(HACKER_LAB_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(HACKER_LAB_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    file_type = "image" if ext in ("png", "jpg", "jpeg", "gif", "webp") else (
        "video" if ext in ("mp4", "mov") else "document")
    return f"/static/uploads/hacker_lab/{safe_name}", file_type


@hackerlab_bp.route("/hacker-lab/team")
@login_required
def hacker_lab_team():
    user = get_current_user()
    can, reason = hacker_lab_mod.can_enter(user["id"])
    if not can:
        flash(reason if reason not in ("consent_required", "access_required") else
              "Avval Hacker Lab shartlariga rozilik bering / kirish huquqini oling.", "error")
        return redirect(url_for(".hacker_lab"))
    direction = query_one("SELECT * FROM directions WHERE id=?", (user.get("selected_direction_id"),))
    if not direction:
        return redirect(url_for(".hacker_lab_choose_direction"))
    posts = hacker_lab_mod.get_direction_posts(direction["id"])
    return render_template("hacker_lab_team.html", direction=direction, posts=posts)


@hackerlab_bp.route("/hacker-lab/team/new", methods=["POST"])
@login_required
def hacker_lab_team_new():
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        flash("Ruxsat yo'q.", "error")
        return redirect(url_for(".hacker_lab"))
    direction_id = user.get("selected_direction_id")
    title = request.form.get("title", "")
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _hacker_lab_save_file(request.files["file"])
    ok, msg = hacker_lab_mod.create_post(user["id"], direction_id, title, body, file_path, file_type)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".hacker_lab_team"))


@hackerlab_bp.route("/hacker-lab/team/<int:post_id>")
@login_required
def hacker_lab_team_post(post_id):
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return redirect(url_for(".hacker_lab"))
    post = hacker_lab_mod.get_post(post_id)
    if not post:
        abort(404)
    replies = hacker_lab_mod.get_post_replies(post_id)
    return render_template("hacker_lab_team_post.html", post=post, replies=replies)


@hackerlab_bp.route("/hacker-lab/team/<int:post_id>/reply", methods=["POST"])
@login_required
def hacker_lab_team_reply(post_id):
    user = get_current_user()
    can, _ = hacker_lab_mod.can_enter(user["id"])
    if not can:
        return redirect(url_for(".hacker_lab"))
    ok, msg = hacker_lab_mod.create_reply(user["id"], post_id, request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for(".hacker_lab_team_post", post_id=post_id))

