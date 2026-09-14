# ============================================================
# CYBER SHATS — Maxsus topshiriq (KRIPTIKIS) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
import special_challenge as challenge_mod

kriptikis_bp = Blueprint("kriptikis_bp", __name__)



# =================================================================
# MAXSUS TOPSHIRIQ (KRIPTIKIS) — 3 bosqichli kriptografik topshiriq
# =================================================================
@kriptikis_bp.route("/maxsus-topshiriq")
@login_required
def special_challenge_page():
    user = get_current_user()
    progress = challenge_mod.get_progress(user["id"])
    max_level = challenge_mod.MAX_LEVEL
    current_level = min(progress["current_level"], max_level)
    challenge = challenge_mod.get_challenge(current_level)
    completed = progress["current_level"] > max_level
    return render_template("special_challenge.html", challenge=challenge, progress=progress,
                            completed=completed, current_level=current_level, max_level=max_level)


@kriptikis_bp.route("/maxsus-topshiriq/unlock", methods=["POST"])
@login_required
def special_challenge_unlock():
    user = get_current_user()
    try:
        result = challenge_mod.unlock_level1(user["id"])
        flash(f"1-bosqich {result['cost']} CODE evaziga o'tildi! 2-bosqichga xush kelibsiz.", "success")
    except challenge_mod.ChallengeError as e:
        flash(str(e), "error")
    return redirect(url_for(".special_challenge_page"))


@kriptikis_bp.route("/maxsus-topshiriq/submit", methods=["POST"])
@login_required
def special_challenge_submit():
    user = get_current_user()
    level = request.form.get("level", type=int) or 0
    answer = request.form.get("answer", "")
    try:
        result = challenge_mod.submit_answer(user["id"], level, answer)
        if result["completed"]:
            flash(f"Tabriklaymiz! Siz Maxsus Topshiriqni TO'LIQ yechdingiz! "
                  f"Mukofot: {result['reward']} CODE.", "success")
        else:
            flash(f"To'g'ri! {result['reward']} CODE mukofot oldingiz. "
                  f"{result['next_level']}-bosqichga o'tdingiz.", "success")
    except challenge_mod.ChallengeError as e:
        flash(str(e), "error")
    return redirect(url_for(".special_challenge_page"))
