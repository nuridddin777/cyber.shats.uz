"""
SHATS CYBER EDU — MIGRATE v39: Edu 2.0 tuzatishlar to'plami
================================================================================
Ushbu migratsiya faqat EDU (edu2 blueprint) qismiga tegishli quyidagi
muammolarni tuzatadi (asosiy saytga tegilmaydi):

  1) VILOYAT/TUMAN VA MAKTAB TAKRORLANISHI — `districts` va `schools`
     jadvallarida UNIQUE cheklov yo'q edi, shu sabab migrate_edu.py bir necha
     marta ishga tushganda har bir tuman/maktab IKKI MARTA yozilgan edi
     (masalan "Chirchiq" ro'yxatda 2 marta chiqadi). Bu yerda:
       a) mavjud takrorlar birlashtiriladi (eng kichik id qoldiriladi,
          unga bog'liq tashqi kalitlar shu idga ko'chiriladi),
       b) kelajakda takrorlanmasligi uchun UNIQUE INDEX qo'shiladi.

  2) EMAIL TASDIQLASH — tashkilot (maktab/texnikum/markaz) ro'yxatdan
     o'tganda emailga kod yuborilishi va shu kodni kiritish sahifasi
     bo'lishi kerak edi, lekin buning uchun na jadval, na ustun bor edi.
     `edu_organizations.email_verified` ustuni va
     `edu_org_email_verifications` jadvali qo'shiladi.

  3) TARIF NARXLARI — Edu tariflari endi quyidagicha (CODE / oy):
       Maktab — Standart   : 120
       Maktab — Pro        : 190
       Texnikum — Standart : 100
       Texnikum — Pro      : 170
       O'quv markazi — Standart : 180
       O'quv markazi — Pro      : 220

Xavfsiz qayta ishga tushiriladi (idempotent).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

NEW_TARIFF_PRICES = {
    "maktab_standart": 120,
    "maktab_pro": 190,
    "texnikum_standart": 100,
    "texnikum_pro": 170,
    "markaz_standart": 180,
    "markaz_pro": 220,
}

# Bog'liq jadval -> ustun nomi (district_id yoki school_id ko'chirish uchun)
_DISTRICT_REF_TABLES = ["users", "schools", "edu_organizations", "edu_teachers", "edu_students"]


def _dedupe_districts(c):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='districts'")
    if not c.fetchone():
        return

    c.execute("SELECT id, name, region_id FROM districts ORDER BY id")
    rows = c.fetchall()
    seen = {}   # (name, region_id) -> kept_id
    remap = {}  # duplicate_id -> kept_id
    for did, name, region_id in rows:
        key = (name, region_id)
        if key in seen:
            remap[did] = seen[key]
        else:
            seen[key] = did

    if not remap:
        return

    for table in _DISTRICT_REF_TABLES:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not c.fetchone():
            continue
        c.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in c.fetchall()]
        if "district_id" not in cols:
            continue
        for dup_id, kept_id in remap.items():
            c.execute(f"UPDATE {table} SET district_id=? WHERE district_id=?", (kept_id, dup_id))

    dup_ids = list(remap.keys())
    c.executemany("DELETE FROM districts WHERE id=?", [(i,) for i in dup_ids])

    # Kelajakda takrorlanmasligi uchun
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_districts_unique ON districts(name, region_id)")


def _dedupe_schools(c):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schools'")
    if not c.fetchone():
        return

    c.execute("SELECT id, name, district_id FROM schools ORDER BY id")
    rows = c.fetchall()
    seen = {}
    remap = {}
    for sid, name, district_id in rows:
        key = (name, district_id)
        if key in seen:
            remap[sid] = seen[key]
        else:
            seen[key] = sid

    if not remap:
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_unique ON schools(name, district_id)")
        return

    # Bog'liq bo'lishi mumkin bo'lgan jadvallar (bo'lsa) — school_id ko'chiriladi
    for table in ["users", "edu_classes", "school_subscriptions"]:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not c.fetchone():
            continue
        c.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in c.fetchall()]
        if "school_id" not in cols:
            continue
        for dup_id, kept_id in remap.items():
            c.execute(f"UPDATE {table} SET school_id=? WHERE school_id=?", (kept_id, dup_id))

    dup_ids = list(remap.keys())
    c.executemany("DELETE FROM schools WHERE id=?", [(i,) for i in dup_ids])

    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_schools_unique ON schools(name, district_id)")


def _add_email_verification(c):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edu_organizations'")
    if not c.fetchone():
        return

    c.execute("PRAGMA table_info(edu_organizations)")
    cols = [r[1] for r in c.fetchall()]
    if "email_verified" not in cols:
        c.execute("ALTER TABLE edu_organizations ADD COLUMN email_verified INTEGER DEFAULT 0")

    c.execute("""CREATE TABLE IF NOT EXISTS edu_org_email_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        attempts INTEGER DEFAULT 0,
        expires_at TEXT NOT NULL,
        last_sent_at TEXT DEFAULT (datetime('now')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(org_id) REFERENCES edu_organizations(id)
    )""")


def _update_tariff_prices(c):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edu_tariffs'")
    if not c.fetchone():
        return
    for code, price in NEW_TARIFF_PRICES.items():
        c.execute("UPDATE edu_tariffs SET price_coins=? WHERE code=?", (price, code))


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    _dedupe_districts(c)
    _dedupe_schools(c)
    _add_email_verification(c)
    _update_tariff_prices(c)

    conn.commit()
    conn.close()
    print("✅ v39 Edu tuzatishlar (tuman takrorlari, email tasdiqlash, yangi tarif narxlari) muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
