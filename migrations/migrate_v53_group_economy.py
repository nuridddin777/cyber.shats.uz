"""
SHATS CYBER — MIGRATE v53: Guruh/Kanal iqtisodiyoti (O'qituvchilar uchun)
================================================================================
- groups.public_id / channels.public_id — 8 xonali noyob ID (avtomatik, lekin
  guruh va kanal orasida bir xil bo'lmaydi).
- groups.is_teacher_owned, channels.is_teacher_owned — faqat tasdiqlangan
  o'qituvchilar guruh/kanal ochishi mumkin.
- monthly_tax_code / next_tax_at — oylik soliq va keyingi yechish sanasi.
- group_join_requests — maxfiy guruhga qo'shilish so'rovlari (o'qituvchi
  tasdiqlashi shart).
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

    for table in ("groups", "channels"):
        for col, ddl in [
            ("public_id", f"ALTER TABLE {table} ADD COLUMN public_id TEXT DEFAULT NULL"),
            ("is_teacher_owned", f"ALTER TABLE {table} ADD COLUMN is_teacher_owned INTEGER DEFAULT 0"),
            ("monthly_tax_code", f"ALTER TABLE {table} ADD COLUMN monthly_tax_code INTEGER DEFAULT 0"),
            ("next_tax_at", f"ALTER TABLE {table} ADD COLUMN next_tax_at TEXT DEFAULT NULL"),
        ]:
            if not _column_exists(c, table, col):
                c.execute(ddl)
                print(f"  + {table}.{col}")

    if not _table_exists(c, "group_join_requests"):
        c.execute("""
            CREATE TABLE group_join_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES groups(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(group_id, user_id)
            )
        """)
        print("  + jadval: group_join_requests")

    conn.commit()
    conn.close()
    print("✅ v53 Guruh/Kanal iqtisodiyoti — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
