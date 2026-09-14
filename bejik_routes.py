# ============================================================
# CYBER SHATS — Bejik va QR kod bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template, send_file, Response, abort
from auth import get_current_user, login_required
from db import query_one, query_all, execute
from config import Config
import os, io

bejik_bp = Blueprint("bejik_bp", __name__)


# BEJIK VA QR KOD (MAXSUS)
# =================================================================
@bejik_bp.route("/bejik")
@login_required
def bejik_page():
    user = get_current_user()
    fresh = query_one("SELECT * FROM users WHERE id=?", (user["id"],))
    scan_count = query_one("SELECT COUNT(*) c FROM qr_scan_log WHERE badge_user_id=?", (user["id"],))["c"]
    recent_scans = query_all(
        "SELECT * FROM qr_scan_log WHERE badge_user_id=? ORDER BY scanned_at DESC LIMIT 15",
        (user["id"],)
    )
    return render_template("bejik.html", u=fresh, scan_count=scan_count, recent_scans=recent_scans)


@bejik_bp.route("/bejik/<custom_id>/qr.png")
def bejik_qr_image(custom_id):
    """Bejikka bog'langan QR kod rasm sifatida (profil tasdiqlash havolasiga yo'naltiradi)."""
    import qrcode
    import io
    target = query_one("SELECT id FROM users WHERE custom_id=?", (custom_id,))
    if not target:
        abort(404)
    url = f"https://{Config.SITE_DOMAIN}/bejik/verify/{custom_id}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@bejik_bp.route("/bejik/verify/<custom_id>")
def bejik_verify(custom_id):
    """QR skanerlanganda ochiladigan tasdiqlash sahifasi — har bir skanerlash log qilinadi."""
    target = query_one("SELECT * FROM users WHERE custom_id=?", (custom_id,))
    if not target:
        abort(404)
    execute("INSERT INTO qr_scan_log (badge_user_id, scanner_ip) VALUES (?,?)",
            (target["id"], request.remote_addr or ""))
    return render_template("bejik_verify.html", u=target)


@bejik_bp.route("/bejik/pdf")
@login_required
def bejik_pdf():
    from reportlab.lib.pagesizes import landscape
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader
    import qrcode
    import io

    user = get_current_user()
    fresh = query_one("SELECT * FROM users WHERE id=?", (user["id"],))

    card_size = (85.6 * mm, 54 * mm)  # standart plastik karta o'lchami
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "generated")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"bejik_{user['id']}.pdf")

    c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(card_size))
    w, h = landscape(card_size)

    bg = HexColor("#0d0a14")
    purple = HexColor("#a855f7")
    text_c = HexColor("#e8e0f5")

    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(purple)
    c.setLineWidth(1.2)
    c.rect(2, 2, w - 4, h - 4, fill=0, stroke=1)

    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(6 * mm, h - 8 * mm, "CYBER SHATS — MAXSUS")

    c.setFillColor(text_c)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(6 * mm, h - 16 * mm, f"{fresh['familiya']} {fresh['ism']}")
    c.setFont("Helvetica", 8)
    c.drawString(6 * mm, h - 21 * mm, f"#{fresh['custom_id']} · LVL {fresh.get('level', 1)}")
    c.drawString(6 * mm, h - 26 * mm, f"XP: {fresh.get('xp', 0)}")

    # QR
    qr_url = f"https://{Config.SITE_DOMAIN}/bejik/verify/{fresh['custom_id']}"
    qr_img = qrcode.make(qr_url)
    qr_buf = io.BytesIO()
    qr_img.save(qr_buf, format="PNG")
    qr_buf.seek(0)
    qr_size = 18 * mm
    c.drawImage(ImageReader(qr_buf), w - qr_size - 5 * mm, 5 * mm, width=qr_size, height=qr_size)

    c.showPage()
    c.save()
    return send_file(pdf_path, as_attachment=True, download_name="bejik.pdf")


# =================================================================
# SOZLAMALAR MAXSUS (MAXSUS)
