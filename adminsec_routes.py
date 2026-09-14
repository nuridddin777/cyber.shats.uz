# ============================================================
# CYBER SHATS — Admin Xavfsizlik va G'azna bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import super_admin_required, admin_required
from db import query_one, query_all, execute, log_action
import treasury as treasury_mod
from security import block_ip

adminsec_bp = Blueprint("adminsec_bp", __name__)


@adminsec_bp.route("/admin/treasury/deposit", methods=["POST"])
@super_admin_required
def admin_deposit_to_treasury():
    """Admin tomonidan g'azna jamg'armasiga to'g'ridan-to'g'ri code solib berish."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    note = request.form.get("note", "").strip()
    ok, msg = treasury_mod.admin_deposit_to_fund(session["user_id"], amount, note)
    log_action(session["user_id"], "admin_treasury_deposit",
               details=f"amount:{amount},note:{note}", ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#treasury")


@adminsec_bp.route("/admin/treasury/reset-all", methods=["POST"])
@super_admin_required
def admin_reset_treasury_all():
    """FAQAT Super Admin — G'azna va BARCHA foydalanuvchi CODE balansini
    0 dan boshlaydi. QAYTARIB BO'LMAYDIGAN amal — shuning uchun aniq
    tasdiqlash matni talab qilinadi."""
    confirm_text = request.form.get("confirm_text", "").strip()
    if confirm_text != "0 DAN BOSHLASH":
        flash("Tasdiqlash matni noto'g'ri kiritildi. Aniq \"0 DAN BOSHLASH\" deb yozing.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#treasury")
    ok, msg = treasury_mod.admin_reset_treasury_and_balances(session["user_id"])
    log_action(session["user_id"], "admin_treasury_full_reset", details=msg, ip=request.remote_addr)
    flash(msg, "success" if ok else "error")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#treasury")


# =================================================================

@adminsec_bp.route("/admin/security")
@admin_required
def admin_security():
    """Xavfsizlik hodisalari, IP bloklash paneli."""
    events = query_all(
        """SELECT se.*, u.ism, u.familiya FROM security_events se
           LEFT JOIN users u ON u.id=se.user_id
           ORDER BY se.created_at DESC LIMIT 100""")
    blocked_ips = query_all("SELECT * FROM blocked_ips ORDER BY created_at DESC LIMIT 50")
    stats = {
        "total": query_one("SELECT COUNT(*) c FROM security_events")["c"],
        "critical": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='critical'")["c"],
        "high": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='high'")["c"],
        "today": query_one("SELECT COUNT(*) c FROM security_events WHERE date(created_at)=date('now')")["c"],
        "blocked_ips": query_one("SELECT COUNT(*) c FROM blocked_ips WHERE expires_at IS NULL OR expires_at > datetime('now')")["c"],
    }
    return render_template("admin_security.html", events=events, blocked_ips=blocked_ips, stats=stats)


@adminsec_bp.route("/admin/security/block-ip", methods=["POST"])
@admin_required
def admin_block_ip():
    ip = request.form.get("ip", "").strip()
    reason = request.form.get("reason", "manual")
    hours = int(request.form.get("hours", 24))
    if ip:
        block_ip(ip, reason, hours, blocked_by=session["user_id"])
        flash(f"{ip} bloklandi ({hours} soat).", "success")
    return redirect(url_for(".admin_security"))


@adminsec_bp.route("/admin/security/unblock-ip/<int:bid>", methods=["POST"])
@admin_required
def admin_unblock_ip(bid):
    execute("DELETE FROM blocked_ips WHERE id=?", (bid,))
    log_action(session["user_id"], "admin_unblock_ip", details=f"bid:{bid}", ip=request.remote_addr)
    flash("IP blokdan chiqarildi.", "success")
    return redirect(url_for(".admin_security"))

