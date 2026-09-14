"""
CYBER SHATS — Migration V23 (MAXSUS: Bio maxsus, CODE sovg'a-kartochka,
Maxsus imtiyozlar, SHATS POS simulyatsiyasi, SHATS JAMOSI)
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

# --- BIO MAXSUS ---
for col, defn in [
    ("bio_motto", "TEXT DEFAULT ''"),
    ("bio_portfolio_url", "TEXT DEFAULT ''"),
    ("bio_github_url", "TEXT DEFAULT ''"),
    ("bio_verified", "INTEGER NOT NULL DEFAULT 0"),
    ("profile_views", "INTEGER NOT NULL DEFAULT 0"),
]:
    if not col_exists(c, "users", col):
        c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")
        print(f"  + users.{col}")

# --- CODE SOVG'A-KARTOCHKA ---
if not table_exists(c, "gift_codes"):
    c.execute("""
        CREATE TABLE gift_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            amount INTEGER NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            redeemed_by INTEGER REFERENCES users(id),
            redeemed_at TEXT
        )
    """)
    print("  + jadval: gift_codes")

# --- MAXSUS IMTIYOZLAR HUB ---
if not table_exists(c, "hacker_perks"):
    c.execute("""
        CREATE TABLE hacker_perks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            link TEXT DEFAULT '',
            icon TEXT DEFAULT 'gift',
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: hacker_perks")

# --- SHATS POS SIMULYATSIYASI ---
if not table_exists(c, "pos_products"):
    c.execute("""
        CREATE TABLE pos_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: pos_products")

if not table_exists(c, "pos_sales"):
    c.execute("""
        CREATE TABLE pos_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            product_id INTEGER NOT NULL REFERENCES pos_products(id),
            qty INTEGER NOT NULL,
            total INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: pos_sales")

conn.commit()

# --- SHATS JAMOSI — mavjud 'organizations' tizimidan foydalanadi ---
c.execute("SELECT COUNT(*) FROM organizations WHERE org_key='shats'")
if c.fetchone()[0] == 0:
    c.execute(
        "INSERT INTO organizations (org_key, name, description, stats_members, stats_projects, stats_years) "
        "VALUES ('shats','SHATS JAMOASI','CYBER SHATS platformasini yaratgan asosiy jamoa.',0,0,0)"
    )
    print("  + SHATS JAMOASI tashkiloti yaratildi")

# --- Namuna imtiyozlar ---
c.execute("SELECT COUNT(*) FROM hacker_perks")
if c.fetchone()[0] == 0:
    perks = [
        ("Eksklyuziv cheat-sheet to'plami", "Xavfsizlik, tarmoq va dasturlash bo'yicha PDF qo'llanmalar.", "", "book"),
        ("Yopiq hamjamiyat tadbirlari", "MAXSUS a'zolar uchun maxsus onlayn uchrashuvlar.", "", "calendar"),
        ("Erta kirish (Beta access)", "Yangi funksiyalarni birinchilardan bo'lib sinab ko'rish huquqi.", "", "zap"),
    ]
    for title, desc, link, icon in perks:
        c.execute("INSERT INTO hacker_perks (title, description, link, icon, order_index) VALUES (?,?,?,?,0)",
                  (title, desc, link, icon))
    print(f"  + {len(perks)} ta imtiyoz qo'shildi")

conn.commit()
conn.close()
print("\nMigration V23 muvaffaqiyatli!")
