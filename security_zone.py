"""
CYBER SHATS — MAXSUS versiya: Xavfsizlik Zonasi moduli.

Shaxsiy sayt/tizim yaratish uchun xavfsizlik bo'yicha qo'llanmalar, lug'at,
shaxsiy "xavfsizlik balli" testi, cheklist va qora ro'yxat.
"""
from db import query_one, query_all, execute


def get_articles_by_category():
    rows = query_all("SELECT * FROM security_articles ORDER BY category, order_index, id")
    grouped = {}
    for r in rows:
        grouped.setdefault(r["category"], []).append(r)
    return grouped


def get_article(slug):
    return query_one("SELECT * FROM security_articles WHERE slug=?", (slug,))


def get_glossary():
    return query_all("SELECT * FROM security_glossary ORDER BY order_index, term")


def get_quiz_questions():
    return query_all("SELECT * FROM security_quiz_questions ORDER BY order_index, id")


def _level_for_score(pct: int) -> str:
    if pct >= 90:
        return "Ekspert"
    if pct >= 70:
        return "Ilg'or"
    if pct >= 50:
        return "O'rta"
    return "Boshlang'ich"


def submit_quiz(user_id: int, answers: dict) -> dict:
    """answers: {question_id(str): 'a'/'b'/'c'/'d'}"""
    questions = get_quiz_questions()
    total = len(questions)
    score = 0
    details = []
    for q in questions:
        chosen = answers.get(str(q["id"]))
        correct = (chosen == q["correct"])
        if correct:
            score += 1
        details.append({"question": q, "chosen": chosen, "correct": correct})

    pct = int(round((score / total) * 100)) if total else 0
    level = _level_for_score(pct)

    execute(
        """INSERT INTO user_security_score (user_id, score, total, level, taken_at)
           VALUES (?,?,?,?, datetime('now'))
           ON CONFLICT(user_id) DO UPDATE SET score=excluded.score, total=excluded.total,
                                               level=excluded.level, taken_at=excluded.taken_at""",
        (user_id, score, total, level)
    )
    return {"score": score, "total": total, "pct": pct, "level": level, "details": details}


def get_user_score(user_id: int):
    return query_one("SELECT * FROM user_security_score WHERE user_id=?", (user_id,))


def get_checklist_with_progress(user_id: int):
    items = query_all("SELECT * FROM security_checklist_items ORDER BY category, order_index, id")
    checked_ids = {r["item_id"] for r in query_all(
        "SELECT item_id FROM user_checklist_progress WHERE user_id=?", (user_id,)
    )}
    grouped = {}
    done = 0
    for it in items:
        it = dict(it)
        it["checked"] = it["id"] in checked_ids
        if it["checked"]:
            done += 1
        grouped.setdefault(it["category"], []).append(it)
    return grouped, done, len(items)


def toggle_checklist_item(user_id: int, item_id: int) -> bool:
    existing = query_one("SELECT 1 FROM user_checklist_progress WHERE user_id=? AND item_id=?", (user_id, item_id))
    if existing:
        execute("DELETE FROM user_checklist_progress WHERE user_id=? AND item_id=?", (user_id, item_id))
        return False
    else:
        execute("INSERT INTO user_checklist_progress (user_id, item_id) VALUES (?,?)", (user_id, item_id))
        return True


def get_blacklist_apps():
    return query_all("SELECT * FROM security_blacklist_apps ORDER BY order_index, id")


# ---------------------------------------------------------------------------
# Parol kuchi tekshiruvi (server tomonida, oddiy entropiya baholash)
# ---------------------------------------------------------------------------
import re


def check_password_strength(password: str) -> dict:
    if not password:
        return {"score": 0, "label": "Bo'sh", "color": "#888", "tips": ["Parol kiriting"]}

    length = len(password)
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[^a-zA-Z0-9]", password))
    variety = sum([has_lower, has_upper, has_digit, has_special])

    common_weak = {"123456", "password", "qwerty", "parol123", "12345678", "admin", "111111"}
    is_common = password.lower() in common_weak

    score = 0
    if length >= 8: score += 1
    if length >= 12: score += 1
    if length >= 16: score += 1
    score += variety  # 0-4

    if is_common:
        score = 0

    tips = []
    if length < 12:
        tips.append("Uzunlikni kamida 12 belgigacha oshiring")
    if not has_upper:
        tips.append("Katta harf qo'shing")
    if not has_digit:
        tips.append("Raqam qo'shing")
    if not has_special:
        tips.append("Maxsus belgi qo'shing (!@#$%...)")
    if is_common:
        tips.append("Bu juda keng tarqalgan parol — butunlay boshqasini tanlang")

    if score <= 2:
        label, color = "Zaif", "#ff4444"
    elif score <= 4:
        label, color = "O'rta", "#ffc107"
    elif score <= 6:
        label, color = "Kuchli", "#00c853"
    else:
        label, color = "Juda kuchli", "#38bff8"

    return {"score": score, "max_score": 7, "label": label, "color": color, "tips": tips}
