# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v59: Do'stlik tizimi
================================================================================
Foydalanuvchilar bir-biriga do'stlik so'rovi yuborishi, qabul/rad qilishi,
do'stlar ro'yxatini ko'rishi mumkin.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "friendships"):
        c.execute("""
            CREATE TABLE friendships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_a_id INTEGER NOT NULL REFERENCES users(id),
                user_b_id INTEGER NOT NULL REFERENCES users(id),
                requested_by INTEGER NOT NULL REFERENCES users(id),
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                responded_at TEXT,
                UNIQUE(user_a_id, user_b_id)
            )
        """)
        c.execute("CREATE INDEX idx_friendships_a ON friendships(user_a_id, status)")
        c.execute("CREATE INDEX idx_friendships_b ON friendships(user_b_id, status)")
        print("  + jadval: friendships")

    conn.commit()
    conn.close()
    print("✅ v59 Do'stlik tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
