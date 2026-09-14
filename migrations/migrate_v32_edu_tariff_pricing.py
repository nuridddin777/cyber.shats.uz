"""
SHATS CYBER EDU — MIGRATE v32: Tashkilot tariflari uchun HAQIQIY narx
================================================================================
Ilgari (v28) barcha edu_tariffs.price_coins qiymatlari 0 edi — tashkilotlar
tarifni "DEMO" tugma orqali BEPUL faollashtirar edi.

Ushbu migratsiya buni o'zgartiradi:
  - *_standart tariflar -> 1200 CODE (barcha turdagi tashkilotlar uchun:
    maktab, texnikum, o'quv markazi)
  - *_pro tariflar      -> 1900 CODE

Narxlar keyinchalik ADMIN PANELIDAN (SHATS CYBER admin -> "Edu tashkilotlar"
bo'limi) istalgan vaqtda o'zgartirilishi mumkin — bu migratsiya faqat
BOSHLANG'ICH qiymatlarni belgilaydi. Shu sabab UPDATE faqat narx hali
o'zgartirilmagan (standart boshlang'ich holatdagi) qatorlarga tegadi —
agar admin allaqachon narxni qo'lda o'zgartirgan bo'lsa, bu migratsiya uni
qayta ustidan yozib yubormaydi (idempotent, xavfsiz qayta ishga tushadi).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

STANDARD_PRICE = 1200
PRO_PRICE = 1900


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='edu_tariffs'")
    if not c.fetchone():
        conn.close()
        return  # edu_tariffs jadvali hali yaratilmagan (v28 ishlamagan bo'lishi mumkin)

    # Faqat hali narxlanmagan (price_coins=0 yoki NULL) qatorlarni yangilaymiz —
    # admin qo'lda kiritgan boshqa narxlarni bosib o'tmaslik uchun.
    c.execute("""
        UPDATE edu_tariffs SET price_coins=?
        WHERE code LIKE '%_standart' AND (price_coins IS NULL OR price_coins=0)
    """, (STANDARD_PRICE,))
    c.execute("""
        UPDATE edu_tariffs SET price_coins=?
        WHERE code LIKE '%_pro' AND (price_coins IS NULL OR price_coins=0)
    """, (PRO_PRICE,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    migrate()
    print("✅ v32 Edu tarif narxlari (Standart=1200, Pro=1900 CODE) muvaffaqiyatli!")
