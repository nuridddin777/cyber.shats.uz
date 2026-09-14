# ============================================================
# CYBER SHATS — Stories va Reels bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app, jsonify
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
import social

social_bp = Blueprint("social_bp", __name__)


def _social_save_file(file_storage, allow_large_video=False):
    """app.py'dagi bilan bir xil — aylanma import'dan qochish uchun
    kechiktirilgan (lazy) import ishlatiladi (bir necha bo'limda,
    jumladan Guruh/Kanalda ham ishlatiladi)."""
    from app import _social_save_file as _real_fn
    return _real_fn(file_storage, allow_large_video)


def _check_panel(panel_key: str):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _check_panel as _real_check_panel
    return _real_check_panel(panel_key)


# =================================================================
# STORIES — 24 soatlik vaqtinchalik kontent (Instagram uslubida)
# =================================================================
@social_bp.route("/stories")
@login_required
def stories_feed():
    user = get_current_user()
    grouped = social.get_active_stories_by_users()
    my_stories = social.get_user_active_stories(user["id"])
    return render_template("stories_feed.html", grouped=grouped, my_stories=my_stories)


@social_bp.route("/stories/create", methods=["POST"])
@login_required
def stories_create():
    user = get_current_user()
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    if not file_path:
        flash("Faqat rasm yoki video yuklash mumkin.", "error")
        return redirect(url_for(".stories_feed"))
    ok, msg, sid = social.create_story(user["id"], file_path, file_type, request.form.get("caption", ""))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".stories_feed"))


@social_bp.route("/stories/user/<int:target_user_id>")
@login_required
def stories_view_user(target_user_id):
    """Bitta foydalanuvchining faol hikoyalarini ketma-ket ko'rsatish."""
    user = get_current_user()
    stories = social.get_user_active_stories(target_user_id)
    if not stories:
        flash("Bu foydalanuvchining faol hikoyasi yo'q.", "error")
        return redirect(url_for(".stories_feed"))
    for s in stories:
        social.mark_story_viewed(s["id"], user["id"])
    target = query_one("SELECT ism, familiya, avatar FROM users WHERE id=?", (target_user_id,))
    return render_template("stories_view.html", stories=stories, target=target)


@social_bp.route("/stories/<int:story_id>/delete", methods=["POST"])
@login_required
def stories_delete(story_id):
    user = get_current_user()
    ok, msg = social.delete_story(story_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".stories_feed"))


# =================================================================
# REELS — qisqa vertikal videolar tasmasi
# =================================================================
@social_bp.route("/reels")
@login_required
def reels_feed():
    check = _check_panel('reels')
    if check: return check
    reels = social.get_reels_feed()
    user = get_current_user()
    liked_ids = set()
    if reels:
        ids = [r["id"] for r in reels]
        placeholders = ",".join("?" for _ in ids)
        liked_rows = query_all(
            f"SELECT reel_id FROM reel_likes WHERE user_id=? AND reel_id IN ({placeholders})",
            tuple([user["id"]] + ids)
        )
        liked_ids = {r["reel_id"] for r in liked_rows}
    return render_template("reels_feed.html", reels=reels, liked_ids=liked_ids)


@social_bp.route("/reels/create", methods=["GET", "POST"])
@login_required
def reels_create():
    if request.method == "GET":
        return render_template("reels_create.html")
    user = get_current_user()
    file_path, file_type = (None, None)
    if "file" in request.files:
        file_path, file_type = _social_save_file(request.files["file"])
    if not file_path or file_type != "video":
        flash("Faqat video fayl yuklash mumkin.", "error")
        return redirect(url_for(".reels_create"))
    ok, msg, rid = social.create_reel(user["id"], file_path, request.form.get("caption", ""))
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".reels_feed"))


@social_bp.route("/api/reels/<int:reel_id>/view", methods=["POST"])
@api_login_required
def api_reel_view(reel_id):
    social.increment_reel_view(reel_id)
    return api_response(True)


@social_bp.route("/api/reels/<int:reel_id>/like", methods=["POST"])
@api_login_required
def api_reel_like(reel_id):
    user = get_current_user()
    liked, count = social.toggle_reel_like(reel_id, user["id"])
    return api_response(True, data={"liked": liked, "like_count": count})


@social_bp.route("/reels/<int:reel_id>/comment", methods=["POST"])
@login_required
def reel_comment(reel_id):
    user = get_current_user()
    ok, msg = social.add_reel_comment(reel_id, user["id"], request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for(".reels_feed") + f"#reel-{reel_id}")


@social_bp.route("/api/reels/<int:reel_id>/comments")
@api_login_required
def api_reel_comments(reel_id):
    comments = social.get_reel_comments(reel_id)
    return api_response(True, data={"comments": comments})


@social_bp.route("/reels/<int:reel_id>/delete", methods=["POST"])
@login_required
def reel_delete(reel_id):
    user = get_current_user()
    ok, msg = social.delete_reel(reel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".reels_feed"))

