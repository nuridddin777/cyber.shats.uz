# ============================================================
# CYBER SHATS — Admin Leaderboard va To'lovlar (Blueprint)
# ============================================================
from flask import Blueprint, render_template
from auth import admin_required
from db import query_one, query_all
from coins import get_leaderboard

adminlead_bp = Blueprint("adminlead_bp", __name__)


@adminlead_bp.route("/admin/leaderboard")
@admin_required
def admin_leaderboard():
    leaders = get_leaderboard(50)
    return render_template("admin_leaderboard.html", leaders=leaders)


@adminlead_bp.route("/admin/payments")
@admin_required
def admin_payments():
    payments = query_all(
        """SELECT pp.*, u.ism, u.familiya, u.email FROM pro_payments pp
           JOIN users u ON u.id=pp.user_id
           ORDER BY pp.created_at DESC LIMIT 100""")
    total_uzs = query_one("SELECT COALESCE(SUM(amount_uzs),0) s FROM pro_payments WHERE status='success'")["s"]
    total_code = query_one("SELECT COALESCE(SUM(amount_code),0) s FROM pro_payments WHERE status='success' AND method='code'")["s"]
    return render_template("admin_payments.html", payments=payments,
                           total_uzs=total_uzs, total_code=total_code)


