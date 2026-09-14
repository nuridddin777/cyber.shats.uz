# -*- coding: utf-8 -*-
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "../database/cyber_shats.db")

def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    c.execute("UPDATE premium_ids SET base_price = 1000 WHERE custom_id IN ('0000000', '7777777')")
    c.execute("UPDATE premium_ids SET base_price = 700 WHERE custom_id NOT IN ('0000000', '7777777')")
    
    c.execute('''
        UPDATE premium_ids
        SET status = 'available'
        WHERE status = 'sold' 
          AND custom_id NOT IN (
              SELECT custom_id FROM users WHERE custom_id IS NOT NULL
          )
    ''')

    c.execute('''
        UPDATE premium_ids
        SET status = 'sold'
        WHERE custom_id IN (
            SELECT custom_id FROM users WHERE custom_id IS NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ v77 ID narxlari (1000 va 700) va sotilganlar ro'yxati ombor bo'yicha yangilandi.")

if __name__ == "__main__":
    migrate()
