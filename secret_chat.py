"""
CYBER SHATS — MAXSUS: Maxfiy Chat (o'z-o'zini yo'q qiluvchi xabarlar).
"""
from datetime import datetime, timedelta
from db import query_one, query_all, execute


def get_or_create_chat(user_a: int, user_b: int) -> dict:
    a, b = sorted([user_a, user_b])
    row = query_one("SELECT * FROM secret_chats WHERE user_a_id=? AND user_b_id=?", (a, b))
    if row:
        return row
    execute("INSERT INTO secret_chats (user_a_id, user_b_id) VALUES (?,?)", (a, b))
    return query_one("SELECT * FROM secret_chats WHERE user_a_id=? AND user_b_id=?", (a, b))


def get_user_chats(user_id: int):
    return query_all(
        """SELECT sc.*, u.ism, u.familiya, u.custom_id,
                  (CASE WHEN sc.user_a_id=? THEN sc.user_b_id ELSE sc.user_a_id END) as peer_id
           FROM secret_chats sc
           JOIN users u ON u.id = (CASE WHEN sc.user_a_id=? THEN sc.user_b_id ELSE sc.user_a_id END)
           WHERE sc.user_a_id=? OR sc.user_b_id=?
           ORDER BY sc.created_at DESC""",
        (user_id, user_id, user_id, user_id)
    )


def send_message(chat_id: int, sender_id: int, content: str, ttl_seconds: int = 60):
    execute(
        "INSERT INTO secret_messages (chat_id, sender_id, content, ttl_seconds) VALUES (?,?,?,?)",
        (chat_id, sender_id, content, ttl_seconds)
    )


def get_messages(chat_id: int, viewer_id: int):
    """Xabarlarni qaytaradi va o'qilgan + muddati o'tganlarni o'chiradi (self-destruct)."""
    _purge_expired(chat_id)
    rows = query_all("SELECT * FROM secret_messages WHERE chat_id=? ORDER BY created_at", (chat_id,))
    now = datetime.now()
    result = []
    for r in rows:
        r = dict(r)
        # O'quvchi (qabul qiluvchi) ko'rgan zahoti "o'qilgan" deb belgilanadi va TTL boshlanadi
        if r["sender_id"] != viewer_id and not r["read_at"]:
            execute("UPDATE secret_messages SET read_at=datetime('now') WHERE id=?", (r["id"],))
            r["read_at"] = now.strftime("%Y-%m-%d %H:%M:%S")
        result.append(r)
    return result


def _purge_expired(chat_id: int):
    rows = query_all("SELECT * FROM secret_messages WHERE chat_id=? AND read_at IS NOT NULL", (chat_id,))
    now = datetime.now()
    for r in rows:
        try:
            read_at = datetime.strptime(r["read_at"], "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            continue
        if now > read_at + timedelta(seconds=r["ttl_seconds"]):
            execute("DELETE FROM secret_messages WHERE id=?", (r["id"],))
