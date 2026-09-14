"""SHATS CYBER V2 — EDU migratsiyasi. Maktab, sinf, mavzu, lab, coin, obuna tizimi."""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

def migrate():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Viloyatlar
    c.execute("""CREATE TABLE IF NOT EXISTS regions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)""")

    # Tumanlar
    c.execute("""CREATE TABLE IF NOT EXISTS districts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        region_id INTEGER, FOREIGN KEY(region_id) REFERENCES regions(id))""")

    # Maktablar
    c.execute("""CREATE TABLE IF NOT EXISTS schools (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        school_type TEXT DEFAULT 'maktab', district_id INTEGER,
        FOREIGN KEY(district_id) REFERENCES districts(id))""")

    # Maktab obunasi
    c.execute("""CREATE TABLE IF NOT EXISTS school_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, school_id INTEGER,
        tarif TEXT DEFAULT 'oddiy', max_students INTEGER DEFAULT 100,
        max_teachers INTEGER DEFAULT 2, is_active INTEGER DEFAULT 1,
        activated_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT DEFAULT (datetime('now','+30 days')),
        FOREIGN KEY(school_id) REFERENCES schools(id))""")

    # EDU sinflar
    c.execute("""CREATE TABLE IF NOT EXISTS edu_classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        school_id INTEGER, teacher_id INTEGER, subject TEXT DEFAULT '',
        class_level TEXT DEFAULT '', description TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(school_id) REFERENCES schools(id),
        FOREIGN KEY(teacher_id) REFERENCES users(id))""")

    # Sinf o'quvchilari
    c.execute("""CREATE TABLE IF NOT EXISTS edu_class_students (
        id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER, user_id INTEGER,
        joined_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(class_id) REFERENCES edu_classes(id),
        FOREIGN KEY(user_id) REFERENCES users(id), UNIQUE(class_id, user_id))""")

    # Mavzular
    c.execute("""CREATE TABLE IF NOT EXISTS edu_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT, class_id INTEGER NOT NULL,
        title TEXT NOT NULL, content TEXT DEFAULT '', topic_order INTEGER DEFAULT 0,
        is_approved INTEGER DEFAULT 0, video_url TEXT DEFAULT '',
        xp_reward INTEGER DEFAULT 10, coin_reward INTEGER DEFAULT 5,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(class_id) REFERENCES edu_classes(id))""")

    # Lab ishlari
    c.execute("""CREATE TABLE IF NOT EXISTS edu_labs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, topic_id INTEGER NOT NULL,
        title TEXT NOT NULL, description TEXT DEFAULT '',
        lab_type TEXT DEFAULT 'text', max_score INTEGER DEFAULT 100,
        is_approved INTEGER DEFAULT 0,
        FOREIGN KEY(topic_id) REFERENCES edu_topics(id))""")

    # Lab topshiriqlari
    c.execute("""CREATE TABLE IF NOT EXISTS edu_lab_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lab_id INTEGER, user_id INTEGER,
        answer_text TEXT DEFAULT '', file_path TEXT DEFAULT '',
        score INTEGER, feedback TEXT DEFAULT '',
        status TEXT DEFAULT 'pending', submitted_at TEXT DEFAULT (datetime('now')),
        graded_at TEXT,
        FOREIGN KEY(lab_id) REFERENCES edu_labs(id),
        FOREIGN KEY(user_id) REFERENCES users(id))""")

    # Mavzu progressi
    c.execute("""CREATE TABLE IF NOT EXISTS edu_topic_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, topic_id INTEGER,
        completed INTEGER DEFAULT 0, completed_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(topic_id) REFERENCES edu_topics(id),
        UNIQUE(user_id, topic_id))""")

    # EDU coinlar
    c.execute("""CREATE TABLE IF NOT EXISTS edu_coins (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE,
        balance INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id))""")

    # EDU coin tranzaksiyalari
    c.execute("""CREATE TABLE IF NOT EXISTS edu_coin_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        amount INTEGER NOT NULL, reason TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id))""")

    # Coin paketlari
    c.execute("""CREATE TABLE IF NOT EXISTS edu_coin_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        coins INTEGER NOT NULL, price_uzs INTEGER NOT NULL,
        bonus_coins INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1)""")

    # Video darslar
    c.execute("""CREATE TABLE IF NOT EXISTS edu_videos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
        description TEXT DEFAULT '', video_path TEXT DEFAULT '',
        uploader_id INTEGER, file_size INTEGER DEFAULT 0,
        is_approved INTEGER DEFAULT 0, views INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(uploader_id) REFERENCES users(id))""")

    # Bayramlar
    c.execute("""CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
        date_month INTEGER, date_day INTEGER, is_active INTEGER DEFAULT 1,
        theme_css TEXT DEFAULT '')""")

    # Users jadvaliga yangi ustunlar
    for col, typ in [("telefon","TEXT DEFAULT ''"),("region_id","INTEGER"),("district_id","INTEGER"),
                     ("school_id","INTEGER"),("edu_class_id","INTEGER"),("edu_coin_balance","INTEGER DEFAULT 0")]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        except:
            pass

    # ===== SEED DATA =====
    regions_data = {
        "Toshkent shahri": ["Bektemir","Chilonzor","Yakkasaroy","Mirzo Ulug'bek","Mirobod","Sergeli","Shayxontohur","Olmazor","Uchtepa","Yashnaobod","Yunusobod"],
        "Toshkent viloyati": ["Angren","Chirchiq","Olmaliq","Bekobod","Zangiota","Qibray","Bo'stonliq","Parkent"],
        "Samarqand": ["Samarqand sh.","Urgut","Kattaqo'rg'on","Bulung'ur","Jomboy","Pastdarg'om","Payariq","Ishtixon"],
        "Buxoro": ["Buxoro sh.","G'ijduvon","Kogon","Qorako'l","Shofirkon","Vobkent","Jondor","Olot"],
        "Farg'ona": ["Farg'ona sh.","Marg'ilon","Quva","Rishton","Bag'dod","Beshariq","Dang'ara","So'x","Uchko'prik","Furqat"],
        "Andijon": ["Andijon sh.","Asaka","Xonobod","Shahrixon","Baliqchi","Bo'z","Jalaquduq","Marhamat","Oltinko'l","Paxtaobod"],
        "Namangan": ["Namangan sh.","Chortoq","Chust","Kosonsoy","Mingbuloq","Norin","Pop","To'raqo'rg'on","Uchqo'rg'on"],
        "Qashqadaryo": ["Qarshi sh.","Shahrisabz","Kitob","G'uzor","Dehqonobod","Koson","Muborak","Yakkabog'","Nishon","Chiroqchi"],
        "Surxondaryo": ["Termiz sh.","Denov","Sherobod","Boysun","Sho'rchi","Jarqo'rg'on","Muzrabot","Qumqo'rg'on","Oltinsoy","Angor"],
        "Navoiy": ["Navoiy sh.","Zarafshon","Karmana","Nurota","Konimex","Qiziltepa","Xatirchi","Tomdi"],
        "Xorazm": ["Urganch sh.","Xiva","Bog'ot","Gurlan","Xonqa","Shovot","Yangiariq","Hazorasp","Qo'shko'pir","Tuproqqal'a"],
        "Jizzax": ["Jizzax sh.","Do'stlik","G'allaorol","Sharof Rashidov","Forish","Mirzacho'l","Zomin","Zafarobod","Yangiobod","Arnasoy","Baxmal","Paxtakor"],
        "Sirdaryo": ["Guliston sh.","Yangiyer","Boyovut","Oqoltin","Sardoba","Mirzaobod","Xovos","Sayxunobod"],
        "Qoraqalpog'iston": ["Nukus sh.","Beruniy","Chimboy","Xo'jayli","Qo'ng'irot","Shumanay","Taxtako'pir","Kegeyli","Mo'ynoq","Amudaryo","Nukus t.","Qanliko'l","Ellikkala"]
    }

    for region_name, districts in regions_data.items():
        c.execute("INSERT OR IGNORE INTO regions (name) VALUES (?)", (region_name,))
        rid = c.execute("SELECT id FROM regions WHERE name=?", (region_name,)).fetchone()[0]
        for dname in districts:
            c.execute("INSERT OR IGNORE INTO districts (name, region_id) VALUES (?,?)", (dname, rid))
            did = c.execute("SELECT id FROM districts WHERE name=? AND region_id=?", (dname, rid)).fetchone()[0]
            # Har tumanga 1 ta namuna maktab
            for st in ["maktab","texnikum","universitet"]:
                sname = f"{dname} {st.capitalize()} №1"
                c.execute("INSERT OR IGNORE INTO schools (name, school_type, district_id) VALUES (?,?,?)",
                          (sname, st, did))

    # Bayramlar
    holidays = [
        ("Yangi yil", 1, 1), ("Xotin-qizlar kuni", 3, 8), ("Navro'z", 3, 21),
        ("Xotira va qadrlash kuni", 5, 9), ("Mustaqillik kuni", 9, 1),
        ("O'qituvchilar kuni", 10, 1), ("Konstitutsiya kuni", 12, 8),
        ("Ro'za hayit", 4, 10), ("Qurbon hayit", 6, 17), ("Vatanparvarlar kuni", 1, 14)
    ]
    for name, m, d in holidays:
        c.execute("INSERT OR IGNORE INTO holidays (name, date_month, date_day) VALUES (?,?,?)", (name, m, d))

    # Coin paketlari
    pkgs = [("Boshlang'ich",50,15000,0),("O'rta",150,40000,10),("Katta",400,90000,50),("Mega",1000,200000,200)]
    for name, coins, price, bonus in pkgs:
        c.execute("INSERT OR IGNORE INTO edu_coin_packages (name, coins, price_uzs, bonus_coins) VALUES (?,?,?,?)",
                  (name, coins, price, bonus))

    conn.commit()
    conn.close()
    print("✅ EDU migratsiyasi va seed data muvaffaqiyatli!")

if __name__ == "__main__":
    migrate()
