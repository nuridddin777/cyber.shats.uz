"""
SHATS CYBER — MIGRATE v48: Amaliy mashqlar qamrovini kengaytirish (Web-Dev, Mobile-Dev)
================================================================================
v47 da 9 ta "kod runner" bilan mos yo'nalish (Python/JS/C++ va h.k.) qamrab
olingan edi. Web Dasturlash va Mobil Dasturlash tashqarida qolgan edi, chunki
ular HTML/CSS/brauzer (Web) yoki Flutter/Dart/Kotlin (Mobile) talab qiladi —
code_runner.py bularni ishga tushira olmaydi.

Bu migratsiya qo'shadi:
  - lessons.exercise_starter_html/css/js — Web Dasturlash uchun UCH qismli
    muharrir (HTML+CSS+JS), natija brauzerda TO'G'RIDAN-TO'G'RI (server orqali
    emas, xavfsiz iframe orqali) jonli ko'rsatiladi — kod ishga tushirish
    kerak emas, shuning uchun xavfsizlik cheklovi ham shart emas.
  - practice_type='web' — Web Dasturlash darslariga.
  - Mobil Dasturlash — Flutter/Dart ishga tushirib bo'lmagani uchun, mavzuning
    ORQASIDAGI MANTIQ (state, navigatsiya, widget kompozitsiyasi) Python orqali
    mashq qilinadi (practice_type='code', exercise_language='python'), buni
    izoh (exercise_prompt) ichida aniq tushuntiramiz.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

WEB_KEYWORD_TEMPLATES = [
    (["flexbox", "layout", "grid"],
     "Uchta rangli katakchani (div) gorizontal joylashtiring, ular orasida teng bo'shliq bo'lsin — Flexbox yordamida.",
     '<div class="row">\n  <div class="box">1</div>\n  <div class="box">2</div>\n  <div class="box">3</div>\n</div>',
     '.row {\n  /* shu yerga flexbox yozing: display, justify-content */\n}\n.box {\n  width: 80px; height: 80px; background: #29e07c; color: #04150a;\n  display: flex; align-items: center; justify-content: center; border-radius: 10px; font-weight: 700;\n}',
     '// Bu mashq uchun JS shart emas — faqat HTML/CSS yetarli\n'),
    (["dom", "hodisa", "events", "animatsiya"],
     "Tugmani bosganda sahifadagi matn rangi va matni o'zgarsin (JavaScript DOM manipulation orqali).",
     '<button id="btn">Bosing</button>\n<p id="matn">Salom, CYBER SHATS!</p>',
     '#matn { font-size: 18px; transition: color .3s; }',
     'document.getElementById("btn").addEventListener("click", function() {\n    // shu yerga yozing: matnni va rangini o\'zgartiring\n});'),
    (["forma", "form"],
     "Ism va email maydonlaridan iborat forma yarating; forma yuborilganda (submit) sahifa qayta yuklanmasin va kiritilgan ism pastda ko'rsatilsin.",
     '<form id="frm">\n  <input type="text" id="ism" placeholder="Ismingiz">\n  <input type="email" id="email" placeholder="Email">\n  <button type="submit">Yuborish</button>\n</form>\n<p id="natija"></p>',
     'input { display:block; margin-bottom:8px; padding:8px; }',
     'document.getElementById("frm").addEventListener("submit", function(e) {\n    e.preventDefault();\n    // shu yerga yozing: natijani #natija ichiga chiqaring\n});'),
    (["fetch", "api", "npm", "paket"],
     "fetch() dan foydalanib (haqiqiy internetsiz, taqlid — mock ma'lumot bilan) 'ma'lumot yuklandi' xabarini 2 soniyadan keyin ekranga chiqaring (setTimeout yordamida taqlid qiling).",
     '<button id="load">Yuklash</button>\n<p id="status">Kutilmoqda...</p>',
     '#status { color: #3ec9ff; }',
     'document.getElementById("load").addEventListener("click", function() {\n    document.getElementById("status").textContent = "Yuklanmoqda...";\n    setTimeout(function() {\n        // shu yerga yozing: status matnini yangilang\n    }, 2000);\n});'),
]

WEB_LEVEL_FALLBACK = (
    "Ism-familiyangiz, kasbingiz (masalan 'Talaba') va qisqa tavsif yozilgan oddiy 'vizit karta' (card) yarating — HTML + CSS bilan chiroyli qilib bezang.",
    '<div class="card">\n  <h2>Ismingiz</h2>\n  <p>Kasbingiz</p>\n  <p>Qisqa tavsif...</p>\n</div>',
    '.card {\n  background: #0e141c; color: #eef7f2; padding: 20px; border-radius: 14px;\n  max-width: 260px; font-family: sans-serif;\n  /* shu yerga davom eting: border, shadow va h.k. qo\'shing */\n}',
    '// Bu mashq uchun JS shart emas\n',
)

MOBILE_KEYWORD_TEMPLATES = [
    (["state", "holat"],
     "Mobil ilova 'holati' (state) ni simulyatsiya qiling: hisoblagich (counter) klassi yarating — increment(), decrement() metodlari va joriy qiymatni chop etuvchi metod bilan (bu — Flutter'dagi setState mantiqining Python'dagi soddalashtirilgan ko'rinishi).",
     "python", "class HisoblagichState:\n    def __init__(self):\n        self.qiymat = 0\n\n    # shu yerga increment/decrement metodlarini yozing\n"),
    (["navigatsi", "navigation"],
     "Mobil ilovadagi ekranlar orasida 'navigatsiya'ni stek (stack) yordamida simulyatsiya qiling: push_screen(nomi) va go_back() funksiyalari, joriy ekran har doim stekning tepasida.",
     "python", "ekranlar_stek = []\n\ndef push_screen(nomi):\n    # shu yerga yozing\n    pass\n\ndef go_back():\n    # shu yerga yozing\n    pass\n"),
    (["widget", "kompozitsiya"],
     "Flutter'dagi 'widget ichida widget' (kompozitsiya) mantig'ini Python klasslari bilan simulyatsiya qiling: 'Konteyner' klassi ichiga bir nechta 'Matn' obyektlarini joylashtiring va ularni chop eting.",
     "python", "class Matn:\n    def __init__(self, mazmun):\n        self.mazmun = mazmun\n\nclass Konteyner:\n    def __init__(self):\n        self.bolalar = []\n    # shu yerga qo'shish/chop etish metodlarini yozing\n"),
]

MOBILE_LEVEL_FALLBACK_NOTE = (
    " (Eslatma: Flutter/Dart bu yerda ishga tushirilmaydi — mavzuning ORQASIDAGI mantiqni Python'da mashq qilamiz, "
    "haqiqiy sintaksisni keyinroq Flutter/Dart'da qo'llaysiz.)"
)


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def _pick_web_template(title):
    low = title.lower()
    for keywords, prompt, html, css, js in WEB_KEYWORD_TEMPLATES:
        if any(kw in low for kw in keywords):
            return prompt, html, css, js
    prompt, html, css, js = WEB_LEVEL_FALLBACK
    return prompt, html, css, js


def _pick_mobile_template(title):
    low = title.lower()
    for keywords, prompt, lang, code in MOBILE_KEYWORD_TEMPLATES:
        if any(kw in low for kw in keywords):
            return prompt + MOBILE_LEVEL_FALLBACK_NOTE, lang, code
    # umumiy python shabloniga tushadi (v47 dagi KEYWORD_TEMPLATES/LEVEL_FALLBACKS orqali) — shu yerda oddiy fallback
    return (
        "Mobil ilovada ishlatiladigan kichik 'sozlamalar' (settings) lug'atini (dictionary) yarating: "
        "til, tungi rejim (True/False), bildirishnoma yoqilganligi kabi kalitlar bilan, so'ng ularni chiroyli chop eting."
        + MOBILE_LEVEL_FALLBACK_NOTE,
        "python",
        "sozlamalar = {\n    \"til\": \"uz\",\n    \"tungi_rejim\": False,\n    \"bildirishnoma\": True,\n}\n# shu yerga chop etish kodini yozing\n"
    )


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    for col, ddl in [
        ("exercise_starter_html", "ALTER TABLE lessons ADD COLUMN exercise_starter_html TEXT DEFAULT ''"),
        ("exercise_starter_css", "ALTER TABLE lessons ADD COLUMN exercise_starter_css TEXT DEFAULT ''"),
        ("exercise_starter_js", "ALTER TABLE lessons ADD COLUMN exercise_starter_js TEXT DEFAULT ''"),
    ]:
        if not _column_exists(c, "lessons", col):
            c.execute(ddl)
            print(f"  + lessons.{col}")

    # --- WEB-DEV ---
    web_updated = 0
    rows = c.execute("""
        SELECT l.id, l.title FROM lessons l
        JOIN courses c ON c.id = l.course_id
        JOIN directions d ON d.id = c.direction_id
        WHERE d.slug='web-dev' AND l.has_practice=1
    """).fetchall()
    for lesson_id, title in rows:
        already = c.execute("SELECT practice_type, exercise_prompt FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        if already and already[0] == "web" and already[1]:
            continue
        prompt, html, css, js = _pick_web_template(title or "")
        c.execute(
            "UPDATE lessons SET practice_type='web', exercise_prompt=?, "
            "exercise_starter_html=?, exercise_starter_css=?, exercise_starter_js=? WHERE id=?",
            (prompt, html, css, js, lesson_id)
        )
        web_updated += 1

    # --- MOBILE-DEV ---
    mobile_updated = 0
    rows = c.execute("""
        SELECT l.id, l.title FROM lessons l
        JOIN courses c ON c.id = l.course_id
        JOIN directions d ON d.id = c.direction_id
        WHERE d.slug='mobile-dev' AND l.has_practice=1
    """).fetchall()
    for lesson_id, title in rows:
        already = c.execute("SELECT practice_type, exercise_prompt FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        if already and already[0] == "code" and already[1]:
            continue
        prompt, lang, code = _pick_mobile_template(title or "")
        c.execute(
            "UPDATE lessons SET practice_type='code', exercise_language=?, exercise_prompt=?, "
            "exercise_starter_code=?, exercise_hint=? WHERE id=?",
            (lang, prompt, code, "Flutter/Dart'dagi haqiqiy sintaksis emas, mantiqni tushunishga yordam bering.", lesson_id)
        )
        mobile_updated += 1

    conn.commit()
    conn.close()
    print(f"  + {web_updated} ta Web Dasturlash darsiga HTML/CSS/JS mashq")
    print(f"  + {mobile_updated} ta Mobil Dasturlash darsiga mantiq (Python) mashq")
    print("✅ v48 Amaliy mashqlar qamrovi kengaytirildi (Web-Dev, Mobile-Dev) — muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
