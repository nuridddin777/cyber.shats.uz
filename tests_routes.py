# ============================================================
# CYBER SHATS — Testlar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute, log_action

tests_bp = Blueprint("tests_bp", __name__)


def award_xp(user_id, amount):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import award_xp as _real_fn
    return _real_fn(user_id, amount)



@tests_bp.route("/tests")
@login_required
def tests():
    user = get_current_user()
    test_list = query_all(
        "SELECT t.*, c.title as course_title, c.slug as course_slug, "
        "(SELECT COUNT(*) FROM test_questions WHERE test_id=t.id) as q_count "
        "FROM tests t LEFT JOIN courses c ON c.id=t.course_id ORDER BY t.id"
    )
    attempted = {r["test_id"]: r for r in query_all(
        "SELECT test_id, MAX(score) as best_score, MAX(total) as total FROM test_attempts WHERE user_id=? GROUP BY test_id",
        (user["id"],))}
    return render_template("tests.html", tests=test_list, attempted=attempted)


@tests_bp.route("/tests/<int:test_id>")
@login_required
def test_take(test_id):
    test = query_one("SELECT t.*, c.title as course_title FROM tests t LEFT JOIN courses c ON c.id=t.course_id WHERE t.id=?", (test_id,))
    if not test:
        abort(404)
    questions = query_all("SELECT * FROM test_questions WHERE test_id=? ORDER BY order_num", (test_id,))
    return render_template("test_take.html", test=test, questions=questions)


@tests_bp.route("/tests/<int:test_id>/submit", methods=["POST"])
@login_required
def test_submit(test_id):
    user = get_current_user()
    questions = query_all("SELECT * FROM test_questions WHERE test_id=?", (test_id,))
    score = 0
    for q in questions:
        chosen = request.form.get(f"q_{q['id']}", "")
        if chosen == q["correct_option"]:
            score += 1
    total = len(questions)
    execute("INSERT INTO test_attempts (user_id, test_id, score, total) VALUES (?,?,?,?)",
            (user["id"], test_id, score, total))
    award_xp(user["id"], score * 10)
    log_action(user["id"], "test_submit", details=f"test:{test_id} score:{score}/{total}", ip=request.remote_addr)
    flash(f"Test yakunlandi! Natija: {score}/{total}", "success" if score >= total * 0.6 else "warn")
    return redirect(url_for("results"))

