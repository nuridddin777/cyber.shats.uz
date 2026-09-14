"""
SHATS CYBER — MIGRATE v37: Bot tariflarini to'g'ridan-to'g'ri so'mda narxlash
================================================================================
Telegram bot orqali HAQIQIY pul evaziga (karta + chek) tarif sotib olishda
endi narx CODE kursidan hisoblanmaydi — har bir tarif uchun ALOHIDA, aniq
belgilangan so'm narxi ishlatiladi (admin buni keyinchalik narxlar
panelidan o'zgartira oladi):

    Pro Oddiy   -> 90 000 so'm
    Cyber Pro   -> 150 000 so'm
    VIP         -> 570 000 so'm
    HackerLab   -> 77 000 so'm

DIQQAT 1: kalitlar ATAYLAB `bot_tariff_price_*` deb nomlangan — chunki
`pro_price_uzs` kaliti ALLAQACHON boshqa (bot bilan bog'liq bo'lmagan)
maqsadda ishlatilar edi (qarang: app.py admin panel — boshqa narx, 99 000).
Agar shu eski kalit qayta ishlatilganida, ikkala funksiya narxlari
bir-birini ustidan yozib, chalkashlik keltirib chiqargan bo'lardi.

DIQQAT 2: bu qiymatlar so'ralgan ko'rsatmaga ko'ra ANIQ shunday kiritildi.
Boshqa uchta tarif "CODE narxi x 10 000" formulasiga mos keladi (9x10000,
15x10000, 57x10000), lekin HackerLab (77 000) shu formuladan farq qiladi
(77 x 10 000 = 770 000 bo'lishi kerak edi) — bu chindan ham shunday
mo'ljallangan bo'lishi mumkin (masalan aksiya narxi), shuning uchun
o'zgartirilmadi va ANIQ so'ralganidek kiritildi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

TARIFF_UZS_PRICES = {
    "bot_tariff_price_pro": "90000",
    "bot_tariff_price_cyber_pro": "150000",
    "bot_tariff_price_vip": "570000",
    "bot_tariff_price_hacker": "77000",
}


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    for key, value in TARIFF_UZS_PRICES.items():
        c.execute("SELECT value FROM pricing_settings WHERE key=?", (key,))
        if not c.fetchone():
            c.execute("INSERT INTO pricing_settings (key, value) VALUES (?,?)", (key, value))

    conn.commit()
    conn.close()
    print("✅ v37 Bot tariflari so'mda narxlash muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
