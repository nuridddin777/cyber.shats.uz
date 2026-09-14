# ============================================================
# CYBER SHATS — Profil ramkalari (frame) do'koni
# ============================================================
from db import query_one, query_all, execute

# Tarif-eksklyuziv ramka faqat SHU tarifga ega bo'lgan foydalanuvchiga
# (avtomatik, sotib olinmasdan) ochiladi.
PLAN_FRAME_MAP = {
    "pro": "t_pro",
    "cyber_pro": "t_cyber_pro",
    "vip": "t_vip",
    "hacker": "t_hacker",
    "admin": "t_admin",
}


def get_all_frames():
    return query_all("SELECT * FROM profile_frames ORDER BY sort_order")


def get_purchasable_frames():
    return query_all("SELECT * FROM profile_frames WHERE tier_required IS NULL ORDER BY price_code")


def get_tier_frames():
    return query_all("SELECT * FROM profile_frames WHERE tier_required IS NOT NULL ORDER BY sort_order")


def get_user_available_frames(user_id: int):
    """Foydalanuvchi TANLASHI mumkin bo'lgan barcha ramkalar: sotib olganlari
    + joriy tarifiga mos keladigan eksklyuziv ramka (agar bor bo'lsa)."""
    user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
    owned_keys = {r["frame_key"] for r in query_all(
        "SELECT frame_key FROM user_owned_frames WHERE user_id=?", (user_id,))}
    tier_frame_key = PLAN_FRAME_MAP.get(user["plan"]) if user else None
    if tier_frame_key:
        owned_keys.add(tier_frame_key)
    if not owned_keys:
        return []
    placeholders = ",".join("?" * len(owned_keys))
    return query_all(
        f"SELECT * FROM profile_frames WHERE frame_key IN ({placeholders}) ORDER BY sort_order",
        tuple(owned_keys)
    )


def user_owns_frame(user_id: int, frame_key: str) -> bool:
    frame = query_one("SELECT tier_required FROM profile_frames WHERE frame_key=?", (frame_key,))
    if not frame:
        return False
    if frame["tier_required"]:
        user = query_one("SELECT plan FROM users WHERE id=?", (user_id,))
        return user and user["plan"] == frame["tier_required"]
    owned = query_one(
        "SELECT 1 FROM user_owned_frames WHERE user_id=? AND frame_key=?", (user_id, frame_key))
    return owned is not None


def buy_frame(user_id: int, frame_key: str) -> tuple[bool, str]:
    from coins import spend_coins, refund_coins
    frame = query_one("SELECT * FROM profile_frames WHERE frame_key=?", (frame_key,))
    if not frame:
        return False, "Bu ramka topilmadi."
    if frame["tier_required"]:
        return False, "Bu ramka faqat tegishli tarifga ega bo'lganlarga avtomatik ochiladi, sotib olinmaydi."
    if query_one("SELECT 1 FROM user_owned_frames WHERE user_id=? AND frame_key=?", (user_id, frame_key)):
        return False, "Bu ramka sizda allaqachon bor."
    ok, msg = spend_coins(user_id, frame["price_code"], "frame_purchase")
    if not ok:
        return False, f"{frame['price_code']} CODE kerak, balansingiz yetarli emas."
    try:
        execute("INSERT INTO user_owned_frames (user_id, frame_key) VALUES (?,?)", (user_id, frame_key))
    except Exception as e:
        refund_coins(user_id, frame["price_code"], "frame_purchase_failed")
        import logging
        logging.getLogger("cybershats").error(f"buy_frame xato, CODE qaytarildi: {e}")
        return False, "Texnik xatolik yuz berdi. CODE'ingiz balansingizga qaytarildi, qaytadan urinib ko'ring."
    return True, f"«{frame['label']}» ramkasi sotib olindi!"


def set_active_frame(user_id: int, frame_key: str) -> tuple[bool, str]:
    if frame_key == "":
        execute("UPDATE users SET active_frame=NULL WHERE id=?", (user_id,))
        return True, "Ramka olib tashlandi."
    if not user_owns_frame(user_id, frame_key):
        return False, "Bu ramka sizda yo'q."
    execute("UPDATE users SET active_frame=? WHERE id=?", (frame_key, user_id))
    return True, "Ramka faollashtirildi!"


def get_frame_style(frame_key: str):
    """Shablonlarda avatar atrofiga qo'yish uchun CSS/animatsiya klassini qaytaradi."""
    if not frame_key:
        return None
    return query_one("SELECT css_style, animation_class FROM profile_frames WHERE frame_key=?", (frame_key,))
