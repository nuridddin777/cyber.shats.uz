"""
SHATS CYBER — MIGRATE v47: Haqiqiy amaliy kod mashqlari + AI yordamchi
================================================================================
Muammo: "amaliyot" (practice) darslarining BARCHASI — yo'nalishidan qat'iy
nazar — bitta qattiq yozilgan SQL Injection demo sahifasini ko'rsatardi
(templates/practice.html). Dasturlash yo'nalishlari (Python, JS, C++, va h.k.)
uchun bu mazmunsiz edi.

Bu migratsiya `lessons` jadvaliga quyidagilarni qo'shadi:
  - practice_type          : 'hacker_lab' (eski SQLi demo, kiberxavfsizlik
                              uchun mos qoladi) | 'code' (yangi — haqiqiy
                              kod yozish mashqi) | 'none'
  - exercise_language       : code_runner.py qo'llab-quvvatlaydigan til
                              (python / javascript_node / cpp)
  - exercise_prompt         : mashq matni (topshiriq)
  - exercise_starter_code   : boshlang'ich kod (talaba shundan boshlaydi)
  - exercise_hint           : AI yordamchiga signal — mashqning "kaliti"
                              (talabaga to'g'ridan-to'g'ri ko'rsatilmaydi,
                              AI shu asosda maqsadli yo'l-yo'riq beradi)

Dasturlash yo'nalishlari (python, javascript, cpp, database, data-science,
ai-ml, devops, cloud, networking) dagi `has_practice=1` darslar kalit so'z
asosida mos mashq shabloni bilan to'ldiriladi (aniq mos kelmasa — kurs
darajasiga (Boshlang'ich/O'rta/Yuqori) mos umumiy shablon qo'llaniladi).
Kiberxavfsizlik va boshqa (SMM/Targetolog/va h.k.) yo'nalishlar — eski
hacker_lab demo bilan o'zgarishsiz qoladi.
"""
import sqlite3
import os
import re

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

CODE_DIRECTIONS = {
    "python": "python", "javascript": "javascript_node", "cpp": "cpp",
    "database": "python", "data-science": "python", "ai-ml": "python",
    "devops": "python", "cloud": "python", "networking": "python",
}

# (kalit so'zlar ro'yxati, til-neytral shablon) — {LANG} runtime bo'yicha to'ldiriladi
KEYWORD_TEMPLATES = [
    (["tsikl", "for ", "while", "loop"],
     "1 dan 20 gacha bo'lgan sonlarni chop eting, lekin 3 ga bo'linadiganlarini 'Fizz' so'zi bilan almashtiring.",
     {"python": "for son in range(1, 21):\n    # shu yerga yozing\n    pass\n",
      "javascript_node": "for (let son = 1; son <= 20; son++) {\n    // shu yerga yozing\n}\n",
      "cpp": "#include <iostream>\nusing namespace std;\nint main() {\n    for (int son = 1; son <= 20; son++) {\n        // shu yerga yozing\n    }\n    return 0;\n}\n"},
     "Modul operatoridan (% yoki mod) foydalanish kerak: son % 3 == 0."),
    (["funksi", "function", "funktsi"],
     "Ikkita son qabul qilib, ularning yig'indisini qaytaruvchi funksiya yozing, so'ng uni 3 xil qiymat bilan chaqirib natijalarni chop eting.",
     {"python": "def yigindi(a, b):\n    # shu yerga yozing\n    pass\n\n# funksiyani chaqiring:\n",
      "javascript_node": "function yigindi(a, b) {\n    // shu yerga yozing\n}\n\n// funksiyani chaqiring:\n",
      "cpp": "#include <iostream>\nusing namespace std;\nint yigindi(int a, int b) {\n    // shu yerga yozing\n    return 0;\n}\nint main() {\n    // funksiyani chaqiring\n    return 0;\n}\n"},
     "Funksiya ichida 'return' (yoki C++ da return) orqali natijani qaytarish kerak, chop etish tashqarida."),
    (["fayl", "file", "istisno", "exception"],
     "Ro'yxatni (list/array) aylanib o'ting va agar element son bo'lmasa, xatoni 'tutib' (try/except yoki try/catch) xabar chiqaring, dastur to'xtamasin.",
     {"python": "malumotlar = [1, 2, 'uch', 4, 'besh']\nfor x in malumotlar:\n    # shu yerga try/except yozing\n    pass\n",
      "javascript_node": "const malumotlar = [1, 2, 'uch', 4, 'besh'];\nfor (const x of malumotlar) {\n    // shu yerga try/catch yozing\n}\n",
      "cpp": "#include <iostream>\nusing namespace std;\nint main() {\n    // C++ da xato ushlashni try/catch bilan sinab ko'ring\n    return 0;\n}\n"},
     "Har bir elementni songa aylantirishga urinib ko'ring, muvaffaqiyatsiz bo'lsa xato ushlanadi."),
    (["oop", "klass", "class", "ob'ekt", "obyekt"],
     "'Talaba' klassini yarating: ism va baho (0-100) maydonlari, hamda o'rtacha bahoni chiqaruvchi metod bilan. 2 ta obyekt yarating va solishtiring.",
     {"python": "class Talaba:\n    def __init__(self, ism, baho):\n        self.ism = ism\n        self.baho = baho\n\n# shu yerga davom eting\n",
      "javascript_node": "class Talaba {\n    constructor(ism, baho) {\n        this.ism = ism;\n        this.baho = baho;\n    }\n}\n\n// shu yerga davom eting\n",
      "cpp": "#include <iostream>\n#include <string>\nusing namespace std;\nclass Talaba {\npublic:\n    string ism;\n    int baho;\n    Talaba(string i, int b) : ism(i), baho(b) {}\n};\nint main() {\n    // shu yerga davom eting\n    return 0;\n}\n"},
     "Klass konstruktordan keyin kamida bitta metod yoki funksiya orqali solishtirish mantig'i qo'shilishi kerak."),
    (["algoritm", "sort", "saralash", "qidiruv", "search"],
     "Sonlar ro'yxatini (kamida 8 ta element) o'sish tartibida saralang — tayyor sort funksiyasini ISHLATMASDAN, o'zingiz algoritm yozing (bubble sort yoki shunga o'xshash).",
     {"python": "sonlar = [5, 2, 9, 1, 7, 3, 8, 4]\n# shu yerga o'z saralash algoritmingizni yozing (built-in sort() ishlatmang)\n",
      "javascript_node": "let sonlar = [5, 2, 9, 1, 7, 3, 8, 4];\n// shu yerga o'z saralash algoritmingizni yozing (built-in sort() ishlatmang)\n",
      "cpp": "#include <iostream>\nusing namespace std;\nint main() {\n    int sonlar[] = {5, 2, 9, 1, 7, 3, 8, 4};\n    // shu yerga o'z saralash algoritmingizni yozing\n    return 0;\n}\n"},
     "Bubble sort: qo'shni elementlarni juftlab solishtirib, kerak bo'lsa o'rnini almashtirish, bir necha marta qaytarilishi kerak."),
    (["massiv", "list", "array", "ro'yxat"],
     "10 ta tasodifiy (yoki qo'lda kiritilgan) sonlardan iborat ro'yxat yarating, so'ng eng katta, eng kichik va o'rtacha qiymatni toping.",
     {"python": "sonlar = [12, 5, 8, 19, 3, 27, 1, 15, 9, 22]\n# shu yerga yozing: max, min, o'rtacha\n",
      "javascript_node": "const sonlar = [12, 5, 8, 19, 3, 27, 1, 15, 9, 22];\n// shu yerga yozing: max, min, o'rtacha\n",
      "cpp": "#include <iostream>\nusing namespace std;\nint main() {\n    int sonlar[] = {12, 5, 8, 19, 3, 27, 1, 15, 9, 22};\n    // shu yerga yozing\n    return 0;\n}\n"},
     "Massivni aylanib o'tib, joriy max/min/yig'indi o'zgaruvchilarini yangilab borish kerak."),
]

LEVEL_FALLBACKS = {
    "Boshlang'ich": (
        "Ekranga o'z ismingiz va CYBER SHATS'da nechanchi kundan beri o'qiyotganingizni (istalgan son) chop eting, "
        "so'ng 1 dan 10 gacha sonlarni chop etuvchi kichik tsikl yozing.",
        {"python": "ism = \"Talaba\"\n# shu yerga yozing\n",
         "javascript_node": "const ism = \"Talaba\";\n// shu yerga yozing\n",
         "cpp": "#include <iostream>\nusing namespace std;\nint main() {\n    string ism = \"Talaba\";\n    // shu yerga yozing\n    return 0;\n}\n"},
        "Bu — kirish darajasidagi mashq, asosiy sintaksis (o'zgaruvchi, chop etish, oddiy tsikl) yetarli."),
    "O'rta": (
        "Foydalanuvchidan (yoki tayyor ro'yxatdan) bir nechta so'z oling va ularning har birining uzunligini chop eting, "
        "so'ng eng uzun so'zni aniqlang.",
        {"python": "sozlar = [\"kod\", \"dasturlash\", \"algoritm\", \"AI\"]\n# shu yerga yozing\n",
         "javascript_node": "const sozlar = [\"kod\", \"dasturlash\", \"algoritm\", \"AI\"];\n// shu yerga yozing\n",
         "cpp": "#include <iostream>\n#include <vector>\n#include <string>\nusing namespace std;\nint main() {\n    vector<string> sozlar = {\"kod\", \"dasturlash\", \"algoritm\", \"AI\"};\n    // shu yerga yozing\n    return 0;\n}\n"},
        "O'rta darajadagi mashq — ro'yxat/massiv bilan ishlash va shart operatorlarini birlashtirish kerak."),
    "Yuqori": (
        "Berilgan matnda har bir harfning necha marta uchraganini hisoblab, natijani chiroyli formatda chop eting "
        "(masalan lug'at/dictionary yoki mos struktura yordamida).",
        {"python": "matn = \"cyber shats platformasi\"\n# shu yerga yozing (dict yordamida hisoblang)\n",
         "javascript_node": "const matn = \"cyber shats platformasi\";\n// shu yerga yozing (Map yoki object yordamida hisoblang)\n",
         "cpp": "#include <iostream>\n#include <map>\n#include <string>\nusing namespace std;\nint main() {\n    string matn = \"cyber shats platformasi\";\n    // shu yerga yozing (map yordamida hisoblang)\n    return 0;\n}\n"},
        "Yuqori darajadagi mashq — xesh-jadval/lug'at (dict/Map/map) tuzilmasidan foydalanish kerak."),
}


def _table_exists(c, name):
    return c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def _pick_template(title, level):
    low = title.lower()
    for keywords, prompt, code_by_lang, hint in KEYWORD_TEMPLATES:
        if any(kw in low for kw in keywords):
            return prompt, code_by_lang, hint
    return LEVEL_FALLBACKS.get(level, LEVEL_FALLBACKS["Boshlang'ich"])


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    for col, ddl in [
        ("practice_type", "ALTER TABLE lessons ADD COLUMN practice_type TEXT DEFAULT 'hacker_lab'"),
        ("exercise_language", "ALTER TABLE lessons ADD COLUMN exercise_language TEXT DEFAULT NULL"),
        ("exercise_prompt", "ALTER TABLE lessons ADD COLUMN exercise_prompt TEXT DEFAULT ''"),
        ("exercise_starter_code", "ALTER TABLE lessons ADD COLUMN exercise_starter_code TEXT DEFAULT ''"),
        ("exercise_hint", "ALTER TABLE lessons ADD COLUMN exercise_hint TEXT DEFAULT ''"),
    ]:
        if not _column_exists(c, "lessons", col):
            c.execute(ddl)
            print(f"  + lessons.{col}")

    if not _table_exists(c, "directions") or not _table_exists(c, "courses"):
        conn.commit(); conn.close(); return

    updated = 0
    for slug, lang in CODE_DIRECTIONS.items():
        rows = c.execute("""
            SELECT l.id, l.title, c.level FROM lessons l
            JOIN courses c ON c.id = l.course_id
            JOIN directions d ON d.id = c.direction_id
            WHERE d.slug=? AND l.has_practice=1
        """, (slug,)).fetchall()
        for lesson_id, title, level in rows:
            already = c.execute("SELECT practice_type, exercise_prompt FROM lessons WHERE id=?", (lesson_id,)).fetchone()
            if already and already[0] == "code" and already[1]:
                continue  # allaqachon sozlangan (masalan admin qo'lda o'zgartirgan) — qayta yozmaymiz
            prompt, code_by_lang, hint = _pick_template(title or "", level or "")
            starter = code_by_lang.get(lang, code_by_lang.get("python", ""))
            c.execute(
                "UPDATE lessons SET practice_type='code', exercise_language=?, exercise_prompt=?, "
                "exercise_starter_code=?, exercise_hint=? WHERE id=?",
                (lang, prompt, starter, hint, lesson_id)
            )
            updated += 1

    conn.commit()
    conn.close()
    print(f"  + {updated} ta darsga haqiqiy kod mashqi biriktirildi")
    print("✅ v47 Amaliy kod mashqlari + AI yordamchi — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
