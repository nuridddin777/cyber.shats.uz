# ============================================================
# CYBER SHATS — Kutubxona / Yangiliklar (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, render_template
from auth import login_required
from db import query_all

library_bp = Blueprint("library_bp", __name__)


def _check_panel(panel_key: str):
    """app.py'dagi bilan bir xil — bir nechta blueprint'da ishlatiladi."""
    from app import _check_panel as _real_check_panel
    return _real_check_panel(panel_key)


# =================================================================
# E-KUTUBXONA / YANGILIKLAR / GAMIFIKATSIYA
# =================================================================
@library_bp.route("/library")
@login_required
def library():
    check = _check_panel("library")
    if check: return check
    category = request.args.get("cat", "")
    sql = "SELECT * FROM books"
    args = ()
    if category:
        sql += " WHERE category=?"
        args = (category,)
    sql += " ORDER BY id DESC"
    books = query_all(sql, args)
    return render_template("library.html", books=books, active_cat=category)


@library_bp.route("/news")
@login_required
def news():
    category = request.args.get("cat", "")
    sql = "SELECT * FROM news"
    args = ()
    if category:
        sql += " WHERE category=?"
        args = (category,)
    sql += " ORDER BY published_at DESC LIMIT 40"
    items = query_all(sql, args)
    return render_template("news.html", items=items, active_cat=category)






@library_bp.route("/gamification")
@login_required
def gamification():
    """DIQQAT: bu sahifa endi mustaqil emas — pastdagi /leaderboard
    marshrutiga yo'naltiriladi (qarang: quyida ikkinchi ta'rif)."""
    return redirect(url_for("leaderboard"))

