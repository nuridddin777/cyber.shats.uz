# ============================================================
# CYBER SHATS — Admin AI Insights bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import admin_required, super_admin_required
from db import query_one, query_all, execute, log_action
from utils import api_response
import ai_recommendations
import random, string

adminai_bp = Blueprint("adminai_bp", __name__)


@adminai_bp.route("/admin/ai-insights")
@admin_required
def admin_ai_insights():
    """Admin uchun BEPUL AI brifingi — platforma holati bo'yicha qisqa
    xulosalar. CODE/kunlik limitga bog'liq EMAS (har doim bepul, admin_required
    yetarli)."""
    stats = {
        "new_users_7d": query_one(
            "SELECT COUNT(*) c FROM users WHERE created_at >= datetime('now','-7 days')")["c"],
        "total_users": query_one("SELECT COUNT(*) c FROM users WHERE role='student'")["c"],
        "today_revenue": query_one(
            "SELECT COALESCE(SUM(amount_uzs),0) s FROM pro_payments WHERE status='success' "
            "AND date(created_at)=date('now')")["s"],
        "courses_without_test": query_one(
            "SELECT COUNT(*) c FROM courses WHERE is_active=1 AND id NOT IN (SELECT course_id FROM tests)")["c"],
        "security_events_24h": query_one(
            "SELECT COUNT(*) c FROM security_events WHERE created_at >= datetime('now','-1 day')")["c"],
    }
    top = query_one(
        "SELECT title, students_count FROM courses ORDER BY students_count DESC LIMIT 1")
    stats["top_course"] = top["title"] if top else "yo'q"
    stats["top_course_students"] = top["students_count"] if top else 0

    insight_text, err = ai_recommendations.generate_admin_insights(stats)
    if err:
        return api_response(False, error=err)
    return api_response(True, data={"insight": insight_text, "stats": stats})


@adminai_bp.route("/admin/codes/quick-generate", methods=["POST"])
@super_admin_required
def admin_quick_generate_codes():
    """Admin dashboard'dan tezkor kod yaratish."""
    course_id = request.form.get("course_id", type=int)
    count = min(int(request.form.get("count", 5)), 50)
    if not course_id:
        flash("Kurs tanlanmadi.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
    for _ in range(count):
        code = "CS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        execute("INSERT INTO course_access_codes (course_id, access_code) VALUES (?,?)", (course_id, code))
    log_action(session["user_id"], "quick_generate_codes", details=f"course:{course_id},count:{count}", ip=request.remote_addr)
    flash(f"{count} ta kirish kodi yaratildi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

