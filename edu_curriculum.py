# ============================================================
# EDU CURRICULUM — Fan mundarijasi (sinf/kurs mavzulari) va amaliylar
# ============================================================
# Kirish nazorati BUTUNLAY tashkilot (org) tarifiga bog'liq — foydalanuvchi
# (o'qituvchi/o'quvchi) darajasida EMAS. Shu sababli "Markaz Pro" tarifni
# sotib olganda, o'sha tashkilotdagi BARCHA o'qituvchi va o'quvchilar
# avtomatik Pro darajadagi mazmunni (5 amaliy + rasm tavsiyalari) ko'radi —
# alohida "foydalanuvchi Pro ligini" belgilash SHART EMAS.
#
# Texnikum uchun: 10-11-sinf darsligi mavzulari "Informatika asoslari"
# nomi ostida 1-2-kurs uchun ishlatiladi — buni edu_curriculum_topics
# jadvalidagi `applies_to_org_types` ustuni orqali amalga oshiramiz
# (masalan bir xil mavzu qatoriga 'maktab,texnikum' yozilsa, ikkala
# turdagi tashkilotga ham chiqadi).
# ============================================================
from edu_orgs import EduOrgError, get_org_tariff


def list_grades_for_org_type(conn, org_type):
    """Shu tashkilot turi uchun mavjud sinf/kurs yorliqlarini qaytaradi."""
    rows = conn.execute(
        "SELECT DISTINCT grade_label FROM edu_curriculum_topics "
        "WHERE is_active=1 AND (',' || applies_to_org_types || ',') LIKE ('%,' || ? || ',%') "
        "ORDER BY grade_label",
        (org_type,),
    ).fetchall()
    return [r["grade_label"] for r in rows]


def list_topics(conn, org_type, grade_label):
    """Berilgan tashkilot turi + sinf/kurs uchun mavzular ro'yxati (bob tartibida)."""
    rows = conn.execute(
        "SELECT * FROM edu_curriculum_topics "
        "WHERE is_active=1 AND grade_label=? "
        "AND (',' || applies_to_org_types || ',') LIKE ('%,' || ? || ',%') "
        "ORDER BY sort_order, chapter_no",
        (grade_label, org_type),
    ).fetchall()
    return rows


def get_topic_or_raise(conn, topic_id):
    topic = conn.execute("SELECT * FROM edu_curriculum_topics WHERE id=? AND is_active=1", (topic_id,)).fetchone()
    if not topic:
        raise EduOrgError("Bunday mavzu topilmadi")
    return topic


def is_org_pro(conn, org_id):
    """Tashkilot Pro tarifga egami (has_advanced_labs=1) — shu bayroq
    'Markaz Pro' bo'lsa BARCHA o'qituvchi/o'quvchiga avtomatik tarqaladi,
    chunki tekshiruv org_id orqali, foydalanuvchi orqali emas."""
    try:
        org, tarif = get_org_tariff(conn, org_id)
    except EduOrgError:
        return False, None, None
    return bool(tarif["has_advanced_labs"]), org, tarif


def list_practicals_for_topic(conn, org_id, topic_id):
    """
    Tashkilot tarifiga qarab amaliylarni qaytaradi:
      - Standart -> faqat order_no=1 (1 ta amaliy)
      - Pro      -> order_no 1..5 (5 tagacha amaliy), rasm tavsiyalari bilan
    Qaytaradi: (topic, practicals_list, is_pro, locked_count)
    """
    topic = get_topic_or_raise(conn, topic_id)
    is_pro, org, tarif = is_org_pro(conn, org_id)

    all_rows = conn.execute(
        "SELECT * FROM edu_curriculum_practicals WHERE topic_id=? ORDER BY order_no", (topic_id,)
    ).fetchall()

    if is_pro:
        visible = all_rows
        locked_count = 0
    else:
        visible = [r for r in all_rows if not r["is_pro_only"]]
        locked_count = len(all_rows) - len(visible)

    return topic, visible, is_pro, locked_count
