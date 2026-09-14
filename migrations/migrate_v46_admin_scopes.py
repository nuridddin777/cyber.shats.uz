"""
SHATS CYBER — MIGRATE v46: 3 ta admin darajasi (Super Admin + 2 ta yo'nalish admini)
================================================================================
- admin_direction_scope: qaysi admin qaysi yo'nalish(lar)ni boshqarishi mumkinligi
  (ko'p-ko'pga, super_admin uchun bo'sh — u cheklovsiz).
- Eski admin (id=1) allaqachon 'super_admin' — o'zgarmaydi.
- 2 ta YANGI oddiy admin yaratiladi, 18 ta yo'nalish ular orasida 9/9 bo'linadi:
    Admin A — "Dasturlash va Tizimlar": web-dev, python, javascript, cpp,
              mobile-dev, networking, database, cloud, devops
    Admin B — "Xavfsizlik, Data va Biznes": cyber-security, ai-ml, data-science,
              smm, targetolog, logistika, ingliz-tili, matematika, office
- Bu ikkala admin CODE tanga berish/olish, foydalanuvchi tarifini (reja) o'zgartirish
  va boshqa admin qo'shish huquqiga EGA EMAS — bu cheklovlar route darajasida
  (@super_admin_required) amalga oshiriladi, shu migratsiya faqat rol/yo'nalish
  ma'lumotlarini tayyorlaydi.
- Parollar HECH QACHON ochiq (plaintext) holda saqlanmaydi — faqat hash. Shu sababli
  super admin boshqa adminning parolini "ko'ra olmaydi", faqat RESET (yangi parol
  belgilash) qila oladi — bu route alohida qo'shiladi.
"""
import sqlite3
import os
import secrets
import string

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

NEW_ADMINS = [
    {
        "ism": "Yo'nalish", "familiya": "Admin A", "email": "admin.a@shatscyber.uz",
        "directions": ["web-dev", "python", "javascript", "cpp", "mobile-dev",
                        "networking", "database", "cloud", "devops"],
    },
    {
        "ism": "Yo'nalish", "familiya": "Admin B", "email": "admin.b@shatscyber.uz",
        "directions": ["cyber-security", "ai-ml", "data-science", "smm",
                        "targetolog", "logistika", "ingliz-tili", "matematika", "office"],
    },
]


def _table_exists(c, name):
    return c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _gen_password(n=10):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def _gen_custom_id(c):
    import random
    for _ in range(2000):
        cid = str(random.randint(1_000_000, 9_999_999))
        if c.execute("SELECT id FROM users WHERE custom_id=?", (cid,)).fetchone():
            continue
        if c.execute("SELECT id FROM premium_ids WHERE custom_id=?", (cid,)).fetchone():
            continue
        return cid
    raise RuntimeError("custom_id topilmadi")


def _gen_admin_id(c):
    import random
    for _ in range(500):
        cid = str(random.randint(1000, 9999))
        if not c.execute("SELECT id FROM users WHERE admin_id=?", (cid,)).fetchone():
            return cid
    raise RuntimeError("admin_id topilmadi")


def migrate(db_path=None):
    from werkzeug.security import generate_password_hash

    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "admin_direction_scope"):
        c.execute("""
            CREATE TABLE admin_direction_scope (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER NOT NULL REFERENCES users(id),
                direction_id INTEGER NOT NULL REFERENCES directions(id),
                assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(admin_user_id, direction_id)
            )
        """)
        print("  + jadval: admin_direction_scope")

    created_credentials = []

    for spec in NEW_ADMINS:
        existing = c.execute("SELECT id FROM users WHERE email=?", (spec["email"],)).fetchone()
        if existing:
            admin_user_id = existing[0]
        else:
            password = _gen_password()
            pw_hash = generate_password_hash(password)
            custom_id = _gen_custom_id(c)
            admin_id = _gen_admin_id(c)
            c.execute(
                """INSERT INTO users (ism, familiya, email, password_hash, role, custom_id,
                                       admin_id, plan, email_verified)
                   VALUES (?,?,?,?,'admin',?,?, 'enterprise', 1)""",
                (spec["ism"], spec["familiya"], spec["email"], pw_hash, custom_id, admin_id)
            )
            admin_user_id = c.lastrowid
            created_credentials.append((spec["email"], password, admin_id))
            print(f"  + yangi admin: {spec['email']} (Admin ID #{admin_id})")

        for slug in spec["directions"]:
            d = c.execute("SELECT id FROM directions WHERE slug=?", (slug,)).fetchone()
            if not d:
                continue
            c.execute(
                "INSERT OR IGNORE INTO admin_direction_scope (admin_user_id, direction_id) VALUES (?,?)",
                (admin_user_id, d[0])
            )

    conn.commit()
    conn.close()

    if created_credentials:
        print("\n  ============================================================")
        print("  YANGI ADMIN HISOBLARI — BULARNI DARHOL SAQLANG VA XAVFSIZ YETKAZING:")
        for email, pw, admin_id in created_credentials:
            print(f"    Email: {email}   Parol: {pw}   Admin ID: #{admin_id}")
        print("  Birinchi kirishdan so'ng parolni albatta o'zgartirishni tavsiya qilamiz.")
        print("  ============================================================\n")

    print("✅ v46 Uch darajali admin tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
