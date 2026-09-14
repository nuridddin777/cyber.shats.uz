"""
SHATS CYBER V2 — MIGRATE v30: Edu <-> G'azna (Treasury) integratsiyasi
=========================================================================
Talab: "edu qismidagi code tangalar haridi va harajati G'aznaga ulanadi
huddi SHATS CYBERGA o'xshab".

Mavjud tizimda (coins.py -> _treasury_fund_in) foydalanuvchi biror
xizmatga (Pro, kurs, AI, o'tkazma komissiyasi) coin sarflaganda bu summa
YAGONA `treasury_fund` jamg'armasiga qo'shiladi. Bu migratsiya Edu
tashkilotlari (maktab/texnikum/markaz) uchun ham AYNAN SHU jamg'armadan
foydalanishni ta'minlaydi — alohida "Edu g'aznasi" YARATILMAYDI.

O'zgarish:
  - treasury_fund_log jadvaliga ixtiyoriy `edu_org_id` ustuni qo'shiladi
    (qaysi Edu tashkiloti sabab bo'lganini kuzatish uchun; user_id NULL qoladi,
    chunki tashkilot/o'qituvchi/o'quvchi `users` jadvalida emas).

Bu migratsiya v28 dan keyin ishga tushirilishi kerak (treasury_fund_log
allaqachon mavjud bo'lishi kerak — u asosiy schema.sql da bor).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    exists = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='treasury_fund_log'"
    ).fetchone()
    if not exists:
        raise RuntimeError("treasury_fund_log jadvali topilmadi — asosiy schema.sql ishga tushirilganiga ishonch hosil qiling.")

    try:
        c.execute("ALTER TABLE treasury_fund_log ADD COLUMN edu_org_id INTEGER DEFAULT NULL REFERENCES edu_organizations(id)")
    except sqlite3.OperationalError:
        pass  # ustun allaqachon mavjud

    # treasury_fund yagona qator (id=1) mavjudligiga ishonch hosil qilamiz
    c.execute("INSERT OR IGNORE INTO treasury_fund (id, balance) VALUES (1, 0)")

    conn.commit()
    conn.close()
    print("✅ v30 Edu <-> G'azna integratsiyasi migratsiyasi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
