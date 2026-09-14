#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHATS CYBER — Foydalanuvchi ID'larini ketma-ket raqamlashtirish (bir martalik)
================================================================================
Admin panelida (`/admin/users`) foydalanuvchilar ro'yxatidagi ICHKI raqam
(`users.id`, saytdagi "custom_id" bilan ADASHTIRMANG — bu ikkinchisi 7 xonali
premium ID tizimi) test/dev davrida o'chirilgan foydalanuvchilar tufayli
"teshik"larga ega bo'lib qolgan (masalan: 9, 153, ...). Bu skript ularni
QAYTA RAQAMLAYDI — 1 dan boshlab, hech qanday teshiksiz, ro'yxatga olingan
tartibda (eng qadimgi foydalanuvchi = 1).

DIQQAT — nega "0dan" emas "1dan": Ko'p joylarda kod `if user_id:` yoki
`if session.get("user_id"):` tekshiruvini ishlatadi — Python'da 0 soni
"yolg'on" (False) deb hisoblanadi, shuning uchun ID=0 bo'lgan foydalanuvchi
tizimda "tizimga kirmagan" deb noto'g'ri aniqlanishi mumkin edi. Shu sababli
xavfsiz minimal qiymat sifatida 1 tanlandi (ya'ni 0-dan emas, lekin
TESHIKSIZ, ketma-ket, 1-dan boshlab).

Bu skript avtomatik migratsiyalar ro'yxatiga (app.py) ULANMAGAN — faqat
qo'lda, ishga tushirishdan oldin, BIR MARTA bajariladi:

    python database/renumber_users_sequential.py --yes

Ishlatishdan OLDIN albatta backup oling: python migrate.py --backup
Bu skript ishlagandan so'ng, agar kimdir sayt sessiyasida tizimga kirgan
bo'lsa — uning sessiyasi eskirgan ID'ga ishora qilib qolishi mumkin,
shuning uchun barcha foydalanuvchilarni qayta kirishga (logout/login)
so'rash tavsiya etiladi.
"""
import sqlite3
import os
import sys

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _discover_user_fk_columns(conn) -> list[tuple[str, str]]:
    """Bazadagi barcha jadvallarni skanerlab, users(id)ga ishora qiluvchi
    barcha (jadval, ustun) juftliklarini avtomatik topadi — qo'lda ro'yxat
    yuritish shart emas, shuning uchun hech qanday jadval "unutilmaydi"."""
    c = conn.cursor()
    tables = [r[0] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()]
    refs = []
    for t in tables:
        for fk in c.execute(f'PRAGMA foreign_key_list("{t}")').fetchall():
            # fk columns: id, seq, table, from, to, on_update, on_delete, match
            if fk[2] == "users":
                refs.append((t, fk[3]))
    return refs


def renumber(db_path=None, confirm=True):
    db_path = db_path or DB
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = OFF")
    c = conn.cursor()

    users = c.execute("SELECT id FROM users ORDER BY created_at ASC, id ASC").fetchall()
    old_ids = [r[0] for r in users]
    if not old_ids:
        print("Foydalanuvchilar topilmadi — hech narsa qilinmadi.")
        conn.close()
        return

    mapping = {old_id: new_id for new_id, old_id in enumerate(old_ids, start=1)}
    already_sequential = all(old == new for old, new in mapping.items())
    if already_sequential:
        print("✅ Foydalanuvchi ID'lari allaqachon 1-dan boshlab ketma-ket — o'zgartirish kerak emas.")
        conn.close()
        return

    print("Quyidagi ID almashtirish amalga oshiriladi:")
    for old_id, new_id in mapping.items():
        if old_id != new_id:
            print(f"  #{old_id}  ->  #{new_id}")

    if confirm:
        answer = input("Davom etishga aminmisiz? ('HA' deb yozing): ").strip()
        if answer != "HA":
            print("❌ Bekor qilindi.")
            conn.close()
            return

    fk_refs = _discover_user_fk_columns(conn)
    print(f"\n{len(fk_refs)} ta bog'liq (jadval, ustun) juftligi topildi, {len(mapping)} ta foydalanuvchi qayta raqamlanadi...")

    try:
        conn.execute("BEGIN")
        # 1-BOSQICH: vaqtinchalik manfiy qiymatlarga o'tkazamiz — bu real
        # qiymatlar orasida to'qnashuv (UNIQUE constraint xatosi) bo'lishini oldini oladi.
        for old_id, new_id in mapping.items():
            c.execute("UPDATE users SET id=? WHERE id=?", (-new_id, old_id))
            for table, col in fk_refs:
                c.execute(f'UPDATE "{table}" SET "{col}"=? WHERE "{col}"=?', (-new_id, old_id))

        # 2-BOSQICH: manfiydan haqiqiy (musbat) yangi ID'ga o'tkazamiz.
        for new_id in mapping.values():
            c.execute("UPDATE users SET id=? WHERE id=?", (new_id, -new_id))
            for table, col in fk_refs:
                c.execute(f'UPDATE "{table}" SET "{col}"=? WHERE "{col}"=?', (new_id, -new_id))

        # AUTOINCREMENT hisoblagichini yangilaymiz — keyingi ro'yxatdan o'tgan
        # foydalanuvchi to'g'ridan-to'g'ri (max+1) ID olishi uchun.
        max_id = max(mapping.values())
        c.execute("UPDATE sqlite_sequence SET seq=? WHERE name='users'", (max_id,))
        if c.rowcount == 0:
            c.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('users', ?)", (max_id,))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"❌ Xatolik yuz berdi, hech narsa o'zgartirilmadi: {e}")
        conn.close()
        return

    # Tekshiruv — hech qanday "yetim" (orphan) yozuv qolmaganini tasdiqlaymiz.
    conn.execute("PRAGMA foreign_keys = ON")
    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()

    if problems:
        print(f"⚠️  DIQQAT: {len(problems)} ta bog'liqlik muammosi topildi — backup'dan tiklashni ko'rib chiqing:")
        for p in problems[:20]:
            print("   ", p)
    else:
        print(f"\n✅ {len(mapping)} ta foydalanuvchi muvaffaqiyatli qayta raqamlandi (1 dan {max_id} gacha, teshiksiz).")
        print("ℹ️  Agar kimdir hozir tizimga kirgan bo'lsa, uni qayta kirishga (logout/login) so'rang.")


if __name__ == "__main__":
    skip_confirm = "--yes" in sys.argv
    renumber(confirm=not skip_confirm)
