#!/usr/bin/env python3
"""
CYBER SHATS — Oylik guruh/kanal soliqlarini yechuvchi rejalashtiruvchi skripti

QANDAY ISHGA TUSHIRISH KERAK (server administratori uchun):
Bu skript avtomatik ishlamaydi — uni KUNIGA BIR MARTA (masalan har kuni
soat 03:00 da) ishga tushirish uchun cron job qo'shishingiz kerak:

    crontab -e
    # quyidagi qatorni qo'shing:
    0 3 * * * cd /path/to/cyber-shats && /usr/bin/python3 run_monthly_tax_charge.py >> logs/tax_charge.log 2>&1

Yoki systemd timer / Render/Railway Cron Job xizmatidan foydalaning.

DIQQAT: app.py ishga tushganda ham har bir admin panel ochilishida
"xavfsizlik tarmog'i" sifatida bir marta chaqiriladi (agar cron
sozlanmagan bo'lsa ham, admin panelga tashrif buyurilganda soliqlar
tekshiriladi) — lekin bu ISHONCHLI usul EMAS, cron albatta sozlanishi kerak.
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app as app_module
import social


def main():
    with app_module.app.app_context():
        result = social.charge_all_group_channel_taxes()
        print(f"[{datetime.datetime.now()}] Yechildi: {len(result['charged'])}, Xato: {len(result['failed'])}")
        for c in result["charged"]:
            print(f"  ✅ {c['table']}#{c['id']} — {c['amount']} CODE")
        for f in result["failed"]:
            print(f"  ⚠️ {f['table']}#{f['id']} — {f['amount']} CODE (balans yetarli emas)")


if __name__ == "__main__":
    main()
