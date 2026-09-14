"""
CYBER SHATS — Migration V27 (To'lov agregatorlari + OneID)
Click / Payme / Uzum Pay orqali karta bilan real-vaqtli CODE sotib olish
va OneID (id.egov.uz) orqali shaxsni tasdiqlash uchun jadval/ustunlar.
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

# --- TO'LOV TRANZAKSIYALARI ---
if not table_exists(c, "payment_transactions"):
    c.execute("""
        CREATE TABLE payment_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            provider TEXT NOT NULL,                 -- click | payme | uzum
            provider_txn_id TEXT,                    -- agregatordagi order/transaction ID
            merchant_trans_id TEXT NOT NULL UNIQUE,  -- bizning tomonimizda generatsiya qilingan unikal order ID
            card_type TEXT,                          -- uzcard | humo | visa | mastercard | noma'lum
            amount_uzs INTEGER NOT NULL,
            code_amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',  -- pending | paid | failed | cancelled
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            paid_at TEXT,
            raw_payload TEXT
        )
    """)
    c.execute("CREATE INDEX idx_payment_txn_user ON payment_transactions(user_id)")
    c.execute("CREATE INDEX idx_payment_txn_provider_txn ON payment_transactions(provider, provider_txn_id)")
    print("  + jadval: payment_transactions")

# --- FOYDALANUVCHI SAQLAGAN KARTALAR (faqat agregator tokeni, PAN emas!) ---
if not table_exists(c, "user_saved_cards"):
    c.execute("""
        CREATE TABLE user_saved_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            provider TEXT NOT NULL,
            card_token TEXT NOT NULL,     -- Click/Payme bergan token
            masked_pan TEXT,              -- masalan "8600 **** **** 1234"
            card_type TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: user_saved_cards")

# --- USERS jadvaliga OneID ustunlari ---
if table_exists(c, "users"):
    if not col_exists(c, "users", "oneid_verified"):
        c.execute("ALTER TABLE users ADD COLUMN oneid_verified INTEGER NOT NULL DEFAULT 0")
        print("  + ustun: users.oneid_verified")
    if not col_exists(c, "users", "oneid_pinfl"):
        c.execute("ALTER TABLE users ADD COLUMN oneid_pinfl TEXT DEFAULT NULL")
        print("  + ustun: users.oneid_pinfl")
    if not col_exists(c, "users", "oneid_full_name"):
        c.execute("ALTER TABLE users ADD COLUMN oneid_full_name TEXT DEFAULT NULL")
        print("  + ustun: users.oneid_full_name")

conn.commit()
conn.close()
print("\nMigration V27 muvaffaqiyatli!")
