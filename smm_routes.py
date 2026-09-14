# ============================================================
# CYBER SHATS — SMM/Targetolog/Logistika bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute, log_action
from utils import api_response
from smm_ai import chat_smm, SMM_DIRECTIONS, get_smm_history

smm_bp = Blueprint("smm_bp", __name__)


def award_xp(user_id, amount):
    from app import award_xp as _real_fn
    return _real_fn(user_id, amount)



# =================================================================
# SMM / TARGETOLOG / LOGISTIKA — Faqat Pro (alohida AI chat)
# =================================================================
@smm_bp.route("/smm")
@login_required
def smm_hub():
    user = get_current_user()
    return render_template("smm_hub.html", smm_directions=SMM_DIRECTIONS, user=user)


@smm_bp.route("/smm/<direction>")
@login_required
def smm_chat(direction):
    user = get_current_user()
    if direction not in SMM_DIRECTIONS:
        abort(404)
    history = get_smm_history(user["id"], direction)
    config = SMM_DIRECTIONS[direction]
    return render_template("smm_chat.html", direction=direction, config=config,
                           smm_directions=SMM_DIRECTIONS, history=history)


@smm_bp.route("/api/smm/chat", methods=["POST"])
@api_login_required
def api_smm_chat():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    direction = data.get("direction", "smm")
    if not message:
        return api_response(False, error="Xabar bo'sh bo'lishi mumkin emas", status=400)
    reply, is_live = chat_smm(user["id"], direction, message)
    award_xp(user["id"], 2)
    log_action(user["id"], "smm_chat", details=f"dir:{direction}", ip=request.remote_addr)
    return api_response(True, data={"reply": reply, "is_live": is_live})

