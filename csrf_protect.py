# ============================================================
# CYBER SHATS — Global CSRF himoyasi va xavfsizlik sarlavhalari
# ============================================================
# Bu modul butun ilova (app.py) uchun CSRF (Cross-Site Request Forgery)
# himoyasini ta'minlaydi. edu_orgs blueprint'i buni allaqachon o'zi
# uchun alohida qilgan edi (edu_orgs_routes.py) — bu modul esa QOLGAN
# barcha POST/PUT/PATCH/DELETE so'rovlarni (asosiy app.py + virtual_world
# + edu blueprint'lari) himoya qiladi.
#
# Ishlash prinsipi ("synchronizer token"):
#   1. Har bir sessiya uchun tasodifiy, taxmin qilib bo'lmaydigan token
#      generatsiya qilinadi va sessiyada saqlanadi.
#   2. Shu token har bir sahifada (base.html orqali) yashirin forma
#      maydoni va JS orqali barcha fetch() so'rovlariga sarlavha
#      (X-CSRFToken) sifatida qo'shiladi.
#   3. Har bir holatni o'zgartiruvchi so'rovda (POST/PUT/PATCH/DELETE)
#      yuborilgan token sessiyadagi token bilan solishtiriladi
#      (doimiy vaqtli — timing-attack'ga qarshi hmac.compare_digest).
#      Mos kelmasa — 403 qaytariladi.
#
# Istisnolar (CSRF tekshiruvidan ATAY chetlab o'tiladi):
#   - To'lov agregatorlaridan (Click/Payme/Uzum) keladigan webhook'lar —
#     ular brauzer sessiyasiga ega emas, o'z imzosi (signature) bilan
#     tasdiqlanadi (qarang: payment_webhooks.py).
#   - edu_orgs blueprint'i — o'zining CSRF tizimi bor (edu2_csrf).
import hmac
import secrets

from flask import session, request, abort

CSRF_SESSION_KEY = "_csrf_token"

# So'rov yo'llari shu prefikslar bilan boshlansa, global CSRF tekshiruvidan
# o'tkazilmaydi (chunki ular tashqi xizmatlardan keladi va imzo bilan
# tasdiqlanadi, yoki o'zining alohida CSRF tizimi bor).
CSRF_EXEMPT_PREFIXES = (
    "/payment/webhook/",   # Click / Payme / Uzum — tashqi serverdan keladi
    "/api/webapp/",        # Telegram Mini App API'lari — brauzer sessiyasi
                           # EMAS, initData HMAC-SHA256 orqali tasdiqlanadi
                           # (webapp_auth.verify_init_data), bu o'zi CSRF'ga
                           # teng kuchli himoya (soxtalashtirib bo'lmaydi).
)
CSRF_EXEMPT_BLUEPRINTS = {
    "edu_orgs",   # o'zining CSRF tekshiruvi bor (edu_orgs_routes.py)
}


def get_csrf_token() -> str:
    """Joriy sessiya uchun CSRF tokenini qaytaradi, yo'q bo'lsa yaratadi."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_hex(24)
        session[CSRF_SESSION_KEY] = token
    return token


def _extract_submitted_token() -> str:
    """So'rovdan yuborilgan CSRF tokenini turli manbalardan qidiradi."""
    # 1) Oddiy HTML forma maydoni
    token = request.form.get("csrf_token")
    if token:
        return token
    # 2) fetch() orqali yuborilgan maxsus sarlavha
    token = request.headers.get("X-CSRFToken") or request.headers.get("X-CSRF-Token")
    if token:
        return token
    # 3) JSON tanasi ichida yuborilgan bo'lishi mumkin
    if request.is_json:
        data = request.get_json(silent=True) or {}
        if isinstance(data, dict) and data.get("csrf_token"):
            return data["csrf_token"]
    return ""


def csrf_protect():
    """@app.before_request ichida chaqiriladigan global CSRF tekshiruvi."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None

    path = request.path or ""
    if any(path.startswith(p) for p in CSRF_EXEMPT_PREFIXES):
        return None
    if request.blueprint in CSRF_EXEMPT_BLUEPRINTS:
        return None

    expected = session.get(CSRF_SESSION_KEY, "")
    submitted = _extract_submitted_token()

    if not expected or not submitted or not hmac.compare_digest(str(expected), str(submitted)):
        abort(403)
    return None


def apply_security_headers(response):
    """@app.after_request ichida chaqiriladi — barcha javoblarga xavfsizlik
    sarlavhalarini qo'shadi (clickjacking, MIME-sniffing, XSS'ning ba'zi
    turlariga qarshi)."""
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "geolocation=(), microphone=(), camera=()"
    )
    # Eslatma: qattiq Content-Security-Policy ataylab qo'shilmadi, chunki
    # loyihada ko'plab inline <script>/<style> va cdnjs.cloudflare.com dan
    # uchinchi tomon skriptlari ishlatiladi — noto'g'ri CSP butun saytni
    # (jumladan barcha tugmalar/animatsiyalarni) buzib qo'yishi mumkin.
    # Agar kelajakda inline skriptlar nonce/hash bilan almashtirilsa,
    # bu yerga qat'iy CSP qo'shish tavsiya etiladi.
    return response
