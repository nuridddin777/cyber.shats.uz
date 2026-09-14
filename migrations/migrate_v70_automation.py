# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v70: Avtomatlashtirish infratuzilmasi
================================================================================
11 xil avtomatik funksiya uchun kerakli ustunlar/jadvallar:
- users.login_streak, last_login_date — kunlik faollik ketma-ketligi
- telegram_users'ga qo'shimcha "oxirgi eslatma" ustunlari — spam bo'lmasligi
  uchun har turdagi eslatma alohida nazorat qilinadi
- bot_state — kunlik/bir martalik triggerlarni kuzatish (masalan "bugun
  soat 09:00 xisobot allaqachon yuborilganmi")
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

    for col, ddl in [
        ("login_streak", "ALTER TABLE users ADD COLUMN login_streak INTEGER DEFAULT 0"),
        ("last_login_date", "ALTER TABLE users ADD COLUMN last_login_date TEXT DEFAULT NULL"),
    ]:
        if not _column_exists(c, "users", col):
            c.execute(ddl)
            print(f"  + users.{col}")

    for col, ddl in [
        ("last_inactivity_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_inactivity_notice_at TEXT DEFAULT NULL"),
        ("last_tickets_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_tickets_notice_at TEXT DEFAULT NULL"),
        ("last_email_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_email_notice_at TEXT DEFAULT NULL"),
        ("last_collection_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_collection_notice_at TEXT DEFAULT NULL"),
    ]:
        if not _column_exists(c, "telegram_users", col):
            c.execute(ddl)
            print(f"  + telegram_users.{col}")

    if not _table_exists(c, "bot_state"):
        c.execute("""
            CREATE TABLE bot_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + jadval: bot_state")

    if not _table_exists(c, "friend_request_reminders"):
        c.execute("""
            CREATE TABLE friend_request_reminders (
                friendship_rowid INTEGER PRIMARY KEY,
                reminded_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        print("  + jadval: friend_request_reminders")

    conn.commit()
    conn.close()
    print("✅ v70 Avtomatlashtirish infratuzilmasi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
