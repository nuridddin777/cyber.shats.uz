# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v66: ID tarixi (koleksiyasi)
================================================================================
Foydalanuvchi egalik qilgan HAR BIR ID (hozirgi ham, avvalgi ham) shu
jadvalda saqlanadi va profilida ko'rinadi. Bir marta ishlatilgan ID
(hatto endi "eski" bo'lsa ham) — boshqa hech kim tomonidan qayta
Random ID orqali yoki to'g'ridan-to'g'ri olib bo'lmaydi, FAQAT admin
uni ataylab qayta muomalaga (bozorga yoki Random hovuziga) qaytarsagina.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "user_id_history"):
        c.execute("""
            CREATE TABLE user_id_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                custom_id TEXT NOT NULL,
                obtained_via TEXT NOT NULL DEFAULT 'unknown',
                status TEXT NOT NULL DEFAULT 'current',
                released_to_pool INTEGER NOT NULL DEFAULT 0,
                obtained_at TEXT NOT NULL DEFAULT (datetime('now')),
                released_at TEXT
            )
        """)
        c.execute("CREATE INDEX idx_id_history_user ON user_id_history(user_id)")
        c.execute("CREATE INDEX idx_id_history_custom ON user_id_history(custom_id)")
        print("  + jadval: user_id_history")

        # Hozir foydalanuvchilarda mavjud ID'larni tarixga "current" deb yozamiz
        rows = c.execute("SELECT id, custom_id FROM users WHERE custom_id IS NOT NULL").fetchall()
        for uid, cid in rows:
            c.execute(
                "INSERT INTO user_id_history (user_id, custom_id, obtained_via, status) VALUES (?,?,?,'current')",
                (uid, cid, "mavjud")
            )
        print(f"  + {len(rows)} ta joriy ID tarixga yozildi")

    conn.commit()
    conn.close()
    print("✅ v66 ID tarixi (koleksiyasi) — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
