"""
SHATS CYBER V2 — MIGRATE v31: Maxsus (Pro) versiya — 20 ta innovatsion g'oya
================================================================================
Bu — Edu tashkilotlariga emas, balki SHATS CYBER asosiy platformasining
JISMONIY FOYDALANUVCHILARIGA (individual talaba/dasturchi, mavjud
`users.plan` — pro/cyber_pro/vip) mo'ljallangan xususiyatlar katalogi:

  1.  AI-Code Reviewer          11. Real-time Collaborative Coding
  2.  Sandbox IDE (WebContainers)12. Voice Assistant (ko'zi ojizlar uchun)
  3.  Gamified RPG Roadmap       13. AI Bug Explainer & Fixer
  4.  Peer-to-Peer Interview Sim 14. "Speed Coding" Arena
  5.  AI Personalized Syllabus   15. "Figma to Code" Sandbox
  6.  Interactive Git Flow Sim   16. Open Source Contribution Hub
  7.  Bug Hunting Playground     17. Database Visualizer Playground
  8.  Mock API Generator         18. AI Resume & LinkedIn Optimizer
  9.  Automatic Portfolio Builder19. Architecture Designer Lab
  10. Cyber-Attack Sandbox       20. Code Translation Playground

Har biri uchun kirish nazorati (gating) mavjud kod bazasidagi naqsh bilan
BIR XIL: `user.plan in ('pro','cyber_pro','vip')` YOKI
`user.role in ('admin','super_admin','mentor')` (qarang: app.py'dagi
ko'plab shunga o'xshash tekshiruvlar, masalan 576-qator).

MUHIM CHEKLOV: bu ham FAQAT katalog + kirish nazorati + progress
kuzatuvi. Har birining haqiqiy ijro muhiti (WebContainers, WebRTC,
Claude API integratsiyasi, Figma API va h.k.) — alohida, ko'p sonli
muhandislik ishlari. Ustuvorlik: infratuzilmasi ENG SODDA
bo'lganlaridan (masalan AI Bug Explainer, AI Resume Optimizer — bular
faqat Claude API chaqiruvi) boshlash tavsiya etiladi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS platform_innovation_features (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feature_key TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL,
        tech_stack TEXT DEFAULT '',
        runtime_type TEXT NOT NULL,        -- ai_api | webcontainer | gamification | webrtc |
                                            -- websocket | figma_api | oss_integration | visualization
        required_plan TEXT DEFAULT 'pro',  -- pro | cyber_pro | vip (users.plan bilan mos)
        is_active INTEGER DEFAULT 1,
        sort_order INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS platform_innovation_progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        feature_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'started',     -- started|in_progress|completed
        data_json TEXT DEFAULT '{}',       -- har xil turdagi progress ma'lumoti (moslashuvchan)
        score REAL,
        started_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(feature_id) REFERENCES platform_innovation_features(id),
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(feature_id, user_id)
    )""")

    features = [
        ("ai_code_reviewer", "AI-Code Reviewer", "ai_tools",
         "Yuklangan kodni Claude API orqali tahlil qilib, xavfsizlik "
         "kamchiliklari, optimizatsiya kerak bo'lgan joylar va clean code "
         "qoidalariga mosligini ballab beradi.", "Claude API", "ai_api", "pro", 10),

        ("sandbox_ide", "Sandbox IDE", "dev_environment",
         "Hech narsa o'rnatmasdan brauzerda to'liq kod yozish va ishga "
         "tushirish muhiti (WebContainers/Docker asosida virtual Linux).",
         "WebContainers, Docker", "webcontainer", "pro", 20),

        ("gamified_rpg_roadmap", "Gamified RPG Roadmap", "gamification",
         "O'quv jarayonini RPG o'yiniga aylantiradi — qahramon tanlash, "
         "har dars bitta 'boss', level va sovrinlar.", "Gamification engine",
         "gamification", "pro", 30),

        ("p2p_interview_sim", "Peer-to-Peer Interview Simulator", "career",
         "WebRTC orqali ikki talaba tasodifiy ulanib, bir-birini texnik "
         "suhbatga tayyorlaydi va baholaydi.", "WebRTC", "webrtc", "pro", 40),

        ("ai_personalized_syllabus", "AI-driven Personalized Syllabus", "ai_tools",
         "Boshlang'ich test asosida AI har talaba uchun individual o'quv "
         "dasturi (zaif fanlarga qo'shimcha darslar) tuzadi.", "Claude API",
         "ai_api", "pro", 50),

        ("git_flow_simulator", "Interactive Git Flow Simulator", "dev_tools",
         "Git buyruqlari yozilganda branch/merge animatsiyasini vizual "
         "ko'rsatuvchi laboratoriya.", "Git internals, animation", "visualization", "pro", 60),

        ("bug_hunting_playground", "Bug Hunting Playground", "dev_tools",
         "Ataylab xato qoldirilgan kodlar ombori — talaba xatoni topib "
         "refactoring qiladi.", "Static analysis", "visualization", "pro", 70),

        ("mock_api_generator", "Mock API Generator", "dev_tools",
         "Frontend talabalar uchun backend yozmasdan tayyor soxta API "
         "ma'lumotlari (mahsulotlar, rasmlar) xizmati.", "REST/JSON generator",
         "webcontainer", "pro", 80),

        ("auto_portfolio_builder", "Automatic Portfolio Builder", "career",
         "Talabaning eng yaxshi 5 loyihasi va reytingini avtomatik chiroyli "
         "portfolio saytiga yig'adi.", "Static site generator", "visualization", "pro", 90),

        ("cyber_attack_sandbox", "Cyber-Attack Sandbox", "cybersecurity",
         "Virtual bulut muhitida zaif 'qurbon' sayt — SQL Injection/XSS "
         "hujumlarini xavfsiz sinab ko'rish va himoyalashni o'rganish.",
         "Isolated cloud sandbox", "webcontainer", "cyber_pro", 100),

        ("realtime_collab_coding", "Real-time Collaborative Coding", "dev_tools",
         "Bir nechta talaba bitta kod ustida real vaqtda birgalikda ishlashi "
         "(Google Docs kabi).", "WebSocket, OT/CRDT", "websocket", "pro", 110),

        ("voice_assistant_accessibility", "Smart AI-Voice Assistant (ko'zi ojizlar uchun)",
         "accessibility",
         "Butun platforma va kod muhitini ovozli buyruqlar va ekran o'quvchi "
         "AI (TTS/STT) orqali boshqarish imkoniyati.", "TTS/STT", "ai_api", "pro", 120),

        ("ai_bug_explainer", "AI Bug Explainer & Fixer", "ai_tools",
         "Murakkab xato loglarini Claude API orqali sodda tilda tushuntirib, "
         "3 xil to'g'rilash variantini taklif qiladi.", "Claude API", "ai_api", "pro", 130),

        ("speed_coding_arena", "\"Speed Coding\" Arena", "competitive",
         "Ikki talabani WebSocket orqali bog'lab, kim birinchi xatosiz "
         "yechsa g'olib bo'ladigan tezkor duel tizimi.", "WebSocket", "websocket", "pro", 140),

        ("figma_to_code_sandbox", "\"Figma to Code\" Sandbox", "frontend",
         "Figma dizayni integratsiyasi — talaba yozgan kod dizayn bilan "
         "piksel-piksel solishtiriladi va farqlar ko'rsatiladi.", "Figma API",
         "figma_api", "pro", 150),

        ("oss_contribution_hub", "Open Source Contribution Hub", "career",
         "Kichik ochiq kodli loyihalar ro'yxati — talaba issue'larni hal "
         "qilib GitHub profilini shakllantiradi.", "GitHub API", "oss_integration", "pro", 160),

        ("db_visualizer_playground", "Database Visualizer Playground", "backend",
         "SQL so'rovi yozilganda jadvallar orasidagi qidiruv/birlashish "
         "jarayonini interaktiv 2D grafikda ko'rsatadi.", "SQL engine, visualization",
         "visualization", "pro", 170),

        ("ai_resume_optimizer", "AI Resume & LinkedIn Optimizer", "career",
         "Yuklangan rezyumeni Claude tahlil qilib, grammatik xato va zaif "
         "jumlalarni aniqlaydi, LinkedIn uchun tavsiya beradi.", "Claude API",
         "ai_api", "pro", 180),

        ("architecture_designer_lab", "Architecture Designer Lab", "system_design",
         "Server/DB/Cache/Load Balancer bloklarini ulab tizim arxitekturasi "
         "chizish, AI zaif nuqtalarni tahlil qiladi.", "Claude API, diagram engine",
         "ai_api", "cyber_pro", 190),

        ("code_translation_playground", "Code Translation Playground", "ai_tools",
         "Bir tildagi kodni boshqa tilga o'girish va ikki til farqlarini "
         "batafsil tushuntirish.", "Claude API", "ai_api", "pro", 200),
    ]

    for key, title, category, desc, tech, runtime, plan, order in features:
        c.execute("""INSERT OR IGNORE INTO platform_innovation_features
            (feature_key, title, category, description, tech_stack, runtime_type,
             required_plan, sort_order)
            VALUES (?,?,?,?,?,?,?,?)""",
            (key, title, category, desc, tech, runtime, plan, order))

    conn.commit()
    conn.close()
    print("✅ v31 Maxsus versiya — 20 ta innovatsion g'oya katalogi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
