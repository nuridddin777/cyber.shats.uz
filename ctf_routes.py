# ============================================================
# CYBER SHATS — Maxsus vazifalar (CTF) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, abort
from auth import get_current_user, login_required
from db import query_one, query_all, execute

ctf_bp = Blueprint("ctf_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


@ctf_bp.route("/maxsus-vazifalar")
@login_required
def ctf_tasks_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    tasks = query_all("SELECT * FROM ctf_tasks ORDER BY difficulty, id")
    solved_ids = {r["task_id"] for r in query_all(
        "SELECT task_id FROM ctf_submissions WHERE user_id=? AND correct=1", (user["id"],)
    )}
    total_points = query_one(
        "SELECT COALESCE(SUM(points_awarded),0) p FROM ctf_submissions WHERE user_id=? AND correct=1",
        (user["id"],)
    )["p"]
    leaderboard = query_all(
        """SELECT u.ism, u.familiya, u.custom_id, SUM(s.points_awarded) as total
           FROM ctf_submissions s JOIN users u ON u.id=s.user_id
           WHERE s.correct=1 GROUP BY u.id ORDER BY total DESC LIMIT 10"""
    )
    return render_template("ctf_tasks.html", tasks=tasks, solved_ids=solved_ids,
                           total_points=total_points, leaderboard=leaderboard)


@ctf_bp.route("/maxsus-vazifalar/<int:task_id>/submit", methods=["POST"])
@login_required
def ctf_submit(task_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    task = query_one("SELECT * FROM ctf_tasks WHERE id=?", (task_id,))
    if not task:
        abort(404)
    already = query_one("SELECT * FROM ctf_submissions WHERE task_id=? AND user_id=? AND correct=1",
                         (task_id, user["id"]))
    if already:
        flash("Bu vazifani allaqachon yechgansiz!", "success")
        return redirect(url_for(".ctf_tasks_page"))
    flag = request.form.get("flag", "").strip()
    correct = (flag == task["flag"])
    if correct:
        execute(
            "INSERT INTO ctf_submissions (task_id, user_id, correct, points_awarded) VALUES (?,?,1,?) "
            "ON CONFLICT(task_id, user_id) DO UPDATE SET correct=1, points_awarded=excluded.points_awarded",
            (task_id, user["id"], task["points"])
        )
        flash(f"To'g'ri! +{task['points']} ball qo'shildi.", "success")
    else:
        execute(
            "INSERT INTO ctf_submissions (task_id, user_id, correct, points_awarded) VALUES (?,?,0,0) "
            "ON CONFLICT(task_id, user_id) DO NOTHING",
            (task_id, user["id"])
        )
        flash("Noto'g'ri flag. Qayta urinib ko'ring.", "error")
    return redirect(url_for(".ctf_tasks_page"))
