# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v56: ID tizimi qayta qurildi
================================================================================
- Umumiy "istalgan ID" premium bozori TO'XTATILDI — endi FAQAT quyidagi
  20 ta chiroyli ID sotiladi yoki auktsionga qo'yiladi (120-777 CODE oralig'ida):
    0000000, 1111111...9999999 (10 ta bir xil raqamli)
    1234567 (ketma-ket)
    0000001...0000009 (9 ta "deyarli nol")
  Boshqa barcha (avval mavjud bo'lgan, hali sotilmagan) "premium" IDlar
  ro'yxatdan olib tashlanadi.
- users.id_change_count — oddiy (premium bo'lmagan) ID o'zgartirish necha marta
  qilinganini hisoblaydi — narx AVTOMATIK oshib boradi: 1-chi marta 1 CODE,
  2-chi marta 2 CODE, 3-chi va undan keyingi har safar 3 CODE (keids.py:
  set_user_id ichida ishlatiladi).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

CURATED_IDS = [
    ("0000000", "quad7", 777), ("7777777", "quad7", 750), ("1234567", "sequential", 720),
    ("9999999", "quad7", 680), ("8888888", "quad7", 640), ("6666666", "quad7", 600),
    ("5555555", "quad7", 560), ("4444444", "quad7", 520), ("3333333", "quad7", 480),
    ("2222222", "quad7", 440), ("1111111", "quad7", 400),
    ("0000001", "near_zero", 320), ("0000002", "near_zero", 290), ("0000003", "near_zero", 260),
    ("0000004", "near_zero", 230), ("0000005", "near_zero", 200), ("0000006", "near_zero", 175),
    ("0000007", "near_zero", 155), ("0000008", "near_zero", 137), ("0000009", "near_zero", 120),
]


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _column_exists(c, "users", "id_change_count"):
        c.execute("ALTER TABLE users ADD COLUMN id_change_count INTEGER DEFAULT 0")
        print("  + users.id_change_count")

    curated_id_list = [cid for cid, _, _ in CURATED_IDS]

    # Sotilmagan, kurатsiya ro'yxatida bo'lmagan eski "premium" IDlarni tozalaymiz
    # (SOTILGANLARGA tegilmaydi — tarixiy yozuv sifatida qoladi)
    placeholders = ",".join("?" * len(curated_id_list))
    removed = c.execute(
        f"DELETE FROM premium_ids WHERE status='available' AND custom_id NOT IN ({placeholders})",
        curated_id_list
    ).rowcount
    if removed:
        print(f"  - {removed} ta kuratsiyadan tashqari eski premium ID o'chirildi")

    updated, inserted = 0, 0
    for cid, id_type, price in CURATED_IDS:
        existing = c.execute("SELECT id, status FROM premium_ids WHERE custom_id=?", (cid,)).fetchone()
        if existing:
            # DIQQAT: avval bu yerda HAR SERVER ISHGA TUSHGANDA narx qayta
            # yozilib turardi (garchi admin panelidan boshqa narx qo'ygan
            # bo'lsa ham) — bu "narxni o'zgartirsam yana eskisiga qaytadi"
            # degan shikoyatning aynan sababi edi! Endi migratsiya faqat
            # BIR MARTA (qator yaratilganda) narx qo'yadi, keyin unga
            # HECH QACHON qayta tegmaydi — admin qo'ygan narx doim saqlanadi.
            pass
        else:
            owned = c.execute("SELECT id FROM users WHERE custom_id=?", (cid,)).fetchone()
            if not owned:
                c.execute(
                    "INSERT INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
                    (cid, id_type, price)
                )
                inserted += 1

    conn.commit()
    conn.close()
    print(f"  + {inserted} ta yangi kuratsiyalangan ID qo'shildi, {updated} tasi narxlandi (120-777 CODE)")
    print("✅ v56 ID tizimi qayta qurildi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
