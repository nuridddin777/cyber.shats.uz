"""
SHATS CYBER — MIGRATE v54: Guruh/Kanal nazorati (2-admin) + Tasdiqlash + Soliq rejalashtiruvchi
================================================================================
- users.group_moderator / users.channel_moderator — Super Admin tayinlaydigan
  ALOHIDA vazifalar: bitta admin guruhlarga, ikkinchisi kanallarga javobgar
  (yo'nalish bilan bog'liq emas — bu cross-cutting nazorat).
- groups.is_verified / channels.is_verified — admin tekshiruvidan o'tganmi
  (soxta ma'lumotlarni aniqlash uchun).
- groups.flagged_reason / channels.flagged_reason — shubhali deb belgilangan
  bo'lsa sabab.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    for col, ddl in [
        ("group_moderator", "ALTER TABLE users ADD COLUMN group_moderator INTEGER DEFAULT 0"),
        ("channel_moderator", "ALTER TABLE users ADD COLUMN channel_moderator INTEGER DEFAULT 0"),
    ]:
        if not _column_exists(c, "users", col):
            c.execute(ddl)
            print(f"  + users.{col}")

    for table in ("groups", "channels"):
        for col, ddl in [
            ("is_verified", f"ALTER TABLE {table} ADD COLUMN is_verified INTEGER DEFAULT 0"),
            ("flagged_reason", f"ALTER TABLE {table} ADD COLUMN flagged_reason TEXT DEFAULT NULL"),
            ("verified_by", f"ALTER TABLE {table} ADD COLUMN verified_by INTEGER DEFAULT NULL"),
        ]:
            if not _column_exists(c, table, col):
                c.execute(ddl)
                print(f"  + {table}.{col}")

    conn.commit()
    conn.close()
    print("✅ v54 Guruh/Kanal nazorati + Soliq rejalashtiruvchi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
