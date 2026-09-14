"""
CYBER SHATS — To'lov agregatorlaridan keladigan WEBHOOK'larni qabul qilish.

Bu yerga Click/Payme/Uzum bizning serverimizga to'lov holati haqida
xabar yuboradi. HAR BIR so'rov imzo (signature) orqali tekshiriladi —
aks holda istalgan kishi "to'lov bo'ldi" deb yolg'on so'rov yuborib,
bepul CODE olishi mumkin bo'lar edi.

Blueprint'ni ro'yxatdan o'tkazish (app.py ichida):
    from payment_webhooks import payment_bp
    app.register_blueprint(payment_bp)

DIQQAT: quyidagi Click/Payme protokoli ularning RASMIY hujjatlariga
(docs.click.uz, developer.help.paycom.uz) asoslangan umumiy sxema.
Merchant hisobingizni olganingizdan so'ng, sandbox muhitida albatta
har bir maydon nomini (masalan xato kodlari) rasmiy hujjat bilan
solishtirib chiqing — agregatorlar vaqti-vaqti bilan kichik
o'zgarishlar kiritadi.
"""
import hashlib
import hmac
import json

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, abort

from config import Config
from payment_gateway import get_transaction, mark_paid, mark_failed, create_payment_order
from db import query_one
from auth import admin_required

payment_bp = Blueprint("payment", __name__, url_prefix="/payment")


# ==================================================================
# CLICK — https://docs.click.uz
# ==================================================================
def _click_signature_valid(data: dict) -> bool:
    action = data.get("action", "0")
    sign_string_parts = [
        data.get("click_trans_id", ""),
        data.get("service_id", ""),
        Config.CLICK_SECRET_KEY,
        data.get("merchant_trans_id", ""),
    ]
    if str(action) == "1":  # Complete bosqichida merchant_prepare_id ham qatnashadi
        sign_string_parts.append(data.get("merchant_prepare_id", ""))
    sign_string_parts += [data.get("amount", ""), action, data.get("sign_time", "")]
    expected = hashlib.md5("".join(str(p) for p in sign_string_parts).encode()).hexdigest()
    return hmac.compare_digest(expected, str(data.get("sign_string", "")))


@payment_bp.route("/webhook/click", methods=["POST"])
def click_webhook():
    data = request.form.to_dict() or request.get_json(silent=True) or {}

    if not Config.CLICK_SECRET_KEY:
        return jsonify({"error": -8, "error_note": "Merchant sozlanmagan (sandbox)"}), 200

    if not _click_signature_valid(data):
        return jsonify({"error": -1, "error_note": "SIGN CHECK FAILED!"}), 200

    merchant_trans_id = data.get("merchant_trans_id", "")
    txn = get_transaction(merchant_trans_id)
    if not txn:
        return jsonify({"error": -5, "error_note": "Buyurtma topilmadi"}), 200

    action = str(data.get("action", "0"))
    if action == "0":  # Prepare
        return jsonify({
            "click_trans_id": data.get("click_trans_id"),
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": txn["id"],
            "error": 0, "error_note": "Success"
        })
    if action == "1":  # Complete
        error_code = int(data.get("error", 0))
        if error_code == 0:
            mark_paid(merchant_trans_id, data.get("click_trans_id", ""), json.dumps(data))
        else:
            mark_failed(merchant_trans_id, json.dumps(data))
        return jsonify({
            "click_trans_id": data.get("click_trans_id"),
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": txn["id"],
            "error": 0, "error_note": "Success"
        })
    return jsonify({"error": -3, "error_note": "Action topilmadi"}), 200


# ==================================================================
# PAYME — JSON-RPC 2.0, Basic Auth (Paycom:merchant_key)
# ==================================================================
def _payme_auth_valid() -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        return False
    import base64
    try:
        decoded = base64.b64decode(auth[6:]).decode()
        login, key = decoded.split(":", 1)
        return login == "Paycom" and hmac.compare_digest(key, Config.PAYME_SECRET_KEY)
    except Exception:
        return False


@payment_bp.route("/webhook/payme", methods=["POST"])
def payme_webhook():
    if not Config.PAYME_SECRET_KEY:
        return jsonify({"error": {"code": -32504, "message": "Merchant sozlanmagan (sandbox)"}}), 200

    if not _payme_auth_valid():
        return jsonify({"error": {"code": -32504, "message": "Ruxsat yo'q"}}), 200

    body = request.get_json(silent=True) or {}
    method = body.get("method")
    params = body.get("params", {})
    rpc_id = body.get("id")
    account = params.get("account", {})
    merchant_trans_id = account.get("order_id", "")

    if method == "CheckPerformTransaction":
        txn = get_transaction(merchant_trans_id)
        if not txn:
            return jsonify({"jsonrpc": "2.0", "id": rpc_id,
                             "error": {"code": -31050, "message": "Buyurtma topilmadi"}})
        return jsonify({"jsonrpc": "2.0", "id": rpc_id, "result": {"allow": True}})

    if method == "CreateTransaction":
        txn = get_transaction(merchant_trans_id)
        if not txn:
            return jsonify({"jsonrpc": "2.0", "id": rpc_id,
                             "error": {"code": -31050, "message": "Buyurtma topilmadi"}})
        return jsonify({"jsonrpc": "2.0", "id": rpc_id, "result": {
            "create_time": 0, "transaction": str(txn["id"]), "state": 1
        }})

    if method == "PerformTransaction":
        provider_txn_id = params.get("id", "")
        mark_paid(merchant_trans_id, provider_txn_id, json.dumps(body))
        return jsonify({"jsonrpc": "2.0", "id": rpc_id, "result": {
            "transaction": str(get_transaction(merchant_trans_id)["id"]),
            "perform_time": 0, "state": 2
        }})

    if method == "CancelTransaction":
        mark_failed(merchant_trans_id, json.dumps(body))
        return jsonify({"jsonrpc": "2.0", "id": rpc_id, "result": {
            "transaction": str(get_transaction(merchant_trans_id)["id"]) if get_transaction(merchant_trans_id) else "0",
            "cancel_time": 0, "state": -1
        }})

    if method == "CheckTransaction":
        txn = get_transaction(merchant_trans_id)
        state = 2 if txn and txn["status"] == "paid" else 1
        return jsonify({"jsonrpc": "2.0", "id": rpc_id, "result": {
            "create_time": 0, "perform_time": 0, "cancel_time": 0,
            "transaction": str(txn["id"]) if txn else "0", "state": state, "reason": None
        }})

    return jsonify({"jsonrpc": "2.0", "id": rpc_id,
                     "error": {"code": -32601, "message": "Method topilmadi"}})


# ==================================================================
# UZUM PAY — HMAC-SHA256 imzo (Payme'ga o'xshash JSON-RPC yoki REST bo'lishi mumkin;
# rasmiy hujjat qo'lga kiritilgach aniq protokolga moslashtiriladi)
# ==================================================================
@payment_bp.route("/webhook/uzum", methods=["POST"])
def uzum_webhook():
    if not Config.UZUM_SECRET_KEY:
        return jsonify({"status": "error", "message": "Merchant sozlanmagan (sandbox)"}), 200

    data = request.get_json(silent=True) or {}
    signature = request.headers.get("X-Signature", "")
    expected = hashlib.sha256((json.dumps(data, sort_keys=True) + Config.UZUM_SECRET_KEY).encode()).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return jsonify({"status": "error", "message": "Imzo mos emas"}), 200

    merchant_trans_id = data.get("order_id", "")
    status = data.get("status", "")
    if status in ("success", "paid", "SUCCESS"):
        mark_paid(merchant_trans_id, data.get("transaction_id", ""), json.dumps(data))
    else:
        mark_failed(merchant_trans_id, json.dumps(data))
    return jsonify({"status": "ok"})


# ==================================================================
# Foydalanuvchi checkout'dan qaytgandagi sahifa (webhook emas — vizual natija)
# ==================================================================
@payment_bp.route("/return/<merchant_trans_id>")
def payment_return(merchant_trans_id):
    txn = get_transaction(merchant_trans_id)
    if not txn:
        flash("Buyurtma topilmadi.", "error")
        return redirect(url_for("coins_page"))
    return render_template("payment_return.html", txn=txn)


# ==================================================================
# SANDBOX rejim — merchant kaliti hali kiritilmaganda, test uchun
# "to'lovni qo'lda tasdiqlash" tugmasi bilan sahifa (FAQAT DEV/DEMO uchun!)
# ==================================================================
@payment_bp.route("/sandbox-checkout/<merchant_trans_id>", methods=["GET", "POST"])
@admin_required
def sandbox_checkout(merchant_trans_id):
    # MUHIM (tuzatilgan xavfsizlik xatosi — CRITICAL): bu route avval HECH
    # QANDAY ruxsat tekshiruvisiz ochiq edi — istalgan (hatto tizimga
    # kirmagan) foydalanuvchi o'zining haqiqiy pul evaziga yaratilgan
    # buyurtmasini shu yerga POST qilib, pul to'lamasdan CODE olishi mumkin
    # edi (chunki hozircha haqiqiy to'lov agregatorlari sozlanmagan —
    # xuddi shu sabab bu tugma productionda ham REAL ishlab turgan edi).
    # Endi: faqat tizimga kirgan ADMIN/SUPER_ADMIN, VA faqat hech qanday
    # haqiqiy to'lov agregatori sozlanmagan bo'lsa (rivojlantirish/demo
    # muhiti) ishlaydi — aks holda 404.
    if Config.CLICK_SECRET_KEY or Config.PAYME_SECRET_KEY or Config.UZUM_SECRET_KEY:
        abort(404)

    txn = get_transaction(merchant_trans_id)
    if not txn:
        flash("Buyurtma topilmadi.", "error")
        return redirect(url_for("coins_page"))

    if request.method == "POST":
        # Bu FAQAT sandbox — haqiqiy loyihada bu tugma ishlamasligi shart,
        # chunki haqiqiy pul agregator orqali o'tadi, bu yerda emas.
        mark_paid(merchant_trans_id, f"SANDBOX-{merchant_trans_id}", "sandbox-manual-confirm")
        flash("Sandbox: to'lov shartli tasdiqlandi, CODE qo'shildi.", "success")
        return redirect(url_for("payment.payment_return", merchant_trans_id=merchant_trans_id))

    return render_template("payment_sandbox.html", txn=txn)
