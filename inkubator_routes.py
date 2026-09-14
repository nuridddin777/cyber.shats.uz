# ============================================================
# CYBER SHATS — Startap Inkubatori bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

inkubator_bp = Blueprint("inkubator_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()


# =================================================================
# STARTAP INKUBATORI (MAXSUS)
# =================================================================
@inkubator_bp.route("/inkubator")
@login_required
def incubator_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    ideas = query_all(
        """SELECT i.*, u.ism, u.familiya,
                  (SELECT COUNT(*) FROM incubator_votes v WHERE v.idea_id=i.id) as vote_count
           FROM incubator_ideas i JOIN users u ON u.id = i.user_id
           ORDER BY vote_count DESC, i.created_at DESC"""
    )
    my_votes = {r["idea_id"] for r in query_all("SELECT idea_id FROM incubator_votes WHERE user_id=?", (user["id"],))}
    return render_template("incubator.html", ideas=ideas, my_votes=my_votes)


@inkubator_bp.route("/inkubator/create", methods=["POST"])
@login_required
def incubator_create():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    if title and description:
        execute("INSERT INTO incubator_ideas (user_id, title, description) VALUES (?,?,?)",
                (user["id"], title, description))
        flash("G'oyangiz joylandi!", "success")
    return redirect(url_for(".incubator_page"))


@inkubator_bp.route("/inkubator/<int:idea_id>/vote", methods=["POST"])
@login_required
def incubator_vote(idea_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    existing = query_one("SELECT 1 FROM incubator_votes WHERE idea_id=? AND user_id=?", (idea_id, user["id"]))
    if existing:
        execute("DELETE FROM incubator_votes WHERE idea_id=? AND user_id=?", (idea_id, user["id"]))
    else:
        execute("INSERT INTO incubator_votes (idea_id, user_id) VALUES (?,?)", (idea_id, user["id"]))
    return redirect(url_for(".incubator_page"))


@inkubator_bp.route("/inkubator/<int:idea_id>/comment", methods=["POST"])
@login_required
def incubator_comment(idea_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    content = request.form.get("content", "").strip()
    if content:
        execute("INSERT INTO incubator_comments (idea_id, user_id, content) VALUES (?,?,?)",
                (idea_id, user["id"], content))
    return redirect(url_for(".incubator_page"))
