"""
SHATS CYBER V2 — MIGRATE v29: PRO — Chuqurlashgan laboratoriyalar (Advanced Labs)
====================================================================================
Diqqat: bu migratsiya v28 (database/migrate_v28_edu_orgs.py) dan KEYIN ishga
tushirilishi kerak, chunki edu_tariffs jadvaliga ustunlar qo'shadi.

Bu bosqichda qo'shiladigan narsalar:

  1) edu_tariffs jadvaliga yangi bayroqlar (faqat Pro tariflarda yoqiladi):
       - has_advanced_labs        : 8 ta murakkab laboratoriya ko'rinadimi
       - has_deep_textbooks       : chuqurlashgan darsliklar (kengaytirilgan kurs)
       - has_student_ai_assistant : o'quvchilar uchun maxsus AI-yordamchi

  2) edu_advanced_labs — 8 ta laboratoriya KATALOGI (texnik topshiriqdan):
       1. wasm_os_sim              — WebAssembly-based OS Simulator
       2. reverse_malware_sandbox  — Reverse Engineering & Malware Sandbox (Docker)
       3. edge_ai_cv_lab           — Edge AI & Computer Vision Lab (TF.js/OpenCV.js)
       4. distributed_consensus    — Distributed Systems & Consensus Lab (Raft/Paxos)
       5. compiler_builder         — Automated Compiler Builder (lexer/parser/AST)
       6. competitive_profiling    — Compiler-Optimized Competitive Programming
       7. db_sharding_sim          — AI-Augmented DB Sharding & Replication Simulator
       8. neural_net_from_scratch  — Neural Network Architecture Builder (sof NumPy)

     Har biri qaysi tashkilot turiga mos ekanligi (org_type) va qanday runtime
     (wasm/docker/browser_cv/...) kerakligi bilan belgilanadi — bu keyingi
     bosqichda har bir lab uchun ALOHIDA ijro muhiti (runtime) qurishda ishlatiladi.

  3) edu_advanced_lab_submissions — o'quvchi topshirig'i/urinishi, natija, metrikalar
     (masalan profiler uchun nano-soniya, DB sim uchun RPS, va h.k. — JSON ko'rinishida)

  4) Kirish nazorati (gating): faqat tashkilot Pro tarifga ega bo'lsagina
     bu laborotoriyalar ochiladi — buni tekshiruvchi funksiya advanced_labs.py da.

MUHIM CHEKLOV: bu migratsiya faqat KATALOG/ARXITEKTURA darajasida.
Har bir laboratoriyaning haqiqiy ijro muhiti (masalan haqiqiy Docker
konteynerlarni ishga tushirish, WASM kompilyatsiya qilish, kamera oqimini
TensorFlow.js bilan tahlil qilish) — bu 8 ta ALOHIDA, katta hajmdagi
muhandislik loyihasi bo'lib, xavfsizlik devor (sandbox escape, resource
abuse) talablari tufayli alohida infratuzilma (masalan izolyatsiyalangan
konteyner klasteri) talab qiladi. Shu sabab bu yerda faqat ma'lumotlar
tuzilishi va kirish nazorati tayyorlandi; runtime'lar navbatma-navbat,
bittalab qurilishi tavsiya etiladi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    # Bu migratsiya v28 talab qiladi
    exists = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='edu_tariffs'"
    ).fetchone()
    if not exists:
        raise RuntimeError(
            "edu_tariffs jadvali topilmadi! Avval database/migrate_v28_edu_orgs.py ni ishga tushiring."
        )

    # ------------------------------------------------------------------
    # 1) edu_tariffs ga Pro-only bayroqlar
    # ------------------------------------------------------------------
    for col, typ in [
        ("has_advanced_labs", "INTEGER DEFAULT 0"),
        ("has_deep_textbooks", "INTEGER DEFAULT 0"),
        ("has_student_ai_assistant", "INTEGER DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE edu_tariffs ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass  # ustun allaqachon mavjud

    c.execute("""UPDATE edu_tariffs
                 SET has_advanced_labs=1, has_deep_textbooks=1, has_student_ai_assistant=1
                 WHERE code LIKE '%_pro'""")

    # ------------------------------------------------------------------
    # 2) Laboratoriyalar katalogi
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_advanced_labs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lab_key TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        tech_stack TEXT DEFAULT '',           -- masalan "WebAssembly, C/Rust"
        runtime_type TEXT NOT NULL,           -- wasm | docker_sandbox | browser_cv |
                                               -- network_sim | ast_visualizer |
                                               -- profiler | db_sim | numpy_sandbox
        allowed_org_types TEXT NOT NULL,      -- vergul bilan: "texnikum,oquv_markazi"
        min_tarif_level TEXT DEFAULT 'pro',
        difficulty TEXT DEFAULT 'yuqori',     -- o'rta / yuqori / juda_yuqori
        team_based INTEGER DEFAULT 0,         -- masalan distributed_consensus guruh ishi
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    )""")

    # ------------------------------------------------------------------
    # 3) O'quvchi topshiriqlari / urinishlari
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_advanced_lab_submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lab_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,          -- edu_students.id
        team_id INTEGER,                       -- guruh ishi bo'lsa (distributed_consensus)
        code_text TEXT DEFAULT '',
        file_path TEXT DEFAULT '',
        status TEXT DEFAULT 'in_progress',     -- in_progress|submitted|graded|failed
        score REAL,
        metrics_json TEXT DEFAULT '{}',        -- masalan {"latency_ns": 120, "cache_hit_rate": 0.94}
        feedback TEXT DEFAULT '',
        attempt_number INTEGER DEFAULT 1,
        started_at TEXT DEFAULT (datetime('now')),
        submitted_at TEXT,
        graded_at TEXT,
        FOREIGN KEY(lab_id) REFERENCES edu_advanced_labs(id),
        FOREIGN KEY(student_id) REFERENCES edu_students(id)
    )""")

    # ------------------------------------------------------------------
    # SEED: 8 ta laboratoriya (texnik topshiriqdan aynan olindi)
    # ------------------------------------------------------------------
    labs = [
        ("wasm_os_sim", "WebAssembly-based OS Simulator",
         "os_systems",
         "Brauzer ichida ishlaydigan kichik operatsion tizim simulyatori. "
         "O'quvchi C yoki Rust'da xotira boshqaruvi (RAM), jarayon rejalashtiruvchisi "
         "(scheduler) va fayl tizimini noldan yozadi va vizual tahlil qiladi.",
         "WebAssembly, C/Rust", "wasm", "texnikum,oquv_markazi", "yuqori", 0, 0),

        ("reverse_malware_sandbox", "Reverse Engineering & Malware Sandbox",
         "cybersecurity",
         "Docker ichida izolyatsiyalangan sandbox. O'quvchilarga zararsizlantirilgan, "
         "lekin virusga o'xshash tayyor kodlar beriladi — ular teskari muhandislik "
         "(reverse engineering) orqali tahlil qilib, himoya kodi (antivirus) yozadi.",
         "Docker, sandboxing", "docker_sandbox", "texnikum,oquv_markazi", "juda_yuqori", 1, 10),

        ("edge_ai_cv_lab", "Edge AI & Computer Vision Lab",
         "ai_computer_vision",
         "TensorFlow.js yoki OpenCV.js orqali kamera oqimini real vaqtda tahlil qiluvchi "
         "neyrotarmoq. O'quvchi qo'l harakati, yuz mimikasi yoki odamlar sonini "
         "aniqlaydigan modelni yozadi va sinovdan o'tkazadi.",
         "TensorFlow.js, OpenCV.js, JS/Python", "browser_cv", "texnikum,oquv_markazi", "yuqori", 0, 20),

        ("distributed_consensus", "Distributed Systems & Consensus Lab",
         "distributed_systems",
         "Virtual tarmoq tugunlari simulyatori. Guruhlar har biri bitta server kodini "
         "yozadi, tizim ularni bitta tarmoqqa birlashtiradi va nosozliklarga qaramay "
         "ma'lumot yaxlitligini saqlash uchun Raft/Paxos konsensus algoritmini "
         "amalga oshirishlari kerak.",
         "Raft/Paxos, tarmoq simulyatsiyasi", "network_sim", "texnikum,oquv_markazi", "juda_yuqori", 1, 30),

        ("compiler_builder", "Automated Compiler Builder",
         "compilers_and_languages",
         "AST vizualizatori bilan jihozlangan muhit. O'quvchi o'zining kichik "
         "dasturlash tilini yaratadi — leksik tahlilchi (lexer) va sintaktik "
         "tahlilchi (parser) yozadi, kodning mashina kodiga o'girilishini "
         "vizual sxemalar orqali kuzatadi.",
         "Lexer/Parser, AST", "ast_visualizer", "texnikum,oquv_markazi", "juda_yuqori", 0, 40),

        ("competitive_profiling", "Compiler-Optimized Competitive Programming",
         "performance_engineering",
         "Chuqur profil analizatori — kodning har bir qatori protsessor taktini va "
         "xotirani qanchalik band qilishini ko'rsatadi. O'quvchi nafaqat masalani "
         "yechadi, balki L1/L2 kesh unumdorligini maksimal darajaga olib chiqishi kerak.",
         "Profiling, CPU cache", "profiler", "texnikum,oquv_markazi", "juda_yuqori", 0, 50),

        ("db_sharding_sim", "AI-Augmented DB Sharding & Replication Simulator",
         "databases",
         "Katta yuklamali ma'lumotlar bazasi simulyatori. O'quvchi ma'lumotlarni "
         "qismlarga bo'lish (sharding), nusxalash (replication) va indekslashni "
         "dasturlaydi; tizim simulyatsiya qilingan 10 million foydalanuvchi so'rovini "
         "yuborib, arxitektura chidamliligini vizual grafikda ko'rsatadi.",
         "Sharding, replication, load simulation", "db_sim", "texnikum,oquv_markazi", "juda_yuqori", 0, 60),

        ("neural_net_from_scratch", "Neural Network Architecture Builder",
         "artificial_intelligence",
         "Tayyor AI kutubxonalarisiz (TensorFlow/PyTorch YO'Q), faqat sof NumPy bilan "
         "ishlaydigan muhit. O'quvchi qatlamlar (layers), faollashtirish funksiyalari "
         "va backpropagation algoritmini matematik formulalar orqali noldan yozadi.",
         "Python, NumPy (sof matematika)", "numpy_sandbox", "texnikum,oquv_markazi", "juda_yuqori", 0, 70),
    ]

    for key, title, category, desc, tech, runtime, org_types, difficulty, team, order in labs:
        c.execute("""INSERT OR IGNORE INTO edu_advanced_labs
            (lab_key, title, category, description, tech_stack, runtime_type,
             allowed_org_types, difficulty, team_based, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (key, title, category, desc, tech, runtime, org_types, difficulty, team, order))

    conn.commit()
    conn.close()
    print("✅ v29 PRO — Chuqurlashgan laboratoriyalar (Advanced Labs) migratsiyasi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
