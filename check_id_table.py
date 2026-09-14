import sqlite3
import os

db_path = '/home/kai/projects/cyber-shats/database/cyber_shats.db'
if not os.path.exists(db_path):
    print("DB not found at", db_path)
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name LIKE '%id%';")
    for name, sql in c.fetchall():
        print(f"Table: {name}\n{sql}\n")
    conn.close()
