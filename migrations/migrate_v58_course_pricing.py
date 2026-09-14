# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v58: Ingliz tili/Matematika yopildi + Kurslar narxi qayta hisoblandi
================================================================================
1) "Ingliz tili" va "Matematika" yo'nalishidagi barcha kurslar YOPILADI
   (is_active=0) — o'chirilmaydi, faqat yashiriladi (agar kelajakda kerak
   bo'lsa qayta tiklash mumkin).

2) Barcha PULIK kurslarning narxi qayta hisoblanadi. AVVAL XATO bor edi:
   40 ta pulik kursning HAMMASI bir xil — 10,000 CODE turardi (darslar
   soni 8 tadanmi, 24 tadanmi — farqi yo'q edi)! Endi narx kursning
   HAQIQIY hajmiga (darslar soni) va darajasiga (Boshlang'ich/O'rta/Yuqori)
   qarab 30 CODE dan 700 CODE gacha o'zgaradi.

   Formula: score = darslar_soni * daraja_koeffitsienti (Pro-only kurslar
   uchun +15%), so'ng bu score [min,max] oralig'idan [30,700] CODE
   oralig'iga chiziqli ko'chiriladi, 5 CODE ga yaxlitlanadi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

LEVEL_MULT = {"Boshlang'ich": 1.0, "O'rta": 1.4, "Yuqori": 1.9}
PRICE_MIN, PRICE_MAX = 30, 700


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    # 1) Ingliz tili / Matematika — yopiladi
    closed = c.execute("""
        UPDATE courses SET is_active=0
        WHERE direction_id IN (SELECT id FROM directions WHERE slug IN ('ingliz-tili','matematika'))
          AND is_active=1
    """).rowcount
    if closed:
        print(f"  - {closed} ta kurs yopildi (Ingliz tili + Matematika)")

    # 2) Pulik kurslar narxini qayta hisoblash
    rows = c.execute(
        "SELECT id, level, lessons_count, is_pro_only FROM courses WHERE is_active=1 AND is_paid=1"
    ).fetchall()
    if rows:
        scores = []
        for _id, level, lessons_count, is_pro_only in rows:
            mult = LEVEL_MULT.get(level, 1.4)
            score = (lessons_count or 10) * mult
            if is_pro_only:
                score *= 1.15
            scores.append(score)
        mn, mx = min(scores), max(scores)
        span = (mx - mn) or 1

        updated = 0
        for (course_id, level, lessons_count, is_pro_only), score in zip(rows, scores):
            raw_price = PRICE_MIN + (score - mn) / span * (PRICE_MAX - PRICE_MIN)
            price = max(PRICE_MIN, min(PRICE_MAX, round(raw_price / 5) * 5))
            c.execute("UPDATE courses SET code_price=? WHERE id=?", (price, course_id))
            updated += 1
        print(f"  ~ {updated} ta pulik kurs narxi qayta hisoblandi (30-700 CODE oralig'ida, hajmiga qarab)")

    conn.commit()
    conn.close()
    print("✅ v58 Ingliz/Matematika yopildi + Kurslar narxi tuzatildi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
