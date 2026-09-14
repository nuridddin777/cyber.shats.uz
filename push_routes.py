# ============================================================
# CYBER SHATS — Push bildirishnomalar (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash
from auth import get_current_user, api_login_required, login_required
from db import log_action
from utils import api_response
import webpush_mod as push_mod
from config import Config

push_bp = Blueprint("push_bp", __name__)


@push_bp.route("/api/push/vapid-public-key")
def api_push_vapid_key():
    """Frontend uchun VAPID public key (obuna yaratishda kerak)."""
    return api_response(True, data={
        "publicKey": Config.VAPID_PUBLIC_KEY,
        "configured": push_mod.is_push_configured(),
    })


@push_bp.route("/api/push/subscribe", methods=["POST"])
@api_login_required
def api_push_subscribe():
    """Brauzer push obunasini saqlash."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint", "")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh", "")
    auth = keys.get("auth", "")
    ua = request.headers.get("User-Agent", "")[:255]
    ok, msg = push_mod.save_subscription(user["id"], endpoint, p256dh, auth, ua)
    if ok:
        log_action(user["id"], "push_subscribed", ip=request.remote_addr)
        return api_response(True, data={"message": msg})
    return api_response(False, error=msg)


@push_bp.route("/api/push/unsubscribe", methods=["POST"])
@api_login_required
def api_push_unsubscribe():
    """Push obunasini bekor qilish (foydalanuvchi ovozni/push'ni o'chirganda)."""
    data = request.get_json(silent=True) or {}
    endpoint = data.get("endpoint", "")
    if endpoint:
        push_mod.remove_subscription(endpoint)
    return api_response(True)


@push_bp.route("/api/push/test", methods=["POST"])
@login_required
def api_push_test():
    """Foydalanuvchi o'zi sinash uchun test push yuborish."""
    user = get_current_user()
    if not push_mod.has_active_subscription(user["id"]):
        flash("Avval push bildirishnomalarni yoqing.", "error")
        return redirect(request.referrer or url_for("dashboard"))
    result = push_mod.send_push_to_user(
        user["id"], "Test bildirishnoma",
        "Bu CYBER SHATS dan sinov xabari. Push ishlayapti!", "/dashboard"
    )
    if result.get("sent", 0) > 0:
        flash(f"Test push yuborildi ({result['sent']} ta qurilmaga).", "success")
    else:
        flash("Push yuborilmadi: " + result.get("error", "noma'lum xato"), "error")
    return redirect(request.referrer or url_for("dashboard"))

