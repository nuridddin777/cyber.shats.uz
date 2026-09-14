# ============================================================
# CYBER SHATS — Tashkilotlar (M.A.T/JXT) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

tashkilot_bp = Blueprint("tashkilot_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()



# =================================================================
# TASHKILOTLAR — M.A.T MAXSUS / JXT TASHKILOTI (MAXSUS)
# =================================================================
@tashkilot_bp.route("/tashkilot/<org_key>")
@login_required
def organization_page(org_key):
    guard = _require_hacker_plan()
    if guard:
        return guard
    if org_key not in ("mat", "jxt", "shats"):
        abort(404)
    org = query_one("SELECT * FROM organizations WHERE org_key=?", (org_key,))
    posts = query_all("SELECT * FROM organization_posts WHERE org_key=? ORDER BY created_at DESC LIMIT 20", (org_key,))
    user = get_current_user()
    my_request = query_one("SELECT * FROM organization_requests WHERE org_key=? AND user_id=? ORDER BY id DESC LIMIT 1",
                            (org_key, user["id"]))
    return render_template("organization.html", org=org, posts=posts, my_request=my_request)


@tashkilot_bp.route("/tashkilot/<org_key>/request", methods=["POST"])
@login_required
def organization_request(org_key):
    guard = _require_hacker_plan()
    if guard:
        return guard
    if org_key not in ("mat", "jxt", "shats"):
        abort(404)
    user = get_current_user()
    message = request.form.get("message", "").strip()
    execute("INSERT INTO organization_requests (org_key, user_id, message) VALUES (?,?,?)",
            (org_key, user["id"], message))
    flash("So'rovingiz yuborildi! Tashkilot rahbariyati ko'rib chiqadi.", "success")
    return redirect(url_for(".organization_page", org_key=org_key))

