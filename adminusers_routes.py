# ============================================================
# CYBER SHATS — Admin foydalanuvchilar boshqaruvi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required, super_admin_required
from db import query_one, query_all, execute, log_action
from admins import (get_all_admins, create_new_admin, promote_user_to_admin,
                     demote_admin, super_admin_change_admin_id,
                     get_admin_directions, admin_can_manage_direction, admin_can_manage_course,
                     super_admin_reset_admin_password)
import admins as admins_mod
from coins import add_coins

adminusers_bp = Blueprint("adminusers_bp", __name__)




@adminusers_bp.route("/admin/users/<int:user_id>/toggle-block", methods=["POST"])
@admin_required
def admin_toggle_block(user_id):
    user = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if user:
        execute("UPDATE users SET is_blocked=? WHERE id=?", (0 if user["is_blocked"] else 1, user_id))
        log_action(session["user_id"], "admin_toggle_block", details=f"user:{user_id}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard"))


# =================================================================
# ADMIN — Adminlar boshqaruvi (admin qo'shish, 4 xonali admin_id)
# =================================================================

@adminusers_bp.route("/admin/admins/create", methods=["POST"])
@super_admin_required
def admin_create_admin():
    """Yangi login/parol bilan admin yaratadi (har bir admin faqat o'zini yaratganlarni emas,
    istalgan adminni yaratishi mumkin — lekin role='super_admin' faqat super_admin tomonidan beriladi)."""
    ism = request.form.get("ism", "").strip()
    familiya = request.form.get("familiya", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "admin")

    current = get_current_user()
    if role == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin boshqa Super Admin tayinlashi mumkin.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")

    ok, msg = create_new_admin(ism, familiya, email, password, role)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_create_admin", details=f"email:{email},role:{role}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/admins/promote", methods=["POST"])
@super_admin_required
def admin_promote_user():
    """Mavjud foydalanuvchini admin/mentor qilib tayinlaydi."""
    try:
        target_user_id = int(request.form.get("user_id", 0))
    except ValueError:
        target_user_id = 0
    role = request.form.get("role", "admin")

    current = get_current_user()
    if role == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin boshqa Super Admin tayinlashi mumkin.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")

    if not target_user_id:
        flash("Foydalanuvchi ID kiritilmadi.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")

    ok, msg = promote_user_to_admin(target_user_id, role)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_promote_user", details=f"target:{target_user_id},role:{role}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/admins/<int:user_id>/demote", methods=["POST"])
@super_admin_required
def admin_demote_admin(user_id):
    """Adminlik huquqini olib tashlaydi. Super adminni faqat super_admin tushira oladi."""
    target = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    current = get_current_user()
    if target and target["role"] == "super_admin" and current["role"] != "super_admin":
        flash("Faqat Super Admin Super Adminni tushira oladi.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")
    if target and target["id"] == current["id"]:
        flash("O'zingizni admin huquqidan mahrum qila olmaysiz.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")

    ok, msg = demote_admin(user_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "admin_demote_admin", details=f"target:{user_id}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/admins/<int:user_id>/change-admin-id", methods=["POST"])
@super_admin_required
def admin_change_admin_id(user_id):
    """FAQAT Super Admin boshqa adminning 4 xonali Admin ID raqamini o'zgartira oladi."""
    new_admin_id = request.form.get("admin_id", "").strip()
    ok, msg = super_admin_change_admin_id(user_id, new_admin_id)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "super_admin_change_admin_id",
                   details=f"target:{user_id},new_id:{new_admin_id}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/admins/<int:user_id>/reset-password", methods=["POST"])
@super_admin_required
def admin_reset_admin_password(user_id):
    """FAQAT Super Admin. Parollar hash holida saqlanadi — shuning uchun 'ko'rish'
    o'rniga YANGI parol o'rnatiladi (reset)."""
    new_password = request.form.get("new_password", "")
    ok, msg = super_admin_reset_admin_password(user_id, new_password)
    flash(msg, "success" if ok else "error")
    if ok:
        log_action(session["user_id"], "super_admin_reset_admin_password",
                   details=f"target:{user_id}", ip=request.remote_addr)
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/admins/<int:user_id>/set-directions", methods=["POST"])
@super_admin_required
def admin_set_admin_directions(user_id):
    """FAQAT Super Admin. Oddiy adminga qaysi yo'nalish(lar)ni boshqarish huquqini beradi."""
    target = query_one("SELECT * FROM users WHERE id=?", (user_id,))
    if not target or target["role"] not in ("admin", "mentor"):
        flash("Bu foydalanuvchi oddiy admin/mentor emas (super_admin cheklovsiz).", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")
    direction_ids = request.form.getlist("direction_ids", type=int)
    execute("DELETE FROM admin_direction_scope WHERE admin_user_id=?", (user_id,))
    for did in direction_ids:
        execute("INSERT OR IGNORE INTO admin_direction_scope (admin_user_id, direction_id) VALUES (?,?)",
                (user_id, did))
    log_action(session["user_id"], "admin_set_admin_directions",
               details=f"target:{user_id},directions:{direction_ids}", ip=request.remote_addr)
    flash(f"{target['ism']} uchun {len(direction_ids)} ta yo'nalish tayinlandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#admins")


@adminusers_bp.route("/admin/directions/<int:direction_id>/edit", methods=["POST"])
@admin_required
def admin_edit_direction(direction_id):
    """Yo'nalish ma'lumotlarini tahrirlash — oddiy admin FAQAT o'ziga tayinlangan
    yo'nalishlarni, super_admin esa barchasini tahrirlashi mumkin."""
    current = get_current_user()
    if not admin_can_manage_direction(current, direction_id):
        flash("Bu yo'nalish sizga tayinlanmagan.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#directions")
    direction = query_one("SELECT * FROM directions WHERE id=?", (direction_id,))
    if not direction:
        abort(404)
    name_uz = request.form.get("name_uz", "").strip()
    description = request.form.get("description", "").strip()
    text_content = request.form.get("text_content", "").strip()
    if name_uz:
        execute("UPDATE directions SET name_uz=?, description=?, text_content=? WHERE id=?",
                (name_uz, description, text_content, direction_id))
        log_action(session["user_id"], "admin_edit_direction",
                   details=f"direction:{direction_id}", ip=request.remote_addr)
        flash(f"«{name_uz}» yo'nalishi yangilandi.", "success")
    else:
        flash("Yo'nalish nomi bo'sh bo'lishi mumkin emas.", "error")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#directions")


# =================================================================
# ADMIN — KENGAYTIRILGAN PANEL
# =================================================================

@adminusers_bp.route("/admin/users")
@admin_required
def admin_users():
    """Barcha foydalanuvchilar ro'yxati + filter."""
    search = request.args.get("q", "").strip()
    plan   = request.args.get("plan", "")
    page   = max(1, int(request.args.get("page", 1)))
    per    = 20
    offset = (page - 1) * per

    sql  = "SELECT u.*, COALESCE(ur.rank_position,0) as rank FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id WHERE 1=1"
    args = []
    if search:
        sql += " AND (u.ism LIKE ? OR u.familiya LIKE ? OR u.email LIKE ?)"
        args += [f"%{search}%", f"%{search}%", f"%{search}%"]
    if plan:
        sql += " AND u.plan=?"
        args.append(plan)
    sql += " ORDER BY u.created_at DESC LIMIT ? OFFSET ?"
    args += [per, offset]
    users = query_all(sql, tuple(args))
    total = query_one("SELECT COUNT(*) c FROM users")["c"] if not search and not plan else len(users)
    is_super_admin = get_current_user().get("role") == "super_admin"
    return render_template("admin_users.html", users=users, search=search, plan=plan,
                           page=page, per=per, total=total or len(users), is_super_admin=is_super_admin)


@adminusers_bp.route("/admin/users/<int:user_id>/set-plan", methods=["POST"])
@super_admin_required
def admin_set_plan(user_id):
    """DIQQAT: 'admin' tarifi — bu boshqalari (pro/vip/hacker) kabi CODE
    evaziga sotib olinmaydigan, FAQAT Super Admin qo'lda bera oladigan
    maxsus tarif. Shuning uchun bu route allaqachon @super_admin_required
    bilan himoyalangan (oddiy adminlar bu yerga umuman kira olmaydi), va
    'admin' tarifi hech qanday /coins/buy-* route orqali sotib olinmaydi
    — faqat shu yerdan, qo'lda beriladi.

    Barcha pulik tariflar (jumladan endi 'admin' ham) — AVTOMATIK
    tugaydigan qilib belgilanadi (bir xil muddat bilan). Muddati
    tugagach, auth.py va telegram_bot.py'dagi tekshiruvlar orqali
    avtomatik 'free'ga tushadi."""
    plan = request.form.get("plan", "free")
    if plan not in ("free", "pro", "cyber_pro", "vip", "hacker", "enterprise", "admin"):
        flash("Noto'g'ri plan.", "error")
        return redirect(url_for(".admin_users"))
    if plan in ("pro", "cyber_pro", "vip", "hacker", "admin"):
        from coins import _calc_plan_expiry
        expires_at = _calc_plan_expiry()
        execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan, expires_at, user_id))
    else:
        execute("UPDATE users SET plan=?, plan_expires_at=NULL WHERE id=?", (plan, user_id))
    log_action(session["user_id"], "admin_set_plan", details=f"user:{user_id},plan:{plan}", ip=request.remote_addr)
    flash(f"Foydalanuvchi plani '{plan}' ga o'zgartirildi.", "success")
    return redirect(url_for(".admin_users"))


@adminusers_bp.route("/admin/users/<int:user_id>/add-coins", methods=["POST"])
@super_admin_required
def admin_add_coins(user_id):
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    dest = request.form.get("redirect_to") or url_for(".admin_users")
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(dest)
    add_coins(user_id, amount, "admin_add", ref_id=session["user_id"])
    log_action(session["user_id"], "admin_add_coins", details=f"user:{user_id},amount:{amount}", ip=request.remote_addr)
    flash(f"Foydalanuvchiga {amount:,} code tangasi qo'shildi.", "success")
    return redirect(dest)


@adminusers_bp.route("/admin/users/<int:user_id>/remove-coins", methods=["POST"])
@super_admin_required
def admin_remove_coins(user_id):
    """Foydalanuvchidan code tangasi ayirish (admin huquqi)."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    dest = request.form.get("redirect_to") or url_for(".admin_users")
    if amount <= 0:
        flash("Miqdor musbat bo'lishi kerak.", "error")
        return redirect(dest)
    user = query_one("SELECT code_balance FROM users WHERE id=?", (user_id,))
    if not user:
        flash("Foydalanuvchi topilmadi.", "error")
        return redirect(dest)
    current = user["code_balance"] or 0
    actual = min(amount, current)  # ko'proq ayirib bo'lmaydi
    if actual <= 0:
        flash("Foydalanuvchining balansi nol — ayirib bo'lmaydi.", "error")
        return redirect(dest)
    execute("UPDATE users SET code_balance = code_balance - ? WHERE id=?", (actual, user_id))
    execute("INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, -actual, "admin_remove", session["user_id"]))
    log_action(session["user_id"], "admin_remove_coins",
               details=f"user:{user_id},amount:{actual}", ip=request.remote_addr)
    flash(f"Foydalanuvchidan {actual:,} code tangasi ayirildi.", "success")
    return redirect(dest)

