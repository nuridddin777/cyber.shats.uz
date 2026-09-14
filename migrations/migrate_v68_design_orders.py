# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v68: Dizayn zakaz berish (G'aznaga)
================================================================================
Foydalanuvchi qanday dizayin xohlayotganini yozib, arizani G'aznaga
yuboradi. G'azna ko'rib chiqib, narx (CODE) belgilaydi va tasdiqlaydi
yoki rad etadi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "design_orders"):
        c.execute("""
            CREATE TABLE design_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                quoted_price INTEGER,
                admin_note TEXT,
                handled_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT
            )
        """)
        c.execute("CREATE INDEX idx_design_orders_user ON design_orders(user_id)")
        c.execute("CREATE INDEX idx_design_orders_status ON design_orders(status)")
        print("  + jadval: design_orders")

    conn.commit()
    conn.close()
    print("✅ v68 Dizayn zakaz berish tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
