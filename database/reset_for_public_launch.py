#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHATS CYBER — LOYIHANI OMMAGA TAQDIM ETISH UCHUN BIR MARTALIK RESET SKRIPTI
================================================================================
DIQQAT: Bu skript ATAYLAB avtomatik migratsiyalar ro'yxatiga (app.py) ULANMAGAN
va har safar server ishga tushganda ISHLAMAYDI. Uni FAQAT QO'LDA, loyihani
haqiqiy foydalanuvchilarga ochishdan OLDIN, BIR MARTA ishga tushiring:

    python database/reset_for_public_launch.py

Bu skript nima qiladi:
  1. G'azna jamg'armasi balansini (treasury_fund) 0'ga tushiradi
  2. G'azna jamg'arma tarixini (treasury_fund_log) tozalaydi
  3. BARCHA foydalanuvchilarning CODE balansini (users.code_balance) 0'ga
     tushiradi (test/dev davrida yig'ilgan sun'iy summalarni tozalash uchun)
  4. CODE tranzaksiyalar tarixini (code_transactions) tozalaydi
  5. Maxsus Topshiriq (KRIPTIKIS) progressini har bir foydalanuvchi uchun
     1-bosqichga qaytaradi (endi 50 bosqichli tizim ishga tushgani sababli)

NIMA O'ZGARMAYDI (ataylab):
  - Foydalanuvchilarning email/parol/kurs progressi/sertifikatlari SAQLANADI
  - custom_id / VIP ID tayinlovlari SAQLANADI (agar admin qo'lda bergan bo'lsa)
  - Tarif (plan) holati SAQLANADI

Ishlatishdan OLDIN albatta backup oling:  python migrate.py --backup
"""
import sqlite3
import os
import sys

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def reset(db_path=None, confirm=True):
    db_path = db_path or DB
    if confirm:
        print("⚠️  DIQQAT: bu amal QAYTARIB BO'LMAYDI (backup olinmagan bo'lsa).")
        print(f"    Baza: {db_path}")
        answer = input("    Davom etishga aminmisiz? ('HA' deb yozing): ").strip()
        if answer != "HA":
            print("❌ Bekor qilindi.")
            return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 1) G'azna jamg'armasi
    c.execute("UPDATE treasury_fund SET balance=0, updated_at=datetime('now') WHERE id=1")
    print("  ✓ G'azna jamg'arma balansi 0'ga tushirildi")

    # 2) G'azna tarixi
    try:
        c.execute("DELETE FROM treasury_fund_log")
        print("  ✓ G'azna jamg'arma tarixi tozalandi")
    except sqlite3.OperationalError:
        pass

    # 3) Foydalanuvchi CODE balanslari
    c.execute("UPDATE users SET code_balance=0")
    print("  ✓ Barcha foydalanuvchilarning CODE balansi 0'ga tushirildi")

    # 3b) AI haftalik obuna muddatlarini ham tozalaymiz (agar ustun mavjud bo'lsa)
    c.execute("PRAGMA table_info(users)")
    if "ai_sub_expires_at" in [r[1] for r in c.fetchall()]:
        c.execute("UPDATE users SET ai_sub_expires_at=NULL")
        print("  ✓ AI haftalik obuna muddatlari tozalandi")

    # 4) CODE tranzaksiyalar tarixi
    try:
        c.execute("DELETE FROM code_transactions")
        print("  ✓ CODE tranzaksiyalar tarixi tozalandi")
    except sqlite3.OperationalError:
        pass

    # 5) Maxsus Topshiriq progressini qayta boshlash
    try:
        c.execute(
            "UPDATE user_special_challenge_progress SET current_level=1, "
            "level1_unlocked_at=NULL, level2_solved_at=NULL, level3_solved_at=NULL, "
            "updated_at=datetime('now')"
        )
        c.execute("DELETE FROM special_challenge_attempts")
        print("  ✓ Maxsus Topshiriq (KRIPTIKIS) progressi 1-bosqichga qaytarildi")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()
    print("\n✅ Loyiha ommaga taqdim etish uchun tayyor — barcha CODE balanslar 0 dan boshlanadi!")


if __name__ == "__main__":
    skip_confirm = "--yes" in sys.argv
    reset(confirm=not skip_confirm)
