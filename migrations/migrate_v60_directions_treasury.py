# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v60: Yo'nalishlar is_active + G'azna reset infratuzilmasi
================================================================================
1) directions.is_active — endi Ingliz tili va Matematika yo'nalishlarining
   O'ZI (faqat kurslari emas) ham BARCHA navigatsiyadan (marquee, orbital
   hub, yo'nalish tanlash, sidebar) yashiriladi.
2) treasury_reset_log — g'aznani "0 dan boshlash" amali qachon va kim
   tomonidan bajarilganini yozib boradi (tarixiy nazorat uchun).
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

    if not _column_exists(c, "directions", "is_active"):
        c.execute("ALTER TABLE directions ADD COLUMN is_active INTEGER DEFAULT 1")
        print("  + directions.is_active")

    closed = c.execute(
        "UPDATE directions SET is_active=0 WHERE slug IN ('ingliz-tili','matematika') AND is_active=1"
    ).rowcount
    if closed:
        print(f"  - {closed} ta yo'nalish butunlay yashirildi (Ingliz tili, Matematika)")

    if not _table_exists(c, "treasury_reset_log"):
        c.execute("""
            CREATE TABLE treasury_reset_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL REFERENCES users(id),
                old_treasury_balance INTEGER,
                affected_users INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + jadval: treasury_reset_log")

    conn.commit()
    conn.close()
    print("✅ v60 Yo'nalishlar is_active + G'azna reset infratuzilmasi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
