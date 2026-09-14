# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v61: Promo kodlar — chegirma emas, CODE bonusi
================================================================================
Avval promo kodlar CODE SOTIB OLISH narxidan foiz/qat'iy CHEGIRMA berardi.
Endi promo kod — mustaqil, bevosita CODE balansiga QO'SHILADIGAN bonus
(hech qanday xarid talab qilinmaydi, faqat kodni "faollashtirish" kifoya).
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

    if not _column_exists(c, "promo_codes", "bonus_code_amount"):
        c.execute("ALTER TABLE promo_codes ADD COLUMN bonus_code_amount INTEGER DEFAULT 0")
        print("  + promo_codes.bonus_code_amount")
        # Eski % chegirmali kodlarni ham CODE bonusiga taxminiy o'tkazamiz
        # (aks holda ular butunlay ma'nosiz qoladi) — faqat ma'lumot yo'qolib
        # ketmasligi uchun, fixed turdagilar to'g'ridan-to'g'ri CODE deb olinadi.
        c.execute("UPDATE promo_codes SET bonus_code_amount = discount_value WHERE discount_type='fixed'")
        c.execute("UPDATE promo_codes SET bonus_code_amount = 5 WHERE discount_type='pct' AND bonus_code_amount=0")

    conn.commit()
    conn.close()
    print("✅ v61 Promo kodlar — CODE bonusi tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
