# ============================================================
# CYBER SHATS — Admin Moderatsiya bo'limi (Blueprint)
# ============================================================
# Sertifikat/O'qituvchi arizalari, Guruh/Kanal ko'rib chiqish, nazoratchi
# tayinlash.
from functools import wraps as _wraps
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required, login_required, super_admin_required
from db import query_one, query_all, execute, log_action
import certificates as cert_mod

adminmod_bp = Blueprint("adminmod_bp", __name__)


# Admin — sertifikat arizalari
@adminmod_bp.route("/admin/certificates")
@admin_required
def admin_certificates():
    status = request.args.get("status", "")
    applications = cert_mod.get_all_applications(status if status else None)
    return render_template("admin_certificates.html",
                           applications=applications, filter_status=status)


@adminmod_bp.route("/admin/certificates/<int:app_id>/review", methods=["POST"])
@admin_required
def admin_certificates_review(app_id):
    decision = request.form.get("decision")
    note = request.form.get("note", "")
    ok, msg = cert_mod.review_application(app_id, session["user_id"], decision, note)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".admin_certificates"))


# Admin — o'qituvchilik arizalari (faqat Super Admin tasdiqlaydi)
@adminmod_bp.route("/admin/teacher-applications")
@admin_required
def admin_teacher_applications():
    status = request.args.get("status", "pending")
    sql = """SELECT ta.*, u.email, u.custom_id, d.name_uz as direction_name
             FROM teacher_applications ta JOIN users u ON u.id=ta.user_id
             LEFT JOIN directions d ON d.id=ta.direction_id"""
    args = ()
    if status:
        sql += " WHERE ta.status=?"
        args = (status,)
    sql += " ORDER BY ta.created_at DESC"
    applications = query_all(sql, args)
    for a in applications:
        a["certificates"] = json.loads(a["certificates_json"] or "[]")
    is_super_admin = get_current_user().get("role") == "super_admin"
    return render_template("admin_teacher_applications.html", applications=applications,
                           filter_status=status, is_super_admin=is_super_admin)


@adminmod_bp.route("/admin/teacher-applications/<int:app_id>/review", methods=["POST"])
@super_admin_required
def admin_teacher_application_review(app_id):
    """FAQAT Super Admin tasdiqlashi/rad etishi mumkin."""
    application = query_one("SELECT * FROM teacher_applications WHERE id=?", (app_id,))
    if not application:
        abort(404)
    decision = request.form.get("decision")
    note = request.form.get("note", "").strip()
    if decision not in ("approved", "rejected"):
        flash("Noto'g'ri qaror.", "error")
        return redirect(url_for(".admin_teacher_applications"))

    execute("UPDATE teacher_applications SET status=?, reviewed_by=?, reviewed_at=datetime('now'), review_note=? WHERE id=?",
            (decision, session["user_id"], note, app_id))
    if decision == "approved":
        execute("UPDATE users SET is_teacher=1 WHERE id=?", (application["user_id"],))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (application["user_id"], "Tabriklaymiz — o'qituvchi sifatida tasdiqlandingiz! 🎉",
                 "Endi o'qituvchi paneliga kirishingiz mumkin.", "success"))
    else:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (application["user_id"], "O'qituvchilik arizangiz rad etildi",
                 note or "Qo'shimcha ma'lumot uchun admin bilan bog'laning.", "error"))
    log_action(session["user_id"], "teacher_application_review",
               details=f"app:{app_id},decision:{decision}", ip=request.remote_addr)
    flash(f"Ariza {'tasdiqlandi' if decision=='approved' else 'rad etildi'}.", "success")
    return redirect(url_for(".admin_teacher_applications"))


# =================================================================
# GURUH/KANAL NAZORATI — 2-ADMIN TIZIMI
# Bitta admin guruhlarga, boshqasi kanallarga javobgar (Super Admin —
# ikkalasiga ham kira oladi). Yo'nalish bilan bog'liq EMAS.
# =================================================================
def group_moderator_required(view):
    from functools import wraps as _wraps
    @_wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user or not (user.get("group_moderator") or user.get("role") == "super_admin"):
            flash("Bu bo'lim faqat guruh nazoratchisi (yoki Super Admin) uchun.", "error")
            return redirect(url_for("admindash_bp.admin_dashboard"))
        return view(*args, **kwargs)
    return wrapped


def channel_moderator_required(view):
    from functools import wraps as _wraps
    @_wraps(view)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user or not (user.get("channel_moderator") or user.get("role") == "super_admin"):
            flash("Bu bo'lim faqat kanal nazoratchisi (yoki Super Admin) uchun.", "error")
            return redirect(url_for("admindash_bp.admin_dashboard"))
        return view(*args, **kwargs)
    return wrapped


@adminmod_bp.route("/admin/groups-review")
@group_moderator_required
def admin_groups_review():
    status = request.args.get("status", "unverified")
    sql = ("SELECT g.*, u.ism, u.familiya, u.custom_id, u.email FROM groups g "
           "JOIN users u ON u.id=g.owner_id")
    if status == "unverified":
        sql += " WHERE g.is_verified=0"
    elif status == "flagged":
        sql += " WHERE g.flagged_reason IS NOT NULL"
    sql += " ORDER BY g.created_at DESC LIMIT 100"
    groups_list = query_all(sql)
    return render_template("admin_groups_review.html", groups_list=groups_list, filter_status=status)


@adminmod_bp.route("/admin/groups-review/<int:group_id>/verify", methods=["POST"])
@group_moderator_required
def admin_group_verify(group_id):
    execute("UPDATE groups SET is_verified=1, verified_by=?, flagged_reason=NULL WHERE id=?",
            (session["user_id"], group_id))
    log_action(session["user_id"], "group_verified", details=f"group:{group_id}", ip=request.remote_addr)
    flash("Guruh tasdiqlandi.", "success")
    return redirect(url_for(".admin_groups_review"))


@adminmod_bp.route("/admin/groups-review/<int:group_id>/flag", methods=["POST"])
@group_moderator_required
def admin_group_flag(group_id):
    reason = request.form.get("reason", "Soxta/shubhali ma'lumot").strip()
    execute("UPDATE groups SET is_verified=0, flagged_reason=?, verified_by=? WHERE id=?",
            (reason, session["user_id"], group_id))
    group = query_one("SELECT owner_id, name FROM groups WHERE id=?", (group_id,))
    if group:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (group["owner_id"], "Guruhingiz belgilandi ⚠️",
                 f"«{group['name']}» guruhi tekshiruvda: {reason}", "warn"))
    log_action(session["user_id"], "group_flagged", details=f"group:{group_id},reason:{reason}", ip=request.remote_addr)
    flash("Guruh belgilandi.", "success")
    return redirect(url_for(".admin_groups_review"))


@adminmod_bp.route("/admin/channels-review")
@channel_moderator_required
def admin_channels_review():
    status = request.args.get("status", "unverified")
    sql = ("SELECT ch.*, u.ism, u.familiya, u.custom_id, u.email FROM channels ch "
           "JOIN users u ON u.id=ch.owner_id")
    if status == "unverified":
        sql += " WHERE ch.is_verified=0"
    elif status == "flagged":
        sql += " WHERE ch.flagged_reason IS NOT NULL"
    sql += " ORDER BY ch.created_at DESC LIMIT 100"
    channels_list = query_all(sql)
    return render_template("admin_channels_review.html", channels_list=channels_list, filter_status=status)


@adminmod_bp.route("/admin/channels-review/<int:channel_id>/verify", methods=["POST"])
@channel_moderator_required
def admin_channel_verify(channel_id):
    execute("UPDATE channels SET is_verified=1, verified_by=?, flagged_reason=NULL WHERE id=?",
            (session["user_id"], channel_id))
    log_action(session["user_id"], "channel_verified", details=f"channel:{channel_id}", ip=request.remote_addr)
    flash("Kanal tasdiqlandi.", "success")
    return redirect(url_for(".admin_channels_review"))


@adminmod_bp.route("/admin/channels-review/<int:channel_id>/flag", methods=["POST"])
@channel_moderator_required
def admin_channel_flag(channel_id):
    reason = request.form.get("reason", "Soxta/shubhali ma'lumot").strip()
    execute("UPDATE channels SET is_verified=0, flagged_reason=?, verified_by=? WHERE id=?",
            (reason, session["user_id"], channel_id))
    channel = query_one("SELECT owner_id, name FROM channels WHERE id=?", (channel_id,))
    if channel:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (channel["owner_id"], "Kanalingiz belgilandi ⚠️",
                 f"«{channel['name']}» kanali tekshiruvda: {reason}", "warn"))
    log_action(session["user_id"], "channel_flagged", details=f"channel:{channel_id},reason:{reason}", ip=request.remote_addr)
    flash("Kanal belgilandi.", "success")
    return redirect(url_for(".admin_channels_review"))


@adminmod_bp.route("/admin/set-moderator/<int:user_id>", methods=["POST"])
@super_admin_required
def admin_set_moderator(user_id):
    """FAQAT Super Admin — adminni guruh yoki kanal nazoratchisi qilib tayinlaydi."""
    kind = request.form.get("kind")  # 'group' | 'channel'
    value = 1 if request.form.get("enabled") == "1" else 0
    target = query_one("SELECT role FROM users WHERE id=?", (user_id,))
    if not target or target["role"] not in ("admin", "mentor"):
        flash("Faqat oddiy admin/mentorga nazoratchi vazifasi berilishi mumkin.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")
    if kind == "group":
        execute("UPDATE users SET group_moderator=? WHERE id=?", (value, user_id))
    elif kind == "channel":
        execute("UPDATE users SET channel_moderator=? WHERE id=?", (value, user_id))
    else:
        flash("Noto'g'ri turi.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")
    log_action(session["user_id"], "set_moderator", details=f"target:{user_id},kind:{kind},value:{value}",
               ip=request.remote_addr)
    flash("Nazoratchi vazifasi yangilandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")

