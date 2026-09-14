"""
CYBER SHATS — Migration V24 (MAXSUS: Bejik va QR kod)
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()

if not table_exists(c, "qr_scan_log"):
    c.execute("""
        CREATE TABLE qr_scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            badge_user_id INTEGER NOT NULL REFERENCES users(id),
            scanned_at TEXT NOT NULL DEFAULT (datetime('now')),
            scanner_ip TEXT DEFAULT ''
        )
    """)
    c.execute("CREATE INDEX idx_qr_scan_user ON qr_scan_log(badge_user_id, scanned_at)")
    print("  + jadval: qr_scan_log")

conn.commit()
conn.close()
print("\nMigration V24 muvaffaqiyatli!")
