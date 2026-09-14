# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v72: Yangi tarif narxlari (bir martalik)
================================================================================
Bir martalik narx tuzatishi — bazada saqlangan eski narxlarni yangi
qiymatlarga o'zgartiradi (keyin admin panelidan o'zgartirsangiz, bu
migratsiya ENDI QAYTA ISHLAMAYDI, yangi narxingiz saqlanadi):
- PRO: 3 CODE
- CYBER PRO: 7 CODE
- VIP: 15 CODE
- MAXSUS: 27 CODE
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

NEW_PRICES = {
    "pro_price_code": 3,
    "cyber_pro_price_code": 7,
    "vip_price_code": 15,
    "hacker_price_code": 27,
}


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    already_ran = c.execute(
        "SELECT value FROM site_settings WHERE key='migration_v72_applied'").fetchone()
    if already_ran:
        conn.close()
        return  # Bir martalik — ikkinchi marta hech narsa qilmaydi

    for key, price in NEW_PRICES.items():
        c.execute(
            "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(price))
        )

    c.execute(
        "INSERT INTO site_settings (key, value) VALUES ('migration_v72_applied', datetime('now'))"
    )
    conn.commit()
    conn.close()
    print("  ~ Tarif narxlari yangilandi: PRO=3, CYBER PRO=7, VIP=15, MAXSUS=27 CODE")
    print("✅ v72 Yangi tarif narxlari — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
