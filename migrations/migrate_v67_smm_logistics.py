# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v67: SMM & Logistika — "Tez kunda"
================================================================================
Ingliz tili/Matematikadan farqli o'laroq (ular BUTUNLAY yashirilgan edi),
SMM va Logistika yo'nalishlari navigatsiyada KO'RINIB TURADI, lekin
"Tez kunda" belgisi bilan — kurslari vaqtincha yopiladi, foydalanuvchi
buni ochib ko'rganda tez orada kelishini biladi.
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

    if not _column_exists(c, "directions", "coming_soon"):
        c.execute("ALTER TABLE directions ADD COLUMN coming_soon INTEGER DEFAULT 0")
        print("  + directions.coming_soon")

    c.execute("UPDATE directions SET coming_soon=1 WHERE slug IN ('smm','logistika')")

    closed = c.execute("""
        UPDATE courses SET is_active=0
        WHERE direction_id IN (SELECT id FROM directions WHERE slug IN ('smm','logistika'))
          AND is_active=1
    """).rowcount
    if closed:
        print(f"  - {closed} ta kurs yopildi (SMM, Logistika) — 'Tez kunda' bilan")

    conn.commit()
    conn.close()
    print("✅ v67 SMM & Logistika — Tez kunda — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
