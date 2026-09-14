# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v57: Shaxsiy dizayin (CODE evaziga) + Eksklyuziv admin temasi
================================================================================
- users.personal_theme_changes — shaxsiy dizaynni necha marta o'zgartirgani.
  1-marta 7 CODE (panelni ochish + birinchi o'zgartirish), 2-marta va undan
  keyin har safar 10 CODE.
- users.exclusive_theme — FAQAT admin tomonidan beriladigan maxsus tema
  (masalan 'cars' — mashinalar uslubi), boshqa hech kim sotib ololmaydi.
- site_settings['site_theme'] — agar hali sozlanmagan bo'lsa 'none' (hech
  qanday mavsumiy tema) qilib urug'lanadi — avval bu yerda YASHIRIN XATO bor
  edi: agar jadval bo'sh bo'lsa, kod avtomatik 'football' (futbol) temasini
  YOQIB YUBORARDI, garchi admin buni ATAYLAB tanlamagan bo'lsa ham.
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

    for col, ddl in [
        ("personal_theme_changes", "ALTER TABLE users ADD COLUMN personal_theme_changes INTEGER DEFAULT 0"),
        ("exclusive_theme", "ALTER TABLE users ADD COLUMN exclusive_theme TEXT DEFAULT NULL"),
    ]:
        if not _column_exists(c, "users", col):
            c.execute(ddl)
            print(f"  + users.{col}")

    existing_theme = c.execute("SELECT value FROM site_settings WHERE key='site_theme'").fetchone()
    if not existing_theme:
        c.execute("INSERT INTO site_settings (key, value) VALUES ('site_theme', 'none')")
        c.execute("INSERT INTO site_settings (key, value) VALUES ('site_theme_name', 'Oddiy (mavsumiy tema yo\u02bbq)')")
        print("  + site_settings.site_theme = 'none' (xato bo'lgan 'football' standartini tuzatdi)")
    elif existing_theme[0] == "football":
        # Bu holat — o'sha xato tufayli tasodifan yoqilib qolgan bo'lishi mumkin.
        # Agar admin buni ATAYLAB tanlagan bo'lsa ham, hozircha xavfsizroq —
        # asl holatga (tema yo'q) qaytaramiz; admin istasa panelidan qayta yoqadi.
        c.execute("UPDATE site_settings SET value='none' WHERE key='site_theme'")
        c.execute("UPDATE site_settings SET value='Oddiy (mavsumiy tema yo\u02bbq)' WHERE key='site_theme_name'")
        print("  ~ site_settings.site_theme 'football'dan 'none'ga qaytarildi (ehtimoliy xato tufayli yoqilgan edi)")

    conn.commit()
    conn.close()
    print("✅ v57 Shaxsiy dizayin + Eksklyuziv tema — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
