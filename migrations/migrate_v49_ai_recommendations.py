"""
SHATS CYBER — MIGRATE v49: AI shaxsiylashtirilgan tavsiyalar
================================================================================
Har bir o'quvchi uchun AI (Gemini) — uning progress, test natijalari va
kuchsiz tomonlariga qarab — shaxsiy tavsiyalar (nimani takrorlash kerak,
qaysi kursni davom ettirish kerak, keyingi qadam) generatsiya qiladi.

Har safar AI'ga so'rov yubormaslik uchun (xarajat + tezlik), natija
`user_ai_recommendations` jadvalida keshlanadi — 24 soatdan keyin "eskirgan"
hisoblanadi va foydalanuvchi "Yangilash" tugmasi orqali qayta so'rashi mumkin.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "user_ai_recommendations"):
        c.execute("""
            CREATE TABLE user_ai_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
                recommendations_json TEXT NOT NULL,
                generated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + jadval: user_ai_recommendations")

    conn.commit()
    conn.close()
    print("✅ v49 AI shaxsiylashtirilgan tavsiyalar — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
