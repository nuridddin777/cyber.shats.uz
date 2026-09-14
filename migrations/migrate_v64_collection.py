# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v64: Koleksiya (100+5 haykalcha) tizimi
================================================================================
- 100 oddiy daraja, 5 toifaga bo'lingan (fon rangi bilan aniqlanadi):
    5-toifa (1-20-daraja)   — to'q ko'k fon
    4-toifa (21-40-daraja)  — yashil fon
    3-toifa (41-60-daraja)  — binafsha fon
    2-toifa (61-80-daraja)  — qizil fon
    1-toifa (81-100-daraja) — tilla fon
- 100 tasini yig'ib bo'lgach yana 5 ta BONUS haykalcha (101-104: kamalak
  fon; 105 — YAKUNIY "CYBER SHATS" haykalchasi: fon qora, haykalcha tilla).
- Har bir daraja — mustaqil, boshqa haykalchalarga o'xshamaydigan shakl
  (prosedural, daraja raqami "urug'" sifatida ishlatiladi).
- Tariflar (Pro/Cyber Pro/VIP) bilan HECH QANDAY aloqasi yo'q.
- Profilda ko'rsatish uchun FAQAT 10 tasi tanlanadi (pin).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "user_collection"):
        c.execute("""
            CREATE TABLE user_collection (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                level INTEGER NOT NULL,
                unlocked_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, level)
            )
        """)
        c.execute("CREATE INDEX idx_user_collection_user ON user_collection(user_id)")
        print("  + jadval: user_collection")

    if not _table_exists(c, "user_pinned_statuettes"):
        c.execute("""
            CREATE TABLE user_pinned_statuettes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                level INTEGER NOT NULL,
                pin_order INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, level)
            )
        """)
        print("  + jadval: user_pinned_statuettes")

    conn.commit()
    conn.close()
    print("✅ v64 Koleksiya (100+5 haykalcha) tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
