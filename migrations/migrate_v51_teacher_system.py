"""
SHATS CYBER — MIGRATE v51: AI limit oshirish, O'qituvchi arizasi tizimi, Profil rasmi
================================================================================
- ai_daily_usage.boost_multiplier — kunlik AI limitini vaqtincha oshirish uchun.
- teacher_applications — profildan yuborilgan "o'qituvchilikka ariza" (Familiya,
  Ism, telefon, yo'nalish, sertifikatlar, kurs narxi va h.k.) — super_admin
  tasdiqlaguncha "pending" holatda turadi.
- users.avatar_path — profil rasmi (endi haqiqiy fayl yuklash imkoniyati bilan).
- users.is_teacher — tasdiqlangan o'qituvchi (alohida panel ochiladi).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _column_exists(c, "ai_daily_usage", "boost_multiplier"):
        c.execute("ALTER TABLE ai_daily_usage ADD COLUMN boost_multiplier INTEGER DEFAULT 1")
        print("  + ai_daily_usage.boost_multiplier")

    if not _column_exists(c, "users", "avatar_path"):
        c.execute("ALTER TABLE users ADD COLUMN avatar_path TEXT DEFAULT NULL")
        print("  + users.avatar_path")

    if not _column_exists(c, "users", "is_teacher"):
        c.execute("ALTER TABLE users ADD COLUMN is_teacher INTEGER DEFAULT 0")
        print("  + users.is_teacher")

    if not _table_exists(c, "teacher_applications"):
        c.execute("""
            CREATE TABLE teacher_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                ism TEXT NOT NULL,
                familiya TEXT NOT NULL,
                phone TEXT NOT NULL,
                direction_id INTEGER REFERENCES directions(id),
                direction_custom TEXT,
                syllabus_text TEXT,
                workplace TEXT,
                course_price_uzs INTEGER NOT NULL DEFAULT 0,
                certificates_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                reviewed_by INTEGER REFERENCES users(id),
                reviewed_at TEXT,
                review_note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + jadval: teacher_applications")

    conn.commit()
    conn.close()
    print("✅ v51 AI limit oshirish + O'qituvchi arizasi + Profil rasmi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
