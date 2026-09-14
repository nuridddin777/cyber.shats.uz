def migrate(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("UPDATE pricing_settings SET value = '3' WHERE key = 'pro_price_code'")
        c.execute("UPDATE pricing_settings SET value = '7' WHERE key = 'cyber_pro_price_code'")
        c.execute("UPDATE pricing_settings SET value = '15' WHERE key = 'vip_price_code'")
        c.execute("UPDATE pricing_settings SET value = '27' WHERE key = 'hacker_price_code'")
        conn.commit()
    except Exception as e:
        print('v76 error:', e)
    finally:
        conn.close()
