# ============================================================
# CYBER SHATS — Video qo'ng'iroq bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, jsonify
from auth import get_current_user, login_required, api_login_required
from db import query_one, query_all, execute
from utils import api_response
import video_calls
import social

call_bp = Blueprint("call_bp", __name__)


@call_bp.route("/call/<room_code>")
@login_required
def call_room(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if not call or not call["is_active"]:
        flash("Qo'ng'iroq topilmadi yoki tugagan.", "error")
        return redirect(url_for("groups_bp.groups_list"))
    # Ruxsat tekshiruvi: faqat tegishli guruh a'zosi yoki kanal obunachisi
    if call["group_id"] and not social.is_member(call["group_id"], user["id"]):
        flash("Bu qo'ng'iroqqa faqat guruh a'zolari qo'shila oladi.", "error")
        return redirect(url_for("groups_bp.groups_list"))
    if call["channel_id"]:
        ch = query_one("SELECT owner_id FROM channels WHERE id=?", (call["channel_id"],))
        is_sub = query_one("SELECT id FROM channel_subscribers WHERE channel_id=? AND user_id=?",
                           (call["channel_id"], user["id"]))
        if not ch or (ch["owner_id"] != user["id"] and not is_sub):
            flash("Bu qo'ng'iroqqa faqat kanal a'zolari qo'shila oladi.", "error")
            return redirect(url_for("groups_bp.channels_list"))

    video_calls.join_call(call["id"], user["id"])
    participants = video_calls.get_active_participants(call["id"])
    back_url = (url_for("groups_bp.group_detail", group_id=call["group_id"]) if call["group_id"]
                else url_for("groups_bp.channel_detail", channel_id=call["channel_id"]))
    return render_template("call_room.html", call=call, participants=participants,
                           is_host=(call["started_by"] == user["id"]), back_url=back_url)


@call_bp.route("/api/call/<room_code>/state")
@api_login_required
def api_call_state(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if not call or not call["is_active"]:
        return api_response(False, error="Qo'ng'iroq faol emas")
    participants = video_calls.get_active_participants(call["id"])
    return api_response(True, data={
        "participants": [dict(p) for p in participants],
        "call_id": call["id"], "my_id": user["id"],
    })


@call_bp.route("/api/call/<room_code>/signal", methods=["POST"])
@api_login_required
def api_call_signal(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if not call or not call["is_active"]:
        return api_response(False, error="Qo'ng'iroq faol emas")
    data = request.get_json(silent=True) or {}
    to_user_id = data.get("to_user_id")
    signal_type = data.get("signal_type")
    payload = data.get("payload")
    if not to_user_id or signal_type not in ("offer", "answer", "ice-candidate", "join", "leave"):
        return api_response(False, error="Noto'g'ri signal ma'lumoti", status=400)
    video_calls.send_signal(call["id"], user["id"], int(to_user_id), signal_type, json.dumps(payload))
    return api_response(True)


@call_bp.route("/api/call/<room_code>/signals")
@api_login_required
def api_call_signals(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if not call:
        return api_response(False, error="Qo'ng'iroq topilmadi")
    try:
        after_id = int(request.args.get("after_id", 0))
    except ValueError:
        after_id = 0
    signals = video_calls.get_signals_for(call["id"], user["id"], after_id)
    out = []
    for s in signals:
        out.append({"id": s["id"], "from_user_id": s["from_user_id"], "signal_type": s["signal_type"],
                    "payload": json.loads(s["payload"])})
    return api_response(True, data={"signals": out})


@call_bp.route("/call/<room_code>/leave", methods=["POST"])
@login_required
def call_leave(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if call:
        video_calls.leave_call(call["id"], user["id"])
        back_url = (url_for("groups_bp.group_detail", group_id=call["group_id"]) if call["group_id"]
                    else url_for("groups_bp.channel_detail", channel_id=call["channel_id"]) if call["channel_id"]
                    else url_for("dashboard"))
        return redirect(back_url)
    return redirect(url_for("dashboard"))


@call_bp.route("/call/<room_code>/end", methods=["POST"])
@login_required
def call_end(room_code):
    user = get_current_user()
    call = video_calls.get_call_by_room(room_code)
    if not call:
        return redirect(url_for("dashboard"))
    ok, msg = video_calls.end_call_for_all(call["id"], user["id"])
    flash(msg, "success" if ok else "error")
    back_url = (url_for("groups_bp.group_detail", group_id=call["group_id"]) if call["group_id"]
                else url_for("groups_bp.channel_detail", channel_id=call["channel_id"]) if call["channel_id"]
                else url_for("dashboard"))
    return redirect(back_url)

