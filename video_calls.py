# ============================================================
# CYBER SHATS — WebRTC video-qo'ng'iroq signalizatsiya moduli
#
# HTTP-polling asosidagi signalizatsiya (WebSocket infratuzilmasi yo'q).
# Haqiqiy video/audio — brauzerlar orasida TO'G'RIDAN-TO'G'RI (P2P) oqadi,
# bu yerda faqat ulanishni o'rnatish uchun kerakli xabarlar (offer/answer/
# ICE candidate) saqlanadi va so'raladi.
#
# Kichik guruhlar uchun MESH topologiya ishlatiladi (har bir a'zo
# boshqa har bir a'zo bilan to'g'ridan-to'g'ri ulanadi) — 6-8 kishigacha
# yaxshi ishlaydi, undan ko'p bo'lsa sifat pasayishi mumkin (SFU server
# kerak bo'lardi, bu keyingi versiya uchun).
# ============================================================
import secrets

from db import query_one, query_all, execute


def get_active_call(group_id=None, channel_id=None):
    if group_id:
        return query_one("SELECT * FROM video_calls WHERE group_id=? AND is_active=1", (group_id,))
    if channel_id:
        return query_one("SELECT * FROM video_calls WHERE channel_id=? AND is_active=1", (channel_id,))
    return None


def start_call(user_id: int, group_id=None, channel_id=None) -> tuple[bool, str, str]:
    """Yangi qo'ng'iroq boshlaydi (agar allaqachon faol bo'lsa — o'shanga qo'shiladi).
    Qaytaradi: (ok, xabar, room_code)"""
    existing = get_active_call(group_id, channel_id)
    if existing:
        join_call(existing["id"], user_id)
        return True, "Mavjud qo'ng'irog'ga qo'shildingiz.", existing["room_code"]

    room_code = secrets.token_urlsafe(12)
    call_id = execute(
        "INSERT INTO video_calls (room_code, group_id, channel_id, started_by) VALUES (?,?,?,?)",
        (room_code, group_id, channel_id, user_id)
    )
    join_call(call_id, user_id)
    return True, "Qo'ng'iroq boshlandi.", room_code


def join_call(call_id: int, user_id: int):
    execute(
        "INSERT INTO video_call_participants (call_id, user_id) VALUES (?,?) "
        "ON CONFLICT(call_id, user_id) DO UPDATE SET left_at=NULL, joined_at=datetime('now')",
        (call_id, user_id)
    )


def leave_call(call_id: int, user_id: int):
    execute("UPDATE video_call_participants SET left_at=datetime('now') WHERE call_id=? AND user_id=?",
            (call_id, user_id))
    remaining = query_one(
        "SELECT COUNT(*) c FROM video_call_participants WHERE call_id=? AND left_at IS NULL", (call_id,))["c"]
    if remaining == 0:
        execute("UPDATE video_calls SET is_active=0, ended_at=datetime('now') WHERE id=?", (call_id,))


def end_call_for_all(call_id: int, requester_id: int) -> tuple[bool, str]:
    call = query_one("SELECT * FROM video_calls WHERE id=?", (call_id,))
    if not call:
        return False, "Qo'ng'iroq topilmadi."
    if call["started_by"] != requester_id:
        return False, "Faqat qo'ng'iroqni boshlagan kishi uni hamma uchun tugata oladi."
    execute("UPDATE video_calls SET is_active=0, ended_at=datetime('now') WHERE id=?", (call_id,))
    execute("UPDATE video_call_participants SET left_at=datetime('now') WHERE call_id=? AND left_at IS NULL",
            (call_id,))
    return True, "Qo'ng'iroq tugatildi."


def get_call_by_room(room_code: str):
    return query_one("SELECT * FROM video_calls WHERE room_code=?", (room_code,))


def get_active_participants(call_id: int):
    return query_all(
        """SELECT vcp.user_id, u.ism, u.familiya, u.avatar_path FROM video_call_participants vcp
           JOIN users u ON u.id=vcp.user_id WHERE vcp.call_id=? AND vcp.left_at IS NULL
           ORDER BY vcp.joined_at ASC""", (call_id,))


def send_signal(call_id: int, from_user_id: int, to_user_id: int, signal_type: str, payload: str):
    execute(
        "INSERT INTO video_call_signals (call_id, from_user_id, to_user_id, signal_type, payload) VALUES (?,?,?,?,?)",
        (call_id, from_user_id, to_user_id, signal_type, payload)
    )


def get_signals_for(call_id: int, to_user_id: int, after_id: int = 0):
    return query_all(
        "SELECT * FROM video_call_signals WHERE call_id=? AND to_user_id=? AND id > ? ORDER BY id ASC",
        (call_id, to_user_id, after_id)
    )
