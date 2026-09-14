# ============================================================
# CYBER SHATS — AI Shaxsiylashtirilgan tavsiyalar (Blueprint)
# ============================================================
from flask import Blueprint, request
from auth import get_current_user, api_login_required
from db import query_one, execute, log_action
from utils import api_response
from coins import ensure_ai_access_general
import ai_recommendations
import datetime, json

airecs_bp = Blueprint("airecs_bp", __name__)


AI_RECS_STALE_HOURS = 24
AI_RECS_MIN_REFRESH_HOURS = 6  # ortiqcha AI so'rovlarining oldini olish uchun


@airecs_bp.route("/api/ai/recommendations")
@api_login_required
def api_ai_recommendations_get():
    """Keshlangan tavsiyalarni qaytaradi (bo'lmasa yoki juda eski bo'lsa,
    frontend buni ko'rib 'generate' endpointini chaqiradi)."""
    user = get_current_user()
    row = query_one("SELECT recommendations_json, generated_at FROM user_ai_recommendations WHERE user_id=?",
                     (user["id"],))
    if not row:
        return api_response(True, data={"recommendations": None, "generated_at": None, "stale": True})
    age_hours = _hours_since(row["generated_at"])
    return api_response(True, data={
        "recommendations": json.loads(row["recommendations_json"]),
        "generated_at": row["generated_at"],
        "stale": age_hours >= AI_RECS_STALE_HOURS,
    })


def _hours_since(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
        return (datetime.datetime.now() - dt).total_seconds() / 3600
    except (ValueError, TypeError):
        return 999


@airecs_bp.route("/api/ai/recommendations/generate", methods=["POST"])
@api_login_required
def api_ai_recommendations_generate():
    user = get_current_user()
    row = query_one("SELECT generated_at FROM user_ai_recommendations WHERE user_id=?", (user["id"],))
    if row and _hours_since(row["generated_at"]) < AI_RECS_MIN_REFRESH_HOURS:
        remaining = round(AI_RECS_MIN_REFRESH_HOURS - _hours_since(row["generated_at"]), 1)
        return api_response(False, error=f"Tavsiyalar yaqinda yangilangan. {remaining} soatdan keyin qayta so'rang.")

    ok, gate_msg = ensure_ai_access_general(user["id"])
    if not ok:
        return api_response(False, error=gate_msg)

    recs, err = ai_recommendations.generate_recommendations(user["id"])
    if err:
        return api_response(False, error=err)

    recs_json = json.dumps(recs, ensure_ascii=False)
    execute("""INSERT INTO user_ai_recommendations (user_id, recommendations_json, generated_at)
               VALUES (?,?,datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET recommendations_json=excluded.recommendations_json,
                                                    generated_at=excluded.generated_at""",
            (user["id"], recs_json))
    log_action(user["id"], "ai_recommendations_generated", details=f"count:{len(recs)}", ip=request.remote_addr)
    return api_response(True, data={"recommendations": recs, "generated_at": datetime.datetime.now().isoformat()})


