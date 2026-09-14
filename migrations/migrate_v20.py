"""
CYBER SHATS — Migration V20 (Maxsus versiya: JAMOA va JAMOA JAMG'ARMASI)

Bu migratsiya "Maxsus versiya" (hacker-tier) uchun Jamoa (Team) tizimini qo'shadi:
- teams: jamoa nomi + avtomatik ketma-ket 5 xonali ID (masalan 00001)
- team_members: a'zolar va rollari (leader/moderator/member)
- team_treasury: jamoa jamg'armasi balansi
- team_treasury_log: jamg'armaga kirim/chiqim tarixi
- team_invites: taklif havolalari/kodlari
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def col_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(r[1] == col for r in c.fetchall())


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# users jadvaliga "hacker" (Maxsus versiya) plani uchun alohida ustun kerak emas —
# users.plan TEXT ustunidan 'hacker' qiymati sifatida foydalaniladi.

if not table_exists(c, "teams"):
    c.execute("""
        CREATE TABLE teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            custom_id TEXT UNIQUE NOT NULL,        -- avtomatik ketma-ket 5 xonali ID, masalan '00001'
            name TEXT NOT NULL,                    -- jamoa nomi (foydalanuvchi tanlaydi)
            leader_id INTEGER NOT NULL REFERENCES users(id),
            description TEXT DEFAULT '',
            is_open INTEGER NOT NULL DEFAULT 1,    -- jamg'arma balansi ochiqmi (1) yopiqmi (0)
            status TEXT NOT NULL DEFAULT 'active', -- active, frozen (soliq to'lanmagan)
            next_billing_at TEXT,                  -- keyingi oylik soliq muddati
            tax_free_until TEXT,                   -- MAXSUS foydalanuvchi uchun 3 oy bepul muddati
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_teams_leader ON teams(leader_id)")
    print("  + jadval: teams")
else:
    for col, defn in [
        ("status", "TEXT NOT NULL DEFAULT 'active'"),
        ("next_billing_at", "TEXT"),
        ("tax_free_until", "TEXT"),
    ]:
        if not col_exists(c, "teams", col):
            c.execute(f"ALTER TABLE teams ADD COLUMN {col} {defn}")
            print(f"  + teams.{col}")

if not table_exists(c, "team_members"):
    c.execute("""
        CREATE TABLE team_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            role TEXT NOT NULL DEFAULT 'member',   -- leader, moderator, member
            joined_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(team_id, user_id)
        )
    """)
    c.execute("CREATE INDEX idx_tm_user ON team_members(user_id)")
    c.execute("CREATE INDEX idx_tm_team ON team_members(team_id)")
    print("  + jadval: team_members")

if not table_exists(c, "team_treasury"):
    c.execute("""
        CREATE TABLE team_treasury (
            team_id INTEGER PRIMARY KEY REFERENCES teams(id),
            balance INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: team_treasury")

if not table_exists(c, "team_treasury_log"):
    c.execute("""
        CREATE TABLE team_treasury_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            user_id INTEGER REFERENCES users(id),         -- kim amalga oshirgan (hissa qo'shgan/olgan)
            direction TEXT NOT NULL,                       -- 'in' (hissa) yoki 'out' (sarf/sovg'a)
            amount INTEGER NOT NULL,
            reason TEXT NOT NULL DEFAULT '',                -- contribute, gift_plan, withdraw, admin_adjust
            note TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_ttl_team ON team_treasury_log(team_id, created_at)")
    print("  + jadval: team_treasury_log")

if not table_exists(c, "team_invites"):
    c.execute("""
        CREATE TABLE team_invites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_id INTEGER NOT NULL REFERENCES teams(id),
            invite_code TEXT UNIQUE NOT NULL,
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT,
            uses_left INTEGER DEFAULT NULL             -- NULL = cheksiz
        )
    """)
    print("  + jadval: team_invites")

if not table_exists(c, "redeem_codes"):
    c.execute("""
        CREATE TABLE redeem_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            plan TEXT NOT NULL DEFAULT 'hacker',      -- qaysi tarifni ochadi
            duration_type TEXT NOT NULL,               -- '1h' yoki '30d'
            created_by INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            used_by INTEGER REFERENCES users(id),
            used_at TEXT
        )
    """)
    c.execute("CREATE INDEX idx_redeem_code ON redeem_codes(code)")
    print("  + jadval: redeem_codes")

# Narx sozlamalari (Maxsus versiya narxi)
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('hacker_price_code','77')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('team_tax_free_code','3')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('team_tax_paid_code','2')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('team_tax_hacker_code','10')")
c.execute("INSERT OR IGNORE INTO pricing_settings (key,value) VALUES ('team_hacker_free_months','3')")

# MUHIM: bazada eski (bootstrap paytida yozilgan) narxlar hali ham turgan bo'lishi mumkin —
# ular pricing.py DEFAULTS'dan USTUN turadi. Shu sababli yangi kelishilgan narxlarni
# to'g'ridan-to'g'ri majburiy yangilaymiz (faqat hali ESKI qiymatda bo'lsa).
_forced_fixes = [
    ("pro_price_code", "57000", "9"),
    ("cyber_pro_price_code", "150000", "15"),
    ("vip_price_code", "540000", "57"),
    ("hacker_price_code", "99", "77"),
    ("welcome_bonus_code", "7000", "5"),
]
for key, old_val, new_val in _forced_fixes:
    c.execute("SELECT value FROM pricing_settings WHERE key=?", (key,))
    row = c.fetchone()
    if row is None:
        c.execute("INSERT INTO pricing_settings (key, value) VALUES (?,?)", (key, new_val))
        print(f"  + {key} = {new_val} (yangi qo'yildi)")
    elif row[0] == old_val:
        c.execute("UPDATE pricing_settings SET value=? WHERE key=?", (new_val, key))
        print(f"  ~ {key}: {old_val} -> {new_val} (eski qiymat tuzatildi)")
print("  + narx sozlamalari: hacker_price_code=77, jamoa soliqlari")

conn.commit()
conn.close()
print("\nMigration V20 muvaffaqiyatli!")
