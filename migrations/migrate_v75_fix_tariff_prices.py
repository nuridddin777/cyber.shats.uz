def migrate(db_path):
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("UPDATE pricing_settings SET value = '30000' WHERE key = 'bot_tariff_price_pro'")
        c.execute("UPDATE pricing_settings SET value = '70000' WHERE key = 'bot_tariff_price_cyber_pro'")
        c.execute("UPDATE pricing_settings SET value = '150000' WHERE key = 'bot_tariff_price_vip'")
        c.execute("UPDATE pricing_settings SET value = '270000' WHERE key = 'bot_tariff_price_hacker'")
        conn.commit()
    except Exception as e:
        print('v75 error:', e)
    finally:
        conn.close()