"""
SHATS CYBER — MIGRATE v34: Maxsus topshiriq (KRIPTIKIS, 3 bosqichli)
================================================================================
Foydalanuvchilar bosh sahifasida (/dashboard) ko'rinadigan 3 bosqichli
kriptografik topshiriq:

  1-bosqich: KRIPTIKIS joylashtirilgan, lekin TO'G'RI JAVOBI YO'Q — faqat
             2 CODE evaziga "ochiladi" (o'tkaziladi) va 2-bosqichga o'tadi.
  2-bosqich: KRIPTIKIS, javobi 18 xonali raqam (336369655976699655).
             XOR shifri bilan shifrlangan, kalit — sayt nomidan.
  3-bosqich: eng qiyin — ko'p qavatli shifr (reverse + Base64 + XOR),
             faqat chinakam ko'nikmaga ega odam yecha oladi.

Javoblar ochiq matnda emas, SHA-256 hash sifatida saqlanadi — hatto ma'lumotlar
bazasiga to'g'ridan-to'g'ri kirgan odam ham javobni ko'ra olmaydi.
"""
import sqlite3
import os
import hashlib

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _h(answer: str) -> str:
    return hashlib.sha256(answer.strip().upper().encode()).hexdigest()


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS special_challenges (
        level INTEGER PRIMARY KEY,           -- 1, 2, 3
        title TEXT NOT NULL,
        clue_text TEXT NOT NULL,             -- foydalanuvchiga ko'rsatiladigan shifrli matn/topshiriq
        hint_text TEXT DEFAULT '',
        unlock_cost_code INTEGER DEFAULT 0,   -- faqat 1-bosqich uchun ishlatiladi (javobsiz, pul evaziga o'tiladi)
        answer_hash TEXT,                     -- SHA-256(javob) — 1-bosqichda NULL (javob yo'q)
        reward_code INTEGER DEFAULT 0,        -- bosqich yechilgach beriladigan mukofot (0 = yo'q)
        is_active INTEGER NOT NULL DEFAULT 1
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_special_challenge_progress (
        user_id INTEGER PRIMARY KEY,
        current_level INTEGER NOT NULL DEFAULT 1,   -- foydalanuvchi hozir turgan bosqich
        level1_unlocked_at TEXT,
        level2_solved_at TEXT,
        level3_solved_at TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS special_challenge_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        level INTEGER NOT NULL,
        is_correct INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    seed = [
        (
            1, "KRIPTIKIS — I bosqich",
            "01001011 01010010 01001001 01010000 01010100 01001001 01001011 01001001 01010011\n"
            "( Bu shifr ataylab TO'LIQ hal qilinmaydigan darajada murakkablashtirilgan — vaqtingizni "
            "behuda sarflamang. Bu bosqich CODE evaziga o'tiladi, javob orqali emas. )",
            "Bu bosqichda javob YO'Q — pastdagi tugma orqali CODE to'lab, 2-bosqichga o'ting.",
            2, None, 0, 1
        ),
        (
            2, "KRIPTIKIS — II bosqich",
            "Shifrlangan javob (HEX, XOR shifri): 607b7767657a6f77706b647e776d6a756c77",
            "Kalit 10 harfdan iborat: platformamiz nomining ikki so'zi, katta harflar bilan, bo'shliqsiz "
            "(masalan: BIRINCHISOZ + IKKINCHISOZ). Javob — 18 xonali raqam.",
            0, _h("336369655976699655"), 5, 1
        ),
        (
            3, "KRIPTIKIS — III bosqich (Eng qiyin)",
            "Yakuniy shifr: =I2c4FmFAgABWEQEDEBE",
            "3 qatlam: (1) satrni teskari o'qing, (2) Base64'dan dekodlang, (3) natijani "
            "5 harfli kalit bilan XOR qiling — kalit shu saytning birinchi so'zi, katta harflar bilan. "
            "Javob — bitta so'z + yil (masalan: SOZYIL2026 uslubida, bo'shliqsiz, katta harflar bilan).",
            0, _h("CYBERELITE2026"), 20, 1
        ),
    ]
    for row in seed:
        c.execute("""INSERT OR IGNORE INTO special_challenges
            (level, title, clue_text, hint_text, unlock_cost_code, answer_hash, reward_code, is_active)
            VALUES (?,?,?,?,?,?,?,?)""", row)

    conn.commit()
    conn.close()
    print("✅ v34 Maxsus topshiriq (KRIPTIKIS, 3 bosqich) muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
