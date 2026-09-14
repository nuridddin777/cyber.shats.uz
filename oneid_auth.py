"""
CYBER SHATS — OneID (id.egov.uz) orqali shaxsni tasdiqlash.

OneID — bu TO'LOV tizimi EMAS. Bu O'zbekiston Respublikasining
"Yagona identifikatsiya tizimi" — foydalanuvchi ID-karta/pasport orqali
"men haqiqatan shu odamman" deb elektron tasdiqlaydi (OAuth2 orqali,
xuddi "Google orqali kirish" kabi, lekin davlat tizimi).

Foydalanish maqsadi: katta summada CODE sotib olishdan oldin yoki
ro'yxatdan o'tishda foydalanuvchi shaxsini tasdiqlash (firibgarlikning
oldini olish — soddalashtirilgan KYC).

RO'YXATDAN O'TISH (haqiqiy ishga tushirishdan oldin SIZ qilishingiz kerak):
  1. Yuridik shaxs/YTT sifatida https://api-catalog.egov.uz yoki OneID
     ma'muriyatiga ariza berish orqali tashkilot sifatida ro'yxatdan
     o'tasiz.
  2. Sizga CLIENT_ID va CLIENT_SECRET beriladi, shuningdek rasmiy
     Authorization/Token/Person endpoint manzillari va aniq protokol
     hujjati (bular vaqti-vaqti bilan yangilanishi mumkin, shuning
     uchun quyida .env orqali sozlanadigan qilib qo'yilgan).
  3. .env fayliga ONEID_CLIENT_ID, ONEID_CLIENT_SECRET va True
     endpoint manzillarini kiritasiz — kodni o'zgartirish shart emas.

Hozircha bu modul CLIENT_ID bo'sh bo'lsa "sozlanmagan" deb xabar beradi.
"""
import secrets
import urllib.parse
import urllib.request
import json

from flask import Blueprint, redirect, request, session, flash, url_for

from config import Config
from db import query_one, execute, log_action
from security import log_security_event

oneid_bp = Blueprint("oneid", __name__, url_prefix="/auth/oneid")


def _fetch(url, headers=None, data=None):
    req = urllib.request.Request(url, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


@oneid_bp.route("/login")
def oneid_login():
    if not Config.ONEID_CLIENT_ID:
        flash("OneID hali sozlanmagan. Avval tashkilot sifatida ro'yxatdan o'ting.", "error")
        return redirect(request.referrer or url_for("dashboard"))

    state = secrets.token_urlsafe(16)
    session["oneid_state"] = state
    params = {
        "response_type": "code",
        "client_id": Config.ONEID_CLIENT_ID,
        "redirect_uri": Config.ONEID_REDIRECT_URI,
        "scope": "profile",
        "state": state,
    }
    return redirect(Config.ONEID_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params))


@oneid_bp.route("/callback")
def oneid_callback():
    if request.args.get("state") != session.pop("oneid_state", None):
        flash("OneID xatosi: state mos kelmadi.", "error")
        return redirect(url_for("dashboard"))

    code = request.args.get("code")
    if not code:
        flash("OneID orqali tasdiqlash bekor qilindi.", "warn")
        return redirect(url_for("dashboard"))

    user_id = session.get("user_id")
    if not user_id:
        flash("Avval saytga kiring.", "error")
        return redirect(url_for("login"))

    try:
        token_data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "code": code,
            "client_id": Config.ONEID_CLIENT_ID,
            "client_secret": Config.ONEID_CLIENT_SECRET,
            "redirect_uri": Config.ONEID_REDIRECT_URI,
        }).encode()
        tokens = _fetch(Config.ONEID_TOKEN_URL,
                        {"Content-Type": "application/x-www-form-urlencoded"}, token_data)
        access_token = tokens.get("access_token", "")

        person = _fetch(Config.ONEID_PERSON_URL + f"?access_token={access_token}")
        pinfl = person.get("pin") or person.get("pinfl") or ""
        full_name = " ".join(filter(None, [
            person.get("last_name", ""), person.get("first_name", ""), person.get("middle_name", "")
        ]))

        if not pinfl:
            raise ValueError("PINFL topilmadi")

        # Bir PINFL bir nechta hisobga bog'lanmasin (bitta odam = bitta hisob)
        already = query_one("SELECT id FROM users WHERE oneid_pinfl=? AND id!=?", (pinfl, user_id))
        if already:
            flash("Bu shaxsga tegishli boshqa hisob allaqachon tasdiqlangan.", "error")
            return redirect(url_for("dashboard"))

        execute("UPDATE users SET oneid_verified=1, oneid_pinfl=?, oneid_full_name=? WHERE id=?",
                (pinfl, full_name, user_id))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (user_id, "Shaxsingiz tasdiqlandi",
                 "OneID orqali shaxsingiz muvaffaqiyatli tasdiqlandi. Endi katta summada CODE sotib olishingiz mumkin.",
                 "success"))
        log_action(user_id, "oneid_verified", ip=request.remote_addr)
        flash("Shaxsingiz OneID orqali muvaffaqiyatli tasdiqlandi!", "success")
    except Exception as e:
        log_security_event(user_id, "oneid_error", request.remote_addr,
                           request.headers.get("User-Agent", ""), str(e), "medium")
        flash("OneID orqali tasdiqlashda xato. Qayta urinib ko'ring.", "error")

    return redirect(url_for("dashboard"))
