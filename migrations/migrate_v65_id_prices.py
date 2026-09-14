# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v65: Chiroyli ID narxlari — yangi narxlash
================================================================================
Bir martalik narx tuzatishi (BIR MARTA ishlaydi, keyin hech qachon qayta
qo'llanmaydi — shuning uchun admin panelidan keyinchalik narxni
o'zgartirsangiz, u endi HECH QACHON eski qiymatga qaytmaydi):

- 0000001 dan 0000009 gacha — 700 CODE
- 1111111 dan 9999999 gacha (barcha bir xil raqamli) — 1000 CODE
- 1234567 va 0000000 — 1300 CODE (eng nodir ikkitasi)
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

NEW_PRICES = {}
for i in range(1, 10):
    NEW_PRICES[f"000000{i}"] = 700
for d in "123456789":
    NEW_PRICES[d * 7] = 1000
NEW_PRICES["1234567"] = 1300
NEW_PRICES["0000000"] = 1300


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    already_ran = c.execute(
        "SELECT value FROM site_settings WHERE key='migration_v65_applied'").fetchone()
    if already_ran:
        conn.close()
        return  # Bir martalik — ikkinchi marta hech narsa qilmaydi

    updated = 0
    for cid, price in NEW_PRICES.items():
        row = c.execute("SELECT id, status FROM premium_ids WHERE custom_id=?", (cid,)).fetchone()
        if row and row[1] == "available":
            c.execute("UPDATE premium_ids SET base_price=? WHERE custom_id=?", (price, cid))
            updated += 1

    c.execute(
        "INSERT INTO site_settings (key, value) VALUES ('migration_v65_applied', datetime('now'))"
    )
    conn.commit()
    conn.close()
    print(f"  ~ {updated} ta chiroyli ID narxi yangilandi (700/1000/1300 CODE sxemasi bo'yicha, BIR MARTALIK)")
    print("✅ v65 Chiroyli ID narxlari — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
