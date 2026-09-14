# ============================================================
# CYBER SHATS — Sertifikat tizimi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from pricing import get_price
import certificates as cert_mod
import random

certs_bp = Blueprint("certs_bp", __name__)


import certificates as cert_mod


@certs_bp.route("/certificates")
@login_required
def certificates_page():
    """Foydalanuvchining barcha kurslar/yo'nalishlari ro'yxati — sertifikat statusi bilan."""
    user = get_current_user()
    # IT yo'nalishlari ro'yxati
    directions = query_all(
        "SELECT * FROM directions WHERE slug NOT IN ('ingliz-tili','matematika','office') ORDER BY sort_order"
    )
    direction_progress = []
    for d in directions:
        progress = cert_mod.get_user_direction_progress(user["id"], d["id"])
        # Mavjud ariza yoki imtihon
        application = query_one(
            "SELECT * FROM certificate_applications WHERE user_id=? AND direction_id=? ORDER BY id DESC LIMIT 1",
            (user["id"], d["id"])
        )
        paid = cert_mod.has_paid_for_exam(user["id"], d["id"])
        direction_progress.append({
            "direction": d,
            "progress": progress,
            "application": application,
            "paid": paid,
            "is_it": cert_mod.is_it_direction(d["slug"]),
        })
    apps = cert_mod.get_user_applications(user["id"])
    return render_template("certificates.html",
                           direction_progress=direction_progress,
                           applications=apps,
                           exam_fee=get_price("certificate_exam_fee"))


@certs_bp.route("/certificates/<int:direction_id>/pay", methods=["POST"])
@login_required
def certificates_pay(direction_id):
    user = get_current_user()
    ok, msg = cert_mod.pay_for_certificate_exam(user["id"], direction_id)
    flash(msg, "success" if ok else "error")
    if ok:
        return redirect(url_for("certificates_exam", direction_id=direction_id))
    return redirect(url_for(".certificates_page"))


@certs_bp.route("/certificates/<int:direction_id>/exam")
@login_required
def certificates_exam(direction_id):
    """Sertifikat imtihoni sahifasi: 50 test (15 daq) + 15 amaliy (30 daq)."""
    user = get_current_user()
    if not cert_mod.has_paid_for_exam(user["id"], direction_id):
        flash("Avval imtihon uchun to'lov qilishingiz kerak.", "error")
        return redirect(url_for(".certificates_page"))
    direction = query_one("SELECT * FROM directions WHERE id=?", (direction_id,))
    if not direction:
        abort(404)
    # 50 ta test savol (yo'nalishdagi barcha kurslar testidan random tanlanadi)
    questions = query_all(
        """SELECT tq.* FROM test_questions tq
           JOIN tests t ON t.id = tq.test_id
           WHERE t.course_id IN (SELECT id FROM courses WHERE direction_id=?)
           ORDER BY RANDOM() LIMIT 50""",
        (direction_id,)
    )
    return render_template("certificates_exam.html",
                           direction=direction,
                           questions=questions,
                           test_duration_min=15,
                           practice_duration_min=30,
                           practice_count=15)


@certs_bp.route("/certificates/<int:direction_id>/submit", methods=["POST"])
@login_required
def certificates_submit(direction_id):
    """Imtihon yakuni — javoblar va amaliylar ballini hisoblaydi."""
    user = get_current_user()
    if not cert_mod.has_paid_for_exam(user["id"], direction_id):
        flash("Avval to'lov qiling.", "error")
        return redirect(url_for(".certificates_page"))

    # Test ballini hisoblash
    test_score = 0
    test_total = 0
    for key, value in request.form.items():
        if key.startswith("q_"):
            qid = key[2:]
            try:
                qid_int = int(qid)
            except ValueError:
                continue
            q = query_one("SELECT correct_option FROM test_questions WHERE id=?", (qid_int,))
            if q:
                test_total += 1
                if (value or "").lower() == q["correct_option"].lower():
                    test_score += 1

    # Amaliy ballini hisoblash (15 ta amaliy, har biri 0-10 ball, mijoz tomonidan o'zi baholaydi
    # demo uchun — real loyihada mentor baholaydi)
    practice_score = 0
    practice_total = 15 * 10  # 150 ball
    for i in range(1, 16):
        v = request.form.get(f"practice_{i}", "0")
        try:
            pv = max(0, min(10, int(v)))
        except ValueError:
            pv = 0
        practice_score += pv

    passed, msg, attempt_id = cert_mod.submit_exam_results(
        user["id"], direction_id, test_score, test_total, practice_score, practice_total
    )

    if passed:
        # Avtomatik ariza yaratish
        ok, app_msg = cert_mod.create_certificate_application(user["id"], direction_id, attempt_id)
        flash(f"Tabriklaymiz! Imtihondan o'tdingiz ({test_score+practice_score}/{test_total+practice_total}). "
              f"Sertifikat arizasi avtomatik yuborildi — admin tasdiqlashini kuting.", "success")
    else:
        flash(f"Afsus, imtihondan o'ta olmadingiz ({test_score+practice_score}/{test_total+practice_total}). "
              f"60% kerak. Qayta to'lab urinish mumkin.", "error")
    return redirect(url_for(".certificates_page"))

