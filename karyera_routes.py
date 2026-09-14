# ============================================================
# CYBER SHATS — Karyera markazi bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

karyera_bp = Blueprint("karyera_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


# KARYERA MARKAZI (MAXSUS)
# =================================================================
@karyera_bp.route("/karyera")
@login_required
def career_center_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    jobs = query_all("SELECT * FROM job_listings WHERE status='open' ORDER BY created_at DESC")
    my_applications = {r["job_id"] for r in query_all(
        "SELECT job_id FROM job_applications WHERE user_id=?", (user["id"],)
    )}
    return render_template("career_center.html", jobs=jobs, my_applications=my_applications)


@karyera_bp.route("/karyera/post", methods=["POST"])
@login_required
def career_post_job():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "Masofaviy").strip()
    if title and company and description:
        execute("INSERT INTO job_listings (posted_by, title, company, description, location) VALUES (?,?,?,?,?)",
                (user["id"], title, company, description, location))
        flash("Ish e'loni joylandi!", "success")
    return redirect(url_for(".career_center_page"))


@karyera_bp.route("/karyera/<int:job_id>/apply", methods=["POST"])
@login_required
def career_apply(job_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    message = request.form.get("message", "").strip()
    try:
        execute("INSERT INTO job_applications (job_id, user_id, message) VALUES (?,?,?)",
                (job_id, user["id"], message))
        flash("Arizangiz yuborildi!", "success")
    except Exception:
        flash("Siz allaqachon ariza topshirgansiz.", "error")
    return redirect(url_for(".career_center_page"))

