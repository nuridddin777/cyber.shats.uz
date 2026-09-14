# -*- coding: utf-8 -*-
"""
CYBER SHATS — SERVER TEKSHIRUV SKRIPTI
================================================================================
BU FAYLNI SIZNING HAQIQIY SERVERINGIZDA ishga tushiring:

    python3 diagnose.py

Chiqishning HAMMASINI (boshidan oxirigacha) nusxalab, menga yuboring.
Bu skript hech narsani o'zgartirmaydi — faqat TEKSHIRADI.
"""
import sys
import os

OK = "OK"
YOQ = "YOQ!!!"

print("=" * 70)
print("CYBER SHATS - SERVER TEKSHIRUVI")
print("=" * 70)

print("\n[1] Python versiyasi: " + sys.version)
if sys.version_info < (3, 10):
    print("    OGOHLANTIRISH: Python 3.10+ tavsiya etiladi!")

print("\n[2] Kerakli paketlar:")
required_packages = ["flask", "requests", "dotenv", "PIL"]
for pkg in required_packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, "__version__", "versiya nomalum")
        print("    " + OK + ": " + pkg + " (" + str(version) + ")")
    except ImportError as e:
        print("    " + YOQ + ": " + pkg + " ORNATILMAGAN! (" + str(e) + ")")

print("\n[3] .env fayli:")
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    print("    " + OK + ": .env fayli topildi: " + env_path)
    from dotenv import load_dotenv
    load_dotenv(env_path)
    critical_vars = ["SECRET_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_CHAT_ID", "SITE_BASE_URL"]
    for var in critical_vars:
        val = os.environ.get(var, "")
        if val:
            masked = val[:8] + "..." if len(val) > 8 else val
            print("       " + OK + ": " + var + " = " + masked)
        else:
            print("       " + YOQ + ": " + var + " BOSH/YOQ")
else:
    print("    " + YOQ + ": .env FAYLI TOPILMADI: " + env_path)
    print("       BU JIDDIY MUAMMO BOLISHI MUMKIN!")

print("\n[4] Malumotlar bazasi:")
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "cyber_shats.db")
seed_path = db_path + ".SEED"
print("    Kutilgan joy: " + db_path)
db_exists = os.path.exists(db_path)
seed_exists = os.path.exists(seed_path)
print("    cyber_shats.db mavjud: " + (OK if db_exists else YOQ))
print("    cyber_shats.db.SEED mavjud: " + (OK if seed_exists else YOQ))

if db_exists:
    import sqlite3
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print("    Jadvallar soni: " + str(len(tables)))

        critical_tables = ['users', 'telegram_users', 'bot_purchase_requests', 'treasury_fund',
                           'premium_ids', 'profile_frames', 'id_reservations', 'design_orders']
        print("\n    Muhim jadvallar tekshiruvi:")
        for t in critical_tables:
            exists = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,)
            ).fetchone()
            print("       " + (OK if exists else YOQ) + ": " + t)

        print("\n    users jadvalidagi muhim ustunlar:")
        cur.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in cur.fetchall()]
        for col in ['login_streak', 'last_login_date', 'active_frame', 'custom_id', 'plan_expires_at']:
            print("       " + (OK if col in user_cols else YOQ) + ": users." + col)

        users_count = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        print("\n    Jami foydalanuvchilar: " + str(users_count))

        journal_mode = cur.execute("PRAGMA journal_mode").fetchone()
        print("    Joriy journal_mode: " + str(journal_mode[0] if journal_mode else "nomalum"))
        conn.close()
    except Exception as e:
        print("    XATO: BAZAGA ULANISHDA MUAMMO: " + str(e))
else:
    print("    OGOHLANTIRISH: baza hali yaratilmagan")

print("\n[5] Muhim fayllar:")
base_dir = os.path.dirname(os.path.abspath(__file__))
critical_files = [
    "app.py", "telegram_bot.py", "webapp_routes.py", "webapp_auth.py",
    "auth.py", "db.py", "ids.py", "coins.py", "frames_shop.py",
    "templates/webapp/shell.html", "static/css/base.css",
]
for f in critical_files:
    full = os.path.join(base_dir, f)
    print("    " + (OK if os.path.exists(full) else YOQ) + ": " + f)

print("\n[6] app.py ni import qilishga urinish:")
sys.path.insert(0, base_dir)
try:
    import app as app_module
    print("    " + OK + ": app.py MUVAFFAQIYATLI import qilindi!")
    print("    Royxatdan otgan marshrutlar soni: " + str(len(list(app_module.app.url_map.iter_rules()))))
except Exception as e:
    print("    XATO: app.py IMPORT QILISHDA XATO:")
    import traceback
    traceback.print_exc()

print("\n[7] Yozish huquqlari:")
write_dirs = ["static/uploads", "static/webapp_receipts", "static/bot_images", "database"]
for d in write_dirs:
    full = os.path.join(base_dir, d)
    try:
        os.makedirs(full, exist_ok=True)
        writable = os.access(full, os.W_OK)
        print("    " + (OK if writable else YOQ) + ": " + d)
    except Exception as e:
        print("    XATO: " + d + " -> " + str(e))

print("\n" + "=" * 70)
print("TEKSHIRUV TUGADI - YUQORIDAGI HAMMA MATNNI NUSXALAB YUBORING")
print("=" * 70)
