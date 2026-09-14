# ============================================================
# CYBER SHATS — AI test generatsiyasi, tekshiruvi va tuzatishi
#
# Mavjud ai.py (Gemini/Anthropic) infratuzilmasidan foydalanadi — yangi
# API kalit yoki provayder qo'shilmaydi. Uchta asosiy imkoniyat:
#   1) generate_test_questions()      — AI yangi test savollari YARATADI
#   2) review_and_fix_test_questions() — AI mavjud savollarni TEKSHIRADI
#                                         va xato topsa TUZATADI
#   3) check_code_exercise()          — AI talabaning kod mashqini
#                                         TEKSHIRADI (to'g'ri/xato + izoh)
# ============================================================
import json
import re

from ai import call_ai_assistant, is_ai_configured


def _extract_json(text: str):
    """AI javobidan JSON qismini ajratib oladi (```json fence, ortiqcha matn
    bo'lishi mumkin — shularni tozalab, json.loads bilan urinadi)."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except (ValueError, TypeError):
        pass
    # Matn ichida qayerdadir massiv/obyekt bo'lishi mumkin — eng kattasini topamiz
    for open_ch, close_ch in (("[", "]"), ("{", "}")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start:end + 1]
            try:
                return json.loads(candidate)
            except (ValueError, TypeError):
                continue
    return None


def _valid_question(q: dict) -> bool:
    if not isinstance(q, dict):
        return False
    required = ("question", "a", "b", "c", "d", "correct")
    if not all(k in q and str(q[k]).strip() for k in required):
        return False
    return str(q["correct"]).strip().lower() in ("a", "b", "c", "d")


def generate_test_questions(course_title: str, course_level: str, direction_name: str,
                             count: int = 5, existing_questions=None):
    """AI orqali yangi test savollari yaratadi.
    Qaytaradi: (questions: list[dict] | None, error: str | None)
    Har bir dict: {"question","a","b","c","d","correct"} — correct: "a"|"b"|"c"|"d"
    """
    if not is_ai_configured():
        return None, ("AI ulanmagan — .env fayliga GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY "
                       "qo'shilishi kerak.")
    count = max(1, min(count, 15))
    existing_note = ""
    if existing_questions:
        titles = "; ".join(str(q)[:90] for q in existing_questions[:30])
        existing_note = f"\n\nQUYIDAGI savollar ALLAQACHON mavjud — ularni AYNAN TAKRORLAMANG:\n{titles}"

    system = (
        "Sen IT ta'lim platformasi (CYBER SHATS) uchun sifatli test savollari yaratuvchi AI'san. "
        "JAVOBING FAQAT sof JSON massiv bo'lishi kerak — hech qanday izoh, sarlavha yoki ```markdown yo'q. "
        'Format: [{"question":"...","a":"...","b":"...","c":"...","d":"...","correct":"a"}, ...] '
        "Har bir savolda FAQAT bitta to'g'ri javob bo'lsin, variantlar bir-biriga o'xshamasin, "
        "savol aniq va bir ma'noli bo'lsin."
    )
    user_message = (
        f"«{course_title}» kursi ({direction_name} yo'nalishi, daraja: {course_level}) bo'yicha "
        f"{count} ta ko'p tanlovli test savoli yarat. O'zbek tilida, kursning haqiqiy mavzusiga mos, "
        f"amaliy bilimni tekshiradigan savollar bo'lsin (faqat nazariy ta'rif emas)."
        f"{existing_note}"
    )
    reply, is_live = call_ai_assistant("umumiy", user_message, system_override=system)
    if not is_live:
        return None, f"AI javob bermadi: {reply[:200]}"

    data = _extract_json(reply)
    if not isinstance(data, list):
        return None, "AI javobini o'qib bo'lmadi (JSON format noto'g'ri). Qayta urinib ko'ring."
    questions = [q for q in data if _valid_question(q)]
    if not questions:
        return None, "AI qaytargan savollar formatga mos emas edi. Qayta urinib ko'ring."
    return questions, None


def review_and_fix_test_questions(course_title: str, questions: list):
    """Mavjud test savollarini AI orqali tekshiradi — xato/tushunarsiz/noto'g'ri
    javobli savollarni TUZATADI. `questions`: [{"id","question","a","b","c","d","correct"}, ...]
    Qaytaradi: (results: list[dict] | None, error: str | None)
    Har bir natija: {"id", "changed": bool, "question","a","b","c","d","correct", "note"}
    """
    if not is_ai_configured():
        return None, ("AI ulanmagan — .env fayliga GEMINI_API_KEY (tekin) yoki ANTHROPIC_API_KEY "
                       "qo'shilishi kerak.")
    if not questions:
        return [], None

    payload = [{"id": q["id"], "question": q["question"], "a": q["a"], "b": q["b"],
                "c": q["c"], "d": q["d"], "correct": q["correct"]} for q in questions]

    system = (
        "Sen test savollarini sifat nazoratidan o'tkazuvchi AI'san. Senga savollar ro'yxati JSON "
        "holida beriladi. Har birini tekshir: savol aniqmi, variantlar mantiqan to'g'rimi, "
        "'correct' maydonida ko'rsatilgan javob HAQIQATDA to'g'rimi. Xato/noaniq narsa topsang — TUZAT. "
        "Xato bo'lmasa — savolni O'ZGARTIRMASDAN qaytar. "
        "JAVOBING FAQAT sof JSON massiv bo'lsin, boshqa matn yo'q. Format: "
        '[{"id":<id>,"changed":true/false,"question":"...","a":"...","b":"...","c":"...","d":"...","correct":"a","note":"nima tuzatildi yoki \'xato topilmadi\'"}, ...]'
    )
    user_message = f"«{course_title}» kursi uchun quyidagi savollarni tekshir va kerak bo'lsa tuzat:\n{json.dumps(payload, ensure_ascii=False)}"

    reply, is_live = call_ai_assistant("umumiy", user_message, system_override=system)
    if not is_live:
        return None, f"AI javob bermadi: {reply[:200]}"

    data = _extract_json(reply)
    if not isinstance(data, list):
        return None, "AI javobini o'qib bo'lmadi (JSON format noto'g'ri). Qayta urinib ko'ring."
    results = []
    for item in data:
        if not isinstance(item, dict) or "id" not in item:
            continue
        if not _valid_question(item):
            continue
        results.append(item)
    if not results:
        return None, "AI natijasi bo'sh yoki formatga mos emas edi."
    return results, None


def check_code_exercise(exercise_prompt: str, student_code: str, run_output: str, run_success: bool):
    """Talabaning kod mashqini AI orqali tekshiradi: topshiriqni haqiqatda
    bajardimi yoki yo'qmi. Qaytaradi: (passed: bool, feedback: str, is_live: bool)"""
    system = (
        "Sen dasturlash mashqlarini tekshiruvchi AI repetitorsan. Senga topshiriq matni, talabaning kodi "
        "va uning ishga tushirilgan natijasi beriladi. Vazifang: kod haqiqatda topshiriqni bajarayaptimi "
        "yoki yo'qmi, aniq baholash. "
        "JAVOBINGNI albatta shu formatda boshla: birinchi qatorda FAQAT 'NATIJA: TO\\'G\\'RI' yoki "
        "'NATIJA: XATO' deb yoz (boshqa hech narsa qo'shmasdan), so'ng yangi qatordan qisqa "
        "(2-4 gap) izoh yoz — nima yaxshi, nima yetishmayapti, o'zbek tilida."
    )
    user_message = (
        f"TOPSHIRIQ: {exercise_prompt}\n\n"
        f"TALABANING KODI:\n```\n{student_code}\n```\n\n"
        f"NATIJA ({'muvaffaqiyatli bajarildi' if run_success else 'xato bilan tugadi'}):\n{run_output[:1500]}"
    )
    reply, is_live = call_ai_assistant("kod", user_message, system_override=system)
    if not is_live:
        return False, reply, False

    first_line = reply.strip().split("\n", 1)[0].upper()
    passed = "TO'G'RI" in first_line or "TOʻGʻRI" in first_line or "TOG'RI" in first_line
    # 'NATIJA:' qatorini olib tashlab, faqat izohni ko'rsatamiz
    feedback = reply.strip()
    if "\n" in feedback:
        feedback = feedback.split("\n", 1)[1].strip()
    return passed, feedback or reply, True
