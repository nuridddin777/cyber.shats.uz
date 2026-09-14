import sqlite3

conn = sqlite3.connect('/home/kai/projects/cyber-shats/database/cyber_shats.db')
cursor = conn.cursor()
cursor.execute("SELECT name, sql FROM sqlite_master WHERE type='table';")
for name, sql in cursor.fetchall():
    print(f"Table: {name}")
    print(sql)
    print("-" * 50)
conn.close()
