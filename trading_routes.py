# ============================================================
# CYBER SHATS — Trading (bekor qilingan, stub) bo'limi (Blueprint)
# ============================================================
from flask import Blueprint, request, redirect, url_for, flash, render_template
from auth import login_required, api_login_required
from utils import api_response

trading_bp = Blueprint("trading_bp", __name__)


@trading_bp.route("/trading")
@login_required
def trading_page():
    # Trading bo'limi butunlay olib tashlandi
    flash("Trading bo'limi olib tashlangan.", "warn")
    return redirect(url_for("dashboard"))


@trading_bp.route("/api/trading/tick")
def api_trading_tick():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/open", methods=["POST"])
@api_login_required
def api_trading_open():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/status")
@api_login_required
def api_trading_status():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/chart")
def api_trading_chart():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/stats")
def api_trading_stats():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/ohlc")
def api_trading_ohlc():
    return api_response(False, error="Trading bo'limi olib tashlangan.")


@trading_bp.route("/api/trading/history")
@api_login_required
def api_trading_history():
    return api_response(False, error="Trading bo'limi olib tashlangan.")

