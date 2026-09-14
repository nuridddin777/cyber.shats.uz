# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v62: Foydalanuvchi o'z IDsini sotishi
================================================================================
Foydalanuvchi o'z joriy ID'siga narx qo'yib sotuvga chiqaradi. FAQAT Super
Admin va G'azna bu takliflarni ko'rib, kerak bo'lsa arzonroq narx taklif
qilib (savdolashib), keyin sotib olishi mumkin. Sotib olingach — pul
foydalanuvchiga o'tadi, uning ID'si yangi tasodifiy IDga almashtiriladi,
sotib olingan ID esa premium IDlar bozoriga (qayta sotish uchun) qo'shiladi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "id_sell_offers"):
        c.execute("""
            CREATE TABLE id_sell_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                custom_id TEXT NOT NULL,
                asking_price INTEGER NOT NULL,
                counter_price INTEGER,
                status TEXT NOT NULL DEFAULT 'pending',
                handled_by INTEGER REFERENCES users(id),
                admin_note TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT
            )
        """)
        c.execute("CREATE INDEX idx_id_sell_offers_status ON id_sell_offers(status)")
        print("  + jadval: id_sell_offers")

    conn.commit()
    conn.close()
    print("✅ v62 Foydalanuvchi ID sotish tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
