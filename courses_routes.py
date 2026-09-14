# ============================================================
# CYBER SHATS — Kurslar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session, abort
from auth import get_current_user, login_required, admin_required
from db import query_one, query_all, execute, log_action
from utils import api_response
from admins import admin_can_manage_course
from coins import get_balance, _update_rating, award_course_completion
import code_runner
import datetime

courses_bp = Blueprint("courses_bp", __name__)


def gen_code(n=8):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import gen_code as _real_fn
    return _real_fn(n)


def _can_access_course(user, course):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _can_access_course as _real_fn
    return _real_fn(user, course)


def _locked_direction_for(user):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _locked_direction_for as _real_fn
    return _real_fn(user)


def award_xp(user_id, amount):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import award_xp as _real_fn
    return _real_fn(user_id, amount)


def get_directions(include_inactive=False):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import get_directions as _real_fn
    return _real_fn(include_inactive)


# =================================================================
# KURSLAR
# =================================================================
@courses_bp.route("/courses")
@login_required
def courses():
    user = get_current_user()
    d_slug = request.args.get("d", "")
    search = request.args.get("q", "").strip()
    level = request.args.get("level", "")

    locked_direction = _locked_direction_for(user)
    if locked_direction:
        # O'quvchi uchun yo'nalish qulflangan — boshqa `d` so'rovi e'tiborga olinmaydi.
        d_slug = locked_direction["slug"]

    sql = ("SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
           "JOIN directions d ON d.id=c.direction_id WHERE c.is_active=1")
    args = []
    if locked_direction:
        # O'z yo'nalishidagi kurslar + oldindan (masalan access-code orqali)
        # boshqa yo'nalishdan yozilib qo'yilgan kurslar ham ko'rinadi.
        sql += " AND (d.slug=? OR c.id IN (SELECT course_id FROM enrollments WHERE user_id=?))"
        args += [d_slug, user["id"]]
    elif d_slug:
        sql += " AND d.slug=?"
        args.append(d_slug)
    if search:
        sql += " AND c.title LIKE ?"
        args.append(f"%{search}%")
    if level:
        sql += " AND c.level=?"
        args.append(level)
    sql += " ORDER BY c.students_count DESC LIMIT 60"
    course_list = query_all(sql, tuple(args))
    directions_list = [locked_direction] if locked_direction else get_directions()
    return render_template("courses.html", courses=course_list, directions=directions_list,
                            active_d=d_slug, search=search, active_level=level,
                            locked_direction=locked_direction)


@courses_bp.route("/courses/<slug>")
@login_required
def course_detail(slug):
    user = get_current_user()
    course = query_one(
        "SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
        "JOIN directions d ON d.id=c.direction_id WHERE c.slug=?", (slug,)
    )
    if not course:
        abort(404)
    if not _can_access_course(user, course):
        flash("Bu kurs sizning tanlagan yo'nalishingizga tegishli emas.", "error")
        return redirect(url_for(".courses"))
    modules = query_all("SELECT * FROM modules WHERE course_id=? ORDER BY order_num", (course["id"],))
    for m in modules:
        m["lessons"] = query_all("SELECT * FROM lessons WHERE module_id=? ORDER BY order_num", (m["id"],))
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    test = query_one("SELECT * FROM tests WHERE course_id=?", (course["id"],))
    return render_template("course_detail.html", course=course, modules=modules, enrollment=enrollment, test=test)


@courses_bp.route("/courses/<slug>/enroll", methods=["POST"])
@login_required
def enroll_course(slug):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    if not _can_access_course(user, course):
        flash("Bu kurs sizning tanlagan yo'nalishingizga tegishli emas.", "error")
        return redirect(url_for(".courses"))
    # Pullik kurs tekshiruvi
    if (course.get("is_paid") or course.get("code_price", 0) > 0):
        existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
        if not existing:
            flash("Bu kursga kirish uchun code tangasi yoki kirish kodi kerak.", "error")
            return redirect(url_for(".course_detail", slug=slug))
    existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if not existing:
        execute("INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                (user["id"], course["id"]))
        execute("UPDATE courses SET students_count = students_count + 1 WHERE id=?", (course["id"],))
        log_action(user["id"], "enroll", details=course["title"], ip=request.remote_addr)
        flash(f"«{course['title']}» kursiga muvaffaqiyatli yozildingiz!", "success")
    first_lesson = query_one("SELECT id FROM lessons WHERE course_id=? ORDER BY order_num LIMIT 1", (course["id"],))
    if first_lesson:
        return redirect(url_for(".lesson", slug=slug, lesson_id=first_lesson["id"]))
    return redirect(url_for(".course_detail", slug=slug))


@courses_bp.route("/courses/<slug>/lesson/<int:lesson_id>")
@login_required
def lesson(slug, lesson_id):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    if not _can_access_course(user, course):
        flash("Bu kurs sizning tanlagan yo'nalishingizga tegishli emas.", "error")
        return redirect(url_for(".courses"))
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"]))
    if not current:
        abort(404)
    all_lessons = query_all("SELECT * FROM lessons WHERE course_id=? ORDER BY order_num", (course["id"],))
    done_ids = {r["lesson_id"] for r in query_all(
        "SELECT lesson_id FROM lesson_progress WHERE user_id=? AND is_done=1", (user["id"],))}
    idx = next((i for i, l in enumerate(all_lessons) if l["id"] == lesson_id), 0)
    prev_lesson = all_lessons[idx - 1] if idx > 0 else None
    next_lesson = all_lessons[idx + 1] if idx < len(all_lessons) - 1 else None
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if not enrollment:
        execute("INSERT INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                (user["id"], course["id"]))
    return render_template("lesson.html", course=course, lesson=current, all_lessons=all_lessons,
                            done_ids=done_ids, prev_lesson=prev_lesson, next_lesson=next_lesson)


@courses_bp.route("/courses/<slug>/lesson/<int:lesson_id>/materials")
@login_required
def lesson_materials(slug, lesson_id):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"])) if course else None
    if not course or not current:
        abort(404)
    if not _can_access_course(user, course):
        flash("Bu kurs sizning tanlagan yo'nalishingizga tegishli emas.", "error")
        return redirect(url_for(".courses"))
    return render_template("lesson_materials.html", course=course, lesson=current)


@courses_bp.route("/courses/<slug>/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(slug, lesson_id):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        return api_response(False, error="Kurs topilmadi", status=404)
    if not _can_access_course(user, course):
        return api_response(False, error="Bu kurs sizning yo'nalishingizga tegishli emas", status=403)
    execute("INSERT OR IGNORE INTO lesson_progress (user_id, lesson_id, is_done) VALUES (?,?,1)",
            (user["id"], lesson_id))
    execute("UPDATE lesson_progress SET is_done=1 WHERE user_id=? AND lesson_id=?", (user["id"], lesson_id))
    total = query_one("SELECT COUNT(*) c FROM lessons WHERE course_id=?", (course["id"],))["c"]
    done = query_one(
        "SELECT COUNT(*) c FROM lesson_progress lp JOIN lessons l ON l.id=lp.lesson_id "
        "WHERE lp.user_id=? AND l.course_id=? AND lp.is_done=1", (user["id"], course["id"]))["c"]
    pct = int((done / total) * 100) if total else 0
    enrollment = query_one("SELECT * FROM enrollments WHERE user_id=? AND course_id=?", (user["id"], course["id"]))
    if enrollment:
        execute("UPDATE enrollments SET progress_percent=? WHERE id=?", (pct, enrollment["id"]))
        if pct == 100 and not enrollment["completed_at"]:
            execute("UPDATE enrollments SET completed_at=? WHERE id=?", (datetime.datetime.now().isoformat(), enrollment["id"]))
            cert_code = f"CS-{gen_code(10)}"
            execute("INSERT INTO certificates (user_id, course_id, cert_code) VALUES (?,?,?)",
                    (user["id"], course["id"], cert_code))
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (user["id"], "Sertifikat tayyor!", f"«{course['title']}» kursini yakunladingiz.", "success"))
            try:
                push_mod.send_push_to_user(user["id"], "Sertifikat tayyor! 🎓",
                                           f"«{course['title']}» kursini yakunladingiz.", "/dashboard")
            except Exception:
                pass
    award_xp(user["id"], 25)
    # Avtomatik kurs bitirish bonusi olib tashlandi — endi bonuslarni faqat admin panel orqali beriladi.
    if pct == 100:
        _update_rating(user["id"])
    log_action(user["id"], "complete_lesson", details=f"lesson:{lesson_id}", ip=request.remote_addr)
    balance = get_balance(user["id"])
    return api_response(True, data={"progress_percent": pct, "code_balance": balance})


# =================================================================
# AMALIYOT / HACKER LAB — FAQAT VIZUAL SIMULYATSIYA (xavfsizlik uchun)
# Bu sahifalarda HAQIQIY ekspluatatsiya kodi yo'q — barcha "hujum"
# faqat oldindan yozilgan JS skript orqali frontendda ko'rsatiladi.
# =================================================================
@courses_bp.route("/courses/<slug>/practice/<int:lesson_id>")
@login_required
def practice(slug, lesson_id):
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    current = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"])) if course else None
    if not course or not current:
        abort(404)
    if not _can_access_course(user, course):
        flash("Bu kurs sizning tanlagan yo'nalishingizga tegishli emas.", "error")
        return redirect(url_for(".courses"))
    if current.get("practice_type") in ("code", "web"):
        can_edit = admin_can_manage_course(user, course) if user.get("role") in ("admin", "mentor", "super_admin") else False
        return render_template("code_practice.html", course=course, lesson=current,
                               languages=code_runner.LANGUAGES, can_edit=can_edit)
    return render_template("practice.html", course=course, lesson=current)


@courses_bp.route("/courses/<slug>/practice/<int:lesson_id>/edit-exercise", methods=["POST"])
@admin_required
def edit_lesson_exercise(slug, lesson_id):
    """Yo'nalish admini (yoki super_admin) ushbu darsning kod mashqini tahrirlaydi."""
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    lesson = query_one("SELECT * FROM lessons WHERE id=? AND course_id=?", (lesson_id, course["id"])) if course else None
    if not course or not lesson:
        abort(404)
    if not admin_can_manage_course(get_current_user(), course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for(".practice", slug=slug, lesson_id=lesson_id))
    prompt = request.form.get("exercise_prompt", "").strip()
    hint = request.form.get("exercise_hint", "").strip()
    if lesson.get("practice_type") == "web":
        html = request.form.get("exercise_starter_html", "")
        css = request.form.get("exercise_starter_css", "")
        js = request.form.get("exercise_starter_js", "")
        execute("UPDATE lessons SET exercise_prompt=?, exercise_hint=?, "
                "exercise_starter_html=?, exercise_starter_css=?, exercise_starter_js=? WHERE id=?",
                (prompt, hint, html, css, js, lesson_id))
    else:
        starter = request.form.get("exercise_starter_code", "")
        lang = request.form.get("exercise_language", "python")
        if lang not in code_runner.LANGUAGES:
            lang = "python"
        execute("UPDATE lessons SET exercise_prompt=?, exercise_starter_code=?, exercise_hint=?, exercise_language=? WHERE id=?",
                (prompt, starter, hint, lang, lesson_id))

@courses_bp.route("/courses/<slug>/activate-code", methods=["POST"])
@login_required
def activate_course_code(slug):
    """Foydalanuvchi kurs uchun access code kiritadi."""
    user = get_current_user()
    course = query_one("SELECT * FROM courses WHERE slug=?", (slug,))
    if not course:
        abort(404)
    code = request.form.get("access_code", "").strip().upper()
    row = query_one("SELECT * FROM course_access_codes WHERE access_code=? AND course_id=? AND is_used=0",
                    (code, course["id"]))
    if not row:
        flash("Noto'g'ri yoki ishlatilgan kod.", "error")
        return redirect(url_for("courses_bp.course_detail", slug=slug))
    import datetime
    execute("UPDATE course_access_codes SET is_used=1, used_by=?, used_at=? WHERE id=?",
            (user["id"], datetime.datetime.now().isoformat(), row["id"]))
    execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
            (user["id"], course["id"]))
    flash(f"«{course['title']}» kursiga muvaffaqiyatli kirish berildi!", "success")
    log_action(user["id"], "activate_course_code", details=f"course:{course['id']}", ip=request.remote_addr)
    return redirect(url_for("courses_bp.course_detail", slug=slug))
