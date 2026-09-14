"""
SHATS CYBER EDU — MIGRATE v35: Markazlar uchun haqiqiy CODE sotib olish
================================================================================
Tashkilot (markaz) o'z panelidan haqiqiy pul evaziga CODE sotib olishi mumkin:
  1. Kerakli miqdorni qo'lda kiritadi -> narx avtomatik hisoblanadi
     (1 CODE narxi SHATS CYBER'dagi bilan AYNAN bir xil — pricing_settings
     jadvalidagi `code_to_som_rate` orqali, standart 10 000 so'm).
  2. Karta raqamlari ko'rsatiladi (asosiy saytdagi bilan bir xil kartalar).
  3. To'lov chekini rasm sifatida yuklaydi.
  4. G'azna (Edu bo'limi) tekshirib tasdiqlaydi yoki rad etadi.
  5. Tasdiqlansa — CODE Edu G'aznasidan tashkilot balansiga o'tadi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS edu_purchase_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        org_id INTEGER NOT NULL,
        code_amount INTEGER NOT NULL,
        price_uzs INTEGER NOT NULL,
        receipt_file_path TEXT,
        status TEXT NOT NULL DEFAULT 'pending',   -- pending | completed | rejected
        admin_note TEXT DEFAULT '',
        reviewed_by INTEGER,                       -- treasury_accounts.id
        reviewed_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    conn.commit()
    conn.close()
    print("✅ v35 Edu markazlar uchun haqiqiy CODE sotib olish tizimi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
