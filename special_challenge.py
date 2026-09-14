# ============================================================
# MAXSUS TOPSHIRIQ (KRIPTIKIS) — 50 bosqichli kriptografik topshiriq
# ============================================================
# 1-bosqich: javobsiz, CODE evaziga o'tiladi.
# 2 — 49-bosqichlar: har biri raqamli/harfli javobli shifr, YECHILSA HAM
#     mukofot BERILMAYDI (faqat keyingi bosqichga o'tkazadi).
# 50-bosqich: YAKUNIY — yechilsa 10 CODE mukofot beriladi.
#
# XAVFSIZLIK: javoblar hech qachon ochiq matnda saqlanmaydi/qaytarilmaydi —
# faqat SHA-256 hash bilan solishtiriladi. Urinishlar soni cheklangan
# (brute-force himoyasi) — ketma-ket noto'g'ri urinishlardan keyin vaqtinchalik
# bloklanadi.

import hashlib
from datetime import datetime, timedelta

from db import query_one, query_all, execute
from coins import get_balance, spend_coins, add_coins, _treasury_fund_in

MAX_ATTEMPTS_PER_WINDOW = 5
ATTEMPT_WINDOW_MINUTES = 10
MAX_LEVEL = 50  # Yakuniy bosqich — shu yerda mukofot (10 CODE) beriladi


class ChallengeError(Exception):
    pass


def _hash(answer: str) -> str:
    return hashlib.sha256(answer.strip().upper().encode()).hexdigest()


def get_challenge(level: int):
    return query_one("SELECT * FROM special_challenges WHERE level=? AND is_active=1", (level,))


def get_all_challenges():
    return query_all("SELECT * FROM special_challenges WHERE is_active=1 ORDER BY level")


def get_progress(user_id: int):
    row = query_one("SELECT * FROM user_special_challenge_progress WHERE user_id=?", (user_id,))
    if not row:
        execute("INSERT INTO user_special_challenge_progress (user_id, current_level) VALUES (?, 1)", (user_id,))
        row = query_one("SELECT * FROM user_special_challenge_progress WHERE user_id=?", (user_id,))
    return row


def _recent_attempt_count(user_id: int, level: int) -> int:
    row = query_one(
        "SELECT COUNT(*) c FROM special_challenge_attempts "
        "WHERE user_id=? AND level=? AND is_correct=0 AND created_at > datetime('now', ?)",
        (user_id, level, f"-{ATTEMPT_WINDOW_MINUTES} minutes")
    )
    return row["c"] if row else 0


def _record_attempt(user_id: int, level: int, is_correct: bool):
    execute(
        "INSERT INTO special_challenge_attempts (user_id, level, is_correct) VALUES (?,?,?)",
        (user_id, level, 1 if is_correct else 0)
    )


def check_attempt_limit(user_id: int, level: int):
    """Urinishlar soni chegaradan oshgan bo'lsa ChallengeError ko'taradi."""
    count = _recent_attempt_count(user_id, level)
    if count >= MAX_ATTEMPTS_PER_WINDOW:
        raise ChallengeError(
            f"Juda ko'p noto'g'ri urinish. {ATTEMPT_WINDOW_MINUTES} daqiqadan so'ng qayta urinib ko'ring."
        )


def unlock_level1(user_id: int):
    """1-bosqichni CODE evaziga 'ochadi' — javob talab qilinmaydi, to'lov o'zi
    2-bosqichga o'tkazadi."""
    progress = get_progress(user_id)
    if progress["current_level"] > 1:
        raise ChallengeError("1-bosqich allaqachon o'tilgan.")

    challenge = get_challenge(1)
    if not challenge:
        raise ChallengeError("Topshiriq topilmadi.")

    cost = challenge["unlock_cost_code"] or 0
    ok, msg = spend_coins(user_id, cost, "special_challenge_level1_unlock")
    if not ok:
        raise ChallengeError(msg)
    _treasury_fund_in(cost, "special_challenge_level1_unlock", user_id)

    execute(
        "UPDATE user_special_challenge_progress SET current_level=2, "
        "level1_unlocked_at=datetime('now'), updated_at=datetime('now') WHERE user_id=?",
        (user_id,)
    )
    return {"cost": cost}


def submit_answer(user_id: int, level: int, answer: str):
    """2- yoki 3-bosqich uchun javobni tekshiradi. To'g'ri bo'lsa keyingi
    bosqichga o'tkazadi (yoki 3-bosqich bo'lsa — topshiriqni yakunlaydi) va
    mukofot (reward_code) beradi."""
    progress = get_progress(user_id)
    if progress["current_level"] != level:
        raise ChallengeError("Bu bosqich hozircha sizga tegishli emas.")

    check_attempt_limit(user_id, level)

    challenge = get_challenge(level)
    if not challenge or not challenge["answer_hash"]:
        raise ChallengeError("Bu bosqichda javob tekshiruvi mavjud emas.")

    if not answer or not answer.strip():
        raise ChallengeError("Javobni kiriting.")

    is_correct = _hash(answer) == challenge["answer_hash"]
    _record_attempt(user_id, level, is_correct)

    if not is_correct:
        remaining = MAX_ATTEMPTS_PER_WINDOW - _recent_attempt_count(user_id, level)
        raise ChallengeError(f"Noto'g'ri javob. Qolgan urinishlar: {max(remaining, 0)}")

    # Faqat YAKUNIY (MAX_LEVEL) bosqichda mukofot beriladi — qolgan barcha
    # bosqichlarni yechish faqat keyingi bosqichga o'tkazadi, CODE bermaydi.
    reward = (challenge["reward_code"] or 0) if level == MAX_LEVEL else 0
    next_level = level + 1
    is_final = level == MAX_LEVEL

    # v34'dan qolgan legacy ustunlar (level2_solved_at/level3_solved_at) —
    # faqat 2- va 3-bosqichlar uchun tarixiy moslik saqlanadi, umumiy holat
    # current_level va updated_at orqali kuzatiladi (50 bosqich uchun umumiy).
    if level == 2:
        execute(
            "UPDATE user_special_challenge_progress SET current_level=?, "
            "level2_solved_at=datetime('now'), updated_at=datetime('now') WHERE user_id=?",
            (next_level, user_id)
        )
    elif level == 3:
        execute(
            "UPDATE user_special_challenge_progress SET current_level=?, "
            "level3_solved_at=datetime('now'), updated_at=datetime('now') WHERE user_id=?",
            (next_level, user_id)
        )
    else:
        execute(
            "UPDATE user_special_challenge_progress SET current_level=?, updated_at=datetime('now') "
            "WHERE user_id=?",
            (next_level, user_id)
        )

    if reward > 0:
        add_coins(user_id, reward, f"special_challenge_level{level}_reward")

    return {"reward": reward, "next_level": next_level, "completed": is_final}
