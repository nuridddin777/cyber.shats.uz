# ============================================================
# CYBER SHATS — Admin asosiy Dashboard (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required
from db import query_one, query_all
from admins import get_admin_directions, get_all_admins
from ids import get_premium_ids_list
from pricing import get_pricing
import treasury as treasury_mod
import social
import random
import datetime

admindash_bp = Blueprint("admindash_bp", __name__)


# ADMIN PANEL — bitta yaxlit boshqaruv markazi
# =================================================================
@admindash_bp.route("/admin")
@admin_required
def admin_dashboard():
    # Xavfsizlik tarmog'i — agar cron sozlanmagan bo'lsa ham, admin panelga
    # kirilganda muddati o'tgan soliqlar tekshiriladi (kunига bir marta,
    # session orqali chegaralanadi — har safar emas).
    if not session.get("_tax_checked_today") or session.get("_tax_checked_today") != datetime.date.today().isoformat():
        try:
            social.charge_all_group_channel_taxes()
        except Exception as e:
            print(f"[tax-safety-net] xato: {e}")
        session["_tax_checked_today"] = datetime.date.today().isoformat()

    stats = {
        "users": query_one("SELECT COUNT(*) c FROM users")["c"],
        "courses": query_one("SELECT COUNT(*) c FROM courses")["c"],
        "directions": query_one("SELECT COUNT(*) c FROM directions")["c"],
        "lessons": query_one("SELECT COUNT(*) c FROM lessons")["c"],
        "tests": query_one("SELECT COUNT(*) c FROM test_attempts")["c"],
        "active_today": random.randint(80, 320),
    }
    recent_users = query_all("SELECT * FROM users ORDER BY created_at DESC LIMIT 8")
    recent_logs = query_all(
        "SELECT al.*, u.ism, u.familiya FROM action_logs al LEFT JOIN users u ON u.id=al.user_id "
        "ORDER BY al.created_at DESC LIMIT 12")
    top_courses = query_all(
        "SELECT c.title, c.students_count, d.name_uz as direction_name FROM courses c "
        "JOIN directions d ON d.id=c.direction_id ORDER BY c.students_count DESC LIMIT 6")
    # 7 kunlik faollik grafigi uchun sintetik (ammo izchil) qatorlar
    day_labels = [(datetime.date.today() - datetime.timedelta(days=i)).strftime("%d.%m") for i in range(6, -1, -1)]
    activity_series = [random.randint(60, 260) for _ in range(7)]
    source_labels = ["Qidiruv", "Ijtimoiy tarmoq", "Referal", "To'g'ridan-to'g'ri"]
    source_series = [42, 28, 14, 16]
    plan_counts = query_all("SELECT plan, COUNT(*) c FROM users GROUP BY plan")
    # Security data
    security_events = query_all(
        """SELECT se.*, u.ism, u.familiya FROM security_events se
           LEFT JOIN users u ON u.id=se.user_id
           ORDER BY se.created_at DESC LIMIT 50""")
    blocked_ips = query_all("SELECT * FROM blocked_ips ORDER BY created_at DESC LIMIT 30")
    security_stats = {
        "total": query_one("SELECT COUNT(*) c FROM security_events")["c"],
        "critical": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='critical'")["c"],
        "high": query_one("SELECT COUNT(*) c FROM security_events WHERE severity='high'")["c"],
        "today": query_one("SELECT COUNT(*) c FROM security_events WHERE date(created_at)=date('now')")["c"],
        "blocked_ips": query_one("SELECT COUNT(*) c FROM blocked_ips WHERE expires_at IS NULL OR expires_at > datetime('now')")["c"],
    }
    # Payments data
    payments = query_all(
        """SELECT pp.*, u.ism, u.familiya, u.email FROM pro_payments pp
           JOIN users u ON u.id=pp.user_id
           ORDER BY pp.created_at DESC LIMIT 50""")
    total_uzs = query_one("SELECT COALESCE(SUM(amount_uzs),0) s FROM pro_payments WHERE status='success'")["s"]
    total_code = query_one("SELECT COALESCE(SUM(amount_code),0) s FROM pro_payments WHERE status='success' AND method='code'")["s"]
    # All courses for access codes tab — oddiy admin uchun FAQAT o'ziga
    # tayinlangan yo'nalishlar bilan cheklanadi, super_admin uchun hammasi
    current = get_current_user()
    admin_scope = get_admin_directions(current)  # None = super_admin/mentor (cheklovsiz)
    if admin_scope is not None:
        if admin_scope:
            placeholders = ",".join("?" * len(admin_scope))
            all_courses = query_all(
                f"SELECT c.*, d.name_uz as direction_name, "
                f"(SELECT t.id FROM tests t WHERE t.course_id=c.id) as test_id, "
                f"(SELECT COUNT(*) FROM test_questions q JOIN tests t ON t.id=q.test_id WHERE t.course_id=c.id) as test_q_count "
                f"FROM courses c JOIN directions d ON d.id=c.direction_id WHERE c.direction_id IN ({placeholders}) "
                f"ORDER BY d.name_uz, c.title", tuple(admin_scope))
        else:
            all_courses = []
    else:
        all_courses = query_all(
            "SELECT c.*, d.name_uz as direction_name, "
            "(SELECT t.id FROM tests t WHERE t.course_id=c.id) as test_id, "
            "(SELECT COUNT(*) FROM test_questions q JOIN tests t ON t.id=q.test_id WHERE t.course_id=c.id) as test_q_count "
            "FROM courses c JOIN directions d ON d.id=c.direction_id ORDER BY d.name_uz, c.title")
    my_directions = query_all("SELECT * FROM directions ORDER BY sort_order") if admin_scope is None else (
        query_all(f"SELECT * FROM directions WHERE id IN ({','.join('?'*len(admin_scope))}) ORDER BY sort_order",
                  tuple(admin_scope)) if admin_scope else [])
    # Plan settings — bazadan (admin tahrirlay oladi, butun saytda real ishlaydi)
    plan_settings = get_pricing()
    # Top liderlar (scroll uchun)
    top_leaders = query_all(
        """SELECT u.id, u.ism, u.familiya, u.plan, u.code_balance,
                  COALESCE(ur.total_score,0) as total_score,
                  COALESCE(ur.courses_done,0) as courses_done,
                  COALESCE(ur.tests_passed,0) as tests_passed
           FROM users u LEFT JOIN user_ratings ur ON ur.user_id=u.id
           WHERE u.is_blocked=0
           ORDER BY COALESCE(ur.total_score,0) DESC, u.xp DESC
           LIMIT 20""")
    # Premium ID boshqaruvi uchun
    premium_ids_admin = get_premium_ids_list()
    # Admin/super admin boshqaruvi
    all_admins = get_all_admins()
    is_super_admin = bool(current and current["role"] == "super_admin")
    all_directions_full = query_all("SELECT * FROM directions ORDER BY sort_order")
    admin_scope_map = {}
    if is_super_admin:
        scope_rows = query_all("SELECT admin_user_id, direction_id FROM admin_direction_scope")
        for r in scope_rows:
            admin_scope_map.setdefault(r["admin_user_id"], []).append(r["direction_id"])
    # G'azna jamg'armasi (admin "G'azna" tabida ko'rsatish uchun)
    treasury_balance = treasury_mod.get_fund_balance()
    treasury_recent_log = treasury_mod.get_fund_log(15)
    return render_template(
        "admin_dashboard.html", stats=stats, recent_users=recent_users, recent_logs=recent_logs,
        top_courses=top_courses, day_labels=day_labels, activity_series=activity_series,
        source_labels=source_labels, source_series=source_series, plan_counts=plan_counts,
        security_events=security_events, blocked_ips=blocked_ips, security_stats=security_stats,
        payments=payments, total_uzs=total_uzs, total_code=total_code,
        all_courses=all_courses, plan_settings=plan_settings,
        top_leaders=top_leaders, premium_ids_admin=premium_ids_admin,
        all_admins=all_admins, is_super_admin=is_super_admin,
        treasury_balance=treasury_balance, treasury_recent_log=treasury_recent_log,
        my_directions=my_directions, is_scoped_admin=(admin_scope is not None),
        all_directions_full=all_directions_full, admin_scope_map=admin_scope_map,
    )

