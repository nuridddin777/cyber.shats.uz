# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v69: Do'stlar faoliyat lentasi (Activity Feed)
================================================================================
Do'stlik funksiyasi endi faqat so'rov yuborish bilan cheklanmaydi —
do'stlaringizning so'nggi yutuqlari (daraja oshishi, kurs tugatishi,
yangi haykalcha topishi) bitta umumiy lentada ko'rinadi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "activity_feed"):
        c.execute("""
            CREATE TABLE activity_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                activity_type TEXT NOT NULL,
                detail TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        c.execute("CREATE INDEX idx_activity_feed_user ON activity_feed(user_id, created_at)")
        print("  + jadval: activity_feed")

    conn.commit()
    conn.close()
    print("✅ v69 Do'stlar faoliyat lentasi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
