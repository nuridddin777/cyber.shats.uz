"""
SHATS CYBER — MIGRATE v36: Telegram bot takomillashtirish
================================================================================
1. telegram_users jadvaliga doimiy bog'lanish ustunlari qo'shiladi
   (linked_site_user_id, linked_custom_id) — foydalanuvchi ID'ni bir marta
   tasdiqlagach, bot buni ESLAB QOLADI va keyingi xaridlarda qayta so'ramaydi.

2. bot_purchase_requests jadvaliga `plan` ustuni qo'shiladi — endi bot orqali
   CODE/kurslardan tashqari TARIFLAR (Pro/Cyber Pro/VIP/HackerLab) ham
   sotiladi.

3. Code paket narxlari (pricing_settings: code_pack_N) 1 dan 100 gacha
   to'liq to'ldiriladi (rasmga mos: har doim 1 CODE = 10 000 so'm).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

# Rasmdagi to'liq paket ro'yxati (1 CODE = 10 000 so'm bo'yicha barchasi)
FULL_PACKAGE_AMOUNTS = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50,
                        55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
RATE = 10_000


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in c.fetchall())


def _table_exists(c, name):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return c.fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if _table_exists(c, "telegram_users"):
        # DIQQAT: `linked_user_id` ustuni ALLAQACHON v8 migratsiyasida
        # ("saytdagi foydalanuvchi (ID orqali bog'lansa)") yaratilgan edi,
        # lekin hech qayerda ISHLATILMAGAN edi (o'lik ustun). Endi aynan
        # shu ustunni ishlatamiz — qayta-qayta yangi ustun ochib
        # ma'lumotlarni tarqatib yubormaslik uchun.
        if not _column_exists(c, "telegram_users", "linked_user_id"):
            c.execute("ALTER TABLE telegram_users ADD COLUMN linked_user_id INTEGER DEFAULT NULL")
        if not _column_exists(c, "telegram_users", "linked_custom_id"):
            c.execute("ALTER TABLE telegram_users ADD COLUMN linked_custom_id TEXT DEFAULT NULL")

    if _table_exists(c, "bot_purchase_requests"):
        if not _column_exists(c, "bot_purchase_requests", "plan"):
            c.execute("ALTER TABLE bot_purchase_requests ADD COLUMN plan TEXT DEFAULT ''")

    for amount in FULL_PACKAGE_AMOUNTS:
        key = f"code_pack_{amount}"
        c.execute("SELECT value FROM pricing_settings WHERE key=?", (key,))
        if not c.fetchone():
            c.execute("INSERT INTO pricing_settings (key, value) VALUES (?,?)",
                      (key, str(amount * RATE)))

    conn.commit()
    conn.close()
    print("✅ v36 Telegram bot: ID eslab qolish + tarif sotuvi + to'liq paket narxlari muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
