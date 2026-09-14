# ============================================================
# CYBER SHATS — SHATS POS bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import get_current_user, login_required
from db import query_one, query_all, execute

shatspos_bp = Blueprint("shatspos_bp", __name__)


def _require_hacker_plan():
    from app import _require_hacker_plan as _real_fn
    return _real_fn()



# =================================================================
# SHATS POS — savdo simulyatsiyasi (MAXSUS)
# =================================================================
@shatspos_bp.route("/shats-pos")
@login_required
def shats_pos_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    products = query_all("SELECT * FROM pos_products WHERE user_id=? ORDER BY id DESC", (user["id"],))
    sales = query_all(
        """SELECT s.*, p.name as product_name FROM pos_sales s
           JOIN pos_products p ON p.id = s.product_id
           WHERE s.user_id=? ORDER BY s.created_at DESC LIMIT 20""",
        (user["id"],)
    )
    total_revenue = query_one("SELECT COALESCE(SUM(total),0) t FROM pos_sales WHERE user_id=?", (user["id"],))["t"]
    return render_template("shats_pos.html", products=products, sales=sales, total_revenue=total_revenue)


@shatspos_bp.route("/shats-pos/product/add", methods=["POST"])
@login_required
def shats_pos_add_product():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    name = request.form.get("name", "").strip()
    try:
        price = int(request.form.get("price", 0))
        stock = int(request.form.get("stock", 0))
    except ValueError:
        price, stock = 0, 0
    if name and price > 0:
        execute("INSERT INTO pos_products (user_id, name, price, stock) VALUES (?,?,?,?)",
                (user["id"], name, price, stock))
        flash("Mahsulot qo'shildi (virtual do'kon).", "success")
    return redirect(url_for(".shats_pos_page"))


@shatspos_bp.route("/shats-pos/product/<int:product_id>/sell", methods=["POST"])
@login_required
def shats_pos_sell(product_id):
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    product = query_one("SELECT * FROM pos_products WHERE id=? AND user_id=?", (product_id, user["id"]))
    if not product:
        abort(404)
    try:
        qty = int(request.form.get("qty", 1))
    except ValueError:
        qty = 1
    if qty <= 0 or qty > product["stock"]:
        flash("Omborda yetarli mahsulot yo'q (bu — simulyatsiya, real savdo emas).", "error")
        return redirect(url_for(".shats_pos_page"))
    total = qty * product["price"]
    execute("UPDATE pos_products SET stock = stock - ? WHERE id=?", (qty, product_id))
    execute("INSERT INTO pos_sales (user_id, product_id, qty, total) VALUES (?,?,?,?)",
            (user["id"], product_id, qty, total))
    flash(f"Sotildi: {qty} dona, jami {total:,} (virtual, real pul emas).", "success")
    return redirect(url_for(".shats_pos_page"))
