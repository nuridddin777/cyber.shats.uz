"""
SHATS CYBER EDU — MIGRATE v44: Amaliyot uchun interaktiv simulyatsiyalar
================================================================================
Ba'zi mavzular uchun (Scratch dasturlash, HTML veb-sayt) saytdan chiqmasdan
ishlaydigan interaktiv simulyator qo'shiladi. Bu — infratuzilma + 2 ta real
namuna (Scratch blok-simulyatori, HTML/CSS jonli muharrir). Boshqa mavzular
uchun simulyatorlar keyingi bosqichlarda qo'shiladi.

simulation_type qiymatlari:
  - 'scratch_blocks' : Scratch uslubidagi blok-dasturlash simulyatori
  - 'html_editor'     : HTML/CSS yozib, natijasini jonli ko'rish muharriri
  - NULL/'' — bu mavzu uchun hali simulyator yo'q (oddiy matn+amaliy ko'rinadi)
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

# (grade_label, chapter_no) -> simulation_type
SIMULATIONS = {
    ("5-sinf", 4): "scratch_blocks",       # Dasturlashni boshlash
    ("6-sinf", 5): "scratch_blocks",       # Dasturlashni o'rganish (Repeat)
    ("8-sinf", 1): "scratch_blocks",       # O'zgaruvchilar
    ("8-sinf", 2): "html_editor",          # Veb-sayt dizayni
    ("9-sinf", 21): "html_editor",         # Veb-saytlar yaratish
    ("10-11-sinf", 19): "html_editor",     # Veb uchun dasturlash
}


def _table_exists(c, name):
    return c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "edu_curriculum_topics"):
        conn.close()
        return

    if not _column_exists(c, "edu_curriculum_topics", "simulation_type"):
        c.execute("ALTER TABLE edu_curriculum_topics ADD COLUMN simulation_type TEXT DEFAULT ''")

    for (grade_label, chapter_no), sim_type in SIMULATIONS.items():
        c.execute(
            "UPDATE edu_curriculum_topics SET simulation_type=? WHERE grade_label=? AND chapter_no=?",
            (sim_type, grade_label, chapter_no)
        )

    conn.commit()
    conn.close()
    print(f"✅ v44 Interaktiv simulyatsiyalar ({len(SIMULATIONS)} ta mavzuga) muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
