"""
SHATS CYBER — MIGRATE v55: To'liq ishlaydigan video-qo'ng'iroq (WebRTC)
================================================================================
Saytning o'zida ishlaydigan video-chat — Telegram guruh qo'ng'irog'iga
o'xshab, guruhdagi (yoki kanaldagi) barcha a'zolar qatnashishi mumkin.

ARXITEKTURA: WebSocket infratuzilmasi yo'qligi sababli (Flask-SocketIO
o'rnatilmagan), signalizatsiya (offer/answer/ICE) HTTP POLLING orqali
amalga oshiriladi — brauzer har 1.5 soniyada yangi signal bor-yo'qligini
so'raydi. Haqiqiy video/audio oqimi esa TO'G'RIDAN-TO'G'RI (peer-to-peer)
WebRTC orqali uzatiladi — signalizatsiya faqat ULANISHNI o'rnatish uchun
kerak, keyin server orqali video O'TMAYDI.

DIQQAT (cheklov): faqat bepul STUN server ishlatiladi (TURN server yo'q) —
bu ko'pchilik tarmoqlarda ishlaydi, lekin ba'zi qattiq NAT/firewall ortida
(masalan korporativ tarmoq) ulanish muvaffaqiyatsiz bo'lishi mumkin.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "video_calls"):
        c.execute("""
            CREATE TABLE video_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_code TEXT NOT NULL UNIQUE,
                group_id INTEGER REFERENCES groups(id),
                channel_id INTEGER REFERENCES channels(id),
                started_by INTEGER NOT NULL REFERENCES users(id),
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT
            )
        """)
        print("  + jadval: video_calls")

    if not _table_exists(c, "video_call_participants"):
        c.execute("""
            CREATE TABLE video_call_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL REFERENCES video_calls(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                joined_at TEXT NOT NULL DEFAULT (datetime('now')),
                left_at TEXT,
                UNIQUE(call_id, user_id)
            )
        """)
        print("  + jadval: video_call_participants")

    if not _table_exists(c, "video_call_signals"):
        c.execute("""
            CREATE TABLE video_call_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                call_id INTEGER NOT NULL REFERENCES video_calls(id),
                from_user_id INTEGER NOT NULL REFERENCES users(id),
                to_user_id INTEGER NOT NULL REFERENCES users(id),
                signal_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        c.execute("CREATE INDEX idx_signals_lookup ON video_call_signals(call_id, to_user_id, id)")
        print("  + jadval: video_call_signals")

    conn.commit()
    conn.close()
    print("✅ v55 WebRTC video-qo'ng'iroq — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
