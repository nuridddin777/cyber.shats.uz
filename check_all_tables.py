import sqlite3

conn = sqlite3.connect('/home/kai/projects/cyber-shats/database/cyber_shats.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table';")
for (name,) in c.fetchall():
    print(name)
conn.close()
