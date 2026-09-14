"""
CYBER SHATS — Migration V26 (MAXSUS: 7 ta qo'shimcha bo'lim)
Freelance bozori, Mentorlar birlashmasi, Startap inkubatori, Developer Hub,
Xavfsizlik sertifikat markazi, Karyera markazi, Voice/Video qo'ng'iroqlar.
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

# --- FREELANCE BOZORI ---
if not table_exists(c, "freelance_gigs"):
    c.execute("""
        CREATE TABLE freelance_gigs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            gig_type TEXT NOT NULL,           -- 'offer' (xizmat taklif) yoki 'request' (xizmat izlash)
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            price_code INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',   -- open, closed
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: freelance_gigs")

if not table_exists(c, "freelance_responses"):
    c.execute("""
        CREATE TABLE freelance_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gig_id INTEGER NOT NULL REFERENCES freelance_gigs(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: freelance_responses")

# --- MENTORLAR BIRLASHMASI ---
if not table_exists(c, "mentors"):
    c.execute("""
        CREATE TABLE mentors (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            skills TEXT NOT NULL,
            bio TEXT DEFAULT '',
            contact TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: mentors")

if not table_exists(c, "mentor_requests"):
    c.execute("""
        CREATE TABLE mentor_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mentor_id INTEGER NOT NULL REFERENCES users(id),
            student_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',   -- pending, accepted, rejected
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: mentor_requests")

# --- STARTAP INKUBATORI ---
if not table_exists(c, "incubator_ideas"):
    c.execute("""
        CREATE TABLE incubator_ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            stage TEXT NOT NULL DEFAULT 'idea',   -- idea, mvp, growth
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: incubator_ideas")

if not table_exists(c, "incubator_votes"):
    c.execute("""
        CREATE TABLE incubator_votes (
            idea_id INTEGER NOT NULL REFERENCES incubator_ideas(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            PRIMARY KEY (idea_id, user_id)
        )
    """)
    print("  + jadval: incubator_votes")

if not table_exists(c, "incubator_comments"):
    c.execute("""
        CREATE TABLE incubator_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER NOT NULL REFERENCES incubator_ideas(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: incubator_comments")

# --- KARYERA MARKAZI ---
if not table_exists(c, "job_listings"):
    c.execute("""
        CREATE TABLE job_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            posted_by INTEGER NOT NULL REFERENCES users(id),
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT DEFAULT 'Masofaviy',
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: job_listings")

if not table_exists(c, "job_applications"):
    c.execute("""
        CREATE TABLE job_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL REFERENCES job_listings(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(job_id, user_id)
        )
    """)
    print("  + jadval: job_applications")

# --- VOICE/VIDEO QO'NG'IROQ SO'ROVLARI ---
if not table_exists(c, "call_requests"):
    c.execute("""
        CREATE TABLE call_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            requester_id INTEGER NOT NULL REFERENCES users(id),
            target_id INTEGER NOT NULL REFERENCES users(id),
            call_type TEXT NOT NULL DEFAULT 'voice',   -- voice, video
            scheduled_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',     -- pending, accepted, declined, done
            room_code TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: call_requests")

conn.commit()
conn.close()
print("\nMigration V26 muvaffaqiyatli!")
