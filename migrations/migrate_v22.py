"""
CYBER SHATS — Migration V22 (MAXSUS: qolgan bo'limlar)

- secret_chats / secret_messages: Maxfiy chat (o'z-o'zini yo'q qiluvchi xabarlar)
- referrals: Do'stlar taklif tizimi
- ctf_tasks / ctf_submissions: Maxsus vazifalar (CTF)
- live_streams: SHATS LIVE jadvali
- admin_chat_messages: Admin chat (ticket-uslub)
- organizations / organization_posts / organization_requests: M.A.T maxsus va JXT TASHKILOTI
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

# --- MAXFIY CHAT ---
if not table_exists(c, "secret_chats"):
    c.execute("""
        CREATE TABLE secret_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_a_id INTEGER NOT NULL REFERENCES users(id),
            user_b_id INTEGER NOT NULL REFERENCES users(id),
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_a_id, user_b_id)
        )
    """)
    print("  + jadval: secret_chats")

if not table_exists(c, "secret_messages"):
    c.execute("""
        CREATE TABLE secret_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL REFERENCES secret_chats(id),
            sender_id INTEGER NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            ttl_seconds INTEGER NOT NULL DEFAULT 60,
            read_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_secret_msg_chat ON secret_messages(chat_id, created_at)")
    print("  + jadval: secret_messages")

# --- DO'STLAR TAKLIF (REFERRAL) ---
if not table_exists(c, "referrals"):
    c.execute("""
        CREATE TABLE referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL REFERENCES users(id),
            referred_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            reward_given INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_ref_referrer ON referrals(referrer_id)")
    print("  + jadval: referrals")

if not table_exists(c, "users"):
    pass
else:
    c.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in c.fetchall()]
    if "referral_code" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN referral_code TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
        print("  + users.referral_code")
    if "referred_by" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
        print("  + users.referred_by")

# --- MAXSUS VAZIFALAR (CTF) ---
if not table_exists(c, "ctf_tasks"):
    c.execute("""
        CREATE TABLE ctf_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Web',
            difficulty TEXT NOT NULL DEFAULT 'Easy',   -- Easy, Medium, Hard, Elite
            points INTEGER NOT NULL DEFAULT 10,
            flag TEXT NOT NULL,                          -- to'g'ri javob (flag)
            hint TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: ctf_tasks")

if not table_exists(c, "ctf_submissions"):
    c.execute("""
        CREATE TABLE ctf_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL REFERENCES ctf_tasks(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            correct INTEGER NOT NULL DEFAULT 0,
            points_awarded INTEGER NOT NULL DEFAULT 0,
            submitted_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(task_id, user_id)
        )
    """)
    print("  + jadval: ctf_submissions")

# --- SHATS LIVE ---
if not table_exists(c, "live_streams"):
    c.execute("""
        CREATE TABLE live_streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            host_id INTEGER NOT NULL REFERENCES users(id),
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'scheduled',   -- scheduled, live, ended
            stream_url TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: live_streams")

# --- ADMIN CHAT ---
if not table_exists(c, "admin_chat_messages"):
    c.execute("""
        CREATE TABLE admin_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            sender TEXT NOT NULL,                         -- 'user' yoki 'admin'
            message TEXT NOT NULL,
            read_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    c.execute("CREATE INDEX idx_admin_chat_user ON admin_chat_messages(user_id, created_at)")
    print("  + jadval: admin_chat_messages")

# --- TASHKILOTLAR (M.A.T maxsus / JXT TASHKILOTI) ---
if not table_exists(c, "organizations"):
    c.execute("""
        CREATE TABLE organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_key TEXT UNIQUE NOT NULL,               -- 'mat' yoki 'jxt'
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            stats_members INTEGER NOT NULL DEFAULT 0,
            stats_projects INTEGER NOT NULL DEFAULT 0,
            stats_years INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: organizations")

if not table_exists(c, "organization_posts"):
    c.execute("""
        CREATE TABLE organization_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_key TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: organization_posts")

if not table_exists(c, "organization_requests"):
    c.execute("""
        CREATE TABLE organization_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_key TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',      -- pending, accepted, rejected
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: organization_requests")

conn.commit()

# Boshlang'ich tashkilot ma'lumotlari
c.execute("SELECT COUNT(*) FROM organizations")
if c.fetchone()[0] == 0:
    c.execute(
        "INSERT INTO organizations (org_key, name, description, stats_members, stats_projects, stats_years) "
        "VALUES ('mat','M.A.T MAXSUS','Eng katta va kuchli hamkor jamoalardan biri.',0,0,0)"
    )
    c.execute(
        "INSERT INTO organizations (org_key, name, description, stats_members, stats_projects, stats_years) "
        "VALUES ('jxt','JXT TASHKILOTI','Yirik hamkor tashkilot — birgalikda loyihalar va tadbirlar.',0,0,0)"
    )
    print("  + M.A.T va JXT tashkilotlari yaratildi")

# Namuna CTF vazifalar
c.execute("SELECT COUNT(*) FROM ctf_tasks")
if c.fetchone()[0] == 0:
    tasks = [
        ("Base64 sirini oching", "Quyidagi matn Base64 bilan kodlangan: 'U0hBVFNfQ1lCRVJfMjAyNg=='. Uni deshifrlab, flag sifatida yuboring.",
         "Kripto", "Easy", 10, "SHATS_CYBER_2026", "Onlayn Base64 dekoder ishlatib ko'ring."),
        ("Yashirin kommentariya", "Sayt HTML kodida yashiringan kommentariyani toping: <!-- flag: HIDDEN_IN_HTML -->",
         "Web", "Easy", 10, "HIDDEN_IN_HTML", "Brauzerda 'View Source' (Ctrl+U) dan foydalaning."),
        ("Zaif parolni toping", "Foydalanuvchi parol o'rniga o'zining ismini 'admin2024' bilan birlashtirib qo'ygan. Agar ism 'Root' bo'lsa, parol nima?",
         "Mantiq", "Medium", 20, "Rootadmin2024", "Ikkita so'zni birlashtiring, katta-kichik harfga e'tibor bering."),
    ]
    for title, desc, cat, diff, pts, flag, hint in tasks:
        c.execute(
            "INSERT INTO ctf_tasks (title, description, category, difficulty, points, flag, hint) VALUES (?,?,?,?,?,?,?)",
            (title, desc, cat, diff, pts, flag, hint)
        )
    print(f"  + {len(tasks)} ta CTF vazifasi qo'shildi")

conn.commit()
conn.close()
print("\nMigration V22 muvaffaqiyatli!")
