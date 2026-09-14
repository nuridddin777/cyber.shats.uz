"""
SHATS CYBER — MIGRATE v50: Yangi AI iqtisodiyoti
================================================================================
Eski model: FREE foydalanuvchilar uchun haftalik 1 CODE obuna (istalgancha xabar).
YANGI model (talab bo'yicha):
  - "Kod yozish" AI yordami (mashq izohi + tekshirish) — HAR BIR so'rov uchun
    2 CODE (obuna emas, to'g'ridan-to'g'ri to'lov).
  - Oddiy savol-javob (umumiy AI yordamchi, tavsiyalar) — FREE foydalanuvchilar
    uchun kuniga 3 marta BEPUL, undan keyin kutish kerak.
  - Pro/Cyber Pro/VIP/MAXSUS — ikkalasi ham cheksiz (o'zgarishsiz).
  - Admin/Super Admin/Mentor — ikkalasi ham cheksiz va BEPUL.

`ai_daily_usage` — har bir foydalanuvchining "oddiy savol-javob" turidagi
kunlik so'rovlar sonini saqlaydi (kun bo'yicha reset bo'ladi).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "ai_daily_usage"):
        c.execute("""
            CREATE TABLE ai_daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                usage_date TEXT NOT NULL,
                count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, usage_date)
            )
        """)
        print("  + jadval: ai_daily_usage")

    conn.commit()
    conn.close()
    print("✅ v50 Yangi AI iqtisodiyoti — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
