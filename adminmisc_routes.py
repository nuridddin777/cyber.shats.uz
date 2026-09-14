# ============================================================
# CYBER SHATS — Admin Qo'shimcha bo'limlar (Blueprint)
# ============================================================
# Dizayn, Promo kodlar, Narxlash, Trading paneli, Kod almashtirish, Bonus
from flask import Blueprint, request, redirect, url_for, flash, render_template, session
from auth import get_current_user, admin_required, super_admin_required
from db import query_one, query_all, execute, log_action
from utils import resolve_user_id
import trading_stub as trading_mod
import redeem_codes
import group_reports
import random, string

adminmisc_bp = Blueprint("adminmisc_bp", __name__)


@adminmisc_bp.route("/admin/design", methods=["GET", "POST"])
@admin_required
def admin_design():
    """Sayt dizaynini boshqarish — tema, panel holati, trading trend."""
    if request.method == "POST":
        action = request.form.get("action")

        if action == "save_theme":
            theme = request.form.get("theme", "none")
            theme_name = {
                "none": "Oddiy (mavsumiy tema yo'q)",
                "independence35": "O'zbekiston Mustaqilligi — 35 yilligi",
                "oct1": "O'qituvchi va Murabbiylar kuni (1-oktabr)",
                "newyear": "Yangi yil",
            }.get(theme, theme)
            execute("INSERT INTO site_settings (key,value) VALUES ('site_theme',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')", (theme,))
            execute("INSERT INTO site_settings (key,value) VALUES ('site_theme_name',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')", (theme_name,))
            flash(f"Tema o'zgartirildi: {theme_name}! Hamma foydalanuvchilarda darhol ko'rinadi.", "success")

        elif action == "save_panel":
            panels = {
                "trading": "Trading bo'limi",
                "hacker_lab": "Hacker Lab",
                "startups": "Startaplar",
                "forum": "Forum",
                "groups": "Guruhlar",
                "channels": "Kanallar",
                "stories": "Stories",
                "reels": "Reels",
                "library": "E-kutubxona",
                "smm": "SMM",
                "ai": "AI Yordamchi",
            }
            for panel_key in panels:
                is_active = 1 if request.form.get(f"panel_{panel_key}") else 0
                msg = request.form.get(f"msg_{panel_key}", "").strip() or None
                execute(
                    "INSERT INTO panel_status (panel_key,is_active,maintenance_msg,updated_by,updated_at) VALUES (?,?,?,?,datetime('now')) ON CONFLICT(panel_key) DO UPDATE SET is_active=excluded.is_active, maintenance_msg=excluded.maintenance_msg, updated_by=excluded.updated_by, updated_at=excluded.updated_at",
                    (panel_key, is_active, msg, session["user_id"])
                )
            flash("Panel holatlari yangilandi!", "success")

        elif action == "save_trading_trend":
            direction = request.form.get("trend_direction", "neutral")
            target = float(request.form.get("target_pct", "0") or "0")
            days = int(request.form.get("duration_days", "7") or "7")
            volatility = float(request.form.get("volatility", "0.015") or "0.015")
            execute("UPDATE trading_trend SET active=0 WHERE active=1")
            execute(
                "INSERT INTO trading_trend (direction,target_change_pct,duration_days,volatility,created_by,active) VALUES (?,?,?,?,?,1)",
                (direction, target, days, volatility, session["user_id"])
            )
            flash(f"Trading trend yangilandi: {direction} | {target}% / {days} kun | Volatillik: {volatility}", "success")

        elif action == "grant_exclusive":
            target_id = request.form.get("target_user_id", "").strip()
            exclusive_key = request.form.get("exclusive_theme_key", "cars").strip()
            exclusive_labels = {
                "cars": ("🏎️ Garage (moshinalar)", "Garage (moshinalar)"),
                "wolfpack": ("🐺 Qashqirlar Makoni", "Qashqirlar Makoni"),
            }
            if exclusive_key not in exclusive_labels:
                flash("Noto'g'ri tema turi.", "error")
                return redirect(url_for(".admin_design"))
            emoji_label, plain_label = exclusive_labels[exclusive_key]
            target = query_one("SELECT id, ism, familiya, custom_id FROM users WHERE id=? OR custom_id=?",
                               (target_id, target_id))
            if not target:
                flash("Foydalanuvchi topilmadi (ID yoki maxsus ID kiriting).", "error")
            else:
                execute("UPDATE users SET exclusive_theme=? WHERE id=?", (exclusive_key, target["id"]))
                execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                        (target["id"], f"Sizga eksklyuziv dizayin berildi! {emoji_label}",
                         f"Super admin sizga maxsus '{plain_label}' dizaynini berdi — u endi avtomatik faol.",
                         "success"))
                log_action(session["user_id"], "grant_exclusive_theme",
                           details=f"target:{target['id']},theme:{exclusive_key}", ip=request.remote_addr)
                flash(f"«{target['familiya']} {target['ism']}» ga eksklyuziv '{plain_label}' dizayni berildi.", "success")

        elif action == "revoke_exclusive":
            target_id = request.form.get("target_user_id", "").strip()
            execute("UPDATE users SET exclusive_theme=NULL WHERE id=? OR custom_id=?", (target_id, target_id))
            flash("Eksklyuziv dizayin olib tashlandi.", "success")

        elif action == "reset_user_theme":
            target_id = request.form.get("target_user_id", "").strip()
            target = query_one("SELECT id FROM users WHERE id=? OR custom_id=?", (target_id, target_id))
            if target:
                execute("DELETE FROM user_themes WHERE user_id=?", (target["id"],))
                execute("UPDATE users SET personal_theme_changes=0 WHERE id=?", (target["id"],))
                flash("Foydalanuvchi shaxsiy dizayni asl holatga qaytarildi.", "success")
            else:
                flash("Foydalanuvchi topilmadi.", "error")

        return redirect(url_for(".admin_design"))

    settings = {}
    try:
        settings = {r["key"]: r["value"] for r in query_all("SELECT key,value FROM site_settings")}
    except Exception:
        pass

    panels = {}
    try:
        for r in query_all("SELECT * FROM panel_status"):
            panels[r["panel_key"]] = {"active": r["is_active"], "msg": r["maintenance_msg"]}
    except Exception:
        pass

    trend = query_one("SELECT * FROM trading_trend WHERE active=1 ORDER BY id DESC LIMIT 1")
    current_price = trading_mod.get_current_price()
    cars_theme_users = query_all(
        "SELECT id, ism, familiya, custom_id, exclusive_theme FROM users WHERE exclusive_theme IS NOT NULL")
    return render_template("admin_design.html", settings=settings, panels=panels,
                           trend=trend, current_price=current_price, cars_theme_users=cars_theme_users)


@adminmisc_bp.route("/admin/promo-codes", methods=["GET", "POST"])
@admin_required
def admin_promo_codes():
    """Promo kodlarni boshqarish."""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            import random, string
            code = request.form.get("code", "").strip().upper()
            if not code:
                code = "SHATS" + "".join(random.choices(string.digits, k=4))
            try:
                bonus = int(request.form.get("bonus_code_amount", 10))
                max_uses = int(request.form.get("max_uses", 100))
            except ValueError:
                bonus, max_uses = 10, 100
            expires = request.form.get("expires_at", "").strip() or None
            note = request.form.get("note", "").strip() or None
            try:
                execute(
                    "INSERT INTO promo_codes (code,discount_type,discount_value,bonus_code_amount,max_uses,expires_at,note,created_by) VALUES (?,?,?,?,?,?,?,?)",
                    (code, "bonus", 0, bonus, max_uses, expires, note, session["user_id"])
                )
                flash(f"Promo kod yaratildi: {code} (+{bonus} CODE bonus)", "success")
            except Exception:
                flash("Bu promo kod allaqachon mavjud.", "error")

        elif action == "toggle":
            pid = request.form.get("promo_id")
            execute("UPDATE promo_codes SET is_active=1-is_active WHERE id=?", (pid,))
            flash("Holat o'zgartirildi.", "success")

        elif action == "delete":
            pid = request.form.get("promo_id")
            execute("DELETE FROM promo_codes WHERE id=?", (pid,))
            flash("Promo kod o'chirildi.", "success")

        return redirect(url_for(".admin_promo_codes"))

    promos = query_all("SELECT p.*, u.ism, u.familiya FROM promo_codes p LEFT JOIN users u ON u.id=p.created_by ORDER BY p.id DESC")
    return render_template("admin_promo_codes.html", promos=promos)


@adminmisc_bp.route("/admin/pricing/packages", methods=["POST"])
@admin_required
def admin_update_packages():
    """CODE paket narxlarini yangilash."""
    packs = [1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    for amt in packs:
        val = request.form.get(f"code_pack_{amt}", "").strip()
        if val and val.isdigit() and int(val) > 0:
            execute(
                "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (f"code_pack_{amt}", val)
            )
    flash("Paket narxlari saqlandi! Bot keyingi so'rovda yangi narxlarni ishlatadi.", "success")
    return redirect(url_for(".admin_pricing"))


@adminmisc_bp.route("/admin/pricing", methods=["GET", "POST"])
@admin_required
def admin_pricing():
    """CODE narxlari va ayirboshlash kursini boshqarish."""
    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_pricing":
            keys = [
                "pro_price_code", "cyber_pro_price_code", "vip_price_code", "hacker_price_code",
                "welcome_bonus_code", "paid_course_code_default",
                "code_to_som_rate",
                "tarif_basic_uzs", "tarif_standard_uzs", "tarif_pro_uzs", "tarif_vip_uzs",
                "team_tax_free_code", "team_tax_paid_code", "team_tax_hacker_code", "team_hacker_free_months",
            ]
            old_settings = {r["key"]: r["value"] for r in query_all("SELECT key, value FROM pricing_settings")}
            changed = []
            for k in keys:
                val = request.form.get(k, "").strip()
                if val and val.isdigit():
                    if old_settings.get(k) != val:
                        changed.append((k, old_settings.get(k), val))
                    execute(
                        "INSERT INTO pricing_settings (key, value) VALUES (?,?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (k, val)
                    )
            if changed:
                import group_reports
                group_reports.report_price_change(changed)
            flash("Narxlar saqlandi!", "success")
        return redirect(url_for(".admin_pricing"))

    settings = {r["key"]: r["value"] for r in query_all("SELECT key, value FROM pricing_settings")}
    return render_template("admin_pricing.html", settings=settings)


@adminmisc_bp.route("/admin/trading")
@admin_required
def admin_trading():
    flash("Trading bo'limi olib tashlangan.", "warn")
    return redirect(url_for("admindash_bp.admin_dashboard"))


@adminmisc_bp.route("/admin/redeem-codes", methods=["GET", "POST"])
@super_admin_required
def admin_redeem_codes():
    import redeem_codes
    admin_user = get_current_user()
    if request.method == "POST":
        duration_type = request.form.get("duration_type", "30d")
        try:
            count = int(request.form.get("count", 1))
        except ValueError:
            count = 1
        codes = redeem_codes.generate_codes(admin_user["id"], duration_type, count, plan="hacker")
        flash(f"{len(codes)} ta kod yaratildi: " + ", ".join(codes[:10]) + (" ..." if len(codes) > 10 else ""), "success")
        return redirect(url_for(".admin_redeem_codes"))
    codes = redeem_codes.list_recent_codes(100)
    return render_template("admin_redeem_codes.html", codes=codes)


@adminmisc_bp.route("/admin/bonus/give", methods=["POST"])
@super_admin_required
def admin_give_bonus():
    """Admin foydalanuvchi(lar)ga qo'lda CODE bonus beradi."""
    admin_user = get_current_user()
    mode = request.form.get("mode", "single")
    reason_note = request.form.get("note", "").strip() or "admin_bonus"
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        amount = 0

    if amount <= 0:
        flash("Bonus miqdorini to'g'ri kiriting.", "error")
        return redirect(url_for(".admin_pricing"))

    if mode == "all":
        users = query_all("SELECT id FROM users")
        for u in users:
            add_coins(u["id"], amount, "admin_bonus", None)
        log_action(admin_user["id"], "admin_bonus_all", details=f"amount:{amount},note:{reason_note}")
        flash(f"{len(users)} ta foydalanuvchiga {amount:,} CODE bonus berildi!", "success")
    else:
        recipient_raw = request.form.get("recipient", "").strip()
        target_id = resolve_user_id(recipient_raw.lstrip("#")) if recipient_raw else None
        if not target_id:
            flash("Foydalanuvchi topilmadi. ID (#0000) yoki email kiriting.", "error")
            return redirect(url_for(".admin_pricing"))
        add_coins(target_id, amount, "admin_bonus", None)
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (target_id, f"Bonus: {amount:,} CODE",
                 f"Administratsiya tomonidan sizga {amount:,} CODE bonus berildi!" + (f" ({reason_note})" if reason_note != 'admin_bonus' else ""),
                 "success"))
        log_action(admin_user["id"], "admin_bonus_single", details=f"user:{target_id},amount:{amount},note:{reason_note}")
        flash(f"{amount:,} CODE bonus berildi!", "success")

    return redirect(url_for(".admin_pricing"))


@adminmisc_bp.route("/admin/trading/reset-price", methods=["POST"])
@admin_required
def admin_trading_reset_price():
    """Narxni bazaviy 1.0 ga qaytaradi."""
    from db import execute as db_execute
    db_execute("INSERT INTO trading_prices (price, change_pct, direction) VALUES (1.0, 0, 0)")
    flash("Narx 1.0 ga qaytarildi.", "success")
    return redirect(url_for(".admin_trading"))


@adminmisc_bp.route("/admin/trading/close-all", methods=["POST"])
@admin_required
def admin_trading_close_all():
    """Barcha ochiq pozitsiyalarni majburiy yopadi (tiklov qaytariladi)."""
    open_positions = query_all("SELECT * FROM trading_positions WHERE status='open'")
    for pos in open_positions:
        from coins import add_coins
        add_coins(pos["user_id"], pos["amount"], "trading_admin_cancel")
    from db import execute as db_execute
    db_execute("UPDATE trading_positions SET status='cancelled', closed_at=datetime('now') WHERE status='open'")
    flash(f"{len(open_positions)} ta ochiq pozitsiya yopildi, tiklovlar qaytarildi.", "success")
    return redirect(url_for(".admin_trading"))
