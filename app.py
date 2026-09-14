# ============================================================
# CYBER SHATS — Flask asosiy ilova fayli
# Barcha route'lar shu yerda joylashgan.
# ============================================================
import sys
# Windows'da konsol standart kodировкаси (cp1251/cp866) ba'zan emoji va
# o'zbek harflarini chiqara olmay, UnicodeEncodeError bilan dastur butunlay
# yiqilib qolishiga sabab bo'ladi. Shu sababli konsol chiqishini majburiy
# UTF-8'ga o'tkazamiz (Windows'da ham, Linux/macOS'da ham xavfsiz).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os

# =============================================================
# XAVFSIZLIK: MAVJUD MA'LUMOTLAR BAZASINI HECH QACHON O'CHIRMASLIK
# =============================================================
# BU TEKSHIRUV ATAYLAB ENG BOSHIDA, BOSHQA HECH QANDAY IMPORT
# QILINMASDAN OLDIN turibdi. Sabab: agar bu keyinroq (masalan Flask
# ilovasi yaratilgandan keyin) joylashtirilsa, o'sha vaqtgacha allaqachon
# BOSHQA modul (masalan `db.py`) sqlite3.connect() chaqirib, "yo'q" deb
# hisoblangan joyga TASODIFAN BO'SH FAYL yaratib qo'yishi mumkin — va shu
# bo'sh fayl "baza allaqachon bor" deb noto'g'ri xulosaga olib keladi,
# haqiqiy namunaviy ma'lumotlar hech qachon nusxalanmay qoladi. Shuning
# uchun bu tekshiruv MUTLAQ birinchi bo'lib, hech narsa bazaga ulanishdan
# oldin ishlaydi.
#
# Ishlash mantig'i: agar serverda HAQIQIY baza (database/cyber_shats.db)
# allaqachon mavjud bo'lsa — unga HECH QANDAY tarzda tegilmaydi (shuning
# uchun eski foydalanuvchilar hech qachon yo'qolmaydi, zipni necha marta
# qayta joylashtirsangiz ham). Agar u umuman yo'q bo'lsa (haqiqatan ham
# birinchi marta o'rnatilayotgan bo'lsa) — o'shandagina namunaviy
# (database/cyber_shats.db.SEED) bazadan nusxa olinadi.
_early_db_path = os.environ.get("DB_PATH", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "database", "cyber_shats.db"))
_early_db_seed = _early_db_path + ".SEED"
if not os.path.exists(_early_db_path) and os.path.exists(_early_db_seed):
    import shutil as _early_shutil
    os.makedirs(os.path.dirname(_early_db_path), exist_ok=True)
    _early_shutil.copy2(_early_db_seed, _early_db_path)
    print(f"[BOOTSTRAP] Birinchi marta o'rnatish — namunaviy baza nusxalandi: {_early_db_path}")
elif os.path.exists(_early_db_path):
    print(f"[BOOTSTRAP] Mavjud ma'lumotlar bazasi SAQLANMOQDA (tegilmaydi): {_early_db_path}")

import re
import random
import string
import datetime
import json
import logging

# MUHIM: Flask'ning standart logger sozlamalari ba'zi muhitlarda (masalan
# gunicorn ostida) xatolarni ko'rsatmasligi mumkin. Shuning uchun bu yerda
# ANIQ sozlaymiz — 500-xatolarning to'liq traceback'i ALBATTA konsolga
# (Railway'da "Deployments > Logs") chiqishi kafolatlanadi.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort, jsonify
from markupsafe import Markup
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from db import get_db, close_db, query_one, query_all, execute, log_action, ensure_schema, USE_POSTGRES
from auth import (login_required, admin_required, super_admin_required,
                  get_current_user, api_login_required)
from admins import (get_all_admins, create_new_admin, promote_user_to_admin,
                     demote_admin, super_admin_change_admin_id,
                     get_admin_directions, admin_can_manage_direction, admin_can_manage_course,
                     super_admin_reset_admin_password)
import admins as admins_mod
from utils import api_response, time_ago_uz, fmt_duration, to_tashkent, resolve_user_id
from ai import call_ai_assistant, is_ai_configured, active_provider_name, generate_image
import ai_testgen
import ai_recommendations
from security import (check_brute_force, record_failed_login, clear_failed_logins,
                      log_security_event, is_ip_blocked, block_ip, scan_request,
                      check_rate_limit)
from csrf_protect import get_csrf_token, csrf_protect, apply_security_headers
from coins import (get_balance, add_coins, spend_coins, award_course_completion,
                   buy_pro_with_coins, buy_cyber_pro_with_coins, buy_vip_with_coins,
                   buy_course_with_coins, ensure_ai_access,
                   ensure_ai_access_code_help, ensure_ai_access_general, buy_ai_daily_boost,
                   get_leaderboard, get_transactions, _update_rating,
                   transfer_coins, check_and_downgrade_expired_plan)
from messaging import (get_conversations, get_thread, send_message, mark_thread_read,
                       get_unread_total, search_users)
import treasury as treasury_mod
import webpush_mod as push_mod
import pingtest as ping_mod
import announcements as ann_mod
import hacker_lab as hacker_lab_mod
import terminal_sim
import coins_purchase
import special_challenge as challenge_mod
import social
import friends as friends_mod
import chests as chests_mod
import collection as collection_mod
import frames_shop as frames_mod
import video_calls
import startups as startups_mod
import code_runner
import trading_stub as trading_mod  # V2: stub
from virtual_world import virtual_bp
from edu import edu_bp
from payment_webhooks import payment_bp
from oneid_auth import oneid_bp
from oauth_routes import oauth_bp
from ids import (generate_unique_id, set_user_id, get_premium_ids_list,
                 buy_premium_id, get_active_auctions, place_bid, finalize_auction,
                 init_premium_ids, _id_type_and_price,
                 admin_create_premium_id, admin_update_premium_id_price, admin_delete_premium_id,
                 get_vip_ids_list, assign_vip_id, revoke_vip_id, admin_set_alphanumeric_id,
                 admin_close_all_bidding_auctions, generate_random_id_offer, confirm_random_id,
                 REGULAR_ID_CHANGE_PRICE, create_sell_offer, get_user_sell_offer, cancel_sell_offer,
                 user_respond_to_counter, get_pending_sell_offers, admin_counter_offer,
                 admin_accept_offer_at_asking, admin_reject_offer, get_user_id_history,
                 reserve_random_id, get_active_reservation, cancel_reservation, buy_reserved_id,
                 RESERVATION_HOURS)
from smm_ai import chat_smm, SMM_DIRECTIONS, get_smm_history
from pricing import get_pricing, get_price, set_prices

app = Flask(__name__)

from webapp_routes import webapp_bp
app.register_blueprint(webapp_bp)


# DIQQAT: bu — HAR SAFAR yangi zip berilganda QO'LDA yangilanadigan, QATTIQ
# YOZILGAN belgi (joriy vaqt emas!). Maqsad — siz saytni ochganingizda,
# "bu chindan ham eng so'nggi kod ekanmi yoki eski (deploy qilinmagan)
# versiyami" ekanini BIR ZUMDA, hech qanday shubhasiz bilib olishingiz.
# Sahifa pastida (footer'da) ko'rinadi. Agar bu yerda ko'rgan qiymatingiz
# menyubergan oxirgi javobimdagi qiymat bilan mos kelmasa — demak hali
# eski kod ishlab turibdi, serveringizga yangi zip joylashtirilmagan.
BUILD_STAMP = "2026-08-24-14:15-airecs-blueprint-refactor"


app.config.from_object(Config)
# Global xavfsizlik chegarasi — YouTube-kabi katta video (o'qituvchilar uchun 500MB
# gacha) yuklashga ruxsat berish uchun, lekin cheksiz so'rov tanasidan DoS
# hujumidan himoyalanish uchun 550MB qattiq shifat (hard ceiling)qo'yiladi.
app.config["MAX_CONTENT_LENGTH"] = 550 * 1024 * 1024
if app.config.get("SECRET_KEY") == "cyber-shats-dev-secret-key-CHANGE-ME":
    print("⚠️  XAVFSIZLIK OGOHLANTIRISHI: SECRET_KEY hali ham standart (dev) qiymatda! "
          "Production'ga chiqishdan oldin SECRET_KEY muhit o'zgaruvchisini albatta o'zgartiring.")
ensure_schema(app.config["DB_PATH"])  # yetishmayotgan jadval/ustunlarni avtomatik to'g'rilaydi

# ---------------------------------------------------------------
# XAVFSIZLIK: sessiya cookie sozlamalari
# ---------------------------------------------------------------
# HttpOnly — JavaScript orqali sessiya cookie'sini o'qib bo'lmaydi (XSS orqali
# sessiya o'g'irlashning oldini oladi).
# SameSite=Lax — boshqa saytdan yuborilgan so'rovlarda cookie avtomatik
# yuborilmaydi (CSRF himoyasini kuchaytiradi).
# Secure — faqat HTTPS ustidan yuboriladi. Standart holatda O'CHIRILGAN,
# chunki lokal http://localhost orqali sinovda cookie umuman ishlamay
# qoladi. PRODUCTION serverga (HTTPS bilan) chiqarganda albatta
# FORCE_HTTPS_COOKIES=1 qiling (.env orqali)!
from datetime import timedelta
app.permanent_session_lifetime = timedelta(days=3)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = True


@app.context_processor
def _inject_csrf_token():
    """Barcha shablonlarga csrf_token() funksiyasini taqdim etadi."""
    return dict(csrf_token=get_csrf_token)


@app.before_request
def _global_security_gate():
    """Har bir so'rovdan oldin ishlaydigan yagona xavfsizlik nazorati:
    IP bloklash, so'rov chastotasi cheklovi (rate limit), zararli
    kontent skaneri (SQLi/XSS naqshlari) va CSRF tekshiruvi."""
    # Statik fayllarga (rasm, JS, CSS) xavfsizlik tekshiruvlari kerak emas —
    # ular hech qanday holatni o'zgartirmaydi.
    if request.path.startswith("/static"):
        return None

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()

    if is_ip_blocked(ip):
        log_security_event(None, "blocked_ip_request", ip,
                           request.headers.get("User-Agent", ""), request.path, "high")
        abort(403)

    if check_rate_limit(ip):
        return jsonify({"error": "Juda ko'p so'rov. Biroz kuting."}), 429

    # DIQQAT: security.py'dagi scan_request() (SQLi/XSS naqsh skaneri) ATAY
    # bu yerga global qo'shilmadi. Sabab: bu platforma kod bajarish
    # (code_runner), Hacker Lab va kiberxavfsizlik ta'lim kontenti bilan
    # ishlaydi — talabalar dars/vazifa doirasida xuddi shu kalit so'zlarni
    # ("SELECT", "<script>", "eval(") yozishlari TABIIY va qonuniy holat.
    # Global auto-blok bu yerda haqiqiy talabalarni IP darajasida bloklab
    # qo'yishi mumkin edi. scan_request() funksiyasi kerak bo'lgan aniq,
    # tor doiradagi endpoint'larda (masalan tashqi forma/kontakt kabi sof
    # matn maydonlarida) alohida chaqirilishi mumkin.
    return csrf_protect()


@app.after_request
def _apply_security_headers(response):
    return apply_security_headers(response)

# --- EDU 2.0 (tashkilot arxitekturasi) migratsiyalarini avtomatik ishga tushirish ---
# Bu funksiyalar to'liq idempotent (CREATE TABLE IF NOT EXISTS / INSERT OR IGNORE /
# ALTER...except), shuning uchun har ishga tushishda xavfsiz qayta chaqiriladi.
#
# MUHIM (tuzatilgan YANA BIR JIDDIY, TIZIMIY XATO — bu safar IMPORT
# bosqichida): avval BARCHA 46 ta migratsiya IMPORTI bitta try/except
# blokida edi. Real serverda (Railway) haqiqiy log orqali aniqlandi:
# "No module named 'migrations.migrate_v28_edu_orgs'" xatosi chiqqan —
# BU BIRINCHI import EDI, shuning uchun undan KEYINGI 45 ta import
# QATORI HECH QACHON ISHGA TUSHMAGAN! Natijada _migrate_v63 (chest_
# tickets_tariff ustunini qo'shadi), _migrate_v64 (user_collection
# jadvalini yaratadi) va h.k. — BARCHASI UMUMAN MAVJUD BO'LMAGAN
# (undefined) nomlarga aylanib, keyinroq chaqirilganda "name is not
# defined" xatosi berardi. Bu — Random ID/Sandiq/Koleksiya kabi
# bo'limlardagi ko'plab xatolarning ILDIZI bo'lgan bo'lishi mumkin edi.
#
# Endi HAR BIR import QATORI alohida himoyalangan — bittasi (masalan
# v28, sababi noma'lum bo'lsa ham) muvaffaqiyatsiz bo'lsa, FAQAT O'SHA
# BITTASI o'tkazib yuboriladi (funksiyasi hech narsa qilmaydigan
# "bo'sh" funksiyaga almashtiriladi), QOLGAN 45 TASI BARIBIR to'g'ri
# import qilinadi va ishga tushadi.
def _noop_migration(*a, **kw):
    pass


def _safe_import_migration(module_name, migration_name):
    try:
        module = __import__(f"migrations.{module_name}", fromlist=["migrate"])
        return module.migrate
    except Exception as e:
        print(f"⚠️  Migratsiya IMPORT XATOSI ({migration_name}): {e} — bu migratsiya o'tkazib yuboriladi, QOLGANLARI baribir ishlaydi")
        return _noop_migration


_migrate_v28 = _safe_import_migration("migrate_v28_edu_orgs", "v28")
_migrate_v29 = _safe_import_migration("migrate_v29_advanced_labs", "v29")
_migrate_v30 = _safe_import_migration("migrate_v30_edu_treasury_bridge", "v30")
_migrate_v31 = _safe_import_migration("migrate_v31_platform_innovations", "v31")
_migrate_v32 = _safe_import_migration("migrate_v32_edu_tariff_pricing", "v32")
_migrate_v33 = _safe_import_migration("migrate_v33_edu_admin_treasury", "v33")
_migrate_v34 = _safe_import_migration("migrate_v34_special_challenge", "v34")
_migrate_v35 = _safe_import_migration("migrate_v35_edu_purchase_requests", "v35")
_migrate_v36 = _safe_import_migration("migrate_v36_bot_upgrade", "v36")
_migrate_v37 = _safe_import_migration("migrate_v37_tariff_uzs_pricing", "v37")
_migrate_v38 = _safe_import_migration("migrate_v38_ai_weekly_and_kriptikis50", "v38")
_migrate_v39 = _safe_import_migration("migrate_v39_edu_fixes", "v39")
_migrate_v40 = _safe_import_migration("migrate_v40_edu_curriculum", "v40")
_migrate_v42 = _safe_import_migration("migrate_v42_edu_classes_and_pro3", "v42")
_migrate_v43 = _safe_import_migration("migrate_v43_full_text", "v43")
_migrate_v44 = _safe_import_migration("migrate_v44_simulations", "v44")
_migrate_v45 = _safe_import_migration("migrate_v45_primary_direction", "v45")
_migrate_v46 = _safe_import_migration("migrate_v46_admin_scopes", "v46")
_migrate_v47 = _safe_import_migration("migrate_v47_code_exercises", "v47")
_migrate_v48 = _safe_import_migration("migrate_v48_web_mobile_exercises", "v48")
_migrate_v49 = _safe_import_migration("migrate_v49_ai_recommendations", "v49")
_migrate_v50 = _safe_import_migration("migrate_v50_ai_economy", "v50")
_migrate_v51 = _safe_import_migration("migrate_v51_teacher_system", "v51")
_migrate_v52 = _safe_import_migration("migrate_v52_ai_workshop_courses", "v52")
_migrate_v53 = _safe_import_migration("migrate_v53_group_economy", "v53")
_migrate_v54 = _safe_import_migration("migrate_v54_group_oversight", "v54")
_migrate_v55 = _safe_import_migration("migrate_v55_video_calls", "v55")
_migrate_v56 = _safe_import_migration("migrate_v56_id_system", "v56")
_migrate_v57 = _safe_import_migration("migrate_v57_personal_themes", "v57")
_migrate_v58 = _safe_import_migration("migrate_v58_course_pricing", "v58")
_migrate_v59 = _safe_import_migration("migrate_v59_friends", "v59")
_migrate_v60 = _safe_import_migration("migrate_v60_directions_treasury", "v60")
_migrate_v61 = _safe_import_migration("migrate_v61_promo_bonus", "v61")
_migrate_v62 = _safe_import_migration("migrate_v62_id_selling", "v62")
_migrate_v63 = _safe_import_migration("migrate_v63_chests", "v63")
_migrate_v64 = _safe_import_migration("migrate_v64_collection", "v64")
_migrate_v65 = _safe_import_migration("migrate_v65_id_prices", "v65")
_migrate_v66 = _safe_import_migration("migrate_v66_id_history", "v66")
_migrate_v67 = _safe_import_migration("migrate_v67_smm_logistics", "v67")
_migrate_v68 = _safe_import_migration("migrate_v68_design_orders", "v68")
_migrate_v69 = _safe_import_migration("migrate_v69_activity_feed", "v69")
_migrate_v70 = _safe_import_migration("migrate_v70_automation", "v70")
_migrate_v71 = _safe_import_migration("migrate_v71_frames", "v71")
_migrate_v72 = _safe_import_migration("migrate_v72_new_plan_prices", "v72")
_migrate_v73 = _safe_import_migration("migrate_v73_id_reservations", "v73")
_migrate_v74 = _safe_import_migration("migrate_v74_tariff_sale", "v74")
_migrate_v75 = _safe_import_migration("migrate_v75_fix_tariff_prices", "v75")
_migrate_v76 = _safe_import_migration("migrate_v76_fix_tariff_codes", "v76")
_migrate_v77 = _safe_import_migration("migrate_v77_fix_inventory_prices", "v77")

try:
    _db_path = app.config["DB_PATH"]

    # MUHIM (tuzatilgan JIDDIY, TIZIMIY XATO): avval BARCHA 46 ta
    # migratsiya BITTA himoyasiz blokda ketma-ket chaqirilardi. Agar
    # ULARDAN BITTASI (masalan v45) xato bersa — undan KEYINGI HAMMA
    # migratsiya (v46 dan v73 gacha) BUTUNLAY O'TKAZIB YUBORILARDI,
    # chunki xato darhol tashqi except blokka sakrab, qolgan qatorlar
    # HECH QACHON ishga tushmasdi. Bu aynan "yangi bo'limlar (Omadli
    # Sandiq, Dizayn zakaz, Ramkalar — bularning barchasi v67+ da
    # qo'shilgan) doim 500 beradi, eski sahifalar ishlaydi" degan
    # shikoyatning haqiqiy sababi bo'lishi mumkin edi. Endi HAR BIR
    # migratsiya O'ZINING alohida try/except ichida — bittasi xato
    # bersa ham, QOLGAN BARCHASI baribir ishga tushishda davom etadi.
    _all_migrations = [
        ("v28-v31", lambda: (_migrate_v28(_db_path), _migrate_v29(_db_path), _migrate_v30(_db_path), _migrate_v31(_db_path))),
        ("v32", lambda: _migrate_v32(_db_path)),
        ("v33", lambda: _migrate_v33(_db_path)),
        ("v34", lambda: _migrate_v34(_db_path)),
        ("v35", lambda: _migrate_v35(_db_path)),
        ("v36", lambda: _migrate_v36(_db_path)),
        ("v37", lambda: _migrate_v37(_db_path)),
        ("v38", lambda: _migrate_v38(_db_path)),
        ("v39", lambda: _migrate_v39(_db_path)),
        ("v40", lambda: _migrate_v40(_db_path)),
        ("v42", lambda: _migrate_v42(_db_path)),
        ("v43", lambda: _migrate_v43(_db_path)),
        ("v44", lambda: _migrate_v44(_db_path)),
        ("v45", lambda: _migrate_v45(_db_path)),
        ("v46", lambda: _migrate_v46(_db_path)),
        ("v47", lambda: _migrate_v47(_db_path)),
        ("v48", lambda: _migrate_v48(_db_path)),
        ("v49", lambda: _migrate_v49(_db_path)),
        ("v50", lambda: _migrate_v50(_db_path)),
        ("v51", lambda: _migrate_v51(_db_path)),
        ("v52", lambda: _migrate_v52(_db_path)),
        ("v53", lambda: _migrate_v53(_db_path)),
        ("v54", lambda: _migrate_v54(_db_path)),
        ("v55", lambda: _migrate_v55(_db_path)),
        ("v56", lambda: _migrate_v56(_db_path)),
        ("v57", lambda: _migrate_v57(_db_path)),
        ("v58", lambda: _migrate_v58(_db_path)),
        ("v59", lambda: _migrate_v59(_db_path)),
        ("v60", lambda: _migrate_v60(_db_path)),
        ("v61", lambda: _migrate_v61(_db_path)),
        ("v62", lambda: _migrate_v62(_db_path)),
        ("v63", lambda: _migrate_v63(_db_path)),
        ("v64", lambda: _migrate_v64(_db_path)),
        ("v65", lambda: _migrate_v65(_db_path)),
        ("v66", lambda: _migrate_v66(_db_path)),
        ("v67", lambda: _migrate_v67(_db_path)),
        ("v68", lambda: _migrate_v68(_db_path)),
        ("v69", lambda: _migrate_v69(_db_path)),
        ("v70", lambda: _migrate_v70(_db_path)),
        ("v71", lambda: _migrate_v71(_db_path)),
        ("v72", lambda: _migrate_v72(_db_path)),
        ("v73", lambda: _migrate_v73(_db_path)),
        ("v74", lambda: _migrate_v74(_db_path)),
        ("v75", lambda: _migrate_v75(_db_path)),
        ("v76", lambda: _migrate_v76(_db_path)),
        ("v77", lambda: _migrate_v77(_db_path)),
    ]
    _migration_failures = []
    # POSTGRES: bu skriptlar sqlite3.connect(_db_path) ni to'g'ridan-to'g'ri
    # chaqiradi (db.py'ning Postgres adapteridan chetlab o'tadi) va Postgres'ga
    # ko'chirilgan bazada ularning barcha ishi allaqachon bajarilgan holda
    # keladi — shuning uchun ishga tushirilmaydi.
    if not USE_POSTGRES:
        for _mig_name, _mig_fn in _all_migrations:
            try:
                _mig_fn()
            except Exception as _mig_err:
                _migration_failures.append((_mig_name, str(_mig_err)))
                print(f"❌ MIGRATSIYA {_mig_name} XATO BERDI (qolganlari baribir davom etadi): {_mig_err}")
    if _migration_failures:
        print(f"⚠️  JAMI {len(_migration_failures)} ta migratsiya xato berdi: "
              f"{[m[0] for m in _migration_failures]}")
except Exception as _edu2_migrate_err:
    print(f"⚠️  EDU 2.0 migratsiyasida ogohlantirish: {_edu2_migrate_err}")

app.teardown_appcontext(close_db)
app.register_blueprint(oauth_bp)
app.register_blueprint(virtual_bp)
from shop_routes import shop_bp
app.register_blueprint(shop_bp)
from friends_routes import friends_bp
app.register_blueprint(friends_bp)
from ids_routes import ids_bp
app.register_blueprint(ids_bp)
from messages_routes import messages_bp
app.register_blueprint(messages_bp)
from coins_routes import coins_bp
app.register_blueprint(coins_bp)
from certificates_routes import certs_bp
app.register_blueprint(certs_bp)
from library_routes import library_bp
app.register_blueprint(library_bp)
from forum_routes import forum_bp
app.register_blueprint(forum_bp)
from social_routes import social_bp
app.register_blueprint(social_bp)
from startups_routes import startups_bp
app.register_blueprint(startups_bp)
from hackerlab_routes import hackerlab_bp
app.register_blueprint(hackerlab_bp)
from groups_routes import groups_bp
app.register_blueprint(groups_bp)
from treasury_routes import treasury_bp
app.register_blueprint(treasury_bp)
from jamoa_routes import jamoa_bp
app.register_blueprint(jamoa_bp)
from secz_routes import secz_bp
app.register_blueprint(secz_bp)
from courses_routes import courses_bp
app.register_blueprint(courses_bp)
from call_routes import call_bp
app.register_blueprint(call_bp)
from ai_routes import ai_bp
app.register_blueprint(ai_bp)
from tests_routes import tests_bp
app.register_blueprint(tests_bp)
from mentors_routes import mentors_bp
app.register_blueprint(mentors_bp)
from freelance_routes import freelance_bp
app.register_blueprint(freelance_bp)
from karyera_routes import karyera_bp
app.register_blueprint(karyera_bp)
from calls_routes import calls_bp
app.register_blueprint(calls_bp)
from bejik_routes import bejik_bp
app.register_blueprint(bejik_bp)
from inkubator_routes import inkubator_bp
app.register_blueprint(inkubator_bp)
from maxfiy_routes import maxfiy_bp
app.register_blueprint(maxfiy_bp)
from ctf_routes import ctf_bp
app.register_blueprint(ctf_bp)
from shatslive_routes import shatslive_bp
app.register_blueprint(shatslive_bp)
from shatspos_routes import shatspos_bp
app.register_blueprint(shatspos_bp)
from tashkilot_routes import tashkilot_bp
app.register_blueprint(tashkilot_bp)
from sozlamalar_routes import sozlamalar_bp
app.register_blueprint(sozlamalar_bp)
from smm_routes import smm_bp
app.register_blueprint(smm_bp)
from teacher_routes import teacher_bp
app.register_blueprint(teacher_bp)
from kriptikis_routes import kriptikis_bp
app.register_blueprint(kriptikis_bp)
from adminids_routes import adminids_bp
app.register_blueprint(adminids_bp)
from adminusers_routes import adminusers_bp
app.register_blueprint(adminusers_bp)
from adminsec_routes import adminsec_bp
app.register_blueprint(adminsec_bp)
from adminmod_routes import adminmod_bp
app.register_blueprint(adminmod_bp)
from adminann_routes import adminann_bp
app.register_blueprint(adminann_bp)
from admincourses_routes import admincourses_bp
app.register_blueprint(admincourses_bp)
from adminsettings_routes import adminsettings_bp
app.register_blueprint(adminsettings_bp)
from adminaccess_routes import adminaccess_bp
app.register_blueprint(adminaccess_bp)
from adminai_routes import adminai_bp
app.register_blueprint(adminai_bp)
from admintashkilot_routes import admintashkilot_bp
app.register_blueprint(admintashkilot_bp)
from adminchat_routes import adminchat_bp
app.register_blueprint(adminchat_bp)
from adminmisc_routes import adminmisc_bp
app.register_blueprint(adminmisc_bp)
from adminlead_routes import adminlead_bp
app.register_blueprint(adminlead_bp)
from admindash_routes import admindash_bp
app.register_blueprint(admindash_bp)
from push_routes import push_bp
app.register_blueprint(push_bp)
from trading_routes import trading_bp
app.register_blueprint(trading_bp)
from pentest_routes import pentest_bp
app.register_blueprint(pentest_bp)
from codehelp_routes import codehelp_bp
app.register_blueprint(codehelp_bp)
from airecs_routes import airecs_bp
app.register_blueprint(airecs_bp)
# EDU bo'limi (edu_bp, edu_orgs_bp) BUTUNLAY OLIB TASHLANDI (foydalanuvchi
# so'rovi bo'yicha) — tashkilotlar uchun mo'ljallangan alohida tizim endi
# ishlamaydi. edu.py va edu_orgs_routes.py fayllari tarixiy maqsadda
# saqlanib qolgan, lekin ular endi HECH QAYERGA ulanmagan.
app.register_blueprint(payment_bp)
app.register_blueprint(oneid_bp)
app.jinja_env.globals.update(zip=zip)
app.jinja_env.globals['format_number'] = lambda v: f"{int(v):,}" if v else "0"

@app.template_filter('format_number')
def format_number(value):
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value


@app.template_filter('fromjson_safe')
def fromjson_safe(value):
    """JSON stringni list/dict ga aylantirish, xatosiz."""
    if not value:
        return []
    import json as _json
    try:
        return _json.loads(value)
    except Exception:
        return []


@app.template_filter('markdown')
def render_markdown(text):
    """
    Oddiy markdown matnni xavfsiz HTML'ga aylantiradi (yo'nalish materiallari uchun).
    Agar 'markdown' kutubxonasi o'rnatilmagan bo'lsa (masalan pip install qilinmagan),
    sahifa xato bilan to'xtab qolmasligi uchun oddiy fallback formatlash ishlatiladi
    (qatorlarni <br>/<p> ga, **qalin**ni <strong>ga, # sarlavhalarni <h*>ga aylantiradi).
    """
    if not text:
        return ""
    try:
        import markdown as md_lib
        html = md_lib.markdown(text, extensions=["fenced_code", "tables"])
        return Markup(html)
    except ImportError:
        return Markup(_simple_markdown_fallback(text))


def _simple_markdown_fallback(text: str) -> str:
    """'markdown' kutubxonasi yo'q bo'lganda ishlatiladigan juda sodda,
    qo'lda yozilgan formatlash (xavfsiz — avval HTML escape qilinadi)."""
    import html as _html
    import re
    escaped = _html.escape(text)
    lines = escaped.split("\n")
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            out.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h1>{stripped[2:]}</h1>")
        elif stripped.startswith("- ") or stripped.startswith("* "):
            out.append(f"<li>{stripped[2:]}</li>")
        elif stripped == "":
            out.append("<br>")
        else:
            out.append(f"<p>{stripped}</p>")
    joined = "\n".join(out)
    # **qalin** -> <strong>qalin</strong>
    joined = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", joined)
    return joined


@app.template_filter('tashkent_time')
def tashkent_time_filter(iso_str, fmt="%d.%m.%Y %H:%M"):
    """Bazadagi UTC vaqtni O'zbekiston mahalliy vaqtiga (UTC+5) o'tkazadi.
    Shablonlarda: {{ row.created_at|tashkent_time }} yoki {{ row.created_at|tashkent_time('%H:%M') }}"""
    return to_tashkent(iso_str, fmt)


def notify_user(user_id: int, title: str, body: str, ntype: str = "info", push_url: str = "/dashboard"):
    """
    Markaziy bildirishnoma funksiyasi: ham saytdagi notifications jadvaliga yozadi
    (foydalanuvchi sahifada bo'lsa ovozli ko'radi), ham Web Push orqali yuboradi
    (foydalanuvchi saytdan chiqib ketgan bo'lsa ham qurilmasiga keladi).
    """
    execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
            (user_id, title, body, ntype))
    try:
        push_mod.send_push_to_user(user_id, title, body, push_url)
    except Exception:
        pass



@app.before_request
def enforce_page_access():
    """Adminlar tomonidan faol/nofaol qilingan sahifalar uchun ruxsatni tekshiradi."""
    # API, static va h.k. lar uchun cheklamaslik kerak. Asosiy path bo'yicha qaraymiz.
    path = request.path
    row = query_one("SELECT is_active FROM page_access WHERE path=?", (path,))
    if row and row["is_active"] == 0:
        # Sahifa nofaol. Faqat maxsus ID ga ega foydalanuvchilar kira oladi.
        user = get_current_user()
        if not user:
            abort(404)
        allowed_ids = ["7777777", "1234567", "3611904"]
        if str(user.get("custom_id")) not in allowed_ids:
            abort(404)


@app.before_request
def check_plan_expiry():
    """
    Har so'rovda (sessiyada login bo'lgan foydalanuvchi uchun) Pro/Cyber Pro/VIP
    muddati tugaganmi tekshiradi. Tugagan bo'lsa avtomatik 'free'ga tushiradi.
    Fon jarayoni (cron) shart emas — bu yengil tekshiruv.
    """
    uid = session.get("user_id")
    if uid:
        try:
            check_and_downgrade_expired_plan(uid)
        except Exception:
            pass


# ---------------------------------------------------------------
# CONTEXT PROCESSOR — barcha shablonlarga umumiy ma'lumot yuboradi
# ---------------------------------------------------------------
@app.context_processor
def inject_globals():
    user = get_current_user()
    try:
        total_users = query_one("SELECT COUNT(*) c FROM users")["c"]
    except Exception:
        total_users = 0
    online_now = random.randint(140, 480)
    today_new = random.randint(8, 40)
    notif_count = 0
    unread_msg_count = 0
    has_active_story = False
    pending_friend_requests_count = 0
    if user:
        try:
            notif_count = query_one("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],))["c"]
        except Exception:
            notif_count = 0
        try:
            unread_msg_count = get_unread_total(user["id"])
        except Exception:
            unread_msg_count = 0
        try:
            has_active_story = bool(query_one(
                "SELECT id FROM stories WHERE user_id=? AND expires_at > datetime('now') LIMIT 1", (user["id"],)))
        except Exception:
            has_active_story = False
        try:
            pending_friend_requests_count = friends_mod.get_pending_received_count(user["id"])
        except Exception:
            pending_friend_requests_count = 0
    build_date = datetime.date(2026, 1, 1)
    uptime_days = (datetime.date.today() - build_date).days

    # Sayt sozlamalari (tema, panel holati)
    try:
        settings_rows = query_all("SELECT key, value FROM site_settings")
        site_settings = {r["key"]: r["value"] for r in settings_rows}
    except Exception:
        # DIQQAT: standart qiymat 'football' EMAS, balki 'none' bo'lishi kerak —
        # avval bu yerda xato bor edi va jadval bo'sh bo'lganda hammaga
        # tasodifan futbol temasi yoqilib qolardi.
        site_settings = {"site_theme": "none"}

    # Panel holatlari
    try:
        panel_rows = query_all("SELECT panel_key, is_active, maintenance_msg FROM panel_status")
        panel_status = {r["panel_key"]: {"active": r["is_active"], "msg": r["maintenance_msg"]} for r in panel_rows}
    except Exception:
        panel_status = {}

    return dict(
        current_user=user,
        site_name=Config.SITE_NAME,
        site_domain=Config.SITE_DOMAIN,
        hud_online=online_now,
        hud_today=today_new,
        hud_total=total_users,
        hud_version="v2.6.1",
        hud_ip=request.remote_addr or "10.0.0.1",
        uptime_days=uptime_days,
        notif_count=notif_count,
        unread_msg_count=unread_msg_count,
        has_active_story=has_active_story,
        pending_friend_requests_count=pending_friend_requests_count,
        build_stamp=BUILD_STAMP,
        ai_configured=is_ai_configured(),
        ai_provider_name=active_provider_name(),
        now=datetime.datetime.now(),
        time_ago_uz=time_ago_uz,
        fmt_duration=fmt_duration,
        site_settings=site_settings,
        panel_status=panel_status,
    )


# ---------------------------------------------------------------
# YORDAMCHI FUNKSIYALAR
# ---------------------------------------------------------------
def gen_code(n=8):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _check_panel(panel_key: str):
    """Agar panel o'chirilgan bo'lsa maintenance sahifasiga yo'naltiradi."""
    try:
        row = query_one("SELECT is_active, maintenance_msg FROM panel_status WHERE panel_key=?", (panel_key,))
        if row and not row["is_active"]:
            msg = row["maintenance_msg"] or "Bu bo'lim vaqtinchalik texnik ishlar sababli to'xtatilgan. Tez orada qayta ulanadi."
            flash(msg, "warn")
            return redirect(url_for("dashboard"))
    except Exception:
        pass
    return None


def get_directions(include_inactive=False):
    """Barcha faol yo'nalishlarni qaytaradi. DIQQAT: avval yopilgan
    yo'nalishlar (masalan Ingliz tili, Matematika) faqat KURSLARI
    yashirilgan edi, lekin yo'nalishning O'ZI hamon marquee, orbital hub,
    yo'nalish tanlash va sidebar'da ko'rinib turardi. Endi standart holatda
    is_active=0 bo'lgan yo'nalishlar BUTUNLAY chiqarib tashlanadi."""
    if include_inactive:
        return query_all("SELECT * FROM directions ORDER BY sort_order")
    return query_all("SELECT * FROM directions WHERE is_active=1 ORDER BY sort_order")


def _can_access_course(user, course):
    """O'quvchi (student) FAQAT o'zi tanlagan asosiy yo'nalishidagi kurslarga
    kira oladi. Istisno: agar kursga allaqachon yozilgan bo'lsa (masalan
    access-code orqali yoki avval, ushbu funksiya qo'shilishidan oldin
    yozilgan bo'lsa) — bu yozilish buzilmaydi, kirish davom etadi.
    Admin/mentor/o'qituvchi/g'aznachi kabi boshqa rollarga cheklov yo'q."""
    if user.get("role") != "student":
        return True
    if course["direction_id"] == user.get("primary_direction_id"):
        return True
    existing = query_one("SELECT id FROM enrollments WHERE user_id=? AND course_id=?",
                         (user["id"], course["id"]))
    return bool(existing)


def _locked_direction_for(user):
    """Agar bu o'quvchi uchun yo'nalish qulflangan bo'lsa (role=student va
    primary_direction_id bor), o'sha yo'nalish qatorini qaytaradi — aks holda None."""
    if user and user.get("role") == "student" and user.get("primary_direction_id"):
        return query_one("SELECT * FROM directions WHERE id=?", (user["primary_direction_id"],))
    return None


def award_xp(user_id, amount):
    execute("UPDATE users SET xp = xp + ? WHERE id=?", (amount, user_id))
    user = query_one("SELECT xp FROM users WHERE id=?", (user_id,))
    new_level = max(1, user["xp"] // 500 + 1)
    execute("UPDATE users SET level=? WHERE id=?", (new_level, user_id))


def generate_certificate_pdf(cert):
    """Sertifikat uchun haqiqiy PDF fayl yaratadi (reportlab + QR kod)."""
    import qrcode
    import io
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas as pdf_canvas
    from reportlab.lib.utils import ImageReader

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "generated")
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, f"cert_{cert['cert_code']}.pdf")

    green = HexColor("#00ff41")
    bg = HexColor("#000010")
    muted = HexColor("#00cc99")

    c = pdf_canvas.Canvas(pdf_path, pagesize=landscape(A4))
    w, h = landscape(A4)
    c.setFillColor(bg)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setStrokeColor(green)
    c.setLineWidth(2)
    c.rect(14 * mm, 14 * mm, w - 28 * mm, h - 28 * mm, fill=0, stroke=1)
    c.setLineWidth(0.6)
    c.rect(20 * mm, 20 * mm, w - 40 * mm, h - 40 * mm, fill=0, stroke=1)

    c.setFillColor(green)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2, h - 38 * mm, "C Y B E R   S H A T S")

    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(w / 2, h - 60 * mm, "SERTIFIKAT")

    c.setFillColor(HexColor("#e0ffe8"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2, h - 78 * mm, "Mazkur sertifikat quyidagi shaxsga taqdim etiladi:")

    c.setFillColor(green)
    c.setFont("Helvetica-Bold", 22)
    full_name = f"{cert['familiya']} {cert['ism']}".strip()
    c.drawCentredString(w / 2, h - 92 * mm, full_name)

    c.setFillColor(HexColor("#00ccff"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(w / 2, h - 106 * mm, f"« {cert['course_title']} »")

    c.setFillColor(muted)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w / 2, h - 116 * mm,
                         f"kursini muvaffaqiyatli yakunlagani uchun ({cert['duration_weeks']} haftalik dastur)")

    qr_img = qrcode.make(f"https://{Config.SITE_DOMAIN}/certificate/{cert['cert_code']}")
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)
    qr_reader = ImageReader(buf)
    qr_size = 28 * mm
    c.drawImage(qr_reader, w - 50 * mm, 26 * mm, qr_size, qr_size)

    c.setFillColor(muted)
    c.setFont("Helvetica", 9)
    c.drawString(26 * mm, 34 * mm, f"Sertifikat kodi: {cert['cert_code']}")
    c.drawString(26 * mm, 29 * mm, f"Berilgan sana: {str(cert['issued_at'])[:10]}")
    c.drawString(26 * mm, 24 * mm, f"https://{Config.SITE_DOMAIN}")

    c.showPage()
    c.save()
    return pdf_path


# =================================================================
# OMMAVIY (PUBLIC) SAHIFALAR
# =================================================================
@app.route("/system-check")
def system_check():
    """SAYT ORQALI ochiladigan tekshiruv sahifasi — SSH/terminal SHART
    EMAS, oddiy brauzerdan ochilsa yetarli. Har bir sahifani, muhim
    jadval/ustunni va bot holatini tekshirib, aniq (yashil/qizil)
    natija ko'rsatadi. Maxfiy ma'lumotlar (parollar, tokenlar) hech
    qachon to'liq ko'rsatilmaydi — faqat "bor/yo'q" holati."""
    checks = []

    def add(label, ok, detail=""):
        checks.append({"label": label, "ok": ok, "detail": detail})

    try:
        critical_tables = ['users', 'telegram_users', 'bot_purchase_requests', 'treasury_fund',
                           'premium_ids', 'profile_frames', 'id_reservations', 'design_orders',
                           'promo_codes', 'friendships']
        for t in critical_tables:
            row = query_one("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (t,))
            add(f"Jadval: {t}", row is not None)
    except Exception as e:
        add("Bazaga ulanish", False, str(e))

    try:
        cols_row = query_all("PRAGMA table_info(users)")
        col_names = [r["name"] for r in cols_row]
        for col in ['login_streak', 'last_login_date', 'active_frame', 'custom_id', 'plan_expires_at']:
            add(f"users.{col} ustuni", col in col_names)
    except Exception as e:
        add("users ustunlarini tekshirish", False, str(e))

    try:
        wal_row = query_one("PRAGMA journal_mode")
        wal_mode = list(dict(wal_row).values())[0] if wal_row else "?"
        add("SQLite WAL rejimi yoqilgan", wal_mode == "wal", f"joriy: {wal_mode}")
    except Exception as e:
        add("WAL rejimini tekshirish", False, str(e))

    test_paths = [
        "/", "/dashboard", "/my-id", "/id-random", "/chests", "/collection",
        "/checkmarks", "/frames", "/design-order", "/friends", "/coins",
        "/profile", "/webapp", "/leaderboard",
    ]
    with app.test_client() as tc:
        with tc.session_transaction() as sess:
            sess["user_id"] = session.get("user_id")
        for p in test_paths:
            try:
                r = tc.get(p)
                add(f"Sahifa: {p}", r.status_code != 500, f"status: {r.status_code}")
            except Exception as e:
                add(f"Sahifa: {p}", False, str(e)[:200])

    for var in ["SECRET_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_ADMIN_CHAT_ID", "SITE_BASE_URL"]:
        add(f".env: {var}", bool(os.environ.get(var)))

    all_ok = all(c["ok"] for c in checks)
    return render_template("system_check.html", checks=checks, all_ok=all_ok)


@app.route("/")
def index():
    directions = get_directions()
    courses = query_all(
        "SELECT c.*, d.name_uz as direction_name, d.slug as direction_slug FROM courses c "
        "JOIN directions d ON d.id=c.direction_id ORDER BY c.students_count DESC LIMIT 6"
    )
    # ENG MASHHUR YO'NALISHLAR — endi haqiqiy ma'lumot (avval qattiq yozilgan edi):
    # har bir yo'nalishning ENG ko'p o'quvchili kursi + shu yo'nalishdagi umumiy o'quvchilar soni
    popular_directions = query_all("""
        SELECT d.name_uz, d.icon, d.slug,
               (SELECT c2.description FROM courses c2 WHERE c2.direction_id=d.id
                ORDER BY c2.students_count DESC LIMIT 1) as description,
               COALESCE(SUM(c.students_count), 0) as total_students
        FROM directions d LEFT JOIN courses c ON c.direction_id = d.id
        GROUP BY d.id ORDER BY total_students DESC LIMIT 6
    """)
    news = query_all("SELECT * FROM news ORDER BY published_at DESC LIMIT 4")
    total_students = query_one("SELECT COUNT(*) c FROM users WHERE role='student'")["c"]
    total_courses = query_one("SELECT COUNT(*) c FROM courses")["c"]
    daily_startups = startups_mod.get_daily_rotating_startups(6)
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    p = get_pricing()
    return render_template("index.html", directions=directions, courses=courses, news=news,
                            popular_directions=popular_directions,
                            total_students=total_students, total_courses=total_courses,
                            daily_startups=daily_startups,
                            pro_price_code=p["pro_price_code"], cyber_pro_price_code=p["cyber_pro_price_code"],
                            vip_price_code=p["vip_price_code"], code_to_som_rate=p["code_to_som_rate"])


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "0.0.0.0").split(",")[0].strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Brute force tekshiruvi
        blocked, msg = check_brute_force(email, ip)
        if blocked:
            flash(msg, "error")
            return redirect(url_for("login"))

        user = query_one("SELECT * FROM users WHERE email=?", (email,))
        if user and check_password_hash(user["password_hash"], password):
            if user["is_blocked"]:
                flash("Hisobingiz administrator tomonidan bloklangan.", "error")
                log_security_event(user["id"], "blocked_login_attempt", ip,
                                   request.headers.get("User-Agent", ""), f"email:{email}", "medium")
                return redirect(url_for("login"))
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            clear_failed_logins(user["id"])
            execute("UPDATE users SET last_login_ip=? WHERE id=?", (ip, user["id"]))
            log_action(user["id"], "login", ip=ip)
            if not user.get("email_verified"):
                import email_verify
                email_verify.send_verification_code(user["id"], user["email"], user["ism"])
                flash("Davom etishdan oldin emailingizni tasdiqlang.", "warn")
                return redirect(url_for("verify_email"))
            
            flash(f"Xush kelibsiz, {user['ism']}!", "success")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))

        # User topilmasa — G'azna hisoblarini tekshiramiz
        treasury_account = treasury_mod.verify_treasury_login(email, password)
        if treasury_account:
            session.clear()
            session["treasury_account_id"] = treasury_account["id"]
            session["treasury_account_ism"] = treasury_account["ism"]
            session.permanent = True
            clear_failed_logins(email)
            log_action(None, "treasury_login_via_main",
                       details=f"treasury_id:{treasury_account['id']}", ip=ip)
            flash(f"Xush kelibsiz, {treasury_account['ism']}! G'azna paneliga yo'naltirilmoqdasiz.", "success")
            return redirect(url_for("treasury_bp.treasury_dashboard"))

        record_failed_login(email, ip)
        flash("Email yoki parol noto'g'ri.", "error")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/terms")
def terms_page():
    return render_template("terms.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        familiya = request.form.get("familiya", "").strip()
        ism = request.form.get("ism", "").strip()
        email = request.form.get("email", "").strip().lower()
        telefon = request.form.get("telefon", "").strip()
        password = request.form.get("password", "")
        if not ism or not familiya or not email or len(password) < 8:
            flash("Barcha maydonlarni to'ldiring. Parol kamida 8 belgi.", "error")
            return redirect(url_for("register"))
        if not email.endswith("@gmail.com"):
            flash("Faqat @gmail.com email qabul qilinadi.", "error")
            return redirect(url_for("register"))
        existing = query_one("SELECT id FROM users WHERE email=?", (email,))
        if existing:
            flash("Bu email bilan foydalanuvchi allaqachon mavjud.", "error")
            return redirect(url_for("register"))
        uid = execute(
            "INSERT INTO users (ism, familiya, email, password_hash, role) VALUES (?,?,?,?,?)",
            (ism, familiya, email, generate_password_hash(password), "student"),
        )
        # 7 xonali unikal ID avtomatik berish
        new_cid = generate_unique_id()
        execute("UPDATE users SET custom_id=? WHERE id=?", (new_cid, uid))
        # Referal kodi (agar kiritilgan bo'lsa) — faqat statistika, bonus yo'q
        ref_code = request.form.get("ref", "").strip() or request.args.get("ref", "").strip()
        if ref_code:
            import referrals
            referrals.apply_referral(uid, ref_code)
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (uid, "Xush kelibsiz!", "CYBER SHATS platformasiga muvaffaqiyatli ro'yxatdan o'tdingiz.", "success"))
        execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (uid, f"Sizning ID: #{new_cid}",
                 f"Sizga avtomatik ID #{new_cid} berildi. Uni profil sozlamalarida o'zgartirishingiz mumkin (lekin bir xil ID bo'lmasin).",
                 "info"))
        # Reyting jadvalini boshlash
        execute("INSERT OR IGNORE INTO user_ratings (user_id, total_score, rank_position) VALUES (?,?,0)", (uid, 0))
        # Avtomatik bonuslar olib tashlandi — endi bonuslarni faqat admin panel orqali beriladi.
        session.clear()
        session["user_id"] = uid
        session.permanent = True
        log_action(uid, "register", ip=request.remote_addr)

        import group_reports
        group_reports.report_new_registration(uid)

        import email_verify
        email_verify.send_verification_code(uid, email, ism)
        flash("Ro'yxatdan o'tish muvaffaqiyatli! Emailingizga yuborilgan kodni kiriting.", "success")
        return redirect(url_for("verify_email"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    if session.get("user_id"):
        log_action(session["user_id"], "logout", ip=request.remote_addr)
    session.clear()
    flash("Tizimdan muvaffaqiyatli chiqdingiz.", "info")
    return redirect(url_for("index"))


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    uid = session.get("user_id")
    if not uid:
        flash("Davom etish uchun avval tizimga kiring.", "warn")
        return redirect(url_for("login"))
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user:
        session.clear()
        return redirect(url_for("login"))
    if user.get("email_verified"):
        return redirect(url_for("dashboard"))

    import email_verify
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        ok, msg = email_verify.verify_code(uid, code)
        if ok:
            log_action(uid, "email_verified", ip=request.remote_addr)
            flash("Email muvaffaqiyatli tasdiqlandi! Xush kelibsiz.", "success")
            return redirect(url_for("dashboard"))
        flash(msg, "error")
        return redirect(url_for("verify_email"))

    return render_template("verify_email.html", email=user["email"])


@app.route("/verify-email/resend", methods=["POST"])
def verify_email_resend():
    uid = session.get("user_id")
    if not uid:
        return redirect(url_for("login"))
    user = query_one("SELECT * FROM users WHERE id=?", (uid,))
    if not user or user.get("email_verified"):
        return redirect(url_for("dashboard"))

    import email_verify
    ok, msg = email_verify.send_verification_code(uid, user["email"], user["ism"])
    flash(msg, "success" if ok else "error")
    return redirect(url_for("verify_email"))


@app.route("/pricing")
def pricing():
    # Tariflar olib tashlangan — endi barcha imkoniyatlar hammaga bepul va
    # cheksiz. Narxlash sahifasi endi kerak emas.
    flash("Hammasi bepul! Endi platformadagi barcha imkoniyatlar cheksiz mavjud.", "success")
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("index"))


@app.route("/robots.txt")
def robots_txt():
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /api/\n"
        "Disallow: /dashboard\n"
        "Disallow: /profile\n"
        f"Sitemap: https://{Config.SITE_DOMAIN}/sitemap.xml\n"
    )
    return content, 200, {"Content-Type": "text/plain"}


@app.route("/sitemap.xml")
def sitemap_xml():
    courses = query_all("SELECT slug FROM courses WHERE is_active=1")
    urls = ["/", "/login", "/register", "/pricing", "/courses", "/news", "/library", "/forum"]
    xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        xml.append(f"<url><loc>https://{Config.SITE_DOMAIN}{u}</loc></url>")
    for c in courses:
        xml.append(f"<url><loc>https://{Config.SITE_DOMAIN}/courses/{c['slug']}</loc></url>")
    xml.append("</urlset>")
    return "\n".join(xml), 200, {"Content-Type": "application/xml"}


# =================================================================
# DASHBOARD (asosiy interfeys — orbit hub)
# =================================================================
@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    directions = get_directions()
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug, c.icon, c.lessons_count FROM enrollments e "
        "JOIN courses c ON c.id=e.course_id WHERE e.user_id=? ORDER BY e.started_at DESC LIMIT 4",
        (user["id"],),
    )
    notif_count = query_one("SELECT COUNT(*) c FROM notifications WHERE user_id=? AND is_read=0", (user["id"],))["c"]
    recent_news = query_all("SELECT * FROM news ORDER BY published_at DESC LIMIT 3")
    daily_startups = startups_mod.get_daily_rotating_startups(6)

    # Sizning yo'nalishingiz — asosiy yo'nalish bo'yicha kurslar va progress
    locked_direction = _locked_direction_for(user)
    direction_courses = []
    direction_progress_pct = 0
    next_course = None
    if locked_direction:
        direction_courses = query_all(
            """SELECT c.*, e.progress_percent, e.completed_at
               FROM courses c LEFT JOIN enrollments e ON e.course_id=c.id AND e.user_id=?
               WHERE c.direction_id=? AND c.is_active=1 ORDER BY c.id""",
            (user["id"], locked_direction["id"]),
        )
        if direction_courses:
            done = sum(1 for c in direction_courses if c["completed_at"])
            direction_progress_pct = round(done / len(direction_courses) * 100)
            next_course = next((c for c in direction_courses if not c["completed_at"]), None)

    return render_template("dashboard.html", directions=directions, enrollments=enrollments,
                            notif_count=notif_count, recent_news=recent_news,
                            daily_startups=daily_startups,
                            locked_direction=locked_direction, direction_courses=direction_courses,
                            direction_progress_pct=direction_progress_pct, next_course=next_course)



@app.route("/directions")
@login_required
def directions():
    user = get_current_user()
    locked_direction = _locked_direction_for(user)
    return render_template("directions.html", directions=get_directions(), locked_direction=locked_direction)


# =================================================================
# ASOSIY YO'NALISH TANLASH — har bir o'quvchi ro'yxatdan o'tgach
# (email tasdiqlangach) BITTA IT yo'nalishini tanlashi shart. Shundan
# keyingina platformaning qolgan qismi (kurslar va h.k.) ochiladi —
# tekshiruv auth.py:login_required ichida amalga oshiriladi.
# =================================================================
@app.route("/choose-direction", methods=["GET", "POST"])
@login_required
def choose_direction():
    user = get_current_user()
    is_first_time = not user.get("primary_direction_id")

    has_pro_plan = (user.get("plan") in ("pro", "cyber_pro", "vip", "enterprise")
                    or user.get("role") in ("admin", "super_admin", "mentor"))

    if request.method == "POST":
        try:
            direction_id = int(request.form.get("direction_id", 0))
        except ValueError:
            direction_id = 0
        direction = query_one("SELECT * FROM directions WHERE id=?", (direction_id,))
        if not direction:
            flash("Yo'nalish topilmadi.", "error")
            return redirect(url_for("choose_direction"))
        # Butunlay Pro-talab qiluvchi yo'nalishni (SMM, Targetolog, Logistika)
        # oddiy (free) foydalanuvchi asosiy yo'nalish sifatida TANLAY OLMAYDI —
        # aks holda o'zi hech qaysi kursiga yozila olmaydigan yo'nalishga
        # "qulflanib qolardi". Avval Pro rejasini faollashtirsin.
        if direction["is_pro_only"] and not has_pro_plan:
            flash(f"«{direction['name_uz']}» yo'nalishi faqat Pro rejadagi foydalanuvchilar uchun. "
                  f"Avval Pro rejani faollashtiring.", "error")
            return redirect(url_for("choose_direction"))
        execute("UPDATE users SET primary_direction_id=?, direction_chosen_at=datetime('now') WHERE id=?",
                (direction_id, user["id"]))
        log_action(user["id"], "primary_direction_selected", details=f"dir:{direction_id}", ip=request.remote_addr)
        flash(f"«{direction['name_uz']}» yo'nalishi tanlandi! O'rganishni boshlaymiz 🚀", "success")

        first_course = query_one(
            "SELECT slug FROM courses WHERE direction_id=? AND is_active=1 ORDER BY id LIMIT 1", (direction_id,))
        if is_first_time and first_course:
            return redirect(url_for("courses_bp.course_detail", slug=first_course["slug"]))
        return redirect(url_for("dashboard"))

    directions_list = get_directions()
    return render_template("choose_direction.html", directions=directions_list,
                           is_first_time=is_first_time, has_pro_plan=has_pro_plan)



# =================================================================
# AI SHAXSIYLASHTIRILGAN TAVSIYALAR (dashboard kartasi)
# =================================================================

# =================================================================
# IJTIMOIY TARMOQ — GURUHLAR (Telegram guruhiga o'xshab)
# =================================================================
SOCIAL_ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "mov", "mkv", "webm"}
SOCIAL_UPLOAD_DIR = os.path.join("static", "uploads", "social")
SOCIAL_IMAGE_MAX_BYTES = 15 * 1024 * 1024       # 15 MB — oddiy rasm/kichik video
SOCIAL_VIDEO_MAX_BYTES = 20 * 1024 * 1024        # 20 MB — oddiy (o'qituvchi bo'lmagan) video
SOCIAL_TEACHER_VIDEO_MAX_BYTES = 500 * 1024 * 1024  # 500 MB — o'qituvchi guruhi/kanali uchun "YouTube-kabi" katta video


def _social_save_file(file_storage, allow_large_video=False):
    """allow_large_video=True — o'qituvchi guruhi/kanalida YouTube-kabi katta
    (500 MB gacha) video yuklash imkonini beradi; aks holda kichik cheklov."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in SOCIAL_ALLOWED_EXT:
        return None, None

    is_video = ext in ("mp4", "mov", "mkv", "webm")
    if is_video:
        max_bytes = SOCIAL_TEACHER_VIDEO_MAX_BYTES if allow_large_video else SOCIAL_VIDEO_MAX_BYTES
    else:
        max_bytes = SOCIAL_IMAGE_MAX_BYTES
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > max_bytes:
        return None, None

    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(SOCIAL_UPLOAD_DIR, exist_ok=True)
    full_path = os.path.join(SOCIAL_UPLOAD_DIR, safe_name)
    file_storage.save(full_path)
    file_type = "image" if ext in ("png", "jpg", "jpeg", "gif", "webp") else "video"
    return f"/static/uploads/social/{safe_name}", file_type




# =================================================================



# ---- Admin trading paneli ----



# =================================================================
# NATIJALAR / PROFIL / BILDIRISHNOMALAR / SERTIFIKAT
# =================================================================
@app.route("/results")
@login_required
def results():
    user = get_current_user()
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug, c.icon FROM enrollments e JOIN courses c ON c.id=e.course_id "
        "WHERE e.user_id=? ORDER BY e.started_at DESC", (user["id"],))
    avg_progress = int(sum(e["progress_percent"] for e in enrollments) / len(enrollments)) if enrollments else 0
    certificates = query_all(
        "SELECT cert.*, c.title as course_title FROM certificates cert JOIN courses c ON c.id=cert.course_id "
        "WHERE cert.user_id=? ORDER BY cert.issued_at DESC", (user["id"],))
    attempts = query_all(
        "SELECT ta.*, t.title as test_title FROM test_attempts ta JOIN tests t ON t.id=ta.test_id "
        "WHERE ta.user_id=? ORDER BY ta.completed_at DESC LIMIT 10", (user["id"],))
    badges = query_all(
        "SELECT b.* FROM user_badges ub JOIN badges b ON b.id=ub.badge_id WHERE ub.user_id=?", (user["id"],))
    return render_template("results.html", enrollments=enrollments, avg_progress=avg_progress,
                            certificates=certificates, attempts=attempts, badges=badges)


AVATAR_ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}
AVATAR_UPLOAD_DIR = os.path.join("static", "uploads", "avatars")
AVATAR_MAX_BYTES = 5 * 1024 * 1024


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_current_user()
    if request.method == "POST":
        ism = request.form.get("ism", user["ism"]).strip()
        familiya = request.form.get("familiya", user["familiya"]).strip()
        bio = request.form.get("bio", "").strip()

        avatar_file = request.files.get("avatar")
        if avatar_file and avatar_file.filename:
            ext = avatar_file.filename.rsplit(".", 1)[-1].lower() if "." in avatar_file.filename else ""
            if ext not in AVATAR_ALLOWED_EXT:
                flash("Faqat PNG, JPG yoki WEBP formatidagi rasm yuklash mumkin.", "error")
                return redirect(url_for("profile"))
            avatar_file.seek(0, os.SEEK_END)
            size = avatar_file.tell()
            avatar_file.seek(0)
            if size > AVATAR_MAX_BYTES:
                flash("Rasm hajmi 5 MB dan katta bo'lmasligi kerak.", "error")
                return redirect(url_for("profile"))
            import uuid
            safe_name = f"{user['id']}_{uuid.uuid4().hex}.{ext}"
            os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
            avatar_file.save(os.path.join(AVATAR_UPLOAD_DIR, safe_name))
            execute("UPDATE users SET avatar_path=? WHERE id=?", (f"/static/uploads/avatars/{safe_name}", user["id"]))

        execute("UPDATE users SET ism=?, familiya=?, bio=? WHERE id=?", (ism, familiya, bio, user["id"]))
        flash("Profil ma'lumotlari yangilandi.", "success")
        return redirect(url_for("profile"))
    enrollments = query_all(
        "SELECT e.*, c.title, c.slug FROM enrollments e JOIN courses c ON c.id=e.course_id WHERE e.user_id=?",
        (user["id"],))
    badges = query_all(
        "SELECT b.* FROM user_badges ub JOIN badges b ON b.id=ub.badge_id WHERE ub.user_id=?", (user["id"],))
    locked_direction = _locked_direction_for(user)
    test_summary = query_one(
        "SELECT COUNT(*) as taken, AVG(CAST(score AS FLOAT)/total*100) as avg_pct "
        "FROM test_attempts WHERE user_id=? AND total>0", (user["id"],))
    teacher_app = query_one(
        "SELECT * FROM teacher_applications WHERE user_id=? ORDER BY id DESC LIMIT 1", (user["id"],))
    my_active_stories = social.get_user_active_stories(user["id"])
    try:
        frame = frames_mod.get_frame_style(user["active_frame"]) if user["active_frame"] else None
    except (KeyError, IndexError):
        frame = None  # active_frame ustuni hali bazada yo'q bo'lsa (migratsiya kutilmoqda) — sahifa buzilmaydi
    return render_template("profile.html", enrollments=enrollments, badges=badges,
                           locked_direction=locked_direction, test_summary=test_summary,
                           teacher_app=teacher_app, my_active_stories=my_active_stories, frame=frame)


TEACHER_CERT_ALLOWED_EXT = {"png", "jpg", "jpeg", "webp", "pdf"}
TEACHER_CERT_UPLOAD_DIR = os.path.join("static", "uploads", "teacher_certs")
TEACHER_SYLLABUS_ALLOWED_EXT = {"pdf", "doc", "docx"}
TEACHER_SYLLABUS_UPLOAD_DIR = os.path.join("static", "uploads", "teacher_syllabus")


def _save_teacher_file(file_storage, allowed_ext, upload_dir, max_bytes=8 * 1024 * 1024):
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in allowed_ext:
        return None, "format"
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > max_bytes:
        return None, "size"
    import uuid
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, safe_name))
    return f"/{upload_dir.replace(os.sep, '/')}/{safe_name}", None


@app.route("/profile/teacher-apply", methods=["GET", "POST"])
@login_required
def teacher_apply():
    user = get_current_user()
    if user.get("is_teacher"):
        flash("Siz allaqachon tasdiqlangan o'qituvchisiz.", "success")
        return redirect(url_for("teacher_bp.teacher_dashboard"))
    pending = query_one(
        "SELECT id FROM teacher_applications WHERE user_id=? AND status='pending'", (user["id"],))
    if pending and request.method == "GET":
        flash("Sizning arizangiz allaqachon ko'rib chiqilmoqda.", "warn")
        return redirect(url_for("profile"))

    if request.method == "POST":
        ism = request.form.get("ism", "").strip()
        familiya = request.form.get("familiya", "").strip()
        phone_raw = request.form.get("phone", "").strip()
        direction_id = request.form.get("direction_id", "").strip()
        direction_custom = request.form.get("direction_custom", "").strip()
        syllabus_text = request.form.get("syllabus_text", "").strip()
        workplace = request.form.get("workplace", "").strip()
        price_raw = request.form.get("course_price_uzs", "0").replace(" ", "").replace(",", "")

        # Telefon: +998 XX XXX XX XX formatiga tekshiruv
        phone_digits = re.sub(r"\D", "", phone_raw)
        if phone_digits.startswith("998"):
            phone_digits = phone_digits[3:]
        if len(phone_digits) != 9:
            flash("Telefon raqami noto'g'ri formatda. Masalan: +998 90 123 45 67", "error")
            return redirect(url_for("teacher_apply"))
        phone_normalized = f"+998 {phone_digits[0:2]} {phone_digits[2:5]} {phone_digits[5:7]} {phone_digits[7:9]}"

        if not ism or not familiya:
            flash("Ism va familiya majburiy.", "error")
            return redirect(url_for("teacher_apply"))
        if not direction_id and not direction_custom:
            flash("Yo'nalishni tanlang yoki qo'lda kiriting.", "error")
            return redirect(url_for("teacher_apply"))
        try:
            course_price = max(0, int(price_raw or 0))
        except ValueError:
            course_price = 0

        cert_files = request.files.getlist("certificates")
        cert_files = [f for f in cert_files if f and f.filename][:5]
        if len(cert_files) < 1:
            flash("Kamida 1 ta sertifikat yuklashingiz kerak.", "error")
            return redirect(url_for("teacher_apply"))
        if len(cert_files) > 5:
            flash("Ko'pi bilan 5 ta sertifikat yuklash mumkin.", "error")
            return redirect(url_for("teacher_apply"))

        cert_paths = []
        for f in cert_files:
            path, err = _save_teacher_file(f, TEACHER_CERT_ALLOWED_EXT, TEACHER_CERT_UPLOAD_DIR)
            if err == "format":
                flash("Sertifikatlar faqat PNG/JPG/WEBP/PDF formatida bo'lishi kerak.", "error")
                return redirect(url_for("teacher_apply"))
            if err == "size":
                flash("Har bir sertifikat fayli 8 MB dan katta bo'lmasligi kerak.", "error")
                return redirect(url_for("teacher_apply"))
            if path:
                cert_paths.append(path)

        syllabus_file_path = None
        syllabus_upload = request.files.get("syllabus_file")
        if syllabus_upload and syllabus_upload.filename:
            syllabus_file_path, err = _save_teacher_file(
                syllabus_upload, TEACHER_SYLLABUS_ALLOWED_EXT, TEACHER_SYLLABUS_UPLOAD_DIR)
            if err:
                flash("Dars yo'riqnomasi fayli PDF/DOC/DOCX bo'lishi va 8 MB dan oshmasligi kerak.", "error")
                return redirect(url_for("teacher_apply"))

        execute(
            """INSERT INTO teacher_applications (user_id, ism, familiya, phone, direction_id, direction_custom,
               syllabus_text, workplace, course_price_uzs, certificates_json)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user["id"], ism, familiya, phone_normalized,
             int(direction_id) if direction_id else None, direction_custom or None,
             (syllabus_text + (f"\n[Fayl: {syllabus_file_path}]" if syllabus_file_path else "")).strip() or None,
             workplace or None, course_price, json.dumps(cert_paths))
        )
        app_id = query_one("SELECT id FROM teacher_applications WHERE user_id=? ORDER BY id DESC LIMIT 1",
                           (user["id"],))["id"]
        log_action(user["id"], "teacher_apply", details=f"app:{app_id}", ip=request.remote_addr)

        # Adminlarga bildirishnoma
        admins = query_all("SELECT id FROM users WHERE role IN ('admin','super_admin')")
        for a in admins:
            execute("INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                    (a["id"], "Yangi o'qituvchilik arizasi 👨‍🏫",
                     f"{ism} {familiya} o'qituvchilikka ariza yubordi (#{app_id}).", "admin"))

        # Telegram guruhga xabar
        try:
            import telegram_bot
            if telegram_bot.ADMIN_CHAT_ID:
                dir_name = direction_custom
                if direction_id:
                    d = query_one("SELECT name_uz FROM directions WHERE id=?", (int(direction_id),))
                    dir_name = d["name_uz"] if d else direction_custom
                note = (f"👨‍🏫 *Yangi o'qituvchilik arizasi #{app_id}*\n\n"
                        f"Ism: {ism} {familiya}\nTelefon: {phone_normalized}\n"
                        f"Yo'nalish: {dir_name}\nKurs narxi: {course_price:,} so'm\n"
                        f"Sertifikatlar: {len(cert_paths)} ta")
                telegram_bot.tg_send_message(int(telegram_bot.ADMIN_CHAT_ID), note)
        except Exception as e:
            print(f"[teacher_apply] Telegram xabar yuborilmadi: {e}")

        flash("Arizangiz yuborildi! Super admin ko'rib chiqqach xabar beramiz.", "success")
        return redirect(url_for("profile"))

    directions = get_directions()
    return render_template("teacher_apply.html", directions=directions)



@app.route("/notifications")
@login_required
def notifications():
    user = get_current_user()
    items = query_all("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 40", (user["id"],))
    execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (user["id"],))
    return render_template("notifications.html", items=items)


@app.route("/certificate/<cert_code>")
@login_required
def certificate(cert_code):
    cert = query_one(
        "SELECT cert.*, c.title as course_title, c.duration_weeks, u.ism, u.familiya FROM certificates cert "
        "JOIN courses c ON c.id=cert.course_id JOIN users u ON u.id=cert.user_id WHERE cert.cert_code=?",
        (cert_code,))
    if not cert:
        abort(404)
    return render_template("certificate.html", cert=cert)


@app.route("/certificate/<cert_code>/download")
@login_required
def certificate_download(cert_code):
    cert = query_one(
        "SELECT cert.*, c.title as course_title, c.duration_weeks, u.ism, u.familiya FROM certificates cert "
        "JOIN courses c ON c.id=cert.course_id JOIN users u ON u.id=cert.user_id WHERE cert.cert_code=?",
        (cert_code,))
    if not cert:
        abort(404)
    pdf_path = generate_certificate_pdf(cert)
    return send_file(pdf_path, as_attachment=True, download_name=f"sertifikat-{cert_code}.pdf")


# =================================================================
# AI YORDAMCHI
# =================================================================





# =================================================================
# MENTOR PANELI
# =================================================================
@app.route("/mentor")
@admin_required
def mentor():
    students = query_all(
        "SELECT u.id, u.ism, u.familiya, u.email, u.xp, u.level, "
        "(SELECT COUNT(*) FROM enrollments WHERE user_id=u.id) as course_count, "
        "(SELECT AVG(progress_percent) FROM enrollments WHERE user_id=u.id) as avg_progress "
        "FROM users u WHERE u.role='student' ORDER BY u.xp DESC LIMIT 50"
    )
    return render_template("mentor.html", students=students)


# =================================================================
# SOZLAMALAR
# =================================================================
@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user = get_current_user()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "change_password":
            old_pw = request.form.get("old_password", "")
            new_pw = request.form.get("new_password", "")
            if not check_password_hash(user["password_hash"], old_pw):
                flash("Joriy parol noto'g'ri.", "error")
            elif len(new_pw) < 6:
                flash("Yangi parol kamida 6 belgidan iborat bo'lishi kerak.", "error")
            else:
                execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new_pw), user["id"]))
                log_action(user["id"], "change_password", ip=request.remote_addr)
                flash("Parol muvaffaqiyatli o'zgartirildi.", "success")
        elif action == "delete_account":
            log_action(user["id"], "delete_account_request", ip=request.remote_addr)
            session.clear()
            flash("Hisobingiz o'chirish so'rovi qabul qilindi.", "info")
            return redirect(url_for("index"))
        elif action == "save_theme":
            # Endi PRO reja shart emas — HAR BIR foydalanuvchi CODE evaziga
            # shaxsiy dizayin sozlashi mumkin: 1-marta 7 CODE (panel ochish +
            # birinchi o'zgartirish), 2-marta va undan keyin har safar 10 CODE.
            # Pro+/admin/mentor — hali ham bepul va cheksiz (mavjud imtiyoz saqlanadi).
            is_unlimited = (user.get("role") in ("admin", "mentor", "super_admin") or
                            user.get("plan") in ("cyber_pro", "vip", "shats_cyber_pro", "shats_pro", "pro", "hacker"))
            changes = user.get("personal_theme_changes") or 0
            price = 0 if is_unlimited else (7 if changes == 0 else 10)

            charged = True
            if price > 0:
                from coins import spend_coins as _spend_theme_coins
                charged, pay_msg = _spend_theme_coins(user["id"], price, "personal_theme_change")
                if not charged:
                    flash(f"Shaxsiy dizaynni {'ochish' if changes == 0 else 'ozgartirish'} uchun "
                          f"{price} CODE kerak, lekin balansingiz yetarli emas.", "error")

            if charged:
                primary = request.form.get("primary_color", "#2563eb")[:7]
                secondary = request.form.get("secondary_color", "#0ea5e9")[:7]
                accent = request.form.get("accent_color", "#d97706")[:7]
                bg = request.form.get("bg_color", "#f6f9fd")[:7]
                card_bg = request.form.get("card_bg", "#ffffff")[:7]
                border = request.form.get("border_color", "#e2e8f0")[:7]
                font_style = request.form.get("font_style", "mono")
                glow = request.form.get("glow_intensity", "medium")
                execute(
                    """INSERT INTO user_themes
                       (user_id, primary_color, secondary_color, accent_color,
                        bg_color, card_bg, border_color, font_style, glow_intensity, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?, datetime('now'))
                       ON CONFLICT(user_id) DO UPDATE SET
                       primary_color=excluded.primary_color,
                       secondary_color=excluded.secondary_color,
                       accent_color=excluded.accent_color,
                       bg_color=excluded.bg_color,
                       card_bg=excluded.card_bg,
                       border_color=excluded.border_color,
                       font_style=excluded.font_style,
                       glow_intensity=excluded.glow_intensity,
                       updated_at=excluded.updated_at""",
                    (user["id"], primary, secondary, accent, bg, card_bg, border, font_style, glow)
                )
                if not is_unlimited:
                    execute("UPDATE users SET personal_theme_changes=personal_theme_changes+1 WHERE id=?",
                            (user["id"],))
                flash(f"Shaxsiy dizayin saqlandi!" + (f" ({price} CODE yechildi)" if price else ""), "success")
        return redirect(url_for("settings"))
    theme = query_one("SELECT * FROM user_themes WHERE user_id=?", (user["id"],))
    api_key = query_one("SELECT * FROM api_keys WHERE user_id=? AND active=1", (user["id"],))
    locked_direction = _locked_direction_for(user)
    direction_name = locked_direction["name_uz"] if locked_direction else None
    return render_template("settings.html", user_theme=theme, api_key=api_key, direction_name=direction_name)


@app.route("/api/user/theme")
@login_required
def api_user_theme():
    """Joriy foydalanuvchining tema CSS o'zgaruvchilarini qaytaradi."""
    user = get_current_user()
    theme = query_one("SELECT * FROM user_themes WHERE user_id=?", (user["id"],))
    if not theme:
        return api_response(True, data={"has_theme": False})
    return api_response(True, data={
        "has_theme": True,
        "theme": dict(theme),
    })


# =================================================================

# =================================================================
# FOYDALANUVCHI — Pro versiya, Reyting, Coinlar
# =================================================================

@app.route("/leaderboard")
@login_required
def leaderboard():
    board_type = request.args.get("type", "xp")
    user = get_current_user()
    if board_type == "code":
        leaders = query_all(
            """SELECT id, ism, familiya, level, plan, role, code_balance,
                      0 as courses_done, 0 as tests_passed, code_balance as total_score
               FROM users WHERE role='student' AND code_balance > 0
               ORDER BY code_balance DESC LIMIT 100"""
        )
        my_rank_row = query_one(
            "SELECT COUNT(*)+1 as rnk FROM users WHERE role='student' AND code_balance > "
            "(SELECT code_balance FROM users WHERE id=?)", (user["id"],))
        my_rank = my_rank_row["rnk"] if my_rank_row and user.get("code_balance", 0) > 0 else 0
    else:
        leaders = get_leaderboard(100)
        my_rank_row = query_one("SELECT rank_position FROM user_ratings WHERE user_id=?", (user["id"],))
        my_rank = my_rank_row["rank_position"] if my_rank_row else 0

    all_badges = query_all("SELECT * FROM badges")
    earned_ids = {r["badge_id"] for r in query_all("SELECT badge_id FROM user_badges WHERE user_id=?", (user["id"],))}
    next_level_xp = (user["level"]) * 500
    return render_template("leaderboard.html", leaders=leaders, my_rank=my_rank, board_type=board_type,
                           all_badges=all_badges, earned_ids=earned_ids, next_level_xp=next_level_xp)


# =================================================================
# XAVFSIZLIK ZONASI (MAXSUS versiya)
# =================================================================
def _require_hacker_plan():
    user = get_current_user()
    if not user:
        flash("Davom etish uchun tizimga kiring.", "error")
        return redirect(url_for("login"))
    return None




# =================================================================
# DO'STLAR TAKLIF (MAXSUS)
# =================================================================
@app.route("/dostlar-taklif")
@login_required
def referrals_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import referrals
    user = get_current_user()
    code = referrals.ensure_referral_code(user["id"])
    stats = referrals.get_referral_stats(user["id"])
    return render_template("referrals.html", code=code, stats=stats)






# =================================================================
# BIO MAXSUS (MAXSUS)
# =================================================================
@app.route("/bio-maxsus", methods=["GET", "POST"])
@login_required
def bio_maxsus_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    if request.method == "POST":
        execute(
            "UPDATE users SET bio_motto=?, bio_portfolio_url=?, bio_github_url=? WHERE id=?",
            (request.form.get("motto", "")[:200], request.form.get("portfolio_url", "")[:200],
             request.form.get("github_url", "")[:200], user["id"])
        )
        flash("Bio maxsus ma'lumotlari yangilandi!", "success")
        return redirect(url_for("bio_maxsus_page"))
    fresh = query_one("SELECT * FROM users WHERE id=?", (user["id"],))
    return render_template("bio_maxsus.html", user=fresh)


@app.route("/u/<custom_id>")
def public_profile_view(custom_id):
    """MAXSUS foydalanuvchining ochiq shaxsiy sahifasi (shatscyber.uz/u/ID uslubida)."""
    target = query_one("SELECT * FROM users WHERE custom_id=?", (custom_id,))
    if not target:
        abort(404)
    viewer_id = session.get("user_id")
    if viewer_id != target["id"]:
        execute("UPDATE users SET profile_views = profile_views + 1 WHERE id=?", (target["id"],))
        target = query_one("SELECT * FROM users WHERE custom_id=?", (custom_id,))
    friendship_status = friends_mod.get_friendship_status(viewer_id, target["id"]) if viewer_id else None
    pinned_statuettes = collection_mod.get_pinned_statuettes(target["id"])
    mutual_friends = friends_mod.get_mutual_friends(viewer_id, target["id"]) if (viewer_id and viewer_id != target["id"]) else []
    frame = frames_mod.get_frame_style(target["active_frame"]) if target["active_frame"] else None
    return render_template("public_profile.html", u=target, friendship_status=friendship_status,
                           pinned_statuettes=pinned_statuettes, mutual_friends=mutual_friends, frame=frame)


# =================================================================
# CODE SOVG'A-KARTOCHKA (MAXSUS)
# =================================================================
@app.route("/coins/gift-card", methods=["GET", "POST"])
@login_required
def gift_card_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    import random, string
    user = get_current_user()
    if request.method == "POST":
        try:
            amount = int(request.form.get("amount", 0))
        except ValueError:
            amount = 0
        if amount <= 0:
            flash("Miqdorni to'g'ri kiriting.", "error")
            return redirect(url_for("gift_card_page"))
        ok, msg = spend_coins(user["id"], amount, "gift_card_create")
        if not ok:
            flash(msg, "error")
            return redirect(url_for("gift_card_page"))
        code = "GIFT-" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        execute("INSERT INTO gift_codes (code, amount, created_by) VALUES (?,?,?)", (code, amount, user["id"]))
        flash(f"Sovg'a-kartochka yaratildi: {code} ({amount:,} CODE)", "success")
        return redirect(url_for("gift_card_page"))
    my_cards = query_all("SELECT * FROM gift_codes WHERE created_by=? ORDER BY id DESC", (user["id"],))
    return render_template("gift_card.html", my_cards=my_cards)


@app.route("/coins/gift-card/redeem", methods=["POST"])
@login_required
def gift_card_redeem():
    user = get_current_user()
    code = request.form.get("code", "").strip().upper()
    card = query_one("SELECT * FROM gift_codes WHERE code=?", (code,))
    if not card:
        flash("Kod topilmadi.", "error")
    elif card["redeemed_by"]:
        flash("Bu kod allaqachon ishlatilgan.", "error")
    else:
        add_coins(user["id"], card["amount"], "gift_card_redeem", card["id"])
        execute("UPDATE gift_codes SET redeemed_by=?, redeemed_at=datetime('now') WHERE id=?", (user["id"], card["id"]))
        flash(f"{card['amount']:,} CODE hisobingizga qo'shildi!", "success")
    return redirect(url_for("coins_bp.coins_page"))


# =================================================================
# MAXSUS (umumiy imtiyozlar) — MAXSUS
# =================================================================
@app.route("/maxsus-imtiyozlar")
@login_required
def hacker_perks_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    perks = query_all("SELECT * FROM hacker_perks ORDER BY order_index, id")
    return render_template("hacker_perks.html", perks=perks)


    return render_template("admin_hacker_perks.html", perks=perks)






# =================================================================
# DEVELOPER HUB / API (MAXSUS)
# =================================================================
@app.route("/developer-hub")
@login_required
def developer_hub_page():
    guard = _require_hacker_plan()
    if guard:
        return guard
    user = get_current_user()
    api_key = query_one("SELECT * FROM api_keys WHERE user_id=? AND active=1", (user["id"],))
    return render_template("developer_hub.html", api_key=api_key)


def _check_api_key():
    key = request.headers.get("X-API-Key", "")
    if not key:
        return None
    row = query_one("SELECT * FROM api_keys WHERE api_key=? AND active=1", (key,))
    if row:
        execute("UPDATE api_keys SET last_used_at=datetime('now') WHERE id=?", (row["id"],))
    return row


@app.route("/api/v1/me")
def api_v1_me():
    """MAXSUS Developer Hub API — API kalit orqali shaxsiy ma'lumotlarni qaytaradi."""
    key_row = _check_api_key()
    if not key_row:
        return api_response(False, error="Noto'g'ri yoki yo'q API kalit (X-API-Key header talab qilinadi)")
    user = query_one("SELECT id, ism, familiya, custom_id, plan, level, xp, code_balance FROM users WHERE id=?",
                      (key_row["user_id"],))
    return api_response(True, data=dict(user))


# =================================================================

@app.route("/coins/buy-course/<int:course_id>", methods=["POST"])
@login_required
def coins_buy_course(course_id):
    user = get_current_user()
    ok, msg = buy_course_with_coins(user["id"], course_id)
    flash(msg, "success" if ok else "error")
    course = query_one("SELECT slug FROM courses WHERE id=?", (course_id,))
    return redirect(url_for("courses_bp.course_detail", slug=course["slug"]) if course else url_for("courses_bp.courses"))


@app.route("/pricing/pay", methods=["POST"])
@login_required
def pricing_pay():
    """To'lov orqali Pro versiya (karta) — hozircha pending."""
    user = get_current_user()
    method = request.form.get("method", "card")
    execute("INSERT INTO pro_payments (user_id, method, status) VALUES (?,?,?)",
            (user["id"], method, "pending"))
    log_action(user["id"], "pro_payment_initiated", details=f"method:{method}", ip=request.remote_addr)
    flash("To'lov so'rovi qabul qilindi. Administrator tasdiqlashini kuting.", "info")
    return redirect(url_for("pricing"))


# =================================================================
# SERTIFIKAT TIZIMI — yo'nalish bo'yicha 50 test (15daq) + 15 amaliy (30daq)
# =================================================================


# PING TEST (PENTESTING) — plan bo'yicha kvota va narx
# =================================================================
# =================================================================

@app.route("/api/notifications/recent")
@api_login_required
def api_notifications_recent():
    """Trading natijasi uchun so'nggi bildirishnomani qaytaradi."""
    user = get_current_user()
    notifs = query_all(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 3",
        (user["id"],)
    )
    return api_response(True, data=notifs)


@app.route("/api/notifications/pending")
@api_login_required
def api_notifications_pending():
    """Foydalanuvchining o'qilmagan barcha bildirishnomalari (ovozli xabarlar uchun)."""
    user = get_current_user()
    items = query_all(
        "SELECT id, title, body, type, created_at FROM notifications WHERE user_id=? AND is_read=0 ORDER BY id DESC LIMIT 20",
        (user["id"],)
    )
    return api_response(True, data={"notifications": items})


@app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
@api_login_required
def api_notifications_mark_read(notif_id):
    user = get_current_user()
    execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (notif_id, user["id"]))
    return api_response(True)


# =================================================================
# WEB PUSH NOTIFICATIONS — foydalanuvchi saytdan chiqib ketsa ham
# qurilmasiga bildirishnoma kelishi uchun (Push API + Service Worker)
# =================================================================

@app.route("/sw.js")
def service_worker():
    """Service Worker ildiz darajasida xizmat ko'rsatilishi shart (scope cheklovi)."""
    resp = send_file(os.path.join(app.root_path, "static", "sw.js"))
    resp.headers["Content-Type"] = "application/javascript"
    resp.headers["Service-Worker-Allowed"] = "/"
    return resp



# =================================================================
# ID BOSHQARUVI VA AUKTSION
# =================================================================


# =================================================================
# ADMIN — ID va Auktsion boshqaruvi + kurs access kodlari



# =================================================================
# XATOLIK SAHIFALARI
# =================================================================
@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("405.html"), 405

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    # MUHIM TUZATISH: avval bu yerda xato HECH QAYERGA yozilmasdi — hatto
    # server logiga ham! Shuning uchun "500 Serverdagi ichki xatolik"
    # chiqqanda, HAQIQIY sababni topib bo'lmasdi (loglarda ham yo'q edi).
    # Endi to'liq traceback (xato qatorlari) server logiga yoziladi —
    # Railway'da "Deployments > Logs" bo'limida ko'rinadi.
    app.logger.error("500 ICHKI XATOLIK: %s", request.path, exc_info=True)
    return render_template("500.html"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # XAVFSIZLIK: debug rejimi ATAY standart holatda O'CHIRILGAN.
    # Werkzeug debug-konsoli (Flask debug=True) production muhitda ochiq
    # qolib ketsa, tashqi odam orqali serverda ixtiyoriy kod bajarilishiga
    # (RCE) olib kelishi mumkin. Faqat lokal ishlab chiqish paytida ongli
    # ravishda FLASK_DEBUG=1 qilib yoqing.
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
