# ============================================================
# CYBER SHATS — AI shaxsiylashtirilgan tavsiyalar
#
# O'quvchining progress (yo'nalish kurslari, test natijalari, tugallangan
# darslar) asosida AI (Gemini/Anthropic) shaxsiy tavsiyalar generatsiya
# qiladi: nimani takrorlash kerak, keyingi qadam nima, qayerda kuchsiz.
# ============================================================
import json
import re

from ai import call_ai_assistant, is_ai_configured
from db import query_all, query_one


def _extract_json(text: str):
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except (ValueError, TypeError):
        pass
    start = cleaned.find("[")
    end = cleaned.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except (ValueError, TypeError):
            pass
    return None


def _valid_rec(r: dict) -> bool:
    return isinstance(r, dict) and str(r.get("title", "")).strip() and str(r.get("description", "")).strip()


def gather_student_snapshot(user_id: int) -> dict:
    """O'quvchining progress'ini bazadan yig'ib, AI'ga yuborish uchun qisqa
    matn-xulosa tayyorlaydi (raw SQL natijalarini emas — AI tushunadigan
    tabiiy tilga yaqin xulosa)."""
    user = query_one("SELECT ism, primary_direction_id FROM users WHERE id=?", (user_id,))
    direction = None
    if user and user.get("primary_direction_id"):
        direction = query_one("SELECT name_uz FROM directions WHERE id=?", (user["primary_direction_id"],))

    enrollments = query_all(
        "SELECT c.title, c.level, e.progress_percent, e.completed_at, d.name_uz as direction_name "
        "FROM enrollments e JOIN courses c ON c.id=e.course_id JOIN directions d ON d.id=c.direction_id "
        "WHERE e.user_id=? ORDER BY e.started_at DESC LIMIT 15", (user_id,))

    test_results = query_all(
        "SELECT t.title, ta.score, ta.total, c.title as course_title FROM test_attempts ta "
        "JOIN tests t ON t.id=ta.test_id LEFT JOIN courses c ON c.id=t.course_id "
        "WHERE ta.user_id=? ORDER BY ta.completed_at DESC LIMIT 15", (user_id,))

    rating = query_one("SELECT total_score, courses_done, tests_passed FROM user_ratings WHERE user_id=?", (user_id,))

    return {
        "ism": user["ism"] if user else "Talaba",
        "direction": direction["name_uz"] if direction else None,
        "enrollments": [dict(e) for e in enrollments],
        "test_results": [dict(t) for t in test_results],
        "rating": dict(rating) if rating else None,
    }


def _build_prompt(snapshot: dict) -> str:
    lines = [f"O'quvchi: {snapshot['ism']}"]
    if snapshot["direction"]:
        lines.append(f"Asosiy yo'nalishi: {snapshot['direction']}")

    if snapshot["enrollments"]:
        lines.append("\nYozilgan kurslar va progress:")
        for e in snapshot["enrollments"]:
            status = "TUGATGAN" if e["completed_at"] else f"{e['progress_percent']}% bajarilgan"
            lines.append(f"  - {e['title']} ({e['level']}, {e['direction_name']}): {status}")
    else:
        lines.append("\nHali birorta kursga yozilmagan.")

    if snapshot["test_results"]:
        lines.append("\nTest natijalari (oxirgi urinishlar):")
        for t in snapshot["test_results"]:
            pct = round(t["score"] / t["total"] * 100) if t["total"] else 0
            weak = " ⚠️ KUCHSIZ" if pct < 60 else ""
            lines.append(f"  - {t['title']} ({t['course_title']}): {t['score']}/{t['total']} ({pct}%){weak}")
    else:
        lines.append("\nHali birorta test topshirmagan.")

    if snapshot["rating"]:
        r = snapshot["rating"]
        lines.append(f"\nUmumiy: {r['courses_done']} ta kurs tugatgan, {r['tests_passed']} ta test o'tgan, "
                     f"jami ball: {r['total_score']}.")

    return "\n".join(lines)


def generate_recommendations(user_id: int, count: int = 4):
    """AI orqali shaxsiy tavsiyalar generatsiya qiladi.
    Qaytaradi: (recommendations: list[dict] | None, error: str | None)
    Har bir dict: {"title","description","type"} — type: "davom_etish"|"takrorlash"|"yangi_yonalish"|"tabrik"
    """
    if not is_ai_configured():
        return None, ("AI ulanmagan — .env fayliga GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY "
                       "qo'shilishi kerak.")

    snapshot = gather_student_snapshot(user_id)
    student_summary = _build_prompt(snapshot)

    system = (
        "Sen CYBER SHATS ta'lim platformasida o'quvchiga shaxsiy maslahat beruvchi AI repetitorsan. "
        "O'quvchining progress va test natijalari senga beriladi. Vazifang — unga aniq, harakatga "
        "chorlaydigan tavsiyalar berish: qaysi mavzuni takrorlashi kerak (test natijasi past bo'lsa), "
        "qaysi kursni davom ettirishi kerak, keyingi qadam nima. Agar yaxshi natijalar bo'lsa — "
        "tabriklab, keyingi bosqichni taklif qil. "
        "JAVOBING FAQAT sof JSON massiv bo'lsin, boshqa matn yo'q. Format: "
        '[{"type":"davom_etish|takrorlash|yangi_yonalish|tabrik","title":"qisqa sarlavha (5-8 so\'z)",'
        '"description":"1-2 gapli aniq tavsiya"}, ...] '
        f"Aniq {count} ta tavsiya ber, o'zbek tilida, samimiy va motivatsion ohangda."
    )
    reply, is_live = call_ai_assistant("umumiy", student_summary, system_override=system)
    if not is_live:
        return None, f"AI javob bermadi: {reply[:200]}"

    data = _extract_json(reply)
    if not isinstance(data, list):
        return None, "AI javobini o'qib bo'lmadi (format xato)."
    recs = [r for r in data if _valid_rec(r)]
    if not recs:
        return None, "AI qaytargan tavsiyalar formatga mos emas edi."
    return recs, None


def generate_admin_insights(stats: dict):
    """Admin uchun BEPUL, tezkor AI xulosasi — platforma statistikasi asosida
    e'tibor talab qiladigan narsalarni ko'rsatadi. Har doim admin uchun
    bepul (CODE/kunlik limitga bog'liq emas — bu route darajasida ta'minlanadi)."""
    if not is_ai_configured():
        return None, ("AI ulanmagan — .env fayliga GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY "
                       "qo'shilishi kerak.")

    summary = (
        f"So'nggi 7 kunlik yangi foydalanuvchilar: {stats.get('new_users_7d', 0)}\n"
        f"Jami faol foydalanuvchilar: {stats.get('total_users', 0)}\n"
        f"Bugungi to'lovlar (UZS): {stats.get('today_revenue', 0):,}\n"
        f"Eng mashhur kurs: {stats.get('top_course', 'nomalum')} ({stats.get('top_course_students', 0)} o'quvchi)\n"
        f"Testsiz kurslar soni: {stats.get('courses_without_test', 0)}\n"
        f"Bloklangan xavfsizlik hodisalari (24 soat): {stats.get('security_events_24h', 0)}\n"
    )
    system = (
        "Sen CYBER SHATS platformasi uchun admin brifing tayyorlovchi AI tahlilchisan. "
        "Quyidagi statistika asosida ADMINGA 3-4 ta QISQA, aniq va harakatga chorlaydigan xulosa ber "
        "(masalan: qaysi ko'rsatkich yaxshi, qaysi biriga e'tibor kerak, nima qilish tavsiya etiladi). "
        "Har bir xulosa 1 gapdan iborat bo'lsin. Faqat matn qaytar, ro'yxat shaklida (har biri yangi qatorda, "
        "boshida '•' belgisi bilan). O'zbek tilida, professional ohangda."
    )
    reply, is_live = call_ai_assistant("umumiy", summary, system_override=system)
    if not is_live:
        return None, f"AI javob bermadi: {reply[:200]}"
    return reply, None
