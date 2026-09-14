"""
SHATS CYBER EDU — MIGRATE v42: Pro 3 amaliy + Sinf/Bo'lim/Kurs tizimi
================================================================================
1) PRO TARIF — endi har mavzuda 5 emas, 3 ta amaliy (1 Standart + 2 qo'shimcha
   Pro) ko'rsatiladi. Ortiqcha (order_no 4, 5) yozuvlar o'chiriladi.

2) SINF/BO'LIM (maktab) VA KURS (texnikum) tizimi — `edu_org_groups` jadvali
   kengaytiriladi:
     - grade_no      : maktab uchun sinf raqami (5-11), texnikum uchun kurs (1-2)
     - section_letter : maktab uchun bo'lim harfi (A, B, V ...) — texnikumda bo'sh
     - join_code      : shu aniq sinf/bo'lim/kursga ulanish uchun MAXSUS kod
                         (avvalgi umumiy "markaz ulanish kodi"dan farqli —
                         endi HAR BIR SINF/KURS o'zining alohida kodiga ega)
   Bu kodlar HAM markaz tarifni sotib olib, is_active=1 bo'lgandagina ishlaydi
   (edu_orgs.resolve_class_code funksiyasi buni tekshiradi) — xuddi umumiy
   markaz ulanish kodi kabi.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


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

    # ------------------------------------------------------------------
    # 1) PRO amaliylarini 5 tadan 3 taga tushirish
    # ------------------------------------------------------------------
    if _table_exists(c, "edu_curriculum_practicals"):
        c.execute("DELETE FROM edu_curriculum_practicals WHERE order_no > 3")

    # ------------------------------------------------------------------
    # 2) Sinf/bo'lim/kurs tizimi uchun edu_org_groups kengaytmasi
    # ------------------------------------------------------------------
    if _table_exists(c, "edu_org_groups"):
        if not _column_exists(c, "edu_org_groups", "grade_no"):
            c.execute("ALTER TABLE edu_org_groups ADD COLUMN grade_no INTEGER")
        if not _column_exists(c, "edu_org_groups", "section_letter"):
            c.execute("ALTER TABLE edu_org_groups ADD COLUMN section_letter TEXT")
        if not _column_exists(c, "edu_org_groups", "join_code"):
            c.execute("ALTER TABLE edu_org_groups ADD COLUMN join_code TEXT")

        c.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_edu_org_groups_join_code "
            "ON edu_org_groups(join_code) WHERE join_code IS NOT NULL"
        )

    conn.commit()
    conn.close()
    print("✅ v42 Pro 3-amaliy + Sinf/Bo'lim/Kurs tizimi muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
