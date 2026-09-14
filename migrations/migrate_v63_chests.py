# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v63: Sandiqlar (loot box) tizimi + Galichka do'koni
================================================================================
- users.chest_tickets_tariff / chest_tickets_id / chest_tickets_mystery —
  har sandiq turi uchun ALOHIDA chipta hisobi.
- users.chest_keys — sandiq kalitlari (achko), umumiy hisob.
- users.tariff_chest_opens — Tariflar sandig'i UMUMIY ochilgan soni
  (bosqichma-bosqich mukofotlar shunga qarab beriladi).
- users.checkmark_badge — foydalanuvchi tanlagan/sotib olgan kosmetik
  galichka turi (tarif belgisidan MUSTAQIL, alohida shakl/rangda).
- chest_open_log — har bir ochish tarixi (audit + "omadga qarab" balans
  uchun kerak).
- checkmark_shop — sotiladigan galichka turlari katalogi.
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
        ("chest_tickets_tariff", "ALTER TABLE users ADD COLUMN chest_tickets_tariff INTEGER DEFAULT 0"),
        ("chest_tickets_id", "ALTER TABLE users ADD COLUMN chest_tickets_id INTEGER DEFAULT 0"),
        ("chest_tickets_mystery", "ALTER TABLE users ADD COLUMN chest_tickets_mystery INTEGER DEFAULT 0"),
        ("chest_keys", "ALTER TABLE users ADD COLUMN chest_keys INTEGER DEFAULT 0"),
        ("tariff_chest_opens", "ALTER TABLE users ADD COLUMN tariff_chest_opens INTEGER DEFAULT 0"),
        ("checkmark_badge", "ALTER TABLE users ADD COLUMN checkmark_badge TEXT DEFAULT NULL"),
    ]:
        if not _column_exists(c, "users", col):
            c.execute(ddl)
            print(f"  + users.{col}")

    if not _table_exists(c, "chest_open_log"):
        c.execute("""
            CREATE TABLE chest_open_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                chest_type TEXT NOT NULL,
                reward_type TEXT NOT NULL,
                reward_value TEXT,
                keys_won INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        c.execute("CREATE INDEX idx_chest_open_log_user ON chest_open_log(user_id, chest_type)")
        print("  + jadval: chest_open_log")

    if not _table_exists(c, "checkmark_shop"):
        c.execute("""
            CREATE TABLE checkmark_shop (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                badge_key TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                style_css TEXT NOT NULL,
                price_code INTEGER DEFAULT 0,
                price_keys INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
        """)
        print("  + jadval: checkmark_shop")

    # MUHIM (tuzatilgan xato): avval seed (boshlang'ich) ma'lumotlar FAQAT
    # jadval BIRINCHI marta yaratilganda qo'shilardi. Agar jadval biror
    # sababdan (masalan avvalgi urinish yarim to'xtab qolgan bo'lsa) BOR,
    # lekin BO'SH bo'lsa — bu holat "jadval yaratilgan" deb hisoblanib,
    # seed ma'lumotlar HECH QACHON qo'shilmasdi, natijada "Galichkalar"
    # do'koni doim BO'SH ko'rinardi. Endi jadval qatorlari SONI
    # tekshiriladi — agar 0 bo'lsa (jadval bor, lekin bo'sh), baribir
    # qayta to'ldiriladi.
    _cm_count = c.execute("SELECT COUNT(*) FROM checkmark_shop").fetchone()[0]
    if _cm_count == 0:
        # Boshlang'ich galichka turlari — Pro/Cyber Pro/VIP tarif
        # belgilaridan BUTUNLAY farqli shakl va ranglarda (olmos, yulduz,
        # chaqmoq, sakkiz burchak shakllar — tarifdagi dumaloq/oddiy
        # belgilardan farqli).
        seed = [
            ("diamond_ice", "Muz Olmosi", "clip-path:polygon(50% 0%,100% 35%,82% 100%,18% 100%,0% 35%); background:linear-gradient(135deg,#a8e6ff,#2E75D6); color:#fff;", 150, 300),
            ("star_ember", "Cho'g' Yulduzi", "clip-path:polygon(50% 0%,61% 35%,98% 35%,68% 57%,79% 91%,50% 70%,21% 91%,32% 57%,2% 35%,39% 35%); background:linear-gradient(135deg,#ff9f43,#e84118); color:#fff;", 150, 300),
            ("octagon_neon", "Neon Sakkizburchak", "clip-path:polygon(30% 0%,70% 0%,100% 30%,100% 70%,70% 100%,30% 100%,0% 70%,0% 30%); background:linear-gradient(135deg,#00f5d4,#00bbf9); color:#022;", 200, 400),
            ("bolt_violet", "Binafsha Chaqmoq", "clip-path:polygon(45% 0,100% 0,55% 45%,100% 45%,35% 100%,45% 55%,0 55%); background:linear-gradient(135deg,#c471ed,#7b2ff7); color:#fff;", 250, 500),
        ]
        for key, label, css, price_code, price_keys in seed:
            c.execute(
                "INSERT OR IGNORE INTO checkmark_shop (badge_key,label,style_css,price_code,price_keys) VALUES (?,?,?,?,?)",
                (key, label, css, price_code, price_keys)
            )
        print(f"  + {len(seed)} ta boshlang'ich galichka turi (jadval bo'sh bo'lgani uchun qayta to'ldirildi)")

    conn.commit()
    conn.close()
    print("✅ v63 Sandiqlar tizimi + Galichka do'koni — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
