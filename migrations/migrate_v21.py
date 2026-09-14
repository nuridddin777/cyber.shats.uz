"""
CYBER SHATS — Migration V21 (MAXSUS: Xavfsizlik Zonasi)

Xavfsizlik zonasi uchun jadvallar:
- security_articles: qo'llanmalar/darsliklar (SQL Injection, XSS, 2FA, SSL va h.k.)
- security_glossary: xavfsizlik terminlari lug'ati
- security_quiz_questions: shaxsiy "xavfsizlik balli" testi savollari
- user_security_score: foydalanuvchining test natijasi (eng so'nggi)
- security_checklist_items: "saytim xavfsizmi?" cheklist elementlari
- user_checklist_progress: foydalanuvchi cheklist holati
- security_blacklist_apps: xatarli ilovalar/xizmatlar ro'yxati
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cyber_shats.db")


def table_exists(c, table):
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return c.fetchone() is not None


conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("PRAGMA foreign_keys = ON")

if not table_exists(c, "security_articles"):
    c.execute("""
        CREATE TABLE security_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            summary TEXT DEFAULT '',
            content TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: security_articles")

if not table_exists(c, "security_glossary"):
    c.execute("""
        CREATE TABLE security_glossary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            definition TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: security_glossary")

if not table_exists(c, "security_quiz_questions"):
    c.execute("""
        CREATE TABLE security_quiz_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct TEXT NOT NULL,          -- 'a','b','c','d'
            explanation TEXT DEFAULT '',
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: security_quiz_questions")

if not table_exists(c, "user_security_score"):
    c.execute("""
        CREATE TABLE user_security_score (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            score INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            level TEXT NOT NULL DEFAULT 'Boshlang''ich',
            taken_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    print("  + jadval: user_security_score")

if not table_exists(c, "security_checklist_items"):
    c.execute("""
        CREATE TABLE security_checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            text TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: security_checklist_items")

if not table_exists(c, "user_checklist_progress"):
    c.execute("""
        CREATE TABLE user_checklist_progress (
            user_id INTEGER NOT NULL REFERENCES users(id),
            item_id INTEGER NOT NULL REFERENCES security_checklist_items(id),
            checked_at TEXT NOT NULL DEFAULT (datetime('now')),
            PRIMARY KEY (user_id, item_id)
        )
    """)
    print("  + jadval: user_checklist_progress")

if not table_exists(c, "security_blacklist_apps"):
    c.execute("""
        CREATE TABLE security_blacklist_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            reason TEXT NOT NULL,
            order_index INTEGER NOT NULL DEFAULT 0
        )
    """)
    print("  + jadval: security_blacklist_apps")

conn.commit()

# ---------------------------------------------------------------------------
# BOSHLANG'ICH KONTENT (bo'sh bo'lsa yuklaydi)
# ---------------------------------------------------------------------------
c.execute("SELECT COUNT(*) FROM security_articles")
if c.fetchone()[0] == 0:
    articles = [
        ("Veb xavfsizligi", "SQL Injection'dan himoya", "sql-injection",
         "Ma'lumotlar bazasiga zararli so'rov yuborishning oldini olish.",
         "SQL Injection — foydalanuvchi kiritgan ma'lumot to'g'ridan-to'g'ri SQL so'roviga "
         "qo'shilganda yuzaga keladigan zaiflik. Himoya qilish uchun:\n\n"
         "1. Har doim parametrlashtirilgan so'rovlar (prepared statements) ishlating — "
         "hech qachon foydalanuvchi kiritgan matnni to'g'ridan-to'g'ri SQL satriga qo'shmang.\n"
         "2. ORM (SQLAlchemy, Django ORM va h.k.) ishlatish xavfni sezilarli kamaytiradi.\n"
         "3. Kiritilgan ma'lumotni har doim serverda tekshiring (validatsiya), faqat frontendda emas.\n"
         "4. Ma'lumotlar bazasi foydalanuvchisiga minimal huquq bering (faqat kerakli jadvallarga).\n"
         "5. Xatolik xabarlarida SQL tuzilishini foydalanuvchiga ko'rsatmang."),
        ("Veb xavfsizligi", "XSS (Cross-Site Scripting)'dan himoya", "xss-himoya",
         "Saytga zararli JavaScript kod kiritilishining oldini olish.",
         "XSS — boshqa foydalanuvchi brauzerida ishga tushadigan zararli skript kiritish. Turlari: "
         "Stored (saqlanadigan), Reflected (qaytariladigan), DOM-based.\n\n"
         "Himoya choralari:\n"
         "1. Foydalanuvchi kiritgan har qanday matnni sahifada ko'rsatishdan oldin escape qiling "
         "(HTML belgilarini kodlash).\n"
         "2. Content-Security-Policy (CSP) header o'rnating.\n"
         "3. Cookie'larga HttpOnly va Secure flag qo'ying.\n"
         "4. Zamonaviy freymvorklar (React, Vue) standart holatda avtomatik escape qiladi — "
         "dangerouslySetInnerHTML kabi funksiyalardan ehtiyot bo'ling."),
        ("Veb xavfsizligi", "CSRF'dan himoya", "csrf-himoya",
         "Foydalanuvchi nomidan ruxsatsiz amal bajarilishining oldini olish.",
         "CSRF (Cross-Site Request Forgery) — foydalanuvchi bilmagan holda uning nomidan so'rov "
         "yuborilishi. Himoya:\n\n"
         "1. Har bir forma/POST so'rovga CSRF token qo'shing (Flask-WTF, Django avtomatik qo'llaydi).\n"
         "2. SameSite=Strict yoki Lax cookie sozlamasidan foydalaning.\n"
         "3. Muhim amallar uchun qo'shimcha tasdiqlash (parol qayta so'rash) talab qiling."),
        ("Autentifikatsiya", "Parol xavfsizligi va hashing", "parol-xavfsizligi",
         "Parollarni to'g'ri saqlash va kuchli parol siyosati.",
         "Parollarni hech qachon ochiq matnda saqlamang. Bcrypt, Argon2 yoki PBKDF2 kabi "
         "sekin hash funksiyalaridan foydalaning (MD5/SHA1 YETARLI EMAS).\n\n"
         "Kuchli parol siyosati: kamida 8-12 belgi, katta-kichik harf, raqam, maxsus belgi. "
         "Har bir foydalanuvchi uchun 'salt' qo'shing (zamonaviy kutubxonalar avtomatik qiladi)."),
        ("Autentifikatsiya", "Ikki faktorli autentifikatsiya (2FA)", "2fa-qollash",
         "Hisobingizni faqat parol bilan emas, qo'shimcha qatlam bilan himoyalash.",
         "2FA — parolga qo'shimcha ikkinchi tasdiqlash (SMS kod, autentifikator ilova, "
         "biometrika). Google Authenticator yoki Authy kabi TOTP (Time-based One-Time Password) "
         "standartidan foydalanish tavsiya etiladi — SMS orqali kod SIM-swap hujumiga zaifroq."),
        ("Server va infratuzilma", "Server/hosting xavfsizligi cheklisti", "server-xavfsizligi",
         "Serveringizni sozlashda tekshirish kerak bo'lgan asosiy nuqtalar.",
         "• Firewall yoqilganmi? Faqat kerakli portlar (80, 443, SSH) ochiqmi?\n"
         "• SSH parol bilan emas, kalit (key-based) orqali kirishga sozlanganmi?\n"
         "• Muntazam avtomatik backup ishlaydimi?\n"
         "• Server dasturlari (OS, veb-server) so'nggi yangilanishlarga egami?\n"
         "• Root/administrator hisobidan to'g'ridan-to'g'ri kirish o'chirilganmi?\n"
         "• Fail2ban yoki shunga o'xshash brute-force himoyasi o'rnatilganmi?"),
        ("Server va infratuzilma", "SSL/HTTPS sozlash", "ssl-https",
         "Saytingizni shifrlangan aloqa bilan ta'minlash.",
         "Let's Encrypt orqali bepul SSL sertifikat olish mumkin. HTTPS nafaqat ma'lumotni "
         "shifrlaydi, balki qidiruv tizimlari va brauzerlar tomonidan ham talab qilinadi.\n\n"
         "Muhim: HTTP so'rovlarini avtomatik HTTPS'ga yo'naltiring (301 redirect), "
         "HSTS (HTTP Strict Transport Security) header qo'shing."),
        ("Server va infratuzilma", "Ma'lumotlar bazasini himoya qilish", "db-himoya",
         "Ma'lumotlar bazangizni tashqi hujumlardan qanday himoyalash.",
         "• Ma'lumotlar bazasi serveriga faqat ilova serveridan kirish ruxsat etilsin (tashqi tarmoqqa ochiq bo'lmasin).\n"
         "• Standart port(lar)ni o'zgartiring, kuchli parol qo'ying.\n"
         "• Muntazam shifrlangan backup oling va boshqa joyda saqlang.\n"
         "• Nozik ma'lumotlarni (parol, karta raqami) bazada ham shifrlab saqlang."),
        ("Shaxsiy xavfsizlik", "Fishing (firibgarlik) xabarlarni aniqlash", "fishing-aniqlash",
         "Soxta email/xabarlarni qanday tanish mumkin.",
         "Fishing xabarlarning belgilari: shoshiltiruvchi til ('hisobingiz bloklanadi!'), "
         "grammatik xatolar, shubhali havolalar (domenni diqqat bilan tekshiring), "
         "kutilmagan ilova/fayl. Hech qachon email orqali kelgan havoladan parol kiritmang — "
         "har doim rasmiy saytga to'g'ridan-to'g'ri kiriting."),
        ("Shaxsiy xavfsizlik", "VPN sozlash qo'llanmasi", "vpn-sozlash",
         "Ochiq tarmoqlarda xavfsiz ishlash uchun VPN.",
         "VPN trafikni shifrlaydi va IP manzilingizni yashiradi. Ochiq Wi-Fi tarmoqlarida "
         "(kafe, aeroport) har doim ishonchli VPN xizmatidan foydalaning. Bepul VPN'larga "
         "ehtiyot bo'ling — ular ham sizning trafikingizni ko'rishi mumkin."),
        ("Shaxsiy xavfsizlik", "Xavfsiz Wi-Fi konfiguratsiyasi", "wifi-xavfsizligi",
         "Uy/ofis Wi-Fi tarmog'ini himoyalash.",
         "WPA3 (yoki kamida WPA2) shifrlashdan foydalaning. Standart router parolini "
         "o'zgartiring. Mehmonlar uchun alohida tarmoq (guest network) yarating. "
         "Router dasturiy ta'minotini muntazam yangilab turing."),
        ("Shaxsiy xavfsizlik", "Ijtimoiy muhandislik (Social Engineering)", "social-engineering",
         "Odamlar orqali xavfsizlikni buzish usullaridan xabardor bo'lish.",
         "Hujumchilar ko'pincha texnik zaiflik emas, balki odamlarni aldashga harakat qiladi: "
         "o'zini texnik yordam xodimi qilib ko'rsatish, ishonch og'ochish, shoshiltirish. "
         "Hech qachon telefon/email orqali parol yoki maxfiy kodni bermang — rasmiy tashkilot "
         "buni hech qachon so'ramaydi."),
        ("Kriptografiya", "Kriptografiya asoslari", "kriptografiya-asoslari",
         "Shifrlash turlari va ularning qo'llanilishi.",
         "Simmetrik shifrlash (bir xil kalit, masalan AES) tez, lekin kalitni xavfsiz uzatish "
         "muammoli. Asimmetrik shifrlash (ochiq/yopiq kalit juftligi, masalan RSA) HTTPS va "
         "raqamli imzolarda ishlatiladi. Hash funksiyalar (SHA-256) ma'lumot yaxlitligini "
         "tekshirish uchun ishlatiladi va qaytarib bo'lmaydi."),
        ("Brauzer xavfsizligi", "Brauzer xavfsizligi sozlamalari", "brauzer-xavfsizligi",
         "Brauzeringizni xavfsizroq qilish uchun sozlamalar.",
         "• Brauzerni doim yangilab turing.\n"
         "• Faqat kerakli va ishonchli kengaytmalarni o'rnating.\n"
         "• Parol menejeridan foydalaning, har bir sayt uchun turli parol qo'ying.\n"
         "• 'Saqlangan parollar'ni umumiy kompyuterda ko'rsatib qo'ymang.\n"
         "• Shubhali saytlarga kirishdan oldin brauzerning xavfsizlik ogohlantirishiga e'tibor bering."),
    ]
    for cat, title, slug, summary, content in articles:
        c.execute(
            "INSERT INTO security_articles (category, title, slug, summary, content, order_index) VALUES (?,?,?,?,?,?)",
            (cat, title, slug, summary, content, 0)
        )
    print(f"  + {len(articles)} ta xavfsizlik maqolasi qo'shildi")

c.execute("SELECT COUNT(*) FROM security_glossary")
if c.fetchone()[0] == 0:
    terms = [
        ("Firewall (tarmoqlararo ekran)", "Kiruvchi/chiquvchi tarmoq trafigini qoidalar asosida nazorat qiluvchi tizim."),
        ("Malware", "Kompyuter/tizimga zarar yetkazish maqsadida yaratilgan har qanday zararli dastur."),
        ("Ransomware", "Fayllarni shifrlab, ochish uchun to'lov talab qiladigan zararli dastur turi."),
        ("Phishing", "Foydalanuvchini aldab, maxfiy ma'lumotini olishga qaratilgan firibgarlik usuli."),
        ("Zero-day", "Hali ma'lum bo'lmagan, tuzatilmagan dasturiy zaiflik."),
        ("Brute force", "Parolni barcha kombinatsiyalarni sinab topishga urinish usuli."),
        ("Penetration testing", "Tizim xavfsizligini ruxsat bilan sinab ko'rish jarayoni."),
        ("Encryption (shifrlash)", "Ma'lumotni faqat kalitga ega shaxs o'qiy oladigan formatga o'zgartirish."),
        ("VPN", "Virtual Private Network — internet trafigini shifrlab, xavfsiz tunnel orqali yuboruvchi texnologiya."),
        ("Two-Factor Authentication (2FA)", "Parolga qo'shimcha ikkinchi tasdiqlash usuli talab qiluvchi xavfsizlik qatlami."),
    ]
    for term, definition in terms:
        c.execute("INSERT INTO security_glossary (term, definition, order_index) VALUES (?,?,0)", (term, definition))
    print(f"  + {len(terms)} ta lug'at atamasi qo'shildi")

c.execute("SELECT COUNT(*) FROM security_quiz_questions")
if c.fetchone()[0] == 0:
    quiz = [
        ("Parolingizni qayerda saqlash eng xavfsiz?",
         "Brauzer eslatmasida", "Qog'ozga yozib stol ustida", "Ishonchli parol menejerida", "Barcha saytlarda bir xil parol",
         "c", "Parol menejerlari shifrlangan holda saqlaydi va har bir sayt uchun kuchli, alohida parol yaratishga yordam beradi."),
        ("Quyidagilardan qaysi biri 2FA turi hisoblanadi?",
         "Faqat parol", "SMS orqali kod + parol", "Foydalanuvchi nomi", "Email manzili",
         "b", "2FA — parolga (bilasiz) qo'shimcha ikkinchi omil (masalan, telefoningizga keladigan kod) talab qiladi."),
        ("HTTPS nima uchun kerak?",
         "Sayt tezroq ishlashi uchun", "Server va brauzer orasidagi aloqani shifrlash uchun", "SEO uchun umuman kerak emas", "Faqat dizayn uchun",
         "b", "HTTPS ma'lumot almashinuvini shifrlaydi, uni yo'lda ushlab qolish/o'zgartirishdan himoya qiladi."),
        ("Fishing xabarining odatiy belgisi qaysi?",
         "Rasmiy, xotirjam ohang", "Shoshiltiruvchi til va shubhali havola", "Imzo yo'q", "Uzun matn",
         "b", "Fishing xabarlar odatda shoshiltiradi ('hozir amal qiling!') va shubhali/soxta havolalarga yo'naltiradi."),
        ("SQL Injection'dan himoyalanishning eng ishonchli yo'li?",
         "Foydalanuvchi kiritgan matnni to'g'ridan-to'g'ri so'rovga qo'shish", "Parametrlashtirilgan so'rovlar (prepared statements)", "Xatolarni foydalanuvchiga to'liq ko'rsatish", "Ma'lumotlar bazasini administrator huquqi bilan ulash",
         "b", "Parametrlashtirilgan so'rovlar foydalanuvchi kiritgan ma'lumotni kod sifatida emas, faqat qiymat sifatida ishlatadi."),
        ("Ochiq (bepul) Wi-Fi tarmog'ida nima qilish tavsiya etiladi?",
         "Bank ilovasiga bemalol kirish", "VPN yoqib ishlatish", "Parolni saqlab qo'yish", "Hech narsa qilmasa ham bo'ladi",
         "b", "Ochiq tarmoqlarda trafik ko'pincha shifrlanmagan bo'ladi — VPN qo'shimcha himoya qatlami beradi."),
        ("Kuchli parolga misol qaysi?",
         "123456", "parol123", "Tr7$kQ!9mZp2", "ismingiz+tug'ilgan yil",
         "c", "Kuchli parol uzun, tasodifiy, katta-kichik harf, raqam va maxsus belgilardan iborat bo'ladi."),
    ]
    for q, a, b, c_opt, d, correct, expl in quiz:
        c.execute(
            "INSERT INTO security_quiz_questions (question, option_a, option_b, option_c, option_d, correct, explanation, order_index) "
            "VALUES (?,?,?,?,?,?,?,0)",
            (q, a, b, c_opt, d, correct, expl)
        )
    print(f"  + {len(quiz)} ta test savoli qo'shildi")

c.execute("SELECT COUNT(*) FROM security_checklist_items")
if c.fetchone()[0] == 0:
    items = [
        ("Server", "HTTPS/SSL sertifikati o'rnatilgan va majburiy qilingan"),
        ("Server", "Firewall yoqilgan, faqat kerakli portlar ochiq"),
        ("Server", "SSH parol emas, kalit (key) orqali kirishga sozlangan"),
        ("Server", "Muntazam avtomatik backup ishlaydi"),
        ("Kod", "Barcha SQL so'rovlar parametrlashtirilgan (prepared statements)"),
        ("Kod", "Foydalanuvchi kiritgan matn HTML chiqishda escape qilinadi (XSS himoyasi)"),
        ("Kod", "Barcha formalar CSRF tokenidan foydalanadi"),
        ("Autentifikatsiya", "Parollar bcrypt/Argon2 bilan hash qilinib saqlanadi"),
        ("Autentifikatsiya", "2FA (ikki faktorli autentifikatsiya) mavjud"),
        ("Autentifikatsiya", "Login urinishlari cheklangan (brute-force himoyasi)"),
        ("Ma'lumotlar", "Nozik ma'lumotlar (parol, karta) shifrlab saqlanadi"),
        ("Ma'lumotlar", "Ma'lumotlar bazasi tashqi tarmoqqa ochiq emas"),
        ("Monitoring", "Xavfsizlik hodisalari (login, xatolik) log qilinadi"),
        ("Monitoring", "Dasturiy ta'minot (OS, kutubxonalar) muntazam yangilanadi"),
    ]
    for cat, text in items:
        c.execute("INSERT INTO security_checklist_items (category, text, order_index) VALUES (?,?,0)", (cat, text))
    print(f"  + {len(items)} ta cheklist elementi qo'shildi")

c.execute("SELECT COUNT(*) FROM security_blacklist_apps")
if c.fetchone()[0] == 0:
    apps = [
        ("Noma'lum manbadan APK fayllar", "Rasmiy do'kon (Google Play/App Store) tashqarisidan o'rnatilgan ilovalar zararli kod tashishi mumkin."),
        ("'Bepul VPN' (noma'lum provayder)", "Ko'plab bepul VPN xizmatlari foydalanuvchi trafigini yig'ib, uchinchi tomonga sotadi."),
        ("Litsenziyasiz/crack qilingan dasturlar", "Ko'pincha zararli kod (malware) bilan birga tarqatiladi."),
        ("Shubhali qisqartirilgan havolalar", "Havola qayerga olib borishini yashiradi — fishing uchun tez-tez ishlatiladi."),
    ]
    for name, reason in apps:
        c.execute("INSERT INTO security_blacklist_apps (name, reason, order_index) VALUES (?,?,0)", (name, reason))
    print(f"  + {len(apps)} ta qora ro'yxat yozuvi qo'shildi")

conn.commit()
conn.close()
print("\nMigration V21 muvaffaqiyatli!")
