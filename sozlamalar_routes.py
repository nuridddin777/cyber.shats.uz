# ============================================================
# CYBER SHATS — Sozlamalar Maxsus bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, Response
from auth import get_current_user, login_required
from db import query_one, query_all, execute
import secrets, json

sozlamalar_bp = Blueprint("sozlamalar_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


# =================================================================
# =================================================================
@sozlamalar_bp.route("/sozlamalar-maxsus/api-key/generate", methods=["POST"])
@login_required
def api_key_generate():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import secrets
    user = get_current_user()
    execute("UPDATE api_keys SET active=0 WHERE user_id=?", (user["id"],))
    key = "sk_maxsus_" + secrets.token_hex(20)
    execute("INSERT INTO api_keys (user_id, api_key, label) VALUES (?,?,?)", (user["id"], key, "default"))
    flash("Yangi API kalit yaratildi!", "success")
    return redirect(url_for("settings"))


@sozlamalar_bp.route("/sozlamalar-maxsus/api-key/revoke", methods=["POST"])
@login_required
def api_key_revoke():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    execute("UPDATE api_keys SET active=0 WHERE user_id=?", (user["id"],))
    flash("API kalit bekor qilindi.", "success")
    return redirect(url_for("settings"))


@sozlamalar_bp.route("/sozlamalar-maxsus/export")
@login_required
def export_my_data():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import json
    from flask import Response
    user = get_current_user()
    fresh = query_one("SELECT * FROM users WHERE id=?", (user["id"],))
    data = {
        "profile": {k: v for k, v in dict(fresh).items() if k != "password_hash"},
        "code_transactions": [dict(r) for r in query_all(
            "SELECT * FROM code_transactions WHERE user_id=? ORDER BY id DESC LIMIT 500", (user["id"],)
        )] if query_one("SELECT name FROM sqlite_master WHERE type='table' AND name='code_transactions'") else [],
    }
    body = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    return Response(body, mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=mening_malumotlarim.json"})

