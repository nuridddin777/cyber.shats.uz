# ============================================================
# CYBER SHATS — Admin Kurslar boshqaruvi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required
from db import query_one, query_all, execute, log_action
from admins import admin_can_manage_course, get_admin_directions
import admins as admins_mod
from ai_testgen import generate_test_questions, review_and_fix_test_questions
import random
import string

admincourses_bp = Blueprint("admincourses_bp", __name__)


# =================================================================

@admincourses_bp.route("/admin/courses/<int:course_id>/access-codes")
@admin_required
def admin_course_access_codes(course_id):
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if not admins_mod.admin_can_manage_course(get_current_user(), course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
    codes = query_all(
        "SELECT c.*, u.ism, u.familiya FROM course_access_codes c LEFT JOIN users u ON u.id=c.used_by WHERE c.course_id=? ORDER BY c.created_at DESC",
        (course_id,)
    )
    return render_template("admin_access_codes.html", course=course, codes=codes)


@admincourses_bp.route("/admin/courses/<int:course_id>/access-codes/generate", methods=["POST"])
@admin_required
def admin_generate_access_codes(course_id):
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if not admins_mod.admin_can_manage_course(get_current_user(), course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
    count = int(request.form.get("count", 1))
    count = min(count, 50)
    generated = []
    for _ in range(count):
        code = "CS-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
        execute("INSERT INTO course_access_codes (course_id, access_code) VALUES (?,?)", (course_id, code))
        generated.append(code)
    log_action(session["user_id"], "generate_access_codes", details=f"course:{course_id},count:{count}", ip=request.remote_addr)
    flash(f"{count} ta kirish kodi yaratildi.", "success")
    return redirect(url_for(".admin_course_access_codes", course_id=course_id))



@admincourses_bp.route("/admin/courses/<int:course_id>/set-price", methods=["POST"])
@admin_required
def admin_set_course_price(course_id):
    """Kursning code-narxini admin o'zgartiradi (faqat o'ziga tayinlangan yo'nalish ichida)."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if not admins_mod.admin_can_manage_course(get_current_user(), course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
    try:
        price = max(0, int(request.form.get("code_price", 0)))
    except ValueError:
        price = 0
    execute("UPDATE courses SET code_price=? WHERE id=?", (price, course_id))
    log_action(session["user_id"], "admin_set_course_price",
               details=f"course:{course_id},price:{price}", ip=request.remote_addr)
    flash(f"«{course['title']}» kursi narxi {price:,} code ga o'zgartirildi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")


@admincourses_bp.route("/admin/courses/<int:course_id>/toggle-pro", methods=["POST"])
@admin_required
def admin_toggle_course_pro(course_id):
    """Kursni PRO only yoki FREE qilish (faqat o'ziga tayinlangan yo'nalish ichida)."""
    course = query_one("SELECT * FROM courses WHERE id=?", (course_id,))
    if not course:
        abort(404)
    if not admins_mod.admin_can_manage_course(get_current_user(), course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
    new_val = 0 if course["is_pro_only"] else 1
    execute("UPDATE courses SET is_pro_only=? WHERE id=?", (new_val, course_id))
    status = "PRO" if new_val else "FREE"
    log_action(session["user_id"], "toggle_course_pro", details=f"course:{course_id},status:{status}", ip=request.remote_addr)
    flash(f"Kurs '{course['title']}' endi {status} rejimida.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")


# =================================================================
# AI TEST YARATISH / TEKSHIRISH / TUZATISH
# (Gemini — ustuvor, sozlanmagan bo'lsa Anthropic zaxira sifatida)
# =================================================================
@admincourses_bp.route("/admin/courses/<int:course_id>/ai-generate-test", methods=["POST"])
@admin_required
def admin_ai_generate_test(course_id):
    """AI orqali ushbu kurs uchun test savollari YARATADI — test mavjud
    bo'lmasa yangi test ochadi, mavjud bo'lsa savol qo'shadi (takrorlanmasin
    deb AI'ga mavjud savollar ham yuboriladi)."""
    user = get_current_user()
    course = query_one("SELECT c.*, d.name_uz as direction_name FROM courses c "
                        "JOIN directions d ON d.id=c.direction_id WHERE c.id=?", (course_id,))
    if not course:
        abort(404)
    if not admins_mod.admin_can_manage_course(user, course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

    try:
        count = max(1, min(int(request.form.get("count", 5)), 15))
    except ValueError:
        count = 5

    test = query_one("SELECT * FROM tests WHERE course_id=?", (course_id,))
    existing_texts = []
    if test:
        existing_texts = [q["question_text"] for q in
                           query_all("SELECT question_text FROM test_questions WHERE test_id=?", (test["id"],))]

    questions, err = ai_testgen.generate_test_questions(
        course["title"], course.get("level", ""), course["direction_name"], count, existing_texts)
    if err:
        flash(f"AI test yarata olmadi: {err}", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

    if not test:
        execute("INSERT INTO tests (course_id, title, duration_minutes) VALUES (?,?,?)",
                (course_id, f"{course['title']} — Yakuniy Test", 15))
        test = query_one("SELECT * FROM tests WHERE course_id=?", (course_id,))

    start_order = query_one("SELECT COALESCE(MAX(order_num),0) m FROM test_questions WHERE test_id=?",
                             (test["id"],))["m"]
    for i, q in enumerate(questions, start=1):
        execute("""INSERT INTO test_questions (test_id, order_num, question_text, option_a, option_b,
                                                option_c, option_d, correct_option)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (test["id"], start_order + i, q["question"], q["a"], q["b"], q["c"], q["d"],
                 q["correct"].lower()))

    log_action(session["user_id"], "ai_generate_test",
               details=f"course:{course_id},count:{len(questions)}", ip=request.remote_addr)
    flash(f"AI «{course['title']}» kursi uchun {len(questions)} ta yangi test savoli yaratdi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")


@admincourses_bp.route("/admin/tests/<int:test_id>/ai-review", methods=["POST"])
@admin_required
def admin_ai_review_test(test_id):
    """AI mavjud test savollarini TEKSHIRADI — xato/noaniq bo'lsa TUZATADI."""
    user = get_current_user()
    test = query_one("SELECT t.*, c.title as course_title, c.id as course_id FROM tests t "
                      "JOIN courses c ON c.id=t.course_id WHERE t.id=?", (test_id,))
    if not test:
        abort(404)
    course = query_one("SELECT * FROM courses WHERE id=?", (test["course_id"],))
    if not admins_mod.admin_can_manage_course(user, course):
        flash("Bu kurs sizga tayinlangan yo'nalishlarga tegishli emas.", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

    questions = query_all(
        "SELECT id, question_text as question, option_a as a, option_b as b, option_c as c, "
        "option_d as d, correct_option as correct FROM test_questions WHERE test_id=?", (test_id,))
    results, err = ai_testgen.review_and_fix_test_questions(test["course_title"], questions)
    if err:
        flash(f"AI tekshiruvi muvaffaqiyatsiz: {err}", "error")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

    changed_count = 0
    for r in results:
        if r.get("changed"):
            execute("""UPDATE test_questions SET question_text=?, option_a=?, option_b=?, option_c=?,
                       option_d=?, correct_option=? WHERE id=? AND test_id=?""",
                    (r["question"], r["a"], r["b"], r["c"], r["d"], r["correct"].lower(), r["id"], test_id))
            changed_count += 1

    log_action(session["user_id"], "ai_review_test",
               details=f"test:{test_id},checked:{len(results)},fixed:{changed_count}", ip=request.remote_addr)
    if changed_count:
        flash(f"AI {len(results)} ta savolni tekshirdi, {changed_count} tasini tuzatdi.", "success")
    else:
        flash(f"AI {len(results)} ta savolni tekshirdi — barchasi to'g'ri, tuzatish shart emas edi.", "success")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")


@admincourses_bp.route("/admin/tests/ai-bulk-generate", methods=["POST"])
@admin_required
def admin_ai_bulk_generate_tests():
    """Testi bo'lmagan BARCHA kurslarga (admin uchun — faqat o'ziga tayinlangan
    yo'nalishlar doirasida; super_admin uchun — butun platforma) AI orqali
    test yaratadi. Bitta so'rovda ko'p AI chaqiruvi bo'lgani uchun soni
    cheklangan (bir martada maksimal 10 ta kurs)."""
    user = get_current_user()
    scope = get_admin_directions(user)  # None = super_admin/mentor (cheklovsiz)
    sql = """SELECT c.id, c.title, c.level, d.name_uz as direction_name FROM courses c
             JOIN directions d ON d.id=c.direction_id
             WHERE c.is_active=1 AND c.id NOT IN (SELECT course_id FROM tests)"""
    args = ()
    if scope is not None:
        if not scope:
            flash("Sizga hali birorta yo'nalish tayinlanmagan.", "error")
            return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
        placeholders = ",".join("?" * len(scope))
        sql += f" AND c.direction_id IN ({placeholders})"
        args = tuple(scope)
    sql += " LIMIT 10"
    missing_courses = query_all(sql, args)

    if not missing_courses:
        flash("Testsiz kurs topilmadi — barcha (sizga tegishli) kurslarda test allaqachon bor.", "success")
        return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")

    created, failed = 0, 0
    for course in missing_courses:
        questions, err = ai_testgen.generate_test_questions(
            course["title"], course.get("level", ""), course["direction_name"], 5)
        if err or not questions:
            failed += 1
            continue
        execute("INSERT INTO tests (course_id, title, duration_minutes) VALUES (?,?,?)",
                (course["id"], f"{course['title']} — Yakuniy Test", 15))
        test = query_one("SELECT id FROM tests WHERE course_id=?", (course["id"],))
        for i, q in enumerate(questions, start=1):
            execute("""INSERT INTO test_questions (test_id, order_num, question_text, option_a, option_b,
                                                    option_c, option_d, correct_option)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (test["id"], i, q["question"], q["a"], q["b"], q["c"], q["d"], q["correct"].lower()))
        created += 1

    log_action(session["user_id"], "ai_bulk_generate_tests",
               details=f"created:{created},failed:{failed}", ip=request.remote_addr)
    if created:
        flash(f"AI {created} ta kursga yangi test yaratdi." + (f" ({failed} tasida xato yuz berdi.)" if failed else ""), "success")
    else:
        flash(f"AI hech qaysi kursga test yarata olmadi ({failed} ta xato). AI sozlamalarini tekshiring.", "error")
    return redirect(url_for("admindash_bp.admin_dashboard") + "#codes")
