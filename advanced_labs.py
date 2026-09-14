# ============================================================
# ADVANCED LABS — Pro versiya uchun 8 ta chuqurlashgan laboratoriya
# ============================================================
# Bu modul database/migrate_v29_advanced_labs.py orqali yaratilgan
# katalog ustida ishlaydi. Vazifasi:
#   1) Tashkilot Pro tarifga ega ekanligini tekshirish (gating)
#   2) Tashkilot turiga mos laboratoriyalar ro'yxatini chiqarish
#      (masalan maktab uchun bu laboratoriyalar umuman ko'rinmaydi —
#      texnik topshiriqda ular texnikum/markaz darajasidagi mavzular)
#   3) O'quvchi topshirig'ini boshlash / yuborish / baholash
#
# MUHIM: bu yerda HAR BIR labning haqiqiy ijro dvigateli (masalan WASM
# kompilyatori, Docker orkestratori, TensorFlow.js integratsiyasi) YO'Q —
# faqat katalog + kirish nazorati + topshiriq hayot sikli boshqaruvi bor.
# Har bir runtime alohida so'rov bo'yicha, birma-bir qurilishi kerak.

import json
from edu_orgs import EduOrgError, get_org_tariff


def list_labs_for_org(conn, org_id):
    """
    Tashkilot uchun ko'rinadigan laboratoriyalar ro'yxatini qaytaradi.
    - Tarif Pro bo'lmasa -> bo'sh ro'yxat + sabab
    - org_type mos kelmasa (masalan maktab) -> bo'sh ro'yxat + sabab
    """
    org, tarif = get_org_tariff(conn, org_id)

    if not tarif["has_advanced_labs"]:
        return [], "Bu tashkilot tarifi Pro emas — chuqurlashgan laboratoriyalar yopiq"

    rows = conn.execute(
        "SELECT * FROM edu_advanced_labs WHERE is_active=1 ORDER BY sort_order"
    ).fetchall()

    visible = [r for r in rows if org["org_type"] in r["allowed_org_types"].split(",")]

    if not visible:
        return [], f"'{org['org_type']}' turi uchun hozircha chuqurlashgan laboratoriya yo'q"

    return visible, "OK"


def get_lab_or_raise(conn, lab_key):
    lab = conn.execute("SELECT * FROM edu_advanced_labs WHERE lab_key=? AND is_active=1", (lab_key,)).fetchone()
    if not lab:
        raise EduOrgError(f"'{lab_key}' laboratoriyasi topilmadi yoki faol emas")
    return lab


def check_student_can_access_lab(conn, student_id, lab_key):
    """
    O'quvchi shu labga kira oladimi tekshiradi:
      - o'quvchining tashkiloti Pro tarifga ega bo'lishi kerak
      - tashkilot turi lab uchun ruxsat etilgan bo'lishi kerak
    """
    student = conn.execute("SELECT * FROM edu_students WHERE id=?", (student_id,)).fetchone()
    if not student:
        raise EduOrgError("O'quvchi topilmadi")

    lab = get_lab_or_raise(conn, lab_key)
    org, tarif = get_org_tariff(conn, student["org_id"])

    if not tarif["has_advanced_labs"]:
        raise EduOrgError("Bu tashkilot Pro tarifga ega emas — laboratoriya yopiq")
    if org["org_type"] not in lab["allowed_org_types"].split(","):
        raise EduOrgError(f"Bu laboratoriya '{org['org_type']}' turi uchun mo'ljallanmagan")

    return lab


def start_submission(conn, student_id, lab_key, team_id=None):
    """O'quvchi (yoki jamoa) labni boshlaganda yangi urinish yozuvi ochadi."""
    lab = check_student_can_access_lab(conn, student_id, lab_key)

    prev_attempts = conn.execute(
        "SELECT COUNT(*) c FROM edu_advanced_lab_submissions WHERE student_id=? AND lab_id=?",
        (student_id, lab["id"])).fetchone()["c"]

    cur = conn.execute("""
        INSERT INTO edu_advanced_lab_submissions
            (lab_id, student_id, team_id, status, attempt_number)
        VALUES (?,?,?, 'in_progress', ?)
    """, (lab["id"], student_id, team_id, prev_attempts + 1))
    conn.commit()
    return cur.lastrowid


def submit_lab_work(conn, submission_id, code_text="", file_path=""):
    """O'quvchi ishini yuboradi (baholash kutilmoqda)."""
    conn.execute("""
        UPDATE edu_advanced_lab_submissions
        SET code_text=?, file_path=?, status='submitted', submitted_at=datetime('now')
        WHERE id=?
    """, (code_text, file_path, submission_id))
    conn.commit()


def grade_submission(conn, submission_id, score, metrics: dict = None, feedback=""):
    """
    Baholash (hozircha qo'lda/ tashqi tekshiruvchi orqali; keyingi bosqichda
    har bir runtime o'zining avtomatik baholovchisini ulaydi, masalan
    profiler labida metrics={'latency_ns':..., 'cache_hit_rate':...}).
    """
    conn.execute("""
        UPDATE edu_advanced_lab_submissions
        SET score=?, metrics_json=?, feedback=?, status='graded', graded_at=datetime('now')
        WHERE id=?
    """, (score, json.dumps(metrics or {}, ensure_ascii=False), feedback, submission_id))
    conn.commit()
