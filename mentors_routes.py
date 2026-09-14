# ============================================================
# CYBER SHATS — Mentorlar birlashmasi bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

mentors_bp = Blueprint("mentors_bp", __name__)


def _require_hacker_plan():
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _require_hacker_plan as _real_fn
    return _real_fn()



# =================================================================
# MENTORLAR BIRLASHMASI (MAXSUS)
# =================================================================
@mentors_bp.route("/mentorlar")
@login_required
def mentors_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    mentors = query_all(
        """SELECT m.*, u.ism, u.familiya, u.custom_id FROM mentors m
           JOIN users u ON u.id = m.user_id ORDER BY m.created_at DESC"""
    )
    am_i_mentor = query_one("SELECT 1 FROM mentors WHERE user_id=?", (user["id"],))
    return render_template("mentors.html", mentors=mentors, am_i_mentor=bool(am_i_mentor))


@mentors_bp.route("/mentorlar/register", methods=["POST"])
@login_required
def mentors_register():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    skills = request.form.get("skills", "").strip()
    bio = request.form.get("bio", "").strip()
    contact = request.form.get("contact", "").strip()
    if skills:
        execute(
            "INSERT INTO mentors (user_id, skills, bio, contact) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET skills=excluded.skills, bio=excluded.bio, contact=excluded.contact",
            (user["id"], skills, bio, contact)
        )
        flash("Mentor sifatida ro'yxatdan o'tdingiz!", "success")
    return redirect(url_for(".mentors_page"))


@mentors_bp.route("/mentorlar/<int:mentor_id>/request", methods=["POST"])
@login_required
def mentors_request(mentor_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    message = request.form.get("message", "").strip()
    execute("INSERT INTO mentor_requests (mentor_id, student_id, message) VALUES (?,?,?)",
            (mentor_id, user["id"], message))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (mentor_id, "Yangi dars so'rovi!", f"{user['ism']} sizdan mentorlik so'ramoqda.", "info"))
    flash("So'rov yuborildi!", "success")
    return redirect(url_for(".mentors_page"))


