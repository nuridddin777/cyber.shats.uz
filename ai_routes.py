# ============================================================
# CYBER SHATS — AI Yordamchi bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute, log_action
from utils import api_response
from coins import (ensure_ai_access_general, buy_ai_daily_boost, get_balance)
from ai import call_ai_assistant, generate_image
import datetime

ai_bp = Blueprint("ai_bp", __name__)


def award_xp(user_id, amount):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import award_xp as _real_fn
    return _real_fn(user_id, amount)


AI_TYPES = [
    {"id": "umumiy", "name": "Umumiy AI", "icon": "bot"},
    {"id": "kod", "name": "Kod Yozuvchi", "icon": "code"},
    {"id": "cyber", "name": "Cyber Security", "icon": "shield"},
    {"id": "design", "name": "Design AI", "icon": "layers"},
    {"id": "cloud", "name": "Cloud AI", "icon": "cloud"},
    {"id": "tarix", "name": "Tarix AI", "icon": "book"},
]


@ai_bp.route("/ai")
@login_required
def ai_assistant():
    atype = request.args.get("type", "umumiy")
    user = get_current_user()
    history = query_all(
        "SELECT * FROM ai_messages WHERE user_id=? AND assistant_type=? ORDER BY id ASC LIMIT 300",
        (user["id"], atype))

    # Yangi AI iqtisodiyoti: FREE foydalanuvchi kuniga 3 marta bepul,
    # Pro+/admin/mentor — cheksiz. Haftalik obuna modeli endi ishlatilmaydi.
    # Tariflar olib tashlangan — endi hamma cheksiz foydalanadi
    is_unlimited = True
    today = datetime.date.today().isoformat()
    used_today = 0
    if not is_unlimited:
        row = query_one("SELECT count FROM ai_daily_usage WHERE user_id=? AND usage_date=?", (user["id"], today))
        used_today = row["count"] if row else 0
    remaining_today = max(0, 3 - used_today)

    return render_template("ai_assistant.html", ai_types=AI_TYPES, active_type=atype, history=history,
                            is_unlimited_ai=is_unlimited, remaining_today=remaining_today,
                            ai_code_help_price=2)


@ai_bp.route("/ai/tarix")
@login_required
def ai_history():
    """AI bilan bo'lgan BARCHA suhbatlar tarixi (barcha yo'nalishlar bo'yicha,
    eng yangisidan eskisiga qarab, sahifalab ko'rsatiladi) — foydalanuvchi
    ilgari so'ragan HAR QANDAY savolni topa olishi uchun."""
    user = get_current_user()
    atype_filter = request.args.get("type", "").strip()
    q = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per = 40
    offset = (page - 1) * per

    sql = "SELECT * FROM ai_messages WHERE user_id=?"
    args = [user["id"]]
    if atype_filter:
        sql += " AND assistant_type=?"
        args.append(atype_filter)
    if q:
        sql += " AND content LIKE ?"
        args.append(f"%{q}%")
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) c")
    total = query_one(count_sql, tuple(args))["c"]
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    args += [per, offset]
    messages = query_all(sql, tuple(args))

    type_labels = {t["id"]: t["name"] for t in AI_TYPES}
    total_pages = max(1, (total + per - 1) // per)

    return render_template("ai_history.html", messages=messages, ai_types=AI_TYPES,
                            type_labels=type_labels, atype_filter=atype_filter, q=q,
                            page=page, total_pages=total_pages, total=total)


ALLOWED_AI_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_AI_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB/rasm


@ai_bp.route("/api/ai/chat", methods=["POST"])
@api_login_required
def api_ai_chat():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    atype = data.get("type", "umumiy")

    # Rasmlar (ixtiyoriy) — brauzerda base64 (data URL)ga o'tkazilib yuboriladi:
    # [{"media_type": "image/png", "data": "<base64, prefiksiz>"}]
    raw_images = data.get("images") or []
    images = []
    for img in raw_images[:4]:
        media_type = (img.get("media_type") or "").strip()
        b64data = (img.get("data") or "").strip()
        if media_type not in ALLOWED_AI_IMAGE_TYPES or not b64data:
            continue
        # Base64 uzunligidan taxminiy hajmni tekshiramiz (haqiqiy hajm ~ 3/4 * len)
        if len(b64data) * 3 / 4 > MAX_AI_IMAGE_BYTES:
            return api_response(False, error="Rasm hajmi 5 MB dan katta bo'lmasligi kerak.", status=400)
        images.append({"media_type": media_type, "data": b64data})

    if not message and not images:
        return api_response(False, error="Xabar yoki rasm yuboring", status=400)

    # AI obuna tekshiruvi (Pro/Cyber Pro/VIP — cheksiz; FREE — haftalik 1 CODE)
    ok, msg = ensure_ai_access_general(user["id"])
    if not ok:
        return api_response(False, error=msg, status=402)

    history = query_all(
        "SELECT role, content FROM ai_messages WHERE user_id=? AND assistant_type=? ORDER BY id ASC LIMIT 20",
        (user["id"], atype))

    stored_message = message or "(rasm yuborildi)"
    if images:
        stored_message = (stored_message + " [📷 rasm biriktirilgan]").strip()
    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], atype, "user", stored_message))

    reply, is_live = call_ai_assistant(atype, message, history, images=images)

    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], atype, "assistant", reply))
    award_xp(user["id"], 2)
    log_action(user["id"], "ai_chat", details=f"type:{atype}", ip=request.remote_addr)
    balance = get_balance(user["id"])
    return api_response(True, data={"reply": reply, "is_live": is_live, "code_balance": balance})


@ai_bp.route("/api/ai/generate-image", methods=["POST"])
@api_login_required
def api_ai_generate_image():
    """AI orqali matndan rasm yaratish (faqat Gemini). Oddiy savol-javob
    'havzasi' bilan bir xil kunlik limitga kiradi (admin/Pro+ — cheksiz)."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return api_response(False, error="Rasm uchun ta'rif kiriting.", status=400)
    if len(prompt) > 500:
        return api_response(False, error="Ta'rif juda uzun (maksimal 500 belgi).", status=400)

    ok, msg = ensure_ai_access_general(user["id"])
    if not ok:
        return api_response(False, error=msg, status=402)

    img_b64, mime_type, err = generate_image(prompt)
    if err:
        return api_response(False, error=err)

    log_action(user["id"], "ai_generate_image", details=prompt[:100], ip=request.remote_addr)
    return api_response(True, data={"image_base64": img_b64, "mime_type": mime_type})


@ai_bp.route("/ai/boost/<int:multiplier>", methods=["POST"])
@login_required
def ai_buy_boost(multiplier):
    """Kunlik AI (oddiy savol-javob) limitini 2x (5 CODE) yoki 5x (25 CODE)
    ga vaqtincha (faqat bugun uchun) oshiradi."""
    user = get_current_user()
    ok, msg = buy_ai_daily_boost(user["id"], multiplier)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".ai_assistant"))

