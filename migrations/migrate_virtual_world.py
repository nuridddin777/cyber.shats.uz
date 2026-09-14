"""
SHATS CYBER V2 — Virtual Olam (Virtual World) migratsiyasi.
3D virtual dunyo: foydalanuvchilar avatar yaratadi, xonalar (rooms) bo'ylab harakat qiladi,
boshqa foydalanuvchilar bilan muloqot qiladi, buyumlar to'playdi.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ==================== VIRTUAL WORLD TABLES ====================

    # Foydalanuvchi avatari
    c.execute("""CREATE TABLE IF NOT EXISTS vw_avatars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        nickname TEXT NOT NULL,
        avatar_type TEXT DEFAULT 'default',
        skin_color TEXT DEFAULT '#FFB74D',
        hair_style TEXT DEFAULT 'short',
        hair_color TEXT DEFAULT '#4E342E',
        outfit TEXT DEFAULT 'casual',
        outfit_color TEXT DEFAULT '#1E90FF',
        accessory TEXT DEFAULT 'none',
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        coins INTEGER DEFAULT 100,
        current_room_id INTEGER DEFAULT 1,
        position_x REAL DEFAULT 0.0,
        position_y REAL DEFAULT 0.0,
        position_z REAL DEFAULT 0.0,
        is_online INTEGER DEFAULT 0,
        last_seen TEXT DEFAULT (datetime('now')),
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Xonalar (virtual rooms / locations)
    c.execute("""CREATE TABLE IF NOT EXISTS vw_rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        slug TEXT UNIQUE NOT NULL,
        description TEXT,
        room_type TEXT DEFAULT 'public',
        theme TEXT DEFAULT 'cyber_city',
        max_users INTEGER DEFAULT 50,
        bg_color TEXT DEFAULT '#0a0a2e',
        floor_color TEXT DEFAULT '#1a1a3e',
        sky_texture TEXT DEFAULT 'night_sky',
        ambient_sound TEXT,
        is_active INTEGER DEFAULT 1,
        required_level INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Xonadagi obyektlar (NPC, dekor, interaktiv)
    c.execute("""CREATE TABLE IF NOT EXISTS vw_room_objects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        object_type TEXT NOT NULL,
        name TEXT,
        model_key TEXT DEFAULT 'cube',
        position_x REAL DEFAULT 0.0,
        position_y REAL DEFAULT 0.0,
        position_z REAL DEFAULT 0.0,
        rotation_y REAL DEFAULT 0.0,
        scale REAL DEFAULT 1.0,
        color TEXT DEFAULT '#1E90FF',
        is_interactive INTEGER DEFAULT 0,
        interaction_type TEXT,
        interaction_data TEXT,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (room_id) REFERENCES vw_rooms(id)
    )""")

    # Virtual buyumlar (items) — foydalanuvchi sotib oladi yoki topadi
    c.execute("""CREATE TABLE IF NOT EXISTS vw_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        item_type TEXT NOT NULL,
        rarity TEXT DEFAULT 'common',
        description TEXT,
        icon TEXT DEFAULT 'cube',
        model_key TEXT DEFAULT 'cube',
        color TEXT DEFAULT '#FFFFFF',
        price_coins INTEGER DEFAULT 0,
        stat_bonus TEXT,
        is_tradeable INTEGER DEFAULT 1,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Foydalanuvchi inventariyasi
    c.execute("""CREATE TABLE IF NOT EXISTS vw_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        is_equipped INTEGER DEFAULT 0,
        acquired_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (item_id) REFERENCES vw_items(id)
    )""")

    # Chat xabarlari (xona ichida)
    c.execute("""CREATE TABLE IF NOT EXISTS vw_chat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        message_type TEXT DEFAULT 'text',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (room_id) REFERENCES vw_rooms(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Do'stlik tizimi
    c.execute("""CREATE TABLE IF NOT EXISTS vw_friends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (friend_id) REFERENCES users(id),
        UNIQUE(user_id, friend_id)
    )""")

    # Virtual do'kon tranzaksiyalari
    c.execute("""CREATE TABLE IF NOT EXISTS vw_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id INTEGER,
        transaction_type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        description TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # Questlar (topshiriqlar)
    c.execute("""CREATE TABLE IF NOT EXISTS vw_quests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        quest_type TEXT DEFAULT 'daily',
        room_id INTEGER,
        reward_coins INTEGER DEFAULT 10,
        reward_xp INTEGER DEFAULT 25,
        reward_item_id INTEGER,
        required_level INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )""")

    # Quest progressi
    c.execute("""CREATE TABLE IF NOT EXISTS vw_quest_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        quest_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        progress INTEGER DEFAULT 0,
        completed_at TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (quest_id) REFERENCES vw_quests(id),
        UNIQUE(user_id, quest_id)
    )""")

    # ==================== SEED DATA ====================

    # Default xonalar
    rooms = [
        ("Markaziy Maydon", "plaza", "SHATS CYBER virtual olamining bosh maydoni. Barcha yo'llar shu yerdan boshlanadi.", "public", "cyber_city", 100, "#0a0e1a", "#141e30", "night_sky"),
        ("Kod Laboratoriyasi", "code_lab", "Dasturlash amaliyoti uchun virtual laboratoriya. Kompyuterlar va kodlash stansiyalari.", "public", "lab", 30, "#0a1a0a", "#0d2610", "lab_lights"),
        ("Xavfsizlik Markazi", "security_center", "Cyber xavfsizlik bo'yicha mashg'ulotlar markazi. CTF va penetration testing.", "public", "security", 30, "#1a0a0a", "#2d1010", "red_alert"),
        ("Kutubxona", "library", "IT kitoblar va manbalar virtual kutubxonasi. Tinch muhit.", "public", "library", 20, "#0a0a1a", "#12122a", "quiet"),
        ("Ijodkor Studio", "creative_studio", "Dizayn, UI/UX va ijodiy loyihalar uchun studio.", "public", "studio", 25, "#1a0a1a", "#2a102a", "ambient"),
        ("Gaming Arena", "gaming_arena", "O'yinlar va musobaqalar uchun virtual arena.", "public", "arena", 50, "#0a0a0a", "#1a1a1a", "crowd"),
        ("Savdo Markazi", "shop", "Virtual buyumlar do'koni. Avatar kiyimlari, aksessuarlar.", "public", "shop", 40, "#0a1a1a", "#102a2a", "market"),
        ("VIP Zal", "vip_lounge", "Faqat Pro va VIP foydalanuvchilar uchun maxsus xona.", "restricted", "luxury", 20, "#1a1a0a", "#2a2a10", "lounge"),
    ]

    for name, slug, desc, rtype, theme, maxu, bg, floor, sky in rooms:
        c.execute("INSERT OR IGNORE INTO vw_rooms (name, slug, description, room_type, theme, max_users, bg_color, floor_color, sky_texture) VALUES (?,?,?,?,?,?,?,?,?)",
                  (name, slug, desc, rtype, theme, maxu, bg, floor, sky))

    # Default buyumlar
    items = [
        ("Hacker Shlyapa", "hat", "rare", "Maxsus hacker shlyapasi", "hat", "#00ff41", 50),
        ("Neon Ko'zoynak", "accessory", "uncommon", "LED neon ko'zoynaklar", "glasses", "#ff00ff", 30),
        ("Cyber Kiyim", "outfit", "common", "Standart cyber kiyim", "shirt", "#1E90FF", 20),
        ("Golden Badge", "badge", "epic", "Oltin bejik — top foydalanuvchilar uchun", "badge", "#FFD700", 100),
        ("Matrix Plash", "outfit", "legendary", "Matrix filmi uslubidagi qora plash", "coat", "#00ff41", 250),
        ("Hologramma Pet", "pet", "rare", "Virtual hologramma hayvoni", "pet", "#00ffff", 150),
        ("Dasturchi Laptop", "tool", "common", "Virtual laptop — kod yozish uchun", "laptop", "#333333", 40),
        ("Dron", "vehicle", "epic", "Shaxsiy kuzatuv droni", "drone", "#ff6600", 200),
    ]

    for name, itype, rarity, desc, model, color, price in items:
        c.execute("INSERT OR IGNORE INTO vw_items (name, item_type, rarity, description, model_key, color, price_coins) VALUES (?,?,?,?,?,?,?)",
                  (name, itype, rarity, desc, model, color, price))

    # Default questlar
    quests = [
        ("Salom Dunyo!", "Markaziy Maydonga kiring va 3 ta foydalanuvchi bilan salomlashing.", "daily", 1, 5, 10, None),
        ("Birinchi Kod", "Kod Laboratoriyasiga kiring va birinchi dasturingizni yozing.", "daily", 2, 10, 25, None),
        ("Xavfsizlik Asoslari", "Xavfsizlik Markazida birinchi CTF topshiriqni bajaring.", "weekly", 3, 25, 50, None),
        ("Kutubxonachi", "Kutubxonaga kiring va 1 ta kitobni o'qing.", "daily", 4, 5, 15, None),
        ("Do'stlar yig'ish", "5 ta yangi do'st qo'shing.", "weekly", None, 20, 40, None),
        ("Do'kon Sayohati", "Savdo Markaziga kiring va birinchi buyumingizni sotib oling.", "one_time", 7, 15, 30, None),
    ]

    for title, desc, qtype, room, coins, xp, item in quests:
        c.execute("INSERT OR IGNORE INTO vw_quests (title, description, quest_type, room_id, reward_coins, reward_xp, reward_item_id) VALUES (?,?,?,?,?,?,?)",
                  (title, desc, qtype, room, coins, xp, item))

    conn.commit()
    conn.close()
    print("✅ Virtual Olam migratsiyasi muvaffaqiyatli bajarildi!")


if __name__ == "__main__":
    migrate()
