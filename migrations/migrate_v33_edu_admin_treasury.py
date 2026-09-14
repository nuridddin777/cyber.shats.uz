"""
SHATS CYBER EDU — MIGRATE v33: Markaz ID tizimi, ulanish kodi,
alohida Edu admin va alohida Edu G'aznasi
================================================================================
Ushbu migratsiya quyidagilarni qo'shadi:

1) edu_organizations.org_number — har bir tashkilotga beriladigan, ketma-ket,
   5 xonali, GLOBAL (butun tizim bo'yicha yagona) raqam (masalan 10001,
   10002, ...). Admin CODE chiqarayotganda tashkilotni shu raqam orqali
   ham topa oladi.

2) edu_organizations.connect_code — o'qituvchi/o'quvchi ANIQ shu tashkilotga
   ulanish uchun ishlatadigan maxsus kod. Tashkilot tarif SOTIB OLMAGUNCHA
   bu maydon BO'SH (NULL) qoladi — demak hech kim ulana olmaydi. Tarif
   sotib olingan zahoti (yoki 9 xonali kalit bilan ochilganda) avtomatik
   generatsiya qilinadi.

3) edu_admins — SHATS CYBER asosiy admin/super_admin'dan BUTUNLAY MUSTAQIL,
   faqat Edu (tashkilotlar/tariflar/Edu G'aznasi) uchun javobgar alohida
   admin hisobi. Standart hisob: shatsadmin@edu / edu19199655
   (birinchi kirishda parolni albatta o'zgartirish tavsiya etiladi).

4) edu_treasury_fund / edu_treasury_fund_log — Edu qismi uchun ALOHIDA
   jamg'arma (asosiy SHATS CYBER treasury_fund'dan MUSTAQIL — talabga ko'ra
   "Edu qismi uchun alohida jamg'arma ochilishi shart"). Shu paytdan
   boshlab tashkilotlarga CODE chiqarish shu yangi jamg'armadan bo'ladi.

5) edu_activation_keys — G'azna tomonidan chiqariladigan 9 xonali,
   bir martalik faollashtirish kalitlari. Tashkilot bu kalitni kiritib,
   coin sarflamasdan (yoki coin yetishmasa ham) tarifni faollashtira oladi.

DIQQAT (arxitektura o'zgarishi): shu migratsiyadan keyin tashkilotlarga CODE
chiqarish endi ESKI yagona (`treasury_fund`) emas, YANGI (`edu_treasury_fund`)
jamg'armadan amalga oshiriladi — qarang: edu_treasury_bridge.py yangilanishi.
"""
import sqlite3
import os
import secrets
from werkzeug.security import generate_password_hash

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

ORG_NUMBER_START = 10001


def _table_exists(c, name):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return c.fetchone() is not None


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in c.fetchall())


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "edu_organizations"):
        conn.close()
        return  # v28 hali ishlamagan bo'lishi mumkin

    # ------------------------------------------------------------
    # 1) org_number va connect_code ustunlari
    # ------------------------------------------------------------
    if not _column_exists(c, "edu_organizations", "org_number"):
        c.execute("ALTER TABLE edu_organizations ADD COLUMN org_number TEXT")
    if not _column_exists(c, "edu_organizations", "connect_code"):
        c.execute("ALTER TABLE edu_organizations ADD COLUMN connect_code TEXT")

    c.execute("""CREATE TABLE IF NOT EXISTS edu_org_number_counter (
        id INTEGER PRIMARY KEY CHECK (id=1),
        next_number INTEGER NOT NULL DEFAULT %d
    )""" % ORG_NUMBER_START)
    c.execute("INSERT OR IGNORE INTO edu_org_number_counter (id, next_number) VALUES (1, ?)",
              (ORG_NUMBER_START,))

    # Mavjud (bu migratsiyadan oldin ro'yxatdan o'tgan) tashkilotlarga
    # orqaga qarab (backfill) ketma-ket org_number beramiz.
    c.execute("SELECT id FROM edu_organizations WHERE org_number IS NULL ORDER BY id ASC")
    existing_orgs = [row[0] for row in c.fetchall()]
    if existing_orgs:
        c.execute("SELECT next_number FROM edu_org_number_counter WHERE id=1")
        next_num = c.fetchone()[0]
        for org_id in existing_orgs:
            c.execute("UPDATE edu_organizations SET org_number=? WHERE id=?", (str(next_num), org_id))
            next_num += 1
        c.execute("UPDATE edu_org_number_counter SET next_number=? WHERE id=1", (next_num,))

    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_edu_org_number ON edu_organizations(org_number)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_edu_connect_code ON edu_organizations(connect_code) "
              "WHERE connect_code IS NOT NULL")

    # ------------------------------------------------------------
    # 2) edu_admins — asosiy admindan mustaqil Edu admin hisobi
    # ------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        ism TEXT DEFAULT 'Edu Admin',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        last_login_at TEXT DEFAULT NULL
    )""")
    c.execute("SELECT 1 FROM edu_admins WHERE email=?", ("shatsadmin@edu",))
    if not c.fetchone():
        c.execute(
            "INSERT INTO edu_admins (email, password_hash, ism) VALUES (?,?,?)",
            ("shatsadmin@edu", generate_password_hash("edu19199655"), "Edu Bosh Admin")
        )

    # ------------------------------------------------------------
    # 3) Edu uchun ALOHIDA jamg'arma (asosiy treasury_fund'dan mustaqil)
    # ------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_treasury_fund (
        id INTEGER PRIMARY KEY CHECK (id=1),
        balance INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")
    c.execute("INSERT OR IGNORE INTO edu_treasury_fund (id, balance) VALUES (1, 0)")

    c.execute("""CREATE TABLE IF NOT EXISTS edu_treasury_fund_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        direction TEXT NOT NULL,          -- 'in' | 'out'
        amount INTEGER NOT NULL,
        reason TEXT NOT NULL,
        edu_org_id INTEGER,
        edu_admin_id INTEGER,             -- amalni bajargan Edu admin (audit)
        activation_key_id INTEGER,        -- agar 9-xonali kalit orqali bo'lsa
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    # ------------------------------------------------------------
    # 4) 9 xonali faollashtirish kalitlari
    # ------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_activation_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_code TEXT NOT NULL UNIQUE,     -- 9 xonali raqamli kalit
        tarif_code TEXT NOT NULL,          -- qaysi tarifni ochadi (edu_tariffs.code)
        months INTEGER NOT NULL DEFAULT 1,
        is_used INTEGER NOT NULL DEFAULT 0,
        used_by_org_id INTEGER,
        used_at TEXT,
        created_by_edu_admin_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    conn.commit()

    # ------------------------------------------------------------
    # 5) So'ralgan G'azna hisobini yaratish (agar treasury_accounts jadvali
    #    mavjud bo'lsa — bu asosiy SHATS CYBER migratsiyasidan keladi)
    # ------------------------------------------------------------
    if _table_exists(c, "treasury_accounts"):
        c.execute("SELECT 1 FROM treasury_accounts WHERE email=?", ("xisob@shats",))
        if not c.fetchone():
            c.execute(
                "INSERT INTO treasury_accounts (ism, email, password_hash) VALUES (?,?,?)",
                ("G'azna Hisobi", "xisob@shats", generate_password_hash("sha9655ts"))
            )
            conn.commit()

    conn.close()


if __name__ == "__main__":
    migrate()
    print("✅ v33 Markaz ID, ulanish kodi, alohida Edu admin va Edu G'aznasi muvaffaqiyatli!")
