"""
CYBER SHATS — Migration V25 (MAXSUS: Sozlamalar qo'shimchalari, Loyihalar qo'shimchalari)
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


conn = sqlite3.connect(DB)
c = conn.cursor()

# --- SOZLAMALAR: API KALIT ---
if not table_exists(c, "api_keys"):
    c.execute("""
        CREATE TABLE api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            api_key TEXT UNIQUE NOT NULL,
            label TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            last_used_at TEXT,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    print("  + jadval: api_keys")

# --- LOYIHALAR: mentor so'rash / yordam kerak ---
if table_exists(c, "startups"):
    if not col_exists(c, "startups", "needs_help"):
        c.execute("ALTER TABLE startups ADD COLUMN needs_help INTEGER NOT NULL DEFAULT 0")
        print("  + startups.needs_help")
    if not col_exists(c, "startups", "mentor_requested"):
        c.execute("ALTER TABLE startups ADD COLUMN mentor_requested INTEGER NOT NULL DEFAULT 0")
        print("  + startups.mentor_requested")

conn.commit()
conn.close()
print("\nMigration V25 muvaffaqiyatli!")
