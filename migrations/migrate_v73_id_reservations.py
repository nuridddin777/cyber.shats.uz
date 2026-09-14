# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v73: ID band qilish (rezervatsiya) tizimi
================================================================================
Random ID aylantirilganda yoqqan ID chiqsa, lekin CODE yetarli bo'lmasa —
foydalanuvchi uni 2 kunga (48 soat) BEPUL band qilib qo'yishi mumkin.
Shu muddat davomida boshqa HECH KIM bu IDni Random orqali ololmaydi.
Muddat tugasa (sotib olinmasa) — avtomatik bo'shatiladi.
Har foydalanuvchida BIR VAQTDA faqat 1 ta faol band bo'lishi mumkin
(suiiste'mol qilinmasligi uchun).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "id_reservations"):
        c.execute("""
            CREATE TABLE id_reservations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                custom_id TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                reserved_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX idx_id_reservations_user ON id_reservations(user_id, status)")
        c.execute("CREATE INDEX idx_id_reservations_custom ON id_reservations(custom_id, status)")
        print("  + jadval: id_reservations")

    conn.commit()
    conn.close()
    print("✅ v73 ID band qilish (rezervatsiya) tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
