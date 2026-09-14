# ============================================================
# CYBER SHATS — Do'stlik tizimi
# ============================================================
from db import query_one, query_all, execute


def _pair(a, b):
    """user_a_id har doim kichikroq ID bo'lishi kerak — UNIQUE(user_a_id,
    user_b_id) ikki yo'nalishda ham (A->B va B->A) bir xil qatorga tushishi
    uchun."""
    return (a, b) if a < b else (b, a)


def get_friendship_status(user_id: int, other_id: int):
    """Qaytaradi: None (do'st emas), 'pending_sent', 'pending_received', 'friends'"""
    if user_id == other_id:
        return None
    a, b = _pair(user_id, other_id)
    row = query_one("SELECT * FROM friendships WHERE user_a_id=? AND user_b_id=?", (a, b))
    if not row:
        return None
    if row["status"] == "accepted":
        return "friends"
    if row["status"] == "pending":
        return "pending_sent" if row["requested_by"] == user_id else "pending_received"
    return None


def send_friend_request(user_id: int, target_id: int) -> tuple[bool, str]:
    if user_id == target_id:
        return False, "O'zingizga do'stlik so'rovi yubora olmaysiz."
    target = query_one("SELECT id FROM users WHERE id=?", (target_id,))
    if not target:
        return False, "Foydalanuvchi topilmadi."
    a, b = _pair(user_id, target_id)
    existing = query_one("SELECT * FROM friendships WHERE user_a_id=? AND user_b_id=?", (a, b))
    if existing:
        if existing["status"] == "accepted":
            return False, "Siz allaqachon do'stsiz."
        if existing["status"] == "pending":
            return False, "So'rov allaqachon yuborilgan."
        if existing["status"] == "rejected":
            execute("UPDATE friendships SET status='pending', requested_by=?, created_at=datetime('now'), "
                    "responded_at=NULL WHERE user_a_id=? AND user_b_id=?", (user_id, a, b))
            return True, "Do'stlik so'rovi qayta yuborildi."
    execute("INSERT INTO friendships (user_a_id, user_b_id, requested_by, status) VALUES (?,?,?,'pending')",
            (a, b, user_id))
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (target_id, "Yangi do'stlik so'rovi 👋", "Kimdir sizga do'stlik so'rovi yubordi.", "info"))
    return True, "Do'stlik so'rovi yuborildi."


def respond_friend_request(user_id: int, requester_id: int, accept: bool) -> tuple[bool, str]:
    a, b = _pair(user_id, requester_id)
    row = query_one("SELECT * FROM friendships WHERE user_a_id=? AND user_b_id=? AND status='pending'", (a, b))
    if not row:
        return False, "So'rov topilmadi."
    if row["requested_by"] == user_id:
        return False, "O'zingiz yuborgan so'rovga javob berolmaysiz."
    new_status = "accepted" if accept else "rejected"
    execute("UPDATE friendships SET status=?, responded_at=datetime('now') WHERE id=?", (new_status, row["id"]))
    if accept:
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (requester_id, "Do'stlik so'rovi qabul qilindi! 🎉", "Siz endi do'stsiz.", "success"))
    return True, "Do'st sifatida qo'shildi!" if accept else "So'rov rad etildi."


def remove_friend(user_id: int, other_id: int) -> tuple[bool, str]:
    a, b = _pair(user_id, other_id)
    execute("DELETE FROM friendships WHERE user_a_id=? AND user_b_id=? AND status='accepted'", (a, b))
    return True, "Do'stlikdan chiqarildi."


def get_friends_list(user_id: int):
    return query_all("""
        SELECT u.id, u.ism, u.familiya, u.custom_id, u.avatar_path, u.level, u.last_login_date, f.responded_at
        FROM friendships f
        JOIN users u ON u.id = (CASE WHEN f.user_a_id=? THEN f.user_b_id ELSE f.user_a_id END)
        WHERE (f.user_a_id=? OR f.user_b_id=?) AND f.status='accepted'
        ORDER BY (u.last_login_date = date('now')) DESC, f.responded_at DESC
    """, (user_id, user_id, user_id))


def get_pending_received(user_id: int):
    return query_all("""
        SELECT u.id, u.ism, u.familiya, u.custom_id, u.avatar_path, f.created_at
        FROM friendships f
        JOIN users u ON u.id = f.requested_by
        WHERE (f.user_a_id=? OR f.user_b_id=?) AND f.status='pending' AND f.requested_by != ?
        ORDER BY f.created_at DESC
    """, (user_id, user_id, user_id))


def get_pending_sent(user_id: int):
    return query_all("""
        SELECT u.id, u.ism, u.familiya, u.custom_id, u.avatar_path, f.created_at
        FROM friendships f
        JOIN users u ON u.id = (CASE WHEN f.user_a_id=? THEN f.user_b_id ELSE f.user_a_id END)
        WHERE (f.user_a_id=? OR f.user_b_id=?) AND f.status='pending' AND f.requested_by = ?
        ORDER BY f.created_at DESC
    """, (user_id, user_id, user_id, user_id))


def get_pending_received_count(user_id: int) -> int:
    row = query_one("""
        SELECT COUNT(*) c FROM friendships
        WHERE (user_a_id=? OR user_b_id=?) AND status='pending' AND requested_by != ?
    """, (user_id, user_id, user_id))
    return row["c"] if row else 0


# =================================================================
# FAOLIYAT LENTASI — do'stlik endi faqat so'rov yuborish emas
# =================================================================
def log_activity(user_id: int, activity_type: str, detail: str = ""):
    """Har qanday muhim voqeani ('level_up', 'course_done', 'new_statuette'
    va h.k.) foydalanuvchi tarixiga yozadi — do'stlar buni lentada ko'radi."""
    execute("INSERT INTO activity_feed (user_id, activity_type, detail) VALUES (?,?,?)",
            (user_id, activity_type, detail))


ACTIVITY_LABELS = {
    "level_up": ("⬆️", "{name} {level}-darajaga chiqdi!"),
    "course_done": ("🎓", "{name} \"{detail}\" kursini tugatdi!"),
    "new_statuette": ("🏆", "{name} yangi haykalcha topdi: {detail}-daraja!"),
    "new_badge": ("🎖️", "{name} \"{detail}\" nishonini oldi!"),
    "plan_upgrade": ("👑", "{name} {detail} tarifiga o'tdi!"),
}


def get_friends_activity_feed(user_id: int, limit: int = 30):
    """Foydalanuvchining BARCHA do'stlarining so'nggi faoliyatini bitta
    umumiy lentada, xronologik tartibda qaytaradi."""
    rows = query_all("""
        SELECT af.activity_type, af.detail, af.created_at, u.id as friend_id,
               u.ism, u.familiya, u.custom_id, u.avatar_path
        FROM activity_feed af
        JOIN users u ON u.id = af.user_id
        JOIN friendships f ON (
            (f.user_a_id = af.user_id AND f.user_b_id = ?) OR
            (f.user_b_id = af.user_id AND f.user_a_id = ?)
        )
        WHERE f.status = 'accepted'
        ORDER BY af.created_at DESC LIMIT ?
    """, (user_id, user_id, limit))
    result = []
    for r in rows:
        icon, template = ACTIVITY_LABELS.get(r["activity_type"], ("📌", "{name} yangilik qildi."))
        name = f"{r['familiya']} {r['ism']}"
        text = template.format(name=name, level=r["detail"], detail=r["detail"])
        result.append({**dict(r), "icon": icon, "text": text})
    return result


def get_friends_leaderboard(user_id: int):
    """Faqat DO'STLAR orasidagi reyting (butun sayt emas) — kichikroq,
    tanish doiradagi raqobat hissi uchun."""
    return query_all("""
        SELECT u.id, u.ism, u.familiya, u.custom_id, u.avatar_path, u.level, u.xp, u.code_balance
        FROM users u
        JOIN friendships f ON (
            (f.user_a_id = u.id AND f.user_b_id = ?) OR
            (f.user_b_id = u.id AND f.user_a_id = ?)
        )
        WHERE f.status = 'accepted'
        UNION
        SELECT id, ism, familiya, custom_id, avatar_path, level, xp, code_balance
        FROM users WHERE id = ?
        ORDER BY xp DESC
    """, (user_id, user_id, user_id))


def get_mutual_friends(user_id: int, other_id: int):
    """Ikki foydalanuvchining UMUMIY do'stlari ro'yxatini qaytaradi."""
    return query_all("""
        SELECT u.id, u.ism, u.familiya, u.custom_id, u.avatar_path
        FROM users u
        WHERE u.id IN (
            SELECT CASE WHEN f.user_a_id=? THEN f.user_b_id ELSE f.user_a_id END
            FROM friendships f WHERE (f.user_a_id=? OR f.user_b_id=?) AND f.status='accepted'
        ) AND u.id IN (
            SELECT CASE WHEN f2.user_a_id=? THEN f2.user_b_id ELSE f2.user_a_id END
            FROM friendships f2 WHERE (f2.user_a_id=? OR f2.user_b_id=?) AND f2.status='accepted'
        )
    """, (user_id, user_id, user_id, other_id, other_id, other_id))


def get_comparison_stats(user_id: int, other_id: int):
    """Ikki foydalanuvchining XP/CODE/Koleksiya/Daraja statistikasini
    yonma-yon solishtirish uchun."""
    def _stats(uid):
        u = query_one("SELECT ism, familiya, custom_id, avatar_path, level, xp, code_balance FROM users WHERE id=?", (uid,))
        collection_count = query_one("SELECT COUNT(*) c FROM user_collection WHERE user_id=?", (uid,))["c"]
        courses_done = query_one(
            "SELECT COUNT(*) c FROM enrollments WHERE user_id=? AND progress_percent=100", (uid,))["c"]
        return {**dict(u), "collection_count": collection_count, "courses_done": courses_done}
    return _stats(user_id), _stats(other_id)
