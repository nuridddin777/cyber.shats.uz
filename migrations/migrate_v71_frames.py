# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v71: Profil ramkalari (frame) tizimi
================================================================================
Ikki xil ramka:
1. Tarif-eksklyuziv ramkalar — Pro/Cyber Pro/VIP/MAXSUS/Admin tarifiga ega
   bo'lgan foydalanuvchilarga AVTOMATIK ochiladi (sotib olinmaydi).
2. Sotiladigan ramkalar — HAR QANDAY foydalanuvchi CODE evaziga sotib
   olishi mumkin (3 CODE dan 50 CODE gacha, dizayni narxga qarab kuchayadi).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _column_exists(c, "users", "active_frame"):
        c.execute("ALTER TABLE users ADD COLUMN active_frame TEXT DEFAULT NULL")
        print("  + users.active_frame")

    if not _table_exists(c, "profile_frames"):
        c.execute("""
            CREATE TABLE profile_frames (
                frame_key TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                price_code INTEGER NOT NULL DEFAULT 0,
                tier_required TEXT DEFAULT NULL,
                css_style TEXT NOT NULL,
                animation_class TEXT DEFAULT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)
        print("  + jadval: profile_frames")

    # MUHIM (tuzatilgan xato): checkmark_shop'dagi bilan BIR XIL muammo —
    # seed ma'lumotlar avval FAQAT jadval BIRINCHI marta yaratilganda
    # qo'shilardi. Endi qatorlar SONI tekshiriladi (0 bo'lsa — jadval
    # bor, lekin bo'sh — bunday holatda ham qayta to'ldiriladi), shuning
    # uchun "Ramkalar" do'koni endi hech qachon doimiy bo'sh qolmaydi.
    _frame_count = c.execute("SELECT COUNT(*) FROM profile_frames").fetchone()[0]
    if _frame_count == 0:
        seed = [
            # --- SOTILADIGAN RAMKALAR (3 dan 50 CODEgacha, narx oshgani sari
            #     dizayn ham murakkablashadi/chiroylilashadi) ---
            ("f_bronze", "Bronza halqa", 3, None,
             "border:3px solid #B08D57; box-shadow:0 0 0 2px rgba(176,141,87,.25);", None, 1),
            ("f_silver", "Kumush halqa", 6, None,
             "border:3px solid #C0C0C0; box-shadow:0 0 0 2px rgba(192,192,192,.3);", None, 2),
            ("f_azure", "Moviy oqim", 10, None,
             "border:3px solid transparent; background-image:linear-gradient(#0F172A,#0F172A),linear-gradient(135deg,#3B82F6,#60A5FA); background-origin:border-box; background-clip:padding-box,border-box;", None, 3),
            ("f_emerald", "Zumrad chizig'i", 14, None,
             "border:3px solid transparent; background-image:linear-gradient(#0F172A,#0F172A),linear-gradient(135deg,#10b981,#34d399); background-origin:border-box; background-clip:padding-box,border-box;", None, 4),
            ("f_sunset", "Quyosh botishi", 20, None,
             "border:3px solid transparent; background-image:linear-gradient(#0F172A,#0F172A),linear-gradient(135deg,#f97316,#ec4899); background-origin:border-box; background-clip:padding-box,border-box;", None, 5),
            ("f_glow_violet", "Binafsha porlash", 28, None,
             "border:3px solid #a855f7; box-shadow:0 0 14px rgba(168,85,247,.6);", "frame-pulse", 6),
            ("f_double_ring", "Qo'sh halqa", 35, None,
             "border:3px solid #38BDF8; outline:2px solid rgba(56,189,248,.35); outline-offset:3px;", "frame-spin-slow", 7),
            ("f_rainbow", "Kamalak aylanasi", 50, None,
             "border:4px solid transparent; background-image:linear-gradient(#0F172A,#0F172A),linear-gradient(90deg,#ff3b3b,#ffb238,#ffe93b,#3bff6a,#3b82ff,#a83bff,#ff3b3b); background-origin:border-box; background-clip:padding-box,border-box; background-size:200% 200%;",
             "frame-rainbow-flow", 8),

            # --- TARIF-EKSKLYUZIV RAMKALAR (sotib olinmaydi, tarifga qarab
            #     avtomatik ochiladi) ---
            ("t_pro", "PRO ramkasi", 0, "pro",
             "border:3px solid #92400e; box-shadow:0 0 10px rgba(146,64,14,.4);", None, 20),
            ("t_cyber_pro", "CYBER PRO ramkasi", 0, "cyber_pro",
             "border:3px solid transparent; background-image:linear-gradient(#0F172A,#0F172A),linear-gradient(135deg,#ff3366,#3366ff); background-origin:border-box; background-clip:padding-box,border-box;", "frame-pulse", 21),
            ("t_vip", "VIP ramkasi", 0, "vip",
             "border:3px solid #BF953F; box-shadow:0 0 16px rgba(191,149,63,.6);", "frame-shimmer", 22),
            ("t_hacker", "MAXSUS ramkasi", 0, "hacker",
             "border:3px solid #a855f7; box-shadow:0 0 16px rgba(168,85,247,.65);", "frame-glitch", 23),
            ("t_admin", "ADMIN ramkasi", 0, "admin",
             "border:3px solid #475569; box-shadow:0 0 14px rgba(71,85,105,.6);", "frame-spin-slow", 24),
        ]
        for row in seed:
            c.execute(
                "INSERT OR IGNORE INTO profile_frames (frame_key,label,price_code,tier_required,css_style,animation_class,sort_order) VALUES (?,?,?,?,?,?,?)",
                row
            )
        print(f"  + {len(seed)} ta ramka turi (8 sotiladigan + 5 tarif-eksklyuziv) — jadval bo'sh bo'lgani uchun qayta to'ldirildi")

    if not _table_exists(c, "user_owned_frames"):
        c.execute("""
            CREATE TABLE user_owned_frames (
                user_id INTEGER NOT NULL REFERENCES users(id),
                frame_key TEXT NOT NULL,
                bought_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, frame_key)
            )
        """)
        print("  + jadval: user_owned_frames")

    conn.commit()
    conn.close()
    print("✅ v71 Profil ramkalari tizimi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
