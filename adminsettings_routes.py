# ============================================================
# CYBER SHATS — Admin Sozlamalar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import admin_required
from db import execute, log_action
from pricing import set_prices

adminsettings_bp = Blueprint("adminsettings_bp", __name__)


@adminsettings_bp.route("/admin/settings/free-plan", methods=["POST"])
@admin_required
def admin_settings_free_plan():
    """Free plan sozlamalarini bazaga saqlaydi — butun saytda darhol ishlaydi."""
    try:
        ai_limit = int(request.form.get("ai_daily_limit", 10))
    except ValueError:
        ai_limit = 10
    try:
        test_limit = int(request.form.get("free_test_limit", 30))
    except ValueError:
        test_limit = 30
    smm_access = 1 if request.form.get("free_smm", "0") == "1" else 0

    set_prices({
        "free_ai_limit": ai_limit,
        "free_test_limit": test_limit,
        "free_smm_access": smm_access,
    }, updated_by=session["user_id"])
    log_action(session["user_id"], "update_free_plan_settings",
               details=f"ai_limit:{ai_limit},test_limit:{test_limit},smm:{smm_access}",
               ip=request.remote_addr)
    flash("Free plan sozlamalari saqlandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#settings")


@adminsettings_bp.route("/admin/settings/pro-plan", methods=["POST"])
@admin_required
def admin_settings_pro_plan():
    """Pro plan narxlarini bazaga saqlaydi — Pro sotib olish narxi darhol o'zgaradi."""
    try:
        price_uzs = int(request.form.get("pro_price_uzs", 99000))
    except ValueError:
        price_uzs = 99000
    try:
        price_code = int(request.form.get("pro_price_code", 57000))
    except ValueError:
        price_code = 57000
    try:
        ai_limit = int(request.form.get("pro_ai_limit", 100))
    except ValueError:
        ai_limit = 100
    try:
        duration = int(request.form.get("pro_duration_days", 30))
    except ValueError:
        duration = 30

    set_prices({
        "pro_price_uzs": price_uzs,
        "pro_price_code": price_code,
        "pro_ai_limit": ai_limit,
        "pro_duration_days": duration,
    }, updated_by=session["user_id"])
    log_action(session["user_id"], "update_pro_plan_settings",
               details=f"price_uzs:{price_uzs},price_code:{price_code},ai_limit:{ai_limit},duration:{duration}",
               ip=request.remote_addr)
    flash("Pro plan narxlari saqlandi va saytda yangilandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#settings")


@adminsettings_bp.route("/admin/settings/system", methods=["POST"])
@admin_required
def admin_settings_system():
    """Tizim sozlamalarini saqlash."""
    site_name = request.form.get("site_name", "CYBER SHATS")
    site_desc = request.form.get("site_desc", "IT Ta'lim Platformasi")
    maintenance = request.form.get("maintenance", "0")
    registration = request.form.get("registration_open", "1")
    log_action(session["user_id"], "update_system_settings",
               details=f"maintenance:{maintenance},registration:{registration}",
               ip=request.remote_addr)
    flash("Tizim sozlamalari saqlandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#settings")


@adminsettings_bp.route("/admin/settings/pricing", methods=["POST"])
@admin_required
def admin_update_pricing():
    """Barcha CODE narxlarini bitta forma orqali saqlash."""
    keys = [
        "pro_price_code", "cyber_pro_price_code", "vip_price_code",
        "paid_course_code_default",
        "coin_transfer_fee_percent", "plan_duration_days",
        "welcome_bonus_code", "cyber_pro_welcome_bonus", "vip_welcome_bonus",
        "course_reward_code", "cyber_pro_course_bonus", "vip_course_bonus",
        "ai_weekly_price_code",
        "certificate_exam_fee",
        "ping_test_free_quota", "ping_test_pro_quota", "ping_test_cyber_pro_quota", "ping_test_vip_quota",
        "ping_test_cost_free", "ping_test_cost_pro", "ping_test_cost_cyber_pro", "ping_test_cost_vip",
        "id_tier_A_min", "id_tier_A_max",
        "id_tier_B_min", "id_tier_B_max",
        "id_tier_C_min", "id_tier_C_max",
        "id_tier_D_min", "id_tier_D_max",
        "id_tier_E_min", "id_tier_E_max",
    ]
    updates = {}
    for k in keys:
        v = request.form.get(k)
        if v is None or v == "":
            continue
        try:
            updates[k] = int(v)
        except ValueError:
            continue
    # Checkbox (form'da yo'q bo'lsa = o'chirilgan)
    updates["vip_enabled"] = 1 if request.form.get("vip_enabled") == "1" else 0
    set_prices(updates, updated_by=session["user_id"])
    log_action(session["user_id"], "update_pricing_settings",
               details=f"keys:{len(updates)}", ip=request.remote_addr)
    flash(f"{len(updates)} ta narx saqlandi va saytda yangilandi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#pricing")


