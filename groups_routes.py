# ============================================================
# CYBER SHATS — Guruhlar va Kanallar bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, abort
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
import social
import video_calls


def _check_panel(panel_key: str):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _check_panel as _real_check_panel
    return _real_check_panel(panel_key)


def _social_save_file(file_storage, allow_large_video=False):
    """app.py'dagi bilan bir xil — kechiktirilgan import."""
    from app import _social_save_file as _real_fn
    return _real_fn(file_storage, allow_large_video)


groups_bp = Blueprint("groups_bp", __name__)



@groups_bp.route("/groups")
@login_required
def groups_list():
    check = _check_panel('groups')
    if check: return check
    user = get_current_user()
    my_groups = social.get_user_groups(user["id"])
    all_groups = social.get_all_groups()
    my_group_ids = {g["id"] for g in my_groups}
    return render_template("groups_list.html", my_groups=my_groups, all_groups=all_groups, my_group_ids=my_group_ids)


@groups_bp.route("/groups/create", methods=["POST"])
@login_required
def groups_create():
    user = get_current_user()
    ok, msg, gid = social.create_group(
        user["id"], request.form.get("name", ""), request.form.get("description", ""),
        request.form.get("is_public") == "1"
    )
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for(".group_detail", group_id=gid))
    return redirect(url_for(".groups_list"))


@groups_bp.route("/groups/<int:group_id>")
@login_required
def group_detail(group_id):
    user = get_current_user()
    group = social.get_group(group_id)
    if not group:
        abort(404)
    is_member = social.is_member(group_id, user["id"])
    messages = social.get_group_messages(group_id) if is_member else []
    members = social.get_group_members(group_id) if is_member else []
    my_role = social.get_member_role(group_id, user["id"])
    return render_template("group_detail.html", group=group, is_member=is_member,
                           messages=messages, members=members, my_role=my_role)


@groups_bp.route("/groups/<int:group_id>/join", methods=["POST"])
@login_required
def group_join(group_id):
    user = get_current_user()
    ok, msg = social.join_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".group_detail", group_id=group_id))


@groups_bp.route("/groups/<int:group_id>/leave", methods=["POST"])
@login_required
def group_leave(group_id):
    user = get_current_user()
    ok, msg = social.leave_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".groups_list"))


@groups_bp.route("/groups/<int:group_id>/send", methods=["POST"])
@login_required
def group_send_message(group_id):
    user = get_current_user()
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        group = social.get_group(group_id)
        allow_large = bool(group and group.get("is_teacher_owned"))
        file_path, file_type = _social_save_file(request.files["file"], allow_large_video=allow_large)
    ok, msg = social.send_group_message(group_id, user["id"], body, file_path, file_type)
    if not ok:
        flash(msg, "error")
    return redirect(url_for(".group_detail", group_id=group_id))


@groups_bp.route("/api/groups/<int:group_id>/messages")
@api_login_required
def api_group_messages(group_id):
    """Real-vaqtga yaqin yangilanish uchun polling endpoint."""
    user = get_current_user()
    if not social.is_member(group_id, user["id"]):
        return api_response(False, error="A'zo emassiz")
    try:
        after_id = int(request.args.get("after_id", 0))
    except ValueError:
        after_id = 0
    rows = query_all(
        """SELECT m.*, u.ism, u.familiya FROM group_messages m
           JOIN users u ON u.id = m.user_id
           WHERE m.group_id=? AND m.id > ? ORDER BY m.id ASC""",
        (group_id, after_id)
    )
    return api_response(True, data={"messages": rows})


@groups_bp.route("/groups/<int:group_id>/kick/<int:target_user_id>", methods=["POST"])
@login_required
def group_kick(group_id, target_user_id):
    user = get_current_user()
    ok, msg = social.kick_member(group_id, user["id"], target_user_id)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".group_detail", group_id=group_id))


@groups_bp.route("/groups/<int:group_id>/delete", methods=["POST"])
@login_required
def group_delete(group_id):
    user = get_current_user()
    ok, msg = social.delete_group(group_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".groups_list"))


# =================================================================
# IJTIMOIY TARMOQ — KANALLAR (Telegram kanaliga o'xshab)
# =================================================================
@groups_bp.route("/channels")
@login_required
def channels_list():
    check = _check_panel('channels')
    if check: return check
    user = get_current_user()
    my_channels = social.get_user_channels(user["id"])
    all_channels = social.get_all_channels()
    my_channel_ids = {c["id"] for c in my_channels}
    return render_template("channels_list.html", my_channels=my_channels, all_channels=all_channels,
                           my_channel_ids=my_channel_ids)


@groups_bp.route("/channels/create", methods=["POST"])
@login_required
def channels_create():
    user = get_current_user()
    ok, msg, cid = social.create_channel(user["id"], request.form.get("name", ""), request.form.get("description", ""))
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for(".channel_detail", channel_id=cid))
    return redirect(url_for(".channels_list"))


@groups_bp.route("/channels/<int:channel_id>")
@login_required
def channel_detail(channel_id):
    user = get_current_user()
    channel = social.get_channel(channel_id)
    if not channel:
        abort(404)
    subscribed = social.is_subscribed(channel_id, user["id"])
    is_owner = social.is_channel_owner(channel_id, user["id"])
    posts = social.get_channel_posts(channel_id)
    return render_template("channel_detail.html", channel=channel, subscribed=subscribed,
                           is_owner=is_owner, posts=posts)


@groups_bp.route("/channels/<int:channel_id>/subscribe", methods=["POST"])
@login_required
def channel_subscribe(channel_id):
    user = get_current_user()
    ok, msg = social.subscribe_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".channel_detail", channel_id=channel_id))


@groups_bp.route("/channels/<int:channel_id>/unsubscribe", methods=["POST"])
@login_required
def channel_unsubscribe(channel_id):
    user = get_current_user()
    ok, msg = social.unsubscribe_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".channel_detail", channel_id=channel_id))


@groups_bp.route("/channels/<int:channel_id>/post", methods=["POST"])
@login_required
def channel_post_create(channel_id):
    user = get_current_user()
    body = request.form.get("body", "")
    file_path, file_type = (None, None)
    if "file" in request.files:
        channel = query_one("SELECT is_teacher_owned FROM channels WHERE id=?", (channel_id,))
        allow_large = bool(channel and channel.get("is_teacher_owned"))
        file_path, file_type = _social_save_file(request.files["file"], allow_large_video=allow_large)
    ok, msg = social.create_channel_post(channel_id, user["id"], body, file_path, file_type)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".channel_detail", channel_id=channel_id))


@groups_bp.route("/channels/post/<int:post_id>")
@login_required
def channel_post_detail(post_id):
    post = social.get_channel_post(post_id)
    if not post:
        abort(404)
    execute("UPDATE channel_posts SET views = views + 1 WHERE id=?", (post_id,))
    comments = social.get_post_comments(post_id)
    return render_template("channel_post_detail.html", post=post, comments=comments)


@groups_bp.route("/channels/post/<int:post_id>/comment", methods=["POST"])
@login_required
def channel_post_comment(post_id):
    user = get_current_user()
    ok, msg = social.add_post_comment(post_id, user["id"], request.form.get("body", ""))
    if not ok:
        flash(msg, "error")
    return redirect(url_for(".channel_post_detail", post_id=post_id))


@groups_bp.route("/channels/<int:channel_id>/delete", methods=["POST"])
@login_required
def channel_delete(channel_id):
    user = get_current_user()
    ok, msg = social.delete_channel(channel_id, user["id"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".channels_list"))


# =================================================================
# VIDEO-QO'NG'IROQ (WebRTC, Telegram-uslubida — guruh/kanal ichida)
# =================================================================
@groups_bp.route("/groups/<int:group_id>/call/start", methods=["POST"])
@login_required
def group_call_start(group_id):
    user = get_current_user()
    if not social.is_member(group_id, user["id"]):
        flash("Faqat guruh a'zolari qo'ng'iroqqa qo'shila oladi.", "error")
        return redirect(url_for(".group_detail", group_id=group_id))
    ok, msg, room_code = video_calls.start_call(user["id"], group_id=group_id)
    return redirect(url_for("call_bp.call_room", room_code=room_code))


@groups_bp.route("/channels/<int:channel_id>/call/start", methods=["POST"])
@login_required
def channel_call_start(channel_id):
    user = get_current_user()
    channel = social.get_channel(channel_id)
    if not channel:
        abort(404)
    is_subscribed = query_one("SELECT id FROM channel_subscribers WHERE channel_id=? AND user_id=?",
                              (channel_id, user["id"]))
    if channel["owner_id"] != user["id"] and not is_subscribed:
        flash("Faqat kanal a'zolari qo'ng'iroqqa qo'shila oladi.", "error")
        return redirect(url_for(".channel_detail", channel_id=channel_id))
    ok, msg, room_code = video_calls.start_call(user["id"], channel_id=channel_id)
    return redirect(url_for("call_bp.call_room", room_code=room_code))


@groups_bp.route("/groups/<int:group_id>/requests")
@login_required
def group_join_requests(group_id):
    user = get_current_user()
    group = social.get_group(group_id)
    if not group or group["owner_id"] != user["id"]:
        flash("Faqat guruh egasi so'rovlarni ko'ra oladi.", "error")
        return redirect(url_for(".group_detail", group_id=group_id))
    requests_list = query_all(
        """SELECT gjr.*, u.ism, u.familiya, u.custom_id FROM group_join_requests gjr
           JOIN users u ON u.id=gjr.user_id WHERE gjr.group_id=? AND gjr.status='pending'
           ORDER BY gjr.created_at DESC""", (group_id,))
    return render_template("group_join_requests.html", group=group, requests_list=requests_list)


@groups_bp.route("/groups/<int:group_id>/requests/<int:request_id>/review", methods=["POST"])
@login_required
def group_join_request_review(group_id, request_id):
    user = get_current_user()
    approve = request.form.get("decision") == "approve"
    ok, msg = social.review_join_request(request_id, user["id"], approve)
    flash(msg, "success" if ok else "error")
    return redirect(url_for(".group_join_requests", group_id=group_id))


