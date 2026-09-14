# ============================================================
# CYBER SHATS — Jamoa (Team) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

jamoa_bp = Blueprint("jamoa_bp", __name__)



# =================================================================
# JAMOA (Team) va Jamoa Jamg'armasi
# =================================================================
@jamoa_bp.route("/jamoa", methods=["GET"])
@login_required
def jamoa_page():
    import teams
    user = get_current_user()
    team = teams.get_user_team(user["id"])
    billing = None
    treasury = None
    treasury_log = []
    members = []
    if team:
        billing = teams.check_and_charge_tax(dict(team))
        team = teams.get_user_team(user["id"])  # status yangilangan bo'lishi mumkin
        treasury = teams.get_treasury(team["id"])
        treasury_log = teams.get_treasury_log(team["id"])
        members = query_all(
            """SELECT tm.*, u.ism, u.familiya, u.custom_id, u.plan FROM team_members tm
               JOIN users u ON u.id = tm.user_id WHERE tm.team_id=? ORDER BY tm.role, tm.joined_at""",
            (team["id"],)
        )
    tax_preview = teams.get_team_tax(user.get("plan", "free"))
    return render_template("jamoa.html", team=team, billing=billing, treasury=treasury,
                           treasury_log=treasury_log, members=members, tax_preview=tax_preview)


@jamoa_bp.route("/jamoa/create", methods=["POST"])
@login_required
def jamoa_create():
    import teams
    user = get_current_user()
    name = request.form.get("name", "")
    description = request.form.get("description", "")
    ok, msg, team = teams.create_team(user["id"], name, description)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/leave", methods=["POST"])
@login_required
def jamoa_leave():
    import teams
    user = get_current_user()
    ok, msg = teams.leave_team(user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/dissolve", methods=["POST"])
@login_required
def jamoa_dissolve():
    import teams
    user = get_current_user()
    ok, msg = teams.dissolve_team(user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/invite/create", methods=["POST"])
@login_required
def jamoa_invite_create():
    import teams
    user = get_current_user()
    team = teams.get_user_team(user["id"])
    if not team:
        flash("Avval jamoaga a'zo bo'ling.", "error")
        return redirect(url_for(".jamoa_page"))
    code = teams.create_invite(team["id"], user["id"])
    flash(f"Taklif kodi yaratildi: {code}", "success")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/join", methods=["POST"])
@login_required
def jamoa_join():
    import teams
    user = get_current_user()
    code = request.form.get("invite_code", "")
    ok, msg = teams.join_via_invite(user["id"], code)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/treasury/contribute", methods=["POST"])
@login_required
def jamoa_contribute():
    import teams
    user = get_current_user()
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0
    ok, msg = teams.contribute(user["id"], amount)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/treasury/gift", methods=["POST"])
@login_required
def jamoa_gift():
    import teams
    user = get_current_user()
    try:
        target_user_id = int(request.form.get("target_user_id", 0))
    except ValueError:
        target_user_id = 0
    plan_key = request.form.get("plan_key", "")
    ok, msg = teams.gift_plan_from_treasury(user["id"], target_user_id, plan_key)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


@jamoa_bp.route("/jamoa/pay-tax", methods=["POST"])
@login_required
def jamoa_pay_tax():
    import teams
    user = get_current_user()
    ok, msg = teams.pay_pending_tax(user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".jamoa_page"))


