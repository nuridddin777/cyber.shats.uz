# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v74: AKSIYA — barcha tariflardan 1 CODE kamaytirish
================================================================================
Bir martalik aksiya narxi:
- PRO: 3 -> 2 CODE
- CYBER PRO: 7 -> 6 CODE
- VIP: 15 -> 14 CODE
- MAXSUS: 27 -> 26 CODE

Naqd pul (so'm) narxlari O'ZGARMAYDI — faqat CODE narxi kamaytiriladi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

SALE_PRICES = {
    "pro_price_code": 2,
    "cyber_pro_price_code": 6,
    "vip_price_code": 14,
    "hacker_price_code": 26,
}


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    already_ran = c.execute(
        "SELECT value FROM site_settings WHERE key='migration_v74_applied'").fetchone()
    if already_ran:
        conn.close()
        return  # Bir martalik — admin keyinchalik narxni o'zgartirsa, qayta yozib yubormaydi

    for key, price in SALE_PRICES.items():
        c.execute(
            "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(price))
        )

    c.execute(
        "INSERT INTO site_settings (key, value) VALUES ('migration_v74_applied', datetime('now'))"
    )
    c.execute(
        "INSERT INTO site_settings (key, value) VALUES ('tariff_sale_active', '1') "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
    )
    conn.commit()
    conn.close()
    print("  ~ AKSIYA narxlari o'rnatildi: PRO=2, CYBER PRO=6, VIP=14, MAXSUS=26 CODE")
    print("✅ v74 Tarif aksiyasi (-1 CODE) — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
