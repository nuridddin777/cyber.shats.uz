# ============================================================
# CYBER SHATS — Kod muharriri va AI mashq yordami (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required, api_login_required
from db import query_one, execute, log_action
from utils import api_response
from coins import ensure_ai_access_code_help
from ai import call_ai_assistant
import ai_testgen
import code_runner

codehelp_bp = Blueprint("codehelp_bp", __name__)


def complete_lesson(slug, lesson_id):
    """courses_routes.py'dagi bilan bir xil — kechiktirilgan import."""
    from courses_routes import complete_lesson as _real_fn
    return _real_fn(slug, lesson_id)


@codehelp_bp.route("/api/code/exercise-help", methods=["POST"])
@api_login_required
def api_code_exercise_help():
    """AI yordamchi — talabaning joriy kodi va mashq matni asosida maqsadli yordam beradi
    (to'g'ridan-to'g'ri tayyor javobni bermaydi, tushuntiradi/yo'naltiradi)."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id")
    student_code = (data.get("code") or "").strip()
    question = (data.get("question") or "").strip()
    run_error = (data.get("run_error") or "").strip()

    lesson = query_one("SELECT * FROM lessons WHERE id=?", (lesson_id,)) if lesson_id else None
    if not lesson:
        return api_response(False, error="Dars topilmadi")

    ok, gate_msg = ensure_ai_access_code_help(user["id"])
    if not ok:
        return api_response(False, error=gate_msg)

    system_override = (
        "Sen CYBER SHATS platformasida dasturlash o'quvchisiga yordam beruvchi AI repetitorsan. "
        f"Talaba quyidagi mashq ustida ishlayapti:\n\nMASHQ: {lesson['exercise_prompt']}\n\n"
        f"YASHIRIN MASLAHAT (talabaga to'g'ridan-to'g'ri aytilmasin, faqat yo'naltirish uchun): {lesson.get('exercise_hint','')}\n\n"
        "QOIDALAR: To'liq tayyor yechim/kodni bermang. Xatoni tushuntiring, qaysi tushuncha yetishmayotganini "
        "ko'rsating, keyingi qadamni taklif qiling — lekin talaba o'zi yozishi kerak. Qisqa, aniq, o'zbek tilida javob ber."
    )
    user_message = f"Mening joriy kodim:\n```\n{student_code}\n```\n"
    if run_error:
        user_message += f"\nDastur ishga tushganda bu xato chiqdi:\n{run_error}\n"
    user_message += f"\nSavolim: {question or 'Bu yerda nima xato, keyingi qadam nima?'}"

    reply, is_live = call_ai_assistant("kod", user_message, system_override=system_override)
    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], "kod_mashq", "user", f"[Dars #{lesson_id}] {question or run_error or student_code[:200]}"))
    execute("INSERT INTO ai_messages (user_id, assistant_type, role, content) VALUES (?,?,?,?)",
            (user["id"], "kod_mashq", "assistant", reply))
    return api_response(True, data={"reply": reply, "is_live": is_live})


@codehelp_bp.route("/api/code/exercise-check", methods=["POST"])
@api_login_required
def api_code_exercise_check():
    """AI orqali talaba mashqni HAQIQATDA to'g'ri bajarganmi-yo'qmi tekshiradi
    (oddiy 'ishladi/ishlamadi' emas — topshiriqqa mosligini baholaydi).
    To'g'ri bo'lsa darsni avtomatik yakunlangan deb belgilaydi + bonus XP."""
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    lesson_id = data.get("lesson_id")
    student_code = (data.get("code") or "").strip()
    run_output = (data.get("run_output") or "").strip()
    run_success = bool(data.get("run_success"))

    lesson = query_one("SELECT * FROM lessons WHERE id=?", (lesson_id,)) if lesson_id else None
    if not lesson:
        return api_response(False, error="Dars topilmadi")
    if not student_code:
        return api_response(False, error="Avval kodni ishga tushiring.")

    ok, gate_msg = ensure_ai_access_code_help(user["id"])
    if not ok:
        return api_response(False, error=gate_msg)

    passed, feedback, is_live = ai_testgen.check_code_exercise(
        lesson["exercise_prompt"], student_code, run_output, run_success)

    if passed:
        course = query_one("SELECT id, slug FROM courses WHERE id=?", (lesson["course_id"],))
        already_done = query_one("SELECT is_done FROM lesson_progress WHERE user_id=? AND lesson_id=?",
                                 (user["id"], lesson_id))
        if course and not (already_done and already_done["is_done"]):
            complete_lesson(course["slug"], lesson_id)  # progress%, XP, sertifikat va h.k. shu yerda hisoblanadi
            log_action(user["id"], "ai_exercise_passed", details=f"lesson:{lesson_id}", ip=request.remote_addr)

    return api_response(True, data={"passed": passed, "feedback": feedback, "is_live": is_live})




# CODE EDITOR (Cyber Pro uchun) — HTML/CSS/JS real-vaqt preview
# =================================================================
@codehelp_bp.route("/code-editor")
@login_required
def code_editor_page():
    user = get_current_user()
    return render_template("code_editor.html",
                           languages=code_runner.LANGUAGES,
                           default_lang="python")


@codehelp_bp.route("/api/code/run", methods=["POST"])
@api_login_required
def api_code_run():
    """Foydalanuvchi kodini xavfsiz sandboxda bajaradi."""
    data = request.get_json(silent=True) or {}
    lang = (data.get("language") or "python").strip()
    code = (data.get("code") or "").strip()
    if not code:
        return api_response(False, error="Kod bo'sh.")
    result = code_runner.run_code(lang, code)
    return api_response(True, data={"result": result})

