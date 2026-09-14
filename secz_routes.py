# ============================================================
# CYBER SHATS — Xavfsizlik zonasi (MAXSUS versiya) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from utils import api_response
import os

secz_bp = Blueprint("secz_bp", __name__)


def _require_hacker_plan():
    user = get_current_user()
    if not user or user.get("plan") != "hacker":
        flash("Bu bo'lim faqat MAXSUS versiya foydalanuvchilari uchun.", "error")
        return redirect(url_for("coins_bp.coins_page"))
    return None


@secz_bp.route("/xavfsizlik-zonasi")
@login_required
def security_zone_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    user = get_current_user()
    articles = sz.get_articles_by_category()
    glossary = sz.get_glossary()
    blacklist = sz.get_blacklist_apps()
    user_score = sz.get_user_score(user["id"])
    checklist, done, total = sz.get_checklist_with_progress(user["id"])
    return render_template("security_zone.html", articles=articles, glossary=glossary,
                           blacklist=blacklist, user_score=user_score,
                           checklist=checklist, checklist_done=done, checklist_total=total)


@secz_bp.route("/xavfsizlik-zonasi/maqola/<slug>")
@login_required
def security_zone_article(slug):
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    article = sz.get_article(slug)
    if not article:
        abort(404)
    return render_template("security_zone_article.html", article=article)


@secz_bp.route("/xavfsizlik-zonasi/test", methods=["GET", "POST"])
@login_required
def security_zone_quiz():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    user = get_current_user()
    if request.method == "POST":
        answers = {k.replace("q_", ""): v for k, v in request.form.items() if k.startswith("q_")}
        result = sz.submit_quiz(user["id"], answers)
        return render_template("security_zone_quiz_result.html", result=result)
    questions = sz.get_quiz_questions()
    return render_template("security_zone_quiz.html", questions=questions)


@secz_bp.route("/api/xavfsizlik-zonasi/parol-tekshirish", methods=["POST"])
@login_required
def api_security_password_check():
    guard = _require_hacker_plan()
    if guard:
        return api_response(False, error="Ruxsat yo'q")
    import security_zone as sz
    data = request.get_json(silent=True) or {}
    result = sz.check_password_strength(data.get("password", ""))
    return api_response(True, data=result)


@secz_bp.route("/xavfsizlik-zonasi/cheklist/toggle", methods=["POST"])
@login_required
def security_zone_checklist_toggle():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    user = get_current_user()
    try:
        item_id = int(request.form.get("item_id", 0))
    except ValueError:
        item_id = 0
    sz.toggle_checklist_item(user["id"], item_id)
    return redirect(url_for(".security_zone_page") + "#cheklist")


@secz_bp.route("/xavfsizlik-zonasi/sertifikat")
@login_required
def security_certificate_page():
    """Xavfsizlik sertifikat markazi — testda 90%+ to'plagan foydalanuvchi PDF sertifikat oladi."""
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    user = get_current_user()
    score = sz.get_user_score(user["id"])
    eligible = bool(score) and score["total"] > 0 and (score["score"] / score["total"]) >= 0.9
    return render_template("security_certificate.html", score=score, eligible=eligible)


@secz_bp.route("/xavfsizlik-zonasi/sertifikat/pdf")
@login_required
def security_certificate_pdf():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas

    user = get_current_user()
    score = sz.get_user_score(user["id"])
    if not score or score["total"] == 0 or (score["score"] / score["total"]) < 0.9:
        flash("Sertifikat olish uchun testda kamida 90% ball to'plashingiz kerak.", "error")
        return redirect(url_for(".security_zone_quiz"))

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "generated")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"security_cert_{user['id']}.pdf")

    c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(A4))
    w, h = landscape(A4)
    bg = HexColor("#0d0a14")
    purple = HexColor("#a855f7")
    text_c = HexColor("#e8e0f5")

    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(purple)
    c.setLineWidth(2)
    c.rect(15 * mm, 15 * mm, w - 30 * mm, h - 30 * mm, fill=0, stroke=1)

    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(w / 2, h - 45 * mm, "XAVFSIZLIK SERTIFIKATI")
    c.setFillColor(text_c)
    c.setFont("Helvetica", 13)
    c.drawCentredString(w / 2, h - 60 * mm, "Ushbu sertifikat quyidagi shaxsga beriladi:")
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 75 * mm, f"{user['familiya']} {user['ism']}")
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 88 * mm,
                        f"CYBER SHATS MAXSUS — Xavfsizlik testida {score['score']}/{score['total']} ball ({score['level']})")
    c.setFont("Helvetica", 9)
    c.drawCentredString(w / 2, 25 * mm, f"Berilgan sana: {score['taken_at'][:10]}")

    c.showPage()
    c.save()
    return send_file(pdf_path, as_attachment=True, download_name="xavfsizlik_sertifikati.pdf")


@secz_bp.route("/xavfsizlik-zonasi/cheklist/pdf")
@login_required
def security_zone_checklist_pdf():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import security_zone as sz
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas

    user = get_current_user()
    checklist, done, total = sz.get_checklist_with_progress(user["id"])

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "generated")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"security_checklist_{user['id']}.pdf")

    purple = HexColor("#a855f7")
    bg = HexColor("#0d0a14")
    text_c = HexColor("#e8e0f5")

    c = pdf_canvas.Canvas(pdf_path, pagesize=A4)
    w, h = A4
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w / 2, h - 25 * mm, "XAVFSIZLIK CHEKLISTI")
    c.setFont("Helvetica", 10)
    c.setFillColor(text_c)
    c.drawCentredString(w / 2, h - 33 * mm, f"{user['familiya']} {user['ism']} — {done}/{total} bajarilgan")

    y = h - 45 * mm
    for category, items in checklist.items():
        c.setFillColor(purple)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, y, category)
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        for item in items:
            mark = "[X]" if item["checked"] else "[ ]"
            c.setFillColor(HexColor("#00c853") if item["checked"] else text_c)
            c.drawString(24 * mm, y, f"{mark} {item['text']}")
            y -= 6 * mm
            if y < 20 * mm:
                c.showPage()
                c.setFillColor(bg)
                c.rect(0, 0, w, h, fill=1, stroke=0)
                y = h - 20 * mm
        y -= 4 * mm

    c.showPage()
    c.save()
    return send_file(pdf_path, as_attachment=True, download_name="xavfsizlik_cheklisti.pdf")
