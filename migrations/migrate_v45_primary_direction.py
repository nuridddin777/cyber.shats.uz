"""
SHATS CYBER — MIGRATE v45: Majburiy "asosiy yo'nalish" tanlash
================================================================================
Muammo: platformada 18 ta IT yo'nalishi (directions) va ularga tegishli kurslar
bor, lekin ro'yxatdan o'tgan o'quvchi hech qachon "menga qaysi yo'nalish mos"
deb so'ralmaydi — to'g'ridan-to'g'ri hamma narsa (18 ta yo'nalish, barcha
kurslar) bir vaqtda ochiladi va o'quvchi tartibsiz "sayr qiladi".
(`users.selected_direction_id` degan ustun bor edi, lekin u FAQAT Hacker Lab
Pro bo'limi uchun ishlatilardi, umumiy o'quv oqimiga bog'lanmagan edi.)

Bu migratsiya qo'shadi:
  - users.primary_direction_id : o'quvchining MAJBURIY tanlagan asosiy yo'nalishi
                                  (ro'yxatdan o'tgach darhol so'raladi, shundan
                                  keyingina /courses va boshqa sahifalarga kirish
                                  mumkin bo'ladi — /choose-direction sahifasi orqali)
  - users.direction_chosen_at   : qachon tanlangani (statistikadan tashqari, admin
                                  panelda "necha foizi hali tanlamagan" ko'rsatish uchun)

DIQQAT: bu ataylab `selected_direction_id`dan ALOHIDA ustun — chunki
`selected_direction_id` Hacker Lab uchun 3 ta yo'nalishni (smm, targetolog,
logistika — bularda terminal-simulyatsiya yo'q) chiqarib tashlaydi, ikkalasini
bitta ustunga birlashtirish Hacker Lab logikasini buzardi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _column_exists(c, "users", "primary_direction_id"):
        c.execute("ALTER TABLE users ADD COLUMN primary_direction_id INTEGER DEFAULT NULL REFERENCES directions(id)")
        print("  + users.primary_direction_id")

    if not _column_exists(c, "users", "direction_chosen_at"):
        c.execute("ALTER TABLE users ADD COLUMN direction_chosen_at TEXT DEFAULT NULL")
        print("  + users.direction_chosen_at")

    conn.commit()
    conn.close()
    print("✅ v45 Majburiy yo'nalish tanlash — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
