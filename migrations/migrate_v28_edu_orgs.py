"""
SHATS CYBER V2 — MIGRATE v28: EDU 2.0 tashkilot arxitekturasi
================================================================
Bu migratsiya texnik topshiriqda tasvirlangan yangi Edu tizimini qo'shadi:

  - edu_organizations      : Maktab / Texnikum / O'quv markazi (ro'yxatdan o'tish,
                              login/parol, @username, tarif, coin balansi, holat)
  - edu_org_id_counters    : har bir tashkilot uchun ALOHIDA ketma-ket
                              o'qituvchi (2 xonali) va o'quvchi (5 xonali) ID hisoblagichi
  - edu_subjects           : tashkilot turiga qarab fanlar/yo'nalishlar ro'yxati
                              (maktab fanlari, texnikum fanlari, markaz uchun 12 yo'nalish)
  - edu_org_groups         : tashkilot ichidagi guruhlar (sinf/guruh), tashkilot o'zi yaratadi
  - edu_teachers           : o'qituvchilar (login formati: <login>@<org_username>)
  - edu_students           : o'quvchilar (login formati: <login>@<org_username>)
  - edu_tariffs            : Maktab/Texnikum/Markaz uchun Standart va Pro tariflar,
                              limitlar va qo'shimcha slot narxlari
  - edu_coin_commission    : Code(tanga) o'tkazmalarida komissiya jadvali (5..200 oralig'i)
  - edu_gift_code_usage    : "5 ta tanga bepul jo'natish" — har foydalanuvchi uchun
                              1 martalik limit va tarif uzaytirilganda qayta ochilishi

Eski `schools` / `school_subscriptions` jadvallariga tegilmaydi (orqaga moslik uchun),
yangi tizim ular bilan yonma-yon ishlaydi va keyingi bosqichda ko'chirish (data-migration)
skripti bilan bog'lanadi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    # ------------------------------------------------------------------
    # 1) Tashkilotlar: Maktab / Texnikum / O'quv markazi
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_type TEXT NOT NULL CHECK(org_type IN ('maktab','texnikum','oquv_markazi')),
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,          -- masalan '18idum' -> login @18idum
        region_id INTEGER,
        district_id INTEGER,
        phone TEXT DEFAULT '',
        login TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT DEFAULT '',
        telegram_user TEXT DEFAULT '',           -- ixtiyoriy, @ bilan
        tarif_code TEXT DEFAULT '',              -- edu_tariffs.code ga ishora
        is_active INTEGER DEFAULT 0,             -- tarif sotib olinmaguncha 0 (panellar yopiq)
        coin_balance INTEGER DEFAULT 0,
        monitoring_panel_enabled INTEGER DEFAULT 0,
        support_panel_enabled INTEGER DEFAULT 0,
        subscription_started_at TEXT,
        subscription_expires_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(region_id) REFERENCES regions(id),
        FOREIGN KEY(district_id) REFERENCES districts(id)
    )""")

    # ------------------------------------------------------------------
    # 2) Har tashkilot uchun ALOHIDA ID hisoblagich (aralashib ketmasligi uchun)
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_org_id_counters (
        org_id INTEGER PRIMARY KEY,
        teacher_seq INTEGER DEFAULT 0,     -- oxirgi berilgan o'qituvchi tartib raqami
        student_seq INTEGER DEFAULT 0,     -- oxirgi berilgan o'quvchi tartib raqami
        FOREIGN KEY(org_id) REFERENCES edu_organizations(id)
    )""")

    # ------------------------------------------------------------------
    # 3) Fanlar / yo'nalishlar (tashkilot turiga qarab)
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_type TEXT NOT NULL,
        name TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0,
        UNIQUE(org_type, name)
    )""")

    # ------------------------------------------------------------------
    # 4) Guruhlar (sinf/guruh) — tashkilot o'zi yaratadi
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_org_groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER NOT NULL,
        name TEXT NOT NULL,                 -- masalan "9-A", "IT-21"
        subject_id INTEGER,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(org_id) REFERENCES edu_organizations(id),
        FOREIGN KEY(subject_id) REFERENCES edu_subjects(id)
    )""")

    # ------------------------------------------------------------------
    # 5) O'qituvchilar
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER NOT NULL,
        teacher_number TEXT NOT NULL,        -- 2 xonali, org ichida ketma-ket ('01','02'...)
        familiya TEXT NOT NULL,
        ism TEXT NOT NULL,
        subject_id INTEGER,
        login TEXT NOT NULL,                 -- @org_username dan OLDINGI qism
        full_login TEXT UNIQUE NOT NULL,      -- login@org_username (tizimga kirish uchun)
        password_hash TEXT NOT NULL,
        region_id INTEGER,
        district_id INTEGER,
        coin_balance INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        is_extra_slot INTEGER DEFAULT 0,      -- tarif limitidan tashqari, coin evaziga qo'shilgan
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(org_id, teacher_number),
        FOREIGN KEY(org_id) REFERENCES edu_organizations(id),
        FOREIGN KEY(subject_id) REFERENCES edu_subjects(id)
    )""")

    # ------------------------------------------------------------------
    # 6) O'quvchilar
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER NOT NULL,
        student_number TEXT NOT NULL,        -- 5 xonali, org ichida ketma-ket ('00001'...)
        familiya TEXT NOT NULL,
        ism TEXT NOT NULL,
        group_id INTEGER,
        login TEXT NOT NULL,
        full_login TEXT UNIQUE NOT NULL,      -- login@org_username
        password_hash TEXT NOT NULL,
        region_id INTEGER,
        district_id INTEGER,
        coin_balance INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(org_id, student_number),
        FOREIGN KEY(org_id) REFERENCES edu_organizations(id),
        FOREIGN KEY(group_id) REFERENCES edu_org_groups(id)
    )""")

    # ------------------------------------------------------------------
    # 7) Tariflar: Maktab (Standart/Pro), Texnikum (Standart/Pro), Markaz (Standart/Pro)
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_tariffs (
        code TEXT PRIMARY KEY,
        org_type TEXT NOT NULL,
        display_name TEXT NOT NULL,
        max_teachers INTEGER NOT NULL,
        max_students INTEGER NOT NULL,
        max_extra_teachers INTEGER DEFAULT 0,     -- limitdan tashqari qo'shish mumkun bo'lgan soni
        extra_teacher_coin_cost INTEGER DEFAULT 5,-- 1 ta qo'shimcha o'qituvchi = necha coin
        extra_student_group_size INTEGER DEFAULT 5,-- har necha o'quvchiga 1 coin
        extra_student_coin_cost INTEGER DEFAULT 1,
        has_monitoring_panel INTEGER DEFAULT 0,
        has_support_panel INTEGER DEFAULT 0,
        price_coins INTEGER DEFAULT 0
    )""")

    # ------------------------------------------------------------------
    # 8) Coin (tanga) o'tkazma komissiya jadvali
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_coin_commission (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        min_amount INTEGER NOT NULL,
        max_amount INTEGER NOT NULL,
        commission_coins INTEGER NOT NULL
    )""")

    # ------------------------------------------------------------------
    # 9) "5 ta tanga bepul jo'natish" — 1 martalik limit
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_gift_code_usage (
        user_type TEXT NOT NULL,      -- 'teacher' | 'student'
        user_id INTEGER NOT NULL,
        remaining_gifts INTEGER DEFAULT 1,   -- boshida 1 marta beriladi
        updated_at TEXT DEFAULT (datetime('now')),
        PRIMARY KEY(user_type, user_id)
    )""")

    # ==================================================================
    # SEED: Tariflar
    # ==================================================================
    tariffs = [
        # code, org_type, display_name, max_t, max_s, max_extra_t, extra_t_cost,
        # extra_s_group, extra_s_cost, monitoring, support, price_coins
        ("maktab_standart", "maktab", "Maktab — Standart", 2, 600, 4, 5, 5, 1, 0, 0, 1200),
        ("maktab_pro",      "maktab", "Maktab — Pro",      6, 1080, 0, 5, 10, 1, 1, 1, 1900),
        ("texnikum_standart", "texnikum", "Texnikum — Standart", 4, 800, 6, 5, 5, 1, 0, 0, 1200),
        ("texnikum_pro",      "texnikum", "Texnikum — Pro",      10, 1500, 0, 5, 10, 1, 1, 1, 1900),
        ("markaz_standart", "oquv_markazi", "O'quv markazi — Standart", 3, 500, 5, 5, 5, 1, 0, 0, 1200),
        ("markaz_pro",      "oquv_markazi", "O'quv markazi — Pro",      8, 1200, 0, 5, 10, 1, 1, 1, 1900),
    ]
    for t in tariffs:
        c.execute("""INSERT OR IGNORE INTO edu_tariffs
            (code, org_type, display_name, max_teachers, max_students, max_extra_teachers,
             extra_teacher_coin_cost, extra_student_group_size, extra_student_coin_cost,
             has_monitoring_panel, has_support_panel, price_coins)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", t)

    # NOTE: Standart=1200, Pro=1900 CODE — boshlang'ich narxlar. Bularni
    # SHATS CYBER admin panelidan ("Edu tashkilotlar" bo'limi) istalgan
    # vaqtda o'zgartirish mumkin (qarang: edu_orgs_routes.py -> admin_update_tariff_price).

    # ==================================================================
    # SEED: Komissiya jadvali (texnik topshiriqdagi jadval bo'yicha)
    # ==================================================================
    commission_table = [
        (1, 9, 0),      # 5 tagacha (va undan kichik) — komissiyasiz
        (10, 19, 1),
        (20, 29, 2),
        (30, 39, 3),
        (40, 49, 4),
        (50, 59, 5),
        (60, 69, 6),
        (70, 79, 7),
        (80, 89, 8),
        (90, 99, 9),
        (100, 200, 15),
    ]
    c.execute("DELETE FROM edu_coin_commission")
    for lo, hi, com in commission_table:
        c.execute("INSERT INTO edu_coin_commission (min_amount, max_amount, commission_coins) VALUES (?,?,?)",
                  (lo, hi, com))

    # ==================================================================
    # SEED: Fanlar / yo'nalishlar
    # ==================================================================
    maktab_fanlari = [
        "Informatika", "Matematika", "Ona tili", "Ingliz tili", "Fizika",
        "Kimyo", "Biologiya", "Tarix", "Geografiya", "Chizmachilik",
    ]
    texnikum_fanlari = [
        "Informatika", "Axborot xavfsizligi", "Kompyuter tarmoqlari",
        "Kompyuter arxitekturasi va ofis jihozlariga xizmat ko'rsatish",
        "Dasturlash asoslari", "3D dizayn", "Web dasturlash",
        "Ma'lumotlar bazasi", "Operatsion tizimlar", "Raqamli elektronika",
    ]
    markaz_yonalishlari = [
        "Dasturlash", "Kiberxavfsizlik", "Web dizayn", "Mobil ilova yaratish",
        "Grafik dizayn", "3D modellashtirish", "Robototexnika", "SMM",
        "Ingliz tili", "Kompyuter savodxonligi", "Data Science", "Video montaj",
    ]

    for i, name in enumerate(maktab_fanlari):
        c.execute("INSERT OR IGNORE INTO edu_subjects (org_type, name, sort_order) VALUES ('maktab', ?, ?)", (name, i))
    for i, name in enumerate(texnikum_fanlari):
        c.execute("INSERT OR IGNORE INTO edu_subjects (org_type, name, sort_order) VALUES ('texnikum', ?, ?)", (name, i))
    for i, name in enumerate(markaz_yonalishlari):
        c.execute("INSERT OR IGNORE INTO edu_subjects (org_type, name, sort_order) VALUES ('oquv_markazi', ?, ?)", (name, i))

    conn.commit()
    conn.close()
    print("✅ v28 EDU tashkilot arxitekturasi migratsiyasi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
