"""
CYBER SHATS — Xavfsizlik moduli
- Brute force himoya
- IP bloklash
- So'rov chastota cheklash
- Shubhali so'rovlarni log qilish
- SQL injection / XSS urinishlarini aniqlash
"""
import re, datetime
from functools import wraps
from flask import request, jsonify, session
from db import query_one, query_all, execute
from config import Config

# -----------------------------------------------------------------
# IP BLOKLASH TEKSHIRUVI
# -----------------------------------------------------------------
def is_ip_blocked(ip: str) -> bool:
    row = query_one(
        "SELECT * FROM blocked_ips WHERE ip=? AND (expires_at IS NULL OR expires_at > datetime('now'))",
        (ip,)
    )
    return row is not None


def block_ip(ip: str, reason: str = "", duration_hours: int = 24, blocked_by=None):
    expires = (datetime.datetime.utcnow() + datetime.timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "INSERT INTO blocked_ips (ip, reason, blocked_by, expires_at) VALUES (?,?,?,?) "
        "ON CONFLICT (ip) DO UPDATE SET reason=excluded.reason, blocked_by=excluded.blocked_by, "
        "expires_at=excluded.expires_at",
        (ip, reason, blocked_by, expires)
    )
    log_security_event(None, "ip_blocked", ip, "", f"reason:{reason}", "high")


# -----------------------------------------------------------------
# XAVFSIZLIK HODISASI LOG
# -----------------------------------------------------------------
def log_security_event(user_id, event_type: str, ip: str, user_agent: str,
                        details: str = "", severity: str = "low"):
    execute(
        "INSERT INTO security_events (user_id, event_type, ip, user_agent, details, severity) VALUES (?,?,?,?,?,?)",
        (user_id, event_type, ip, user_agent, details, severity)
    )


# -----------------------------------------------------------------
# BRUTE FORCE HIMOYASI
# -----------------------------------------------------------------
def check_brute_force(email: str, ip: str) -> tuple[bool, str]:
    """
    Noto'g'ri login urinishlarini tekshiradi.
    Returns: (blocked: bool, message: str)
    """
    # IP bo'yicha tekshirish
    if is_ip_blocked(ip):
        log_security_event(None, "blocked_ip_attempt", ip, request.headers.get("User-Agent", ""), f"email:{email}", "high")
        return True, "Bu IP manzil bloklangan. Administrator bilan bog'laning."

    # Email bo'yicha tekshirish (foydalanuvchi lock)
    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    if user:
        if user.get("locked_until"):
            locked_until = user["locked_until"]
            now_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            if locked_until > now_str:
                try:
                    locked_dt = datetime.datetime.strptime(locked_until[:19], "%Y-%m-%d %H:%M:%S")
                    mins = max(1, int((locked_dt - datetime.datetime.utcnow()).total_seconds() // 60))
                except ValueError:
                    mins = Config.LOCK_MINUTES
                return True, f"Hisob {mins} daqiqaga bloklangan. Keyinroq urinib ko'ring."

    return False, ""


def record_failed_login(email: str, ip: str):
    """Noto'g'ri login urinishini qayd etadi va kerak bo'lsa bloklaydi."""
    user = query_one("SELECT * FROM users WHERE email=?", (email,))
    if user:
        count = (user.get("failed_login_count") or 0) + 1
        if count >= Config.MAX_FAILED_LOGINS:
            locked_until = (datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.LOCK_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
            execute("UPDATE users SET failed_login_count=?, locked_until=? WHERE id=?",
                    (count, locked_until, user["id"]))
            log_security_event(user["id"], "account_locked", ip,
                               request.headers.get("User-Agent", ""),
                               f"after_{count}_failed_attempts", "high")
            # Ko'p urinish bo'lsa IPni ham bloklash
            if count >= Config.MAX_FAILED_LOGINS * 2:
                block_ip(ip, f"brute_force_email:{email}", 24)
        else:
            execute("UPDATE users SET failed_login_count=? WHERE id=?", (count, user["id"]))

    log_security_event(
        user["id"] if user else None,
        "failed_login", ip, request.headers.get("User-Agent", ""),
        f"email:{email}", "medium"
    )


def clear_failed_logins(user_id: int):
    execute("UPDATE users SET failed_login_count=0, locked_until=NULL WHERE id=?", (user_id,))


# -----------------------------------------------------------------
# SO'ROV NAZORATI (Rate limiting - in-memory, oddiy)
# -----------------------------------------------------------------
_rate_store: dict = {}  # { ip: [timestamp, ...] }

def check_rate_limit(ip: str) -> bool:
    """True = cheklov, False = OK.
    DIQQAT: avval bu FAQAT IP bo'yicha hisoblanardi — O'zbekistonda mobil
    operatorlar ko'pincha CGNAT ishlatadi (ko'plab foydalanuvchi BITTA
    tashqi IP orqali chiqadi), shuning uchun bir nechta halol foydalanuvchi
    BIR-BIRINING harakati tufayli tasodifan bloklanib qolishi mumkin edi.
    Endi: tizimga kirgan foydalanuvchi uchun IP+user_id kombinatsiyasi
    bo'yicha hisoblanadi (faqat ODDIY IP emas) — bu holda ular bir-biriga
    ta'sir qilmaydi. Shuningdek, chegara ko'proq (real ilova + fon so'rovlari
    -bildirishnomalar pollingi kabi- uchun yetarli bo'lishi uchun) oshirildi."""
    import time
    from flask import session as _session
    now = time.time()
    window = Config.RATE_LIMIT_WINDOW
    max_req = Config.RATE_LIMIT_MAX

    key = ip
    try:
        uid = _session.get("user_id")
        if uid:
            key = f"u:{uid}"
    except RuntimeError:
        pass

    if key not in _rate_store:
        _rate_store[key] = []
    _rate_store[key] = [t for t in _rate_store[key] if now - t < window]
    _rate_store[key].append(now)
    if len(_rate_store[key]) > max_req:
        log_security_event(None, "rate_limit_exceeded", ip,
                           request.headers.get("User-Agent", ""), "", "medium")
        return True
    return False


# -----------------------------------------------------------------
# ZARARLI MA'LUMOT ANIQLASH
# -----------------------------------------------------------------
_SQL_PATTERNS = [
    r"(\b(union|select|insert|update|delete|drop|create|alter|exec|execute)\b)",
    r"(--|;|'|\"|\bor\b|\band\b).*?=",
    r"(\bwaitfor\b|\bdelay\b|\bsleep\b)"
]
_XSS_PATTERNS = [
    r"<script[^>]*>",
    r"javascript\s*:",
    r"on\w+\s*=",
    r"<iframe",
    r"eval\s*\("
]

def scan_request() -> tuple[bool, str]:
    """
    Har bir so'rovning parametrlarini skanerlaydi.
    Returns: (threat_found: bool, threat_type: str)
    """
    all_values = []
    for v in request.values.values():
        all_values.append(str(v).lower())
    for v in (request.get_json(silent=True) or {}).values():
        all_values.append(str(v).lower())

    for val in all_values:
        for pat in _SQL_PATTERNS:
            if re.search(pat, val, re.IGNORECASE):
                return True, "sql_injection"
        for pat in _XSS_PATTERNS:
            if re.search(pat, val, re.IGNORECASE):
                return True, "xss_attempt"
    return False, ""


# -----------------------------------------------------------------
# GLOBAL XAVFSIZLIK MIDDLEWARE DEKORATOR
# -----------------------------------------------------------------
def secure_route(view):
    """Barcha himoyalangan route larni o'rab oluvchi dekorator."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()

        # IP bloklash
        if is_ip_blocked(ip):
            log_security_event(None, "blocked_ip_request", ip,
                               request.headers.get("User-Agent", ""), request.path, "high")
            return jsonify({"error": "Ruxsat etilmagan"}), 403

        # Rate limit
        if check_rate_limit(ip):
            return jsonify({"error": "Juda ko'p so'rov. Biroz kuting."}), 429

        # Zararli kontent skaneri
        threat, ttype = scan_request()
        if threat:
            log_security_event(
                session.get("user_id"), ttype, ip,
                request.headers.get("User-Agent", ""),
                f"path:{request.path}", "critical"
            )
            block_ip(ip, f"auto_blocked:{ttype}", 6)
            return jsonify({"error": "So'rov rad etildi"}), 400

        return view(*args, **kwargs)
    return wrapped
