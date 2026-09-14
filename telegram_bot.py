"""
CYBER SHATS V1.3 — Telegram bot (code tangalar sotuvi)

Ishga tushirish:
    python telegram_bot.py

Bot vazifalari:
1. /start — salomlashish va til tanlash
2. Menu: Code sotib olish | Kurs sotib olish
3. Code paketi (1K-100K) tanlash → ID so'rash → karta + chek skrin
4. Kurs sotib olish (1-10 ta tanlash) → ID so'rash → karta + chek skrin
5. Chek g'aznachiga yuboriladi (sayt orqali tasdiqlanadi)
6. Tasdiqdan keyin: g'azna jamg'armasidan code yoki kurs foydalanuvchiga beriladi

Bot 7 til qo'llab-quvvatlaydi (uz, ru, en, tr, kk, ky, tj).
"""
import re
import sys
from utils import send_email
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os
import json
import time
import sqlite3
import logging
from urllib.parse import quote
import requests

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
DB_PATH = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "database", "cyber_shats.db"))

# XAVFSIZLIK: bot mustaqil jarayon sifatida (app.py'dan OLDIN yoki
# umuman u ishga tushmasdan) ham ishga tushishi mumkin. Agar shunday
# holatda haqiqiy baza hali yo'q bo'lsa, SQLite avtomatik BO'SH fayl
# yaratib qo'yishi mumkin edi (jadvalsiz) — bu esa "no such table: users"
# xatosiga olib kelardi. app.py'dagi bilan BIR XIL himoya shu yerda ham:
# faqat HAQIQATAN HAM birinchi marta (baza umuman yo'q bo'lsa) namunadan
# nusxa olinadi, mavjud bazaga esa HECH QACHON tegilmaydi.
_DB_SEED_PATH = DB_PATH + ".SEED"
if not os.path.exists(DB_PATH) and os.path.exists(_DB_SEED_PATH):
    import shutil as _shutil
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    _shutil.copy2(_DB_SEED_PATH, DB_PATH)
    print(f"[BOT BOOTSTRAP] Birinchi marta o'rnatish — namunaviy baza nusxalandi: {DB_PATH}")
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "").strip()

# Ikkita MAXSUS admin Telegram ID'si — CODE/tarif so'rovlari kelganda
# guruhga QO'SHIMCHA ravishda, to'g'ridan-to'g'ri shaxsiy xabar (DM)
# yuboriladi. DIQQAT: bular Telegram foydalanuvchi ID'lari, sayt ID'lari
# EMAS. Bot bu odamlarga DM yubora olishi uchun, ular avval botga
# KAMIDA BIR MARTA /start bosib, suhbatni boshlagan bo'lishi kerak
# (Telegram API cheklovi — botlar hech kim yozmagan foydalanuvchiga
# birinchi bo'lib yoza olmaydi).
SPECIAL_ADMIN_TG_IDS = [8613567608, 5856575656]
ADMIN_TELEGRAM_USERNAME = "shedow_777"

API_BASE = f"https://api.telegram.org/bot{TOKEN}"
CODE_TANGA_IMAGE = os.path.join(BASE_DIR, "static", "bot_images", "code_tanga.png")
CODE_RESULT_IMAGES_DIR = os.path.join(BASE_DIR, "static", "bot_images", "code_results")
INSTRUCTIONS_IMAGE = os.path.join(BASE_DIR, "static", "bot_images", "instructions.png")


def get_code_result_image(amount: int):
    """Berilgan CODE miqdoriga mos tayyor rasm (masalan '50 CODE tushdi!')
    yo'lini qaytaradi — mos rasm bo'lmasa None (shunda oddiy matn xabar
    yuboriladi)."""
    path = os.path.join(CODE_RESULT_IMAGES_DIR, f"{amount}.jpg")
    return path if os.path.exists(path) else None

# Karta raqami va to'lov ma'lumotlari
PAYMENT_CARDS = {
    "uzum_bank": "4916 9903 5863 3797 (Q.TEMUROV)",
}
CARD_HOLDER = "Q.TEMUROV"

# Code paketlari — bazadan dinamik yuklanadi
# Standart narxlar (bazada yo'q bo'lsa ishlatiladi)
_DEFAULT_PACKAGES = [
    (1, 10_000),
    (5, 50_000),
    (10, 100_000),
    (15, 150_000),
    (20, 200_000),
    (25, 250_000),
    (30, 300_000),
]


def get_code_packages():
    """Bazadan joriy paket narxlarini qaytaradi (admin o'zgartirsa yangilanadi)."""
    try:
        conn = db_conn()
        c = conn.cursor()
        rows = c.execute(
            "SELECT key, value FROM pricing_settings WHERE key LIKE 'code_pack_%' ORDER BY CAST(value AS INTEGER)"
        ).fetchall()
        conn.close()
        if rows:
            result = []
            for key, price_str in rows:
                amount = int(key.replace('code_pack_', ''))
                result.append((amount, int(price_str)))
            return sorted(result, key=lambda x: x[0])
    except Exception:
        pass
    return _DEFAULT_PACKAGES


# Eski o'zgaruvchi — mos kelish uchun saqlanadi
CODE_PACKAGES = _DEFAULT_PACKAGES

# Tariflar (Pro/Cyber Pro/VIP/HackerLab) — botda endi sotib olinadi.
# Narx CODE birligida, saytdagi bilan bir xil (pricing_settings orqali dinamik).
TARIFF_PLANS = [
    ("pro", "💠 Pro Oddiy"),
    ("cyber_pro", "💚 Cyber Pro"),
    ("vip", "👑 VIP"),
    ("hacker", "🔴 HackerLab (Maxsus)"),
]
_DEFAULT_TARIFF_PRICES = {"pro": 9, "cyber_pro": 15, "vip": 57, "hacker": 77}

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("telegram_bot")


# =================================================================
# I18N — 7 til
# =================================================================
TEXTS = {
    "uz": {
        "lang_name": "🇺🇿 O'zbek",
        "welcome_named": "Salom, {name}! 👋\n\n*SHATS CYBER* botiga xush kelibsiz!\n\nBu yerdan siz CODE tangalar va kurslar sotib olishingiz mumkin.",
        "choose_lang": "Iltimos, til tanlang:",
        "lang_set": "Til o'rnatildi: {lang_name}",
        "main_menu": "🏠 *Asosiy menyu*\n\nKerakli xizmatni tanlang:",
        "btn_buy_code": "⚡ CODE sotib olish",
        "btn_buy_course": "📚 Kurs sotib olish",
        "btn_link_profile": "🔗 Profil ulash",
        "btn_leaderboard": "🏆 Reyting",
        "ask_link_id": "🔗 *Profil ulash*\n\nSaytdagi ID raqamingizni kiriting (masalan: `1342835`):",
        "ask_link_email": "📧 Endi profilingizga ro'yxatdan o'tgan email manzilingizni kiriting:",
        "link_mismatch": "❌ Email mos kelmadi. Iltimos, saytda ro'yxatdan o'tgan email manzilingizni to'g'ri kiriting, yoki /start bilan qaytadan urinib ko'ring.",
        "ask_link_code": "📧 {email} manziliga 6 xonali tasdiqlash kodi yuborildi.\nIltimos, ushbu kodni shu yerga kiriting (kod 10 daqiqa amal qiladi):",
        "link_code_invalid": "❌ Noto'g'ri kod kiritdingiz. Qaytadan urinib ko'ring.",
        "link_code_expired": "❌ Tasdiqlash kodi muddati o'tgan yoki noto'g'ri. Iltimos, jarayonni boshidan boshlang.",
        "link_email_sent_error": "❌ Emailga xat yuborishda xatolik yuz berdi. Iltimos keyinroq urinib ko'ring.",
        "link_success": "✅ Profil muvaffaqiyatli ulandi!\n\n👤 {name}\n🆔 #{cid}\n\nEndi tarif tugashi haqida va boshqa muhim yangiliklar haqida shu yerdan xabar olasiz.",
        "link_id_not_found": "❌ Bu ID saytda topilmadi. Qaytadan urinib ko'ring yoki /start bosing.",
        "leaderboard_title": "🏆 *TOP-10 Reyting (XP bo'yicha)*\n\n",
        "btn_help": "❓ Yordam",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_back": "⬅️ Orqaga",
        "btn_main_menu": "🏠 Asosiy menyu",
        "btn_cancel": "❌ Bekor qilish",
        "choose_code_pkg": "💎 *Code paket tanlang*\n\nHar 1000 CODE = 1000 so'm\n\nQuyidagi paketlardan birini tanlang:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} so'm",
        "choose_courses_title": "📚 *Kurslar — bir nechtasini tanlashingiz mumkin (1-10 ta)*",
        "course_done": "✅ Tanlash tugadi",
        "course_clear": "🗑 Tanlovni tozalash",
        "selected_courses": "Tanlangan: {n} ta · Jami: {total:,} CODE",
        "max_courses_reached": "Maksimal 10 ta kurs tanlash mumkin.",
        "no_paid_courses": "Hozircha pulli kurslar ro'yxati bo'sh.",
        "no_courses_selected": "Hech qanday kurs tanlanmadi.",
        "ask_id_for_code": "🆔 *Saytdagi ID raqamingizni kiriting*\n\nMasalan: 8520810\n\n(ID profilingizdagi \"Mening ID\" bo'limida ko'rish mumkin)",
        "ask_id_for_course": "🆔 *Saytdagi ID raqamingizni kiriting*\n\nMasalan: 8520810",
        "id_not_found": "❌ Bu ID saytda topilmadi. Iltimos, to'g'ri ID kiriting.",
        "id_invalid": "❌ ID raqami noto'g'ri. Faqat raqam kiriting (masalan: 8520810).",
        "id_confirmed": "✅ ID tasdiqlandi: #{cid}\n👤 Foydalanuvchi: {name}",
        "show_payment_for_code": "💳 *To'lov ma'lumoti*\n\n📦 Buyurtma: ⚡ {code:,} CODE\n💰 Summa: {price:,} so'm\n🆔 ID: #{cid}\n\n*Karta raqami:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 To'lovni amalga oshirib, chekning skrinshotini yuboring",
        "show_payment_for_course": "💳 *To'lov ma'lumoti*\n\n📚 Kurslar: {n} ta\n💰 Jami summa: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Karta raqami:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 To'lovni amalga oshirib, chekning skrinshotini yuboring",
        "awaiting_receipt": "📸 Iltimos, *to'lov chekining rasmini* yuboring (faqat rasm qabul qilinadi).",
        "receipt_received": "✅ Chek qabul qilindi!\n\n⏳ Hozir g'aznachi tomonidan tekshiriladi.\n\nNatija tez orada xabar qilinadi. Iltimos kuting...",
        "receipt_not_image": "⚠️ Iltimos, rasm yuboring (fayl emas).",
        "purchase_approved_code": "✅ *Sotib olish tasdiqlandi!*\n\n⚡ {code:,} CODE hisobingizga qo'shildi!\n🆔 ID: #{cid}\n\nRahmat, qaytib kelishingizdan xursandmiz!",
        "purchase_approved_course": "✅ *Sotib olish tasdiqlandi!*\n\n📚 {n} ta kurs hisobingizga qo'shildi!\n🆔 ID: #{cid}\n\nKurslarga kirish: cyber.shats.uz",
        "purchase_rejected": "❌ *Sotib olish rad etildi.*\n\nSabab: {reason}\n\nIltimos, qaytadan urinib ko'ring.",
        "fund_insufficient": "⚠️ G'aznada hozir yetarli CODE yo'q. Iltimos, biroz keyin urinib ko'ring.",
        "help_text": "*SHATS CYBER bot yordami*\n\n🤖 Bu bot orqali siz:\n• CODE tangalar sotib olishingiz\n• Tarif (Pro/Cyber Pro/VIP/HackerLab) sotib olishingiz\n• Pullik kurslar sotib olishingiz mumkin\n\n📋 *Jarayon:*\n1. Paket/tarif/kurs tanlang\n2. Birinchi safar saytdagi ID raqamingizni kiriting (keyingi safarlarda so'ralmaydi)\n3. Karta orqali to'lang\n4. Chek skrinini yuboring\n5. G'aznachi tekshirib tasdiqlaydi\n6. CODE/tarif/kurslar hisobingizga tushadi\n\n💬 Savol bo'lsa admin bilan bog'laning: @shedow_777",
        "unknown_message": "Tushunmadim. /start orqali asosiy menyuga qayting.",
        "operation_cancelled": "❌ Amal bekor qilindi.",
        "back_to_main": "🏠 Asosiy menyuga qaytdingiz.",
        "btn_buy_tariff": "🎓 Tarif sotib olish",
        "btn_guide": "📋 Yo'riqnoma",
        "btn_contact_admin": "💬 Admin bilan bog'lanish",
        "btn_change_id": "🔄 ID'ni almashtirish",
        "choose_tariff_title": "🎓 *Tarif tanlang*\n\nQuyidagi tariflardan birini tanlang:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} so'm)",
        "ask_id_for_tariff": "🆔 *Saytdagi ID raqamingizni kiriting*\n\nMasalan: 8520810",
        "show_payment_for_tariff": "💳 *To'lov ma'lumoti*\n\n🎓 Tarif: {name}\n💰 Summa: {price:,} so'm\n🆔 ID: #{cid}\n\n*Karta raqami:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 To'lovni amalga oshirib, chekning skrinshotini yuboring",
        "purchase_approved_tariff": "✅ *Sotib olish tasdiqlandi!*\n\n🎓 {name} tarifi faollashtirildi (30 kun)!\n🆔 ID: #{cid}\n\nRahmat!",
        "id_remembered": "✅ ID eslab qolindi: #{cid} ({name})\n\nEndi keyingi xaridlaringizda ID qayta so'ralmaydi. Agar xato ID kiritgan bo'lsangiz, \"🔄 ID'ni almashtirish\" tugmasidan foydalaning.",
        "id_already_linked": "✅ Sizning ID: #{cid} ({name})\n\nDavom etish uchun to'lov ma'lumotlari pastda:",
        "id_unlinked": "🔄 ID unutildi. Keyingi xariddan oldin ID'ni qaytadan kiritishingiz kerak bo'ladi.",
        "contact_admin_text": "💬 *Admin bilan bog'lanish*\n\nSavol yoki muammo bo'lsa, to'g'ridan-to'g'ri yozing:",
        "guide_caption": "📋 *SHATS CYBER — Code tanga sotib olish yo'riqnomasi*\n\nYuqoridagi rasmda barcha bosqichlar ko'rsatilgan: ID olish, botga o'tish, paket tanlash, to'lov qilish va CODE'ni hisobingizga qabul qilish.",
    },
    "ru": {
        "lang_name": "🇷🇺 Русский",
        "welcome_named": "Здравствуйте, {name}! 👋\n\nДобро пожаловать в *SHATS CYBER*!\n\nЗдесь вы можете купить CODE-монеты и курсы.",
        "choose_lang": "Пожалуйста, выберите язык:",
        "lang_set": "Язык установлен: {lang_name}",
        "main_menu": "🏠 *Главное меню*\n\nВыберите услугу:",
        "btn_buy_code": "⚡ Купить CODE",
        "btn_buy_course": "📚 Купить курс",
        "btn_help": "❓ Помощь",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_back": "⬅️ Назад",
        "btn_main_menu": "🏠 Главное меню",
        "btn_cancel": "❌ Отмена",
        "choose_code_pkg": "💎 *Выберите пакет CODE*\n\nКаждые 1000 CODE = 1000 сум\n\nВыберите один из пакетов:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сум",
        "choose_courses_title": "📚 *Курсы — можно выбрать несколько (1-10)*",
        "course_done": "✅ Завершить выбор",
        "course_clear": "🗑 Очистить выбор",
        "selected_courses": "Выбрано: {n} · Итого: {total:,} CODE",
        "max_courses_reached": "Можно выбрать максимум 10 курсов.",
        "no_paid_courses": "Платных курсов пока нет.",
        "no_courses_selected": "Ни одного курса не выбрано.",
        "ask_id_for_code": "🆔 *Введите ваш ID на сайте*\n\nПример: 8520810",
        "ask_id_for_course": "🆔 *Введите ваш ID на сайте*\n\nПример: 8520810",
        "id_not_found": "❌ Этот ID не найден. Введите правильный ID.",
        "id_invalid": "❌ Неверный ID. Введите только цифры.",
        "id_confirmed": "✅ ID подтверждён: #{cid}\n👤 Пользователь: {name}",
        "show_payment_for_code": "💳 *Платёжная информация*\n\n📦 Заказ: ⚡ {code:,} CODE\n💰 Сумма: {price:,} сум\n🆔 ID: #{cid}\n\n*Номер карты:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Оплатите и пришлите скриншот чека",
        "show_payment_for_course": "💳 *Платёжная информация*\n\n📚 Курсов: {n}\n💰 Итого: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Номер карты:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Оплатите и пришлите скриншот чека",
        "awaiting_receipt": "📸 Пожалуйста, отправьте *скриншот чека* (только изображение).",
        "receipt_received": "✅ Чек получен!\n\n⏳ Сейчас проверяется кассиром.\n\nРезультат скоро придёт. Пожалуйста, подождите...",
        "receipt_not_image": "⚠️ Пожалуйста, отправьте изображение.",
        "purchase_approved_code": "✅ *Покупка подтверждена!*\n\n⚡ {code:,} CODE начислено на ваш счёт!\n🆔 ID: #{cid}",
        "purchase_approved_course": "✅ *Покупка подтверждена!*\n\n📚 {n} курсов добавлены!\n🆔 ID: #{cid}",
        "purchase_rejected": "❌ *Покупка отклонена.*\n\nПричина: {reason}",
        "fund_insufficient": "⚠️ В казне недостаточно CODE. Попробуйте позже.",
        "help_text": "*Помощь SHATS CYBER*\n\n🤖 Бот для покупки CODE и курсов.\n\n📋 *Процесс:*\n1. Выберите пакет\n2. Введите ID на сайте\n3. Оплатите картой\n4. Отправьте скриншот чека\n5. Кассир проверит\n6. CODE/курсы поступят на счёт",
        "unknown_message": "Не понял. Используйте /start.",
        "operation_cancelled": "❌ Отменено.",
        "back_to_main": "🏠 Главное меню.",
        "btn_buy_tariff": "🎓 Купить тариф",
        "btn_guide": "📋 Инструкция",
        "btn_contact_admin": "💬 Связаться с админом",
        "btn_change_id": "🔄 Сменить ID",
        "choose_tariff_title": "🎓 *Выберите тариф*\n\nВыберите один из тарифов:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} сум)",
        "ask_id_for_tariff": "🆔 *Введите ваш ID на сайте*\n\nПример: 8520810",
        "show_payment_for_tariff": "💳 *Платёжная информация*\n\n🎓 Тариф: {name}\n💰 Сумма: {price:,} сум\n🆔 ID: #{cid}\n\n*Номер карты:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Оплатите и пришлите скриншот чека",
        "purchase_approved_tariff": "✅ *Покупка подтверждена!*\n\n🎓 Тариф {name} активирован (30 дней)!\n🆔 ID: #{cid}\n\nСпасибо!",
        "id_remembered": "✅ ID запомнен: #{cid} ({name})\n\nТеперь при следующих покупках ID не будет запрашиваться повторно. Если вы ввели неверный ID, используйте кнопку \"🔄 Сменить ID\".",
        "id_already_linked": "✅ Ваш ID: #{cid} ({name})\n\nПлатёжная информация ниже:",
        "id_unlinked": "🔄 ID сброшен. Перед следующей покупкой потребуется ввести ID заново.",
        "contact_admin_text": "💬 *Связь с администратором*\n\nЕсли у вас вопрос или проблема, напишите напрямую:",
        "guide_caption": "📋 *SHATS CYBER — Инструкция по покупке CODE-монет*\n\nНа изображении выше показаны все шаги: получение ID, переход в бота, выбор пакета, оплата и зачисление CODE на счёт.",
    },
    "en": {
        "lang_name": "🇬🇧 English",
        "welcome_named": "Hello, {name}! 👋\n\nWelcome to *SHATS CYBER*!\n\nHere you can buy CODE tokens and courses.",
        "choose_lang": "Please choose a language:",
        "lang_set": "Language set: {lang_name}",
        "main_menu": "🏠 *Main menu*\n\nChoose a service:",
        "btn_buy_code": "⚡ Buy CODE",
        "btn_buy_course": "📚 Buy course",
        "btn_help": "❓ Help",
        "btn_change_lang": "🌐 Change language",
        "btn_back": "⬅️ Back",
        "btn_main_menu": "🏠 Main menu",
        "btn_cancel": "❌ Cancel",
        "choose_code_pkg": "💎 *Choose a CODE package*\n\n1000 CODE = 1000 UZS\n\nPick one:",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} UZS",
        "choose_courses_title": "📚 *Courses — pick 1-10*",
        "course_done": "✅ Done selecting",
        "course_clear": "🗑 Clear selection",
        "selected_courses": "Selected: {n} · Total: {total:,} CODE",
        "max_courses_reached": "You can pick max 10 courses.",
        "no_paid_courses": "No paid courses yet.",
        "no_courses_selected": "No courses selected.",
        "ask_id_for_code": "🆔 *Enter your site ID*\n\nExample: 8520810",
        "ask_id_for_course": "🆔 *Enter your site ID*\n\nExample: 8520810",
        "id_not_found": "❌ ID not found on the site.",
        "id_invalid": "❌ Invalid ID. Numbers only.",
        "id_confirmed": "✅ ID confirmed: #{cid}\n👤 User: {name}",
        "show_payment_for_code": "💳 *Payment info*\n\n📦 Order: ⚡ {code:,} CODE\n💰 Amount: {price:,} UZS\n🆔 ID: #{cid}\n\n*Cards:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Pay and send the receipt screenshot",
        "show_payment_for_course": "💳 *Payment info*\n\n📚 Courses: {n}\n💰 Total: ⚡ {total:,} CODE\n🆔 ID: #{cid}\n\n*Cards:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Pay and send the receipt screenshot",
        "awaiting_receipt": "📸 Please send the *receipt screenshot* (image only).",
        "receipt_received": "✅ Receipt received!\n\n⏳ Treasurer is reviewing.\n\nYou will be notified shortly.",
        "receipt_not_image": "⚠️ Please send an image.",
        "purchase_approved_code": "✅ *Purchase approved!*\n\n⚡ {code:,} CODE credited to ID #{cid}!",
        "purchase_approved_course": "✅ *Purchase approved!*\n\n📚 {n} courses added to ID #{cid}!",
        "purchase_rejected": "❌ *Purchase rejected.*\n\nReason: {reason}",
        "fund_insufficient": "⚠️ Treasury doesn't have enough CODE. Try later.",
        "help_text": "*SHATS CYBER Bot Help*\n\n🤖 Buy CODE and courses.\n\n📋 *Steps:*\n1. Pick a package\n2. Enter your site ID\n3. Pay by card\n4. Send receipt\n5. Treasurer verifies\n6. CODE/courses delivered",
        "unknown_message": "Use /start.",
        "operation_cancelled": "❌ Cancelled.",
        "back_to_main": "🏠 Back to main.",
        "btn_buy_tariff": "🎓 Buy tariff",
        "btn_guide": "📋 Guide",
        "btn_contact_admin": "💬 Contact admin",
        "btn_change_id": "🔄 Change ID",
        "choose_tariff_title": "🎓 *Choose a tariff*\n\nSelect one of the tariffs below:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} UZS)",
        "ask_id_for_tariff": "🆔 *Enter your site ID*\n\nExample: 8520810",
        "show_payment_for_tariff": "💳 *Payment info*\n\n🎓 Tariff: {name}\n💰 Amount: {price:,} UZS\n🆔 ID: #{cid}\n\n*Card number:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Pay and send a screenshot of the receipt",
        "purchase_approved_tariff": "✅ *Purchase approved!*\n\n🎓 {name} tariff activated (30 days)!\n🆔 ID: #{cid}\n\nThank you!",
        "id_remembered": "✅ ID remembered: #{cid} ({name})\n\nYour ID won't be asked again for future purchases. If you entered the wrong ID, use the \"🔄 Change ID\" button.",
        "id_already_linked": "✅ Your ID: #{cid} ({name})\n\nPayment info below:",
        "id_unlinked": "🔄 ID forgotten. You'll need to re-enter your ID before your next purchase.",
        "contact_admin_text": "💬 *Contact admin*\n\nIf you have a question or issue, message directly:",
        "guide_caption": "📋 *SHATS CYBER — CODE purchase guide*\n\nThe image above shows all the steps: getting your ID, opening the bot, choosing a package, paying, and receiving CODE on your account.",
    },
    "tr": {
        "lang_name": "🇹🇷 Türkçe",
        "welcome_named": "Merhaba {name}! 👋\n\n*SHATS CYBER*'e hoş geldiniz!\n\nBuradan CODE jeton ve kurs satın alabilirsiniz.",
        "choose_lang": "Lütfen dil seçin:",
        "lang_set": "Dil ayarlandı: {lang_name}",
        "main_menu": "🏠 *Ana menü*",
        "btn_buy_code": "⚡ CODE satın al",
        "btn_buy_course": "📚 Kurs satın al",
        "btn_help": "❓ Yardım",
        "btn_change_lang": "🌐 Dili değiştir",
        "btn_back": "⬅️ Geri",
        "btn_main_menu": "🏠 Ana menü",
        "btn_cancel": "❌ İptal",
        "choose_code_pkg": "💎 *CODE paketi seçin*\n\n1000 CODE = 1000 som",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} som",
        "choose_courses_title": "📚 *Kurslar — 1-10 tane seçin*",
        "course_done": "✅ Seçimi tamamla",
        "course_clear": "🗑 Temizle",
        "selected_courses": "Seçili: {n} · Toplam: {total:,} CODE",
        "max_courses_reached": "En fazla 10 kurs.",
        "no_paid_courses": "Henüz ücretli kurs yok.",
        "no_courses_selected": "Kurs seçilmedi.",
        "ask_id_for_code": "🆔 *Site ID'nizi girin*\n\nÖrnek: 8520810",
        "ask_id_for_course": "🆔 *Site ID'nizi girin*\n\nÖrnek: 8520810",
        "id_not_found": "❌ ID bulunamadı.",
        "id_invalid": "❌ Geçersiz ID.",
        "id_confirmed": "✅ ID onaylandı: #{cid}\n👤 Kullanıcı: {name}",
        "show_payment_for_code": "💳 *Ödeme*\n\n📦 ⚡ {code:,} CODE\n💰 {price:,} som\n🆔 #{cid}\n\nUZUM BANK: `{uzcard}`\n\n👇 Fişin ekran görüntüsünü gönderin",
        "show_payment_for_course": "💳 *Ödeme*\n\n📚 {n} kurs\n💰 ⚡ {total:,} CODE\n🆔 #{cid}\n\nUZUM BANK: `{uzcard}`\n\n👇 Fişin ekran görüntüsünü gönderin",
        "awaiting_receipt": "📸 Fiş ekran görüntüsünü gönderin.",
        "receipt_received": "✅ Fiş alındı! ⏳ Kontrol ediliyor.",
        "receipt_not_image": "⚠️ Lütfen resim gönderin.",
        "purchase_approved_code": "✅ *Onaylandı!* ⚡ {code:,} CODE eklendi (#{cid})",
        "purchase_approved_course": "✅ *Onaylandı!* {n} kurs eklendi (#{cid})",
        "purchase_rejected": "❌ Reddedildi: {reason}",
        "fund_insufficient": "⚠️ Hazinede yeterli CODE yok.",
        "help_text": "SHATS CYBER bot — CODE ve kurs satın al.",
        "unknown_message": "/start yazın.",
        "operation_cancelled": "❌ İptal.",
        "back_to_main": "🏠 Ana menü.",
        "btn_buy_tariff": "🎓 Tarife satın al",
        "btn_guide": "📋 Kılavuz",
        "btn_contact_admin": "💬 Admin ile iletişim",
        "btn_change_id": "🔄 ID değiştir",
        "choose_tariff_title": "🎓 *Tarife seçin*\n\nAşağıdaki tariflerden birini seçin:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} so'm)",
        "ask_id_for_tariff": "🆔 *Sitedeki ID numaranızı girin*\n\nÖrnek: 8520810",
        "show_payment_for_tariff": "💳 *Ödeme bilgisi*\n\n🎓 Tarife: {name}\n💰 Tutar: {price:,} so'm\n🆔 ID: #{cid}\n\n*Kart numarası:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Ödemeyi yapıp makbuz ekran görüntüsünü gönderin",
        "purchase_approved_tariff": "✅ *Satın alma onaylandı!*\n\n🎓 {name} tarifi etkinleştirildi (30 gün)!\n🆔 ID: #{cid}\n\nTeşekkürler!",
        "id_remembered": "✅ ID hatırlandı: #{cid} ({name})\n\nSonraki alışverişlerde ID tekrar sorulmayacak. Yanlış ID girdiyseniz \"🔄 ID değiştir\" düğmesini kullanın.",
        "id_already_linked": "✅ ID'niz: #{cid} ({name})\n\nÖdeme bilgisi aşağıda:",
        "id_unlinked": "🔄 ID unutuldu. Sonraki alışverişten önce ID'nizi tekrar girmeniz gerekecek.",
        "contact_admin_text": "💬 *Admin ile iletişim*\n\nSorunuz veya sorununuz varsa doğrudan yazın:",
        "guide_caption": "📋 *SHATS CYBER — CODE satın alma kılavuzu*\n\nYukarıdaki görselde tüm adımlar gösterilmektedir: ID alma, bota geçme, paket seçme, ödeme yapma ve CODE'un hesabınıza geçmesi.",
    },
    "kk": {
        "lang_name": "🇰🇿 Қазақ",
        "welcome_named": "Сәлем, {name}! 👋\n\n*SHATS CYBER*-ге қош келдіңіз!",
        "choose_lang": "Тілді таңдаңыз:",
        "lang_set": "Тіл орнатылды: {lang_name}",
        "main_menu": "🏠 *Басты мәзір*",
        "btn_buy_code": "⚡ CODE сатып алу",
        "btn_buy_course": "📚 Курс сатып алу",
        "btn_help": "❓ Көмек",
        "btn_change_lang": "🌐 Тіл",
        "btn_back": "⬅️ Артқа",
        "btn_main_menu": "🏠 Басты мәзір",
        "btn_cancel": "❌ Бас тарту",
        "choose_code_pkg": "💎 *CODE топтаманы таңдаңыз*\n1000 CODE = 1000 сом",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курстар — 1-10*",
        "course_done": "✅ Дайын",
        "course_clear": "🗑 Тазалау",
        "selected_courses": "Таңдалды: {n} · Барлығы: {total:,} CODE",
        "max_courses_reached": "Барынша 10.",
        "no_paid_courses": "Ақылы курс жоқ.",
        "no_courses_selected": "Курс жоқ.",
        "ask_id_for_code": "🆔 *ID-ні енгізіңіз*\n\nМысал: 8520810",
        "ask_id_for_course": "🆔 *ID-ні енгізіңіз*",
        "id_not_found": "❌ ID табылмады.",
        "id_invalid": "❌ ID қате.",
        "id_confirmed": "✅ ID: #{cid}\n👤 {name}",
        "show_payment_for_code": "💳 *Төлем*\n⚡ {code:,} CODE = {price:,} сом\n🆔 #{cid}\nUZUM BANK: `{uzcard}`",
        "show_payment_for_course": "💳 *Төлем*\n📚 {n} курс = ⚡ {total:,} CODE\n🆔 #{cid}\nUZUM BANK: `{uzcard}`",
        "awaiting_receipt": "📸 Чек суретін жіберіңіз.",
        "receipt_received": "✅ Қабылданды! ⏳ Тексерілуде.",
        "receipt_not_image": "⚠️ Сурет жіберіңіз.",
        "purchase_approved_code": "✅ Расталды! ⚡ {code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Расталды! {n} курс (#{cid})",
        "purchase_rejected": "❌ Қабылданбады: {reason}",
        "fund_insufficient": "⚠️ Қазынада жетіспейді.",
        "help_text": "SHATS CYBER бот.",
        "unknown_message": "/start теріңіз.",
        "operation_cancelled": "❌ Бас тартылды.",
        "back_to_main": "🏠 Басты мәзір.",
        "btn_buy_tariff": "🎓 Тарифті сатып алу",
        "btn_guide": "📋 Нұсқаулық",
        "btn_contact_admin": "💬 Админмен байланыс",
        "btn_change_id": "🔄 ID ауыстыру",
        "choose_tariff_title": "🎓 *Тарифті таңдаңыз*\n\nТөмендегі тарифтердің бірін таңдаңыз:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} сум)",
        "ask_id_for_tariff": "🆔 *Сайттағы ID нөміріңізді енгізіңіз*\n\nМысалы: 8520810",
        "show_payment_for_tariff": "💳 *Төлем ақпараты*\n\n🎓 Тариф: {name}\n💰 Сома: {price:,} сум\n🆔 ID: #{cid}\n\n*Карта нөмірі:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Төлемді жасап, чектің скриншотын жіберіңіз",
        "purchase_approved_tariff": "✅ *Сатып алу расталды!*\n\n🎓 {name} тарифі белсендірілді (30 күн)!\n🆔 ID: #{cid}\n\nРақмет!",
        "id_remembered": "✅ ID есте сақталды: #{cid} ({name})\n\nЕнді келесі сатып алуларда ID қайта сұралмайды. Егер қате ID енгізген болсаңыз, \"🔄 ID ауыстыру\" батырмасын пайдаланыңыз.",
        "id_already_linked": "✅ Сіздің ID: #{cid} ({name})\n\nТөлем ақпараты төменде:",
        "id_unlinked": "🔄 ID ұмытылды. Келесі сатып алудың алдында ID қайта енгізу қажет болады.",
        "contact_admin_text": "💬 *Админмен байланыс*\n\nСұрағыңыз немесе мәселеңіз болса, тікелей жазыңыз:",
        "guide_caption": "📋 *SHATS CYBER — CODE сатып алу нұсқаулығы*\n\nЖоғарыдағы суретте барлық қадамдар көрсетілген: ID алу, ботқа өту, пакетті таңдау, төлем жасау және CODE-ты шотыңызға қабылдау.",
    },
    "ky": {
        "lang_name": "🇰🇬 Кыргыз",
        "welcome_named": "Салам, {name}! 👋\n\n*SHATS CYBER* кош келиңиз!",
        "choose_lang": "Тил тандаңыз:",
        "lang_set": "Тил: {lang_name}",
        "main_menu": "🏠 *Башкы меню*",
        "btn_buy_code": "⚡ CODE сатып алуу",
        "btn_buy_course": "📚 Курс сатып алуу",
        "btn_help": "❓ Жардам",
        "btn_change_lang": "🌐 Тил",
        "btn_back": "⬅️ Артка",
        "btn_main_menu": "🏠 Башкы",
        "btn_cancel": "❌ Жокко чыгаруу",
        "choose_code_pkg": "💎 *CODE пакет тандаңыз*",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курстар (1-10)*",
        "course_done": "✅ Бүттү",
        "course_clear": "🗑 Тазалоо",
        "selected_courses": "Тандалды: {n} · Жалпы: {total:,} CODE",
        "max_courses_reached": "Эң көп 10.",
        "no_paid_courses": "Акы курстар жок.",
        "no_courses_selected": "Курс жок.",
        "ask_id_for_code": "🆔 *ID жазыңыз*",
        "ask_id_for_course": "🆔 *ID жазыңыз*",
        "id_not_found": "❌ ID жок.",
        "id_invalid": "❌ ID туура эмес.",
        "id_confirmed": "✅ #{cid} — {name}",
        "show_payment_for_code": "💳 ⚡{code:,} CODE = {price:,} сом · #{cid}\nUZCARD: `{uzcard}`",
        "show_payment_for_course": "💳 📚{n} курс = ⚡{total:,} CODE · #{cid}\nUZCARD: `{uzcard}`",
        "awaiting_receipt": "📸 Чек сүрөтүн жибериңиз.",
        "receipt_received": "✅ Кабыл алынды!",
        "receipt_not_image": "⚠️ Сүрөт жибериңиз.",
        "purchase_approved_code": "✅ Бекитилди! ⚡{code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Бекитилди! {n} курс (#{cid})",
        "purchase_rejected": "❌ Четке кагылды: {reason}",
        "fund_insufficient": "⚠️ Казынада жетишсиз.",
        "help_text": "SHATS CYBER бот.",
        "unknown_message": "/start.",
        "operation_cancelled": "❌ Жокко чыгарылды.",
        "back_to_main": "🏠 Башкы.",
        "btn_buy_tariff": "🎓 Тарифти сатып алуу",
        "btn_guide": "📋 Колдонмо",
        "btn_contact_admin": "💬 Админ менен байланыш",
        "btn_change_id": "🔄 ID алмаштыруу",
        "choose_tariff_title": "🎓 *Тарифти тандаңыз*\n\nТөмөнкү тарифтердин бирин тандаңыз:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} сум)",
        "ask_id_for_tariff": "🆔 *Сайттагы ID номериңизди киргизиңиз*\n\nМисалы: 8520810",
        "show_payment_for_tariff": "💳 *Төлөм маалыматы*\n\n🎓 Тариф: {name}\n💰 Сумма: {price:,} сум\n🆔 ID: #{cid}\n\n*Карта номери:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Төлөмдү жасап, чектин скриншотун жибериңиз",
        "purchase_approved_tariff": "✅ *Сатып алуу ырасталды!*\n\n🎓 {name} тарифи иштетилди (30 күн)!\n🆔 ID: #{cid}\n\nРахмат!",
        "id_remembered": "✅ ID эсте сакталды: #{cid} ({name})\n\nЭми кийинки сатып алууларда ID кайра суралбайт. Ката ID киргизсеңиз, \"🔄 ID алмаштыруу\" баскычын колдонуңуз.",
        "id_already_linked": "✅ Сиздин ID: #{cid} ({name})\n\nТөлөм маалыматы төмөндө:",
        "id_unlinked": "🔄 ID унутулду. Кийинки сатып алуудан мурун ID кайра киргизүү керек болот.",
        "contact_admin_text": "💬 *Админ менен байланыш*\n\nСурооңуз же маселеңиз болсо, түз жазыңыз:",
        "guide_caption": "📋 *SHATS CYBER — CODE сатып алуу колдонмосу*\n\nЖогорудагы сүрөттө бардык кадамдар көрсөтүлгөн: ID алуу, ботко өтүү, пакетти тандоо, төлөм жасоо жана CODE-ду эсебиңизге кабыл алуу.",
    },
    "tj": {
        "lang_name": "🇹🇯 Тоҷикӣ",
        "welcome_named": "Салом, {name}! 👋\n\nБа *SHATS CYBER* хуш омадед!",
        "choose_lang": "Забонро интихоб кунед:",
        "lang_set": "Забон: {lang_name}",
        "main_menu": "🏠 *Менюи асосӣ*",
        "btn_buy_code": "⚡ CODE харидан",
        "btn_buy_course": "📚 Курс харидан",
        "btn_help": "❓ Кӯмак",
        "btn_change_lang": "🌐 Забон",
        "btn_back": "⬅️ Қафо",
        "btn_main_menu": "🏠 Меню",
        "btn_cancel": "❌ Бекор",
        "choose_code_pkg": "💎 *Пакети CODE интихоб кунед*",
        "code_pkg_format": "⚡ {code:,} CODE — {price:,} сом",
        "choose_courses_title": "📚 *Курсҳо (1-10)*",
        "course_done": "✅ Тайёр",
        "course_clear": "🗑 Тоза",
        "selected_courses": "Интихобшуда: {n} · Ҷамъ: {total:,} CODE",
        "max_courses_reached": "Максимум 10.",
        "no_paid_courses": "Курсҳои пулакӣ нест.",
        "no_courses_selected": "Курс интихоб нашуд.",
        "ask_id_for_code": "🆔 *ID-ро ворид кунед*",
        "ask_id_for_course": "🆔 *ID-ро ворид кунед*",
        "id_not_found": "❌ ID ёфт нашуд.",
        "id_invalid": "❌ ID нодуруст.",
        "id_confirmed": "✅ #{cid} — {name}",
        "show_payment_for_code": "💳 ⚡{code:,} CODE = {price:,} сом · #{cid}\nUZCARD: `{uzcard}`",
        "show_payment_for_course": "💳 📚{n} = ⚡{total:,} CODE · #{cid}\nUZCARD: `{uzcard}`",
        "awaiting_receipt": "📸 Расми чекро фиристед.",
        "receipt_received": "✅ Қабул шуд!",
        "receipt_not_image": "⚠️ Расм фиристед.",
        "purchase_approved_code": "✅ Тасдиқ шуд! ⚡{code:,} CODE (#{cid})",
        "purchase_approved_course": "✅ Тасдиқ шуд! {n} курс (#{cid})",
        "purchase_rejected": "❌ Рад шуд: {reason}",
        "fund_insufficient": "⚠️ Захира кам.",
        "help_text": "SHATS CYBER bot.",
        "unknown_message": "/start.",
        "operation_cancelled": "❌ Бекор.",
        "back_to_main": "🏠 Меню.",
        "btn_buy_tariff": "🎓 Харидани тариф",
        "btn_guide": "📋 Дастур",
        "btn_contact_admin": "💬 Тамос бо админ",
        "btn_change_id": "🔄 Иваз кардани ID",
        "choose_tariff_title": "🎓 *Тарифро интихоб кунед*\n\nЯке аз тарифҳои зеринро интихоб кунед:",
        "tariff_pkg_format": "{name} — {price} CODE ({sum:,} сум)",
        "ask_id_for_tariff": "🆔 *Рақами ID-и сомонаро ворид кунед*\n\nМасалан: 8520810",
        "show_payment_for_tariff": "💳 *Маълумоти пардохт*\n\n🎓 Тариф: {name}\n💰 Маблағ: {price:,} сум\n🆔 ID: #{cid}\n\n*Рақами корт:*\n💳 UZUM BANK: `{uzcard}`\n\n👇 Пардохт кунед ва скриншоти чекро фиристед",
        "purchase_approved_tariff": "✅ *Харид тасдиқ шуд!*\n\n🎓 Тарифи {name} фаъол шуд (30 рӯз)!\n🆔 ID: #{cid}\n\nРаҳмат!",
        "id_remembered": "✅ ID дар хотир монд: #{cid} ({name})\n\nАкнун дар харидҳои оянда ID дубора пурсида намешавад. Агар ID нодуруст ворид карда бошед, тугмаи \"🔄 Иваз кардани ID\"-ро истифода баред.",
        "id_already_linked": "✅ ID-и шумо: #{cid} ({name})\n\nМаълумоти пардохт дар поён:",
        "id_unlinked": "🔄 ID фаромӯш шуд. Пеш аз хариди оянда бояд ID-ро дубора ворид кунед.",
        "contact_admin_text": "💬 *Тамос бо админ*\n\nАгар савол ё мушкилот дошта бошед, мустақим нависед:",
        "guide_caption": "📋 *SHATS CYBER — Дастури харидани тангаҳои CODE*\n\nДар тасвири боло ҳамаи қадамҳо нишон дода шудаанд: гирифтани ID, гузариш ба бот, интихоби бастабандӣ, пардохт ва қабули CODE ба ҳисоби шумо.",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    """Tarjima olish, fallback uz ga."""
    msg = TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))
    try:
        return msg.format(**kwargs)
    except (KeyError, IndexError):
        return msg


# =================================================================
# DATABASE HELPERS
# =================================================================
def db_conn():
    """MUHIM (tuzatilgan xato): db.py'dagi bilan BIR XIL WAL rejimi va
    busy_timeout — bot va sayt bir vaqtda bitta faylga yozganda
    'database is locked' xatosi chiqmasligi uchun (batafsil izoh
    db.py'dagi get_db() funksiyasida).

    POSTGRES: DATABASE_URL o'rnatilgan bo'lsa, db.py'ning
    new_connection() orqali xuddi web-sayt ishlatadigan bazaning
    o'ziga ulanadi (endi ikkalasi BIR XIL Postgres'ga yozadi, ikkita
    alohida SQLite fayli emas)."""
    from db import new_connection
    return new_connection(DB_PATH)


def _table_exists(c, name):
    return c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _ensure_bot_schema():
    """Bot mustaqil jarayon sifatida (asosiy Flask ilovasidan alohida)
    ishga tushishi mumkin — agar sayt hali biron marta ishga tushmagan
    bo'lsa (yoki bazadan bu jadval biron sababdan yo'qolib qolgan bo'lsa),
    kerakli JADVALLARNING O'ZI ham, ustunlar ham yo'q bo'lishi mumkin.

    MUHIM (tuzatilgan JIDDIY XATO): avval bu funksiya JADVAL ALLAQACHON
    BOR deb FARAZ QILAR edi — faqat ALTER TABLE (ustun qo'shish) qilar,
    lekin agar telegram_users jadvalining O'ZI umuman mavjud bo'lmasa —
    ALTER TABLE xato berardi, bu xato "e'tiborsiz qoldirilardi" (log
    qilinib, davom etilardi), va NATIJADA BOT /start BUYRUG'IGA HAM
    JAVOB BEROLMAS EDI — chunki get_or_create_tg_user() har safar
    "no such table: telegram_users" xatosiga uchrardi. Endi bu funksiya
    AVVAL jadvalning O'ZI bor-yo'qligini tekshiradi, yo'q bo'lsa TO'LIQ
    sxema bilan yaratadi — shundan keyingina ustunlarni tekshiradi."""
    try:
        conn = db_conn(); c = conn.cursor()

        table_exists = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='telegram_users'"
        ).fetchone()
        if not table_exists:
            c.execute("""
                CREATE TABLE telegram_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL UNIQUE,
                    first_name TEXT DEFAULT '',
                    last_name TEXT DEFAULT '',
                    username TEXT DEFAULT '',
                    language TEXT NOT NULL DEFAULT 'uz',
                    state TEXT NOT NULL DEFAULT 'main',
                    state_data TEXT DEFAULT '',
                    linked_user_id INTEGER DEFAULT NULL,
                    linked_custom_id TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                    last_expiry_notice_at TEXT DEFAULT NULL,
                    last_inactivity_notice_at TEXT DEFAULT NULL,
                    last_tickets_notice_at TEXT DEFAULT NULL,
                    last_email_notice_at TEXT DEFAULT NULL,
                    last_collection_notice_at TEXT DEFAULT NULL
                )
            """)
            c.execute("CREATE INDEX idx_tg_chat ON telegram_users(chat_id)")
            log.info("telegram_users jadvali BUTUNLAY YARATILDI (avval mavjud emas edi)")

        c.execute("PRAGMA table_info(telegram_users)")
        cols = [r[1] for r in c.fetchall()]
        for col, ddl in [
            ("linked_user_id", "ALTER TABLE telegram_users ADD COLUMN linked_user_id INTEGER DEFAULT NULL"),
            ("linked_custom_id", "ALTER TABLE telegram_users ADD COLUMN linked_custom_id TEXT DEFAULT NULL"),
            ("last_expiry_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_expiry_notice_at TEXT DEFAULT NULL"),
            ("last_inactivity_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_inactivity_notice_at TEXT DEFAULT NULL"),
            ("last_tickets_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_tickets_notice_at TEXT DEFAULT NULL"),
            ("last_email_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_email_notice_at TEXT DEFAULT NULL"),
            ("last_collection_notice_at", "ALTER TABLE telegram_users ADD COLUMN last_collection_notice_at TEXT DEFAULT NULL"),
        ]:
            if col not in cols:
                c.execute(ddl)

        bpr_exists = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bot_purchase_requests'"
        ).fetchone()
        if not bpr_exists:
            c.execute("""
                CREATE TABLE bot_purchase_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    tg_user_id INTEGER,
                    request_type TEXT NOT NULL,
                    code_amount INTEGER DEFAULT 0,
                    price_uzs INTEGER DEFAULT 0,
                    courses_json TEXT DEFAULT '',
                    target_custom_id TEXT NOT NULL,
                    site_user_id INTEGER DEFAULT NULL,
                    receipt_file_id TEXT DEFAULT NULL,
                    receipt_file_path TEXT DEFAULT NULL,
                    source TEXT NOT NULL DEFAULT 'bot',
                    status TEXT NOT NULL DEFAULT 'pending',
                    admin_note TEXT DEFAULT '',
                    reviewed_by INTEGER DEFAULT NULL,
                    reviewed_at TEXT DEFAULT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    plan TEXT DEFAULT ''
                )
            """)
            log.info("bot_purchase_requests jadvali BUTUNLAY YARATILDI (avval mavjud emas edi)")

        c.execute("PRAGMA table_info(bot_purchase_requests)")
        cols2 = [r[1] for r in c.fetchall()]
        if "plan" not in cols2:
            c.execute("ALTER TABLE bot_purchase_requests ADD COLUMN plan TEXT DEFAULT ''")

        # MUHIM (yana bir JIDDIY XATO, tuzatildi): bot va sayt (app.py)
        # AYRIM-AYRIM jarayon/xizmat sifatida joylashtirilishi mumkin
        # (masalan alohida "Deploy" — buni haqiqiy log skrinshotida
        # ko'rdik: "no such table: id_reservations"). Agar bot jarayoni
        # app.py'ning migratsiyalari ULGURMAY yoki UMUMAN ishga
        # tushmasdan ishga tushsa — bot ishlatadigan, lekin FAQAT
        # app.py migratsiyalarida yaratiladigan jadvallar (id_reservations,
        # bot_state, friend_request_reminders, promo_codes,
        # promo_code_uses, friendships) yo'q bo'lib qolishi mumkin edi.
        # Endi BOTNING O'ZI ham bularni xavfsiz, mustaqil ravishda
        # yaratadi — qaysi xizmat birinchi ishga tushishidan qat'iy
        # nazar, bot HECH QACHON shu sabab bilan yiqilmaydi.
        if not _table_exists(c, "id_reservations"):
            c.execute("""
                CREATE TABLE id_reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    custom_id TEXT NOT NULL,
                    price INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    reserved_at TEXT NOT NULL DEFAULT (datetime('now')),
                    expires_at TEXT NOT NULL
                )
            """)
            c.execute("CREATE INDEX idx_id_reservations_user ON id_reservations(user_id, status)")
            c.execute("CREATE INDEX idx_id_reservations_custom ON id_reservations(custom_id, status)")
            log.info("id_reservations jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        if not _table_exists(c, "bot_state"):
            c.execute("""
                CREATE TABLE bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            log.info("bot_state jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        if not _table_exists(c, "friend_request_reminders"):
            c.execute("""
                CREATE TABLE friend_request_reminders (
                    friendship_rowid INTEGER PRIMARY KEY,
                    reminded_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            log.info("friend_request_reminders jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        if not _table_exists(c, "friendships"):
            c.execute("""
                CREATE TABLE friendships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_a_id INTEGER NOT NULL,
                    user_b_id INTEGER NOT NULL,
                    requested_by INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    responded_at TEXT DEFAULT NULL
                )
            """)
            log.info("friendships jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        if not _table_exists(c, "promo_codes"):
            c.execute("""
                CREATE TABLE promo_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT NOT NULL UNIQUE,
                    discount_type TEXT NOT NULL DEFAULT 'bonus',
                    discount_value INTEGER DEFAULT 0,
                    bonus_code_amount INTEGER DEFAULT 0,
                    max_uses INTEGER DEFAULT 0,
                    used_count INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    expires_at TEXT DEFAULT NULL,
                    created_by INTEGER,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            log.info("promo_codes jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        if not _table_exists(c, "promo_code_uses"):
            c.execute("""
                CREATE TABLE promo_code_uses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promo_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    used_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            log.info("promo_code_uses jadvali bot tomonidan yaratildi (avval mavjud emas edi)")

        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"_ensure_bot_schema xatolik: {e}")


def get_or_create_tg_user(chat_id, first_name="", last_name="", username=""):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT * FROM telegram_users WHERE chat_id=?", (chat_id,)).fetchone()
    if row:
        c.execute("UPDATE telegram_users SET last_seen_at=datetime('now') WHERE id=?", (row["id"],))
        conn.commit()
        result = dict(row)
        conn.close()
        return result
    c.execute(
        "INSERT INTO telegram_users (chat_id, first_name, last_name, username) VALUES (?,?,?,?)",
        (chat_id, first_name or "", last_name or "", username or "")
    )
    conn.commit()
    tg_id = c.lastrowid
    row = c.execute("SELECT * FROM telegram_users WHERE id=?", (tg_id,)).fetchone()
    conn.close()
    return dict(row)


def set_tg_state(chat_id, state, state_data=None):
    conn = db_conn(); c = conn.cursor()
    data_json = json.dumps(state_data) if state_data is not None else ""
    c.execute("UPDATE telegram_users SET state=?, state_data=? WHERE chat_id=?",
              (state, data_json, chat_id))
    conn.commit(); conn.close()


def get_tg_state(chat_id):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT state, state_data FROM telegram_users WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    if not row: return ("main", {})
    data = {}
    try:
        if row["state_data"]: data = json.loads(row["state_data"])
    except Exception: pass
    return (row["state"], data)


def set_tg_language(chat_id, lang):
    conn = db_conn(); c = conn.cursor()
    c.execute("UPDATE telegram_users SET language=? WHERE chat_id=?", (lang, chat_id))
    conn.commit(); conn.close()


def find_site_user_by_custom_id(custom_id):
    """
    Foydalanuvchini saytda ko'rsatilgan ID raqami orqali topadi.

    MUHIM (tuzatilgan xato): saytda foydalanuvchiga ID sifatida
    `custom_id or id` ko'rsatiladi (qarang: dashboard.html) — ya'ni
    custom_id ni hali sotib olmagan/o'rnatmagan (aksariyat) foydalanuvchilar
    o'zining oddiy `users.id` (asosiy kalit) raqamini ko'radi va aynan shuni
    botga kiritadi. Avvalgi kod FAQAT custom_id ustunidan qidirar edi —
    shu sabab botda "ID topilmadi" xatosi aksariyat foydalanuvchilar uchun
    doimiy chiqar edi. Endi ikkalasi ham (avval custom_id, keyin oddiy id)
    tekshiriladi.
    """
    conn = db_conn(); c = conn.cursor()
    cid_str = str(custom_id).strip()

    row = c.execute(
        "SELECT id, ism, familiya, custom_id, is_blocked FROM users WHERE custom_id=?",
        (cid_str,)
    ).fetchone()

    if not row and cid_str.isdigit():
        row = c.execute(
            "SELECT id, ism, familiya, custom_id, is_blocked FROM users WHERE id=?",
            (int(cid_str),)
        ).fetchone()

    conn.close()
    return dict(row) if row else None


def find_site_user_by_id(user_id):
    """Sayt foydalanuvchisini uning ICHKI (users.id) raqami orqali topadi
    — email bilan birga (Profil ulash — email tekshiruvi uchun kerak)."""
    if not user_id:
        return None
    conn = db_conn(); c = conn.cursor()
    row = c.execute(
        "SELECT id, ism, familiya, custom_id, email, is_blocked FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def build_leaderboard_text(lang="uz"):
    """Bot orqali 'Reyting' tugmasi bosilganda TOP-10 ro'yxatini matn
    ko'rinishida qaytaradi."""
    try:
        conn = db_conn(); c = conn.cursor()
        rows = c.execute(
            """SELECT familiya, ism, level, xp FROM users
               WHERE role='student' ORDER BY xp DESC LIMIT 10"""
        ).fetchall()
        conn.close()
        if not rows:
            return t(lang, "leaderboard_title") + "Hozircha ma'lumot yo'q."
        medals = ["🥇", "🥈", "🥉"] + ["▪️"] * 7
        lines = [t(lang, "leaderboard_title")]
        for i, r in enumerate(rows):
            lines.append(f"{medals[i]} {r['familiya']} {r['ism']} — Lvl {r['level']} ({r['xp']:,} XP)".replace(",", " "))
        return "\n".join(lines)
    except Exception as e:
        log.exception(f"Leaderboard matn xatosi: {e}")
        return "⚠️ Reytingni yuklab bo'lmadi."


def get_paid_courses():
    conn = db_conn(); c = conn.cursor()
    rows = c.execute(
        """SELECT c.id, c.title, c.subtitle, c.code_price, d.name_uz as direction_name
           FROM courses c JOIN directions d ON d.id = c.direction_id
           WHERE c.is_active=1 AND c.code_price > 0
           ORDER BY d.sort_order, c.id"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_purchase_request(chat_id, tg_user_id, request_type,
                            code_amount=0, price_uzs=0, courses_json="", plan="",
                            target_custom_id="", site_user_id=None, receipt_file_id=None):
    conn = db_conn(); c = conn.cursor()
    c.execute(
        """INSERT INTO bot_purchase_requests
           (chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json, plan,
            target_custom_id, site_user_id, receipt_file_id, status)
           VALUES (?,?,?,?,?,?,?,?,?,?,'pending')""",
        (chat_id, tg_user_id, request_type, code_amount, price_uzs, courses_json, plan,
         target_custom_id, site_user_id, receipt_file_id)
    )
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def link_site_user(chat_id, site_user_id, custom_id):
    """Foydalanuvchi ID'sini birinchi marta tasdiqlagach, DOIMIY ravishda
    saqlaydi — shu orqali keyingi xaridlarda bot ID'ni QAYTA SO'RAMAYDI."""
    conn = db_conn(); c = conn.cursor()
    c.execute(
        "UPDATE telegram_users SET linked_user_id=?, linked_custom_id=? WHERE chat_id=?",
        (site_user_id, custom_id, chat_id)
    )
    conn.commit()
    conn.close()


def unlink_site_user(chat_id):
    """Foydalanuvchi ID'sini 'unutish' — masalan noto'g'ri ID bog'langan bo'lsa."""
    conn = db_conn(); c = conn.cursor()
    c.execute(
        "UPDATE telegram_users SET linked_user_id=NULL, linked_custom_id=NULL WHERE chat_id=?",
        (chat_id,)
    )
    conn.commit()
    conn.close()


_DEFAULT_TARIFF_PRICES_UZS = {"pro": 90_000, "cyber_pro": 150_000, "vip": 570_000, "hacker": 77_000}


def _bot_buy_tariff_with_code(user_id: int, plan_key: str, cost: int) -> tuple[bool, str]:
    """MUHIM: coins.py'dagi buy_*_with_coins() funksiyalari db.py'ning
    Flask-bog'liq query_one/execute'idan foydalanadi (Flask 'g' obyekti
    kerak). Bot esa Flask kontekstisiz, mustaqil jarayon — shuning
    uchun ularni to'g'ridan-to'g'ri chaqirish "Working outside of
    application context" xatosi bilan yiqilib qolardi (buni sinab
    tasdiqladim). Shu sabab bu yerda BIR XIL mantiq botning o'z
    db_conn() (oddiy sqlite3) orqali mustaqil qayta yozilgan."""
    conn = db_conn(); c = conn.cursor()
    try:
        user = c.execute("SELECT plan, code_balance FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return False, "Foydalanuvchi topilmadi."
        plan_rank = {"free": 0, "pro": 1, "cyber_pro": 2, "vip": 3, "hacker": 3}
        if plan_key in ("pro",) and user["plan"] in ("pro", "cyber_pro", "vip"):
            return False, "Siz allaqachon Pro yoki yuqori versiya foydalanuvchisiz."
        if plan_key in ("cyber_pro",) and user["plan"] in ("cyber_pro", "vip"):
            return False, "Siz allaqachon Cyber Pro yoki yuqori versiya foydalanuvchisiz."
        if plan_key in ("vip",) and user["plan"] == "vip":
            return False, "Siz allaqachon SHATS CYBER PRO foydalanuvchisiz."
        if plan_key in ("hacker",) and user["plan"] == "hacker":
            return False, "Siz allaqachon MAXSUS versiya foydalanuvchisiz."
        if user["code_balance"] < cost:
            return False, f"Yetarli CODE yo'q. Kerak: {cost}, mavjud: {user['code_balance']}"

        import datetime as _dt
        expires_at = (_dt.datetime.now() + _dt.timedelta(days=30)).isoformat()

        # Atomik: yuqoridagi tekshiruv faqat tezkor rad javob uchun — haqiqiy
        # himoya shu yerda, bitta UPDATE...WHERE bilan (coins.py'dagi
        # spend_coins() bilan bir xil tuzatish).
        row = c.execute(
            "UPDATE users SET code_balance = code_balance - ? WHERE id=? AND code_balance >= ? RETURNING code_balance",
            (cost, user_id, cost)
        ).fetchone()
        if not row:
            conn.rollback()
            return False, f"Yetarli CODE yo'q. Kerak: {cost}."
        c.execute("INSERT INTO code_transactions (user_id, amount, reason) VALUES (?,?,?)",
                  (user_id, -cost, f"buy_{plan_key}_bot"))
        c.execute("UPDATE users SET plan=?, plan_expires_at=? WHERE id=?", (plan_key, expires_at, user_id))
        c.execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (cost,))
        c.execute("INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
                  (cost, f"buy_{plan_key}_bot", user_id))
        conn.commit()
        return True, f"Tarif faollashtirildi! 1 oy amal qiladi ({expires_at[:10]} gacha)."
    except Exception as e:
        conn.rollback()
        log.error(f"_bot_buy_tariff_with_code xato: {e}")
        return False, "Texnik xatolik yuz berdi. CODE yechilmadi, qaytadan urinib ko'ring."
    finally:
        conn.close()


def _bot_buy_course_with_code(user_id: int, course_id: int, cost: int) -> tuple[bool, str]:
    """Yuqoridagi bilan bir xil sabab — kurs sotib olishni ham botning
    o'z mustaqil ulanishi orqali amalga oshiramiz."""
    conn = db_conn(); c = conn.cursor()
    try:
        course = c.execute("SELECT title FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            return False, "Kurs topilmadi."
        existing = c.execute("SELECT id FROM enrollments WHERE user_id=? AND course_id=?",
                             (user_id, course_id)).fetchone()
        if existing:
            return False, "Siz bu kursga allaqachon yozilgansiz."
        user = c.execute("SELECT code_balance FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or user["code_balance"] < cost:
            return False, f"Yetarli CODE yo'q. Kerak: {cost}."

        # Atomik: yuqoridagi tekshiruv faqat tezkor rad javob uchun — haqiqiy
        # himoya shu yerda, bitta UPDATE...WHERE bilan (coins.py'dagi
        # spend_coins() bilan bir xil tuzatish: ikkita bir vaqtdagi so'rov
        # balansni manfiyga tushirib qo'ymasligi uchun).
        row = c.execute(
            "UPDATE users SET code_balance = code_balance - ? WHERE id=? AND code_balance >= ? RETURNING code_balance",
            (cost, user_id, cost)
        ).fetchone()
        if not row:
            conn.rollback()
            return False, f"Yetarli CODE yo'q. Kerak: {cost}."
        c.execute("INSERT INTO code_transactions (user_id, amount, reason) VALUES (?,?,?)",
                  (user_id, -cost, "buy_course_bot"))
        c.execute("INSERT OR IGNORE INTO enrollments (user_id, course_id, progress_percent) VALUES (?,?,0)",
                  (user_id, course_id))
        c.execute("UPDATE treasury_fund SET balance = balance + ?, updated_at = datetime('now') WHERE id=1", (cost,))
        c.execute("INSERT INTO treasury_fund_log (direction, amount, reason, user_id) VALUES ('in', ?, ?, ?)",
                  (cost, "buy_course_bot", user_id))
        conn.commit()
        return True, f"'{course['title']}' kursiga yozildingiz! ({cost} CODE)"
    except Exception as e:
        conn.rollback()
        log.error(f"_bot_buy_course_with_code xato: {e}")
        return False, "Texnik xatolik yuz berdi. CODE yechilmadi, qaytadan urinib ko'ring."
    finally:
        conn.close()


def get_bot_code_tariff_prices():
    """Botda CODE bilan sotib olish uchun — SAYTDAGI (aksiya) narxdan yana
    1 CODE kam, chunki bot orqali CODE bilan sotib olish qo'shimcha
    chegirmali. Masalan sayt narxi PRO=2 bo'lsa, botda PRO=1 bo'ladi."""
    conn = db_conn(); c = conn.cursor()
    key_map = {"pro": "pro_price_code", "cyber_pro": "cyber_pro_price_code",
               "vip": "vip_price_code", "hacker": "hacker_price_code"}
    prices = {}
    for plan_key, pricing_key in key_map.items():
        row = c.execute("SELECT value FROM pricing_settings WHERE key=?", (pricing_key,)).fetchone()
        site_price = int(row[0]) if row else 1
        prices[plan_key] = max(1, site_price - 1)  # yana 1 CODE arzon, lekin kamida 1
    conn.close()
    return prices


def get_tariff_prices():
    """
    Har bir tarifning HAQIQIY PUL (so'm) narxini bazadan oladi.

    MUHIM: bu narx endi CODE kursidan (masalan 'narx_code x 10 000')
    HISOBLANMAYDI — har bir tarif uchun ALOHIDA, aniq belgilangan so'm
    qiymati ishlatiladi (pricing_settings: {plan}_price_uzs). Shunga
    ko'ra HackerLab boshqa uchtasi kabi formulaga to'g'ri kelmasligi
    mumkin — bu kutilgan holat (aksiya/maxsus narx bo'lishi mumkin).
    Admin bu narxlarni narxlar panelidan istalgan vaqt o'zgartira oladi.
    """
    conn = db_conn(); c = conn.cursor()
    prices = {}
    for plan_key, _ in TARIFF_PLANS:
        row = c.execute("SELECT value FROM pricing_settings WHERE key=?",
                        (f"bot_tariff_price_{plan_key}",)).fetchone()
        prices[plan_key] = int(row[0]) if row else _DEFAULT_TARIFF_PRICES_UZS.get(plan_key, 0)
    conn.close()
    return prices


def get_code_to_som_rate():
    """1 CODE necha so'm turishini bazadan oladi (admin/g'azna o'zgartirishi mumkin)."""
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT value FROM pricing_settings WHERE key='code_to_som_rate'").fetchone()
    conn.close()
    return int(row[0]) if row else 10_000


# =================================================================
# TELEGRAM API
# =================================================================
def tg_request(method, **payload):
    try:
        r = requests.post(f"{API_BASE}/{method}", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        log.error(f"tg_request error: {e}")
        return {"ok": False, "error": str(e)}


def tg_send_photo(chat_id, photo_path, caption="", reply_markup=None, parse_mode="Markdown"):
    if not os.path.exists(photo_path):
        return tg_send_message(chat_id, caption, reply_markup=reply_markup, parse_mode=parse_mode)
    try:
        with open(photo_path, "rb") as f:
            data = {"chat_id": str(chat_id), "caption": caption, "parse_mode": parse_mode}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            r = requests.post(f"{API_BASE}/sendPhoto", data=data, files={"photo": f}, timeout=60)
            result = r.json()
        if not result.get("ok") and parse_mode:
            # Xuddi tg_send_message'dagi kabi — caption Markdown'ni buzsa,
            # formatlashsiz qayta yuboramiz (rasm hech bo'lmasa yetib borsin).
            log.warning(f"Rasm captioni Markdown xatosi, oddiy matn bilan qayta urinilmoqda: {result}")
            with open(photo_path, "rb") as f:
                data.pop("parse_mode", None)
                r = requests.post(f"{API_BASE}/sendPhoto", data=data, files={"photo": f}, timeout=60)
                result = r.json()
        return result
    except Exception as e:
        log.error(f"tg_send_photo error: {e}")
        return {"ok": False}


def tg_send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup: payload["reply_markup"] = reply_markup
    result = tg_request("sendMessage", **payload)
    if not result.get("ok") and parse_mode:
        # XAVFSIZLIK/BARQARORLIK: agar matnda Markdown'ni buzadigan belgilar
        # bo'lsa (masalan foydalanuvchi ismida "_", "*", "[" kabi belgilar),
        # Telegram "can't parse entities" xatosi bilan xabarni RAD ETADI va
        # foydalanuvchi HECH NARSA ko'rmaydi (bot "qotib qolgandek" tuyuladi).
        # Shu sabab formatlashsiz (plain text) qayta yuborishga urinamiz —
        # shunda xabar HAR DOIM foydalanuvchiga yetib boradi.
        log.warning(f"Markdown parse xatosi, plain text bilan qayta urinilmoqda: {result}")
        payload.pop("parse_mode", None)
        result = tg_request("sendMessage", **payload)
    return result


def tg_answer_callback(callback_id, text="", show_alert=False):
    return tg_request("answerCallbackQuery", callback_query_id=callback_id, text=text, show_alert=show_alert)


# =================================================================
# KEYBOARDS
# =================================================================
def kb_languages():
    return {"inline_keyboard": [
        [{"text": TEXTS["uz"]["lang_name"], "callback_data": "lang:uz"},
         {"text": TEXTS["ru"]["lang_name"], "callback_data": "lang:ru"}],
        [{"text": TEXTS["en"]["lang_name"], "callback_data": "lang:en"},
         {"text": TEXTS["tr"]["lang_name"], "callback_data": "lang:tr"}],
        [{"text": TEXTS["kk"]["lang_name"], "callback_data": "lang:kk"},
         {"text": TEXTS["ky"]["lang_name"], "callback_data": "lang:ky"}],
        [{"text": TEXTS["tj"]["lang_name"], "callback_data": "lang:tj"}],
    ]}


SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://cyber.shats.uz").strip()


def kb_main_menu(lang):
    kb = {"inline_keyboard": [
        [{"text": "👤 Mening profilim", "callback_data": "menu:my_profile"}],
    ]}
    # Web App tugmasi — FAQAT https:// manzil bilan ishlaydi (Telegram
    # cheklovi). Agar sayt hali HTTP bo'lsa, bu tugma tushib qoladi va
    # o'rniga oddiy 'Mening profilim' xabar-tugmasi ishlatiladi (yuqorida) —
    # bot HECH QACHON buzilmaydi, faqat Mini App vaqtincha mavjud bo'lmaydi.
    if SITE_BASE_URL.startswith("https://"):
        kb["inline_keyboard"].insert(0, [
            {"text": "🚀 Ilovani ochish", "web_app": {"url": f"{SITE_BASE_URL}/webapp"}}
        ])
    kb["inline_keyboard"].extend([
        [{"text": t(lang, "btn_buy_code"), "callback_data": "menu:code"},
         {"text": t(lang, "btn_buy_tariff"), "callback_data": "menu:tariff"}],
        [{"text": t(lang, "btn_buy_course"), "callback_data": "menu:course"},
         {"text": "🎁 Bonus kod", "callback_data": "menu:promo"}],
        [{"text": t(lang, "btn_link_profile"), "callback_data": "menu:link_profile"},
         {"text": t(lang, "btn_leaderboard"), "callback_data": "menu:leaderboard"}],
        [{"text": t(lang, "btn_guide"), "callback_data": "menu:guide"}],
        [{"text": t(lang, "btn_help"), "callback_data": "menu:help"},
         {"text": t(lang, "btn_change_lang"), "callback_data": "menu:lang"}],
        [{"text": t(lang, "btn_contact_admin"), "url": f"https://t.me/{ADMIN_TELEGRAM_USERNAME}"}],
    ])
    return kb


def kb_tariffs(lang):
    """YANGI: endi har bir tarif uchun IKKITA yo'l bor —
    1) 💰 So'mda (chek yuklab, G'azna tasdiqlashi kerak — eski usul)
    2) ⚡ CODE bilan (DARHOL, admin tasdig'isiz, va SAYTDAGIDAN HAM
       ARZONROQ — botga xos qo'shimcha chegirma)."""
    prices_uzs = get_tariff_prices()
    code_prices = get_bot_code_tariff_prices()
    rows = []
    for plan_key, label in TARIFF_PLANS:
        price_uzs = prices_uzs.get(plan_key, 0)
        code_price = code_prices.get(plan_key, 0)
        rows.append([{
            "text": f"{label} — 💰 {price_uzs:,} so'm",
            "callback_data": f"tariff:{plan_key}:{price_uzs}"
        }])
        rows.append([{
            "text": f"{label} — ⚡ {code_price} CODE (arzon!)",
            "callback_data": f"tariffcode:{plan_key}:{code_price}"
        }])
    rows.append([{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def kb_code_packages(lang):
    rows = []
    row = []
    for code, price in get_code_packages():
        row.append({"text": t(lang, "code_pkg_format", code=code, price=price),
                    "callback_data": f"code:{code}:{price}"})
        if len(row) == 1:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def kb_courses(lang, courses, selected_ids):
    """Kurslar ro'yxati, har bir kurs uchun toggle tugmasi."""
    rows = []
    for course in courses[:50]:  # cheklov
        marker = "✅" if course["id"] in selected_ids else "🔲"
        title = course["title"]
        if len(title) > 35: title = title[:33] + "..."
        rows.append([{
            "text": f"{marker} {title} — ⚡{course['code_price']:,}",
            "callback_data": f"course:{course['id']}"
        }])
    rows.append([
        {"text": t(lang, "course_clear"), "callback_data": "course_action:clear"},
        {"text": t(lang, "course_done"), "callback_data": "course_action:done"},
    ])
    rows.append([{"text": "⚡ CODE bilan DARHOL sotib olish (arzon!)", "callback_data": "course_action:buycode"}])
    rows.append([{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}])
    return {"inline_keyboard": rows}


def kb_cancel_back(lang):
    return {"inline_keyboard": [
        [{"text": t(lang, "btn_cancel"), "callback_data": "menu:main"}],
    ]}


def kb_help_menu(lang):
    return {"inline_keyboard": [
        [{"text": t(lang, "btn_change_id"), "callback_data": "menu:change_id"}],
        [{"text": t(lang, "btn_contact_admin"), "url": f"https://t.me/{ADMIN_TELEGRAM_USERNAME}"}],
        [{"text": t(lang, "btn_main_menu"), "callback_data": "menu:main"}],
    ]}


# =================================================================
# HANDLERS
# =================================================================
def handle_start(chat_id, user):
    tg_user = get_or_create_tg_user(
        chat_id,
        first_name=user.get("first_name", ""),
        last_name=user.get("last_name", ""),
        username=user.get("username", "")
    )
    name = user.get("first_name") or user.get("username") or "Foydalanuvchi"
    lang = tg_user.get("language", "uz")
    set_tg_state(chat_id, "main", {})

    # Salomlashish — til tanlash bosqichi YO'Q, darhol asosiy menyu chiqadi
    welcome = t(lang, "welcome_named", name=name)
    tg_send_message(chat_id, welcome)
    show_main_menu(chat_id, lang)


def build_profile_snapshot(chat_id) -> str:
    """Profili ulangan foydalanuvchi uchun — balans, tarif, daraja va
    ID'sini bitta qisqa xabar sifatida tayyorlaydi. Ulanmagan bo'lsa
    bo'sh satr qaytaradi (asosiy menyu shunchaki oddiy ko'rinishda qoladi)."""
    tg_user = get_or_create_tg_user(chat_id)
    if not tg_user.get("linked_user_id"):
        return ""
    conn = db_conn(); c = conn.cursor()
    u = c.execute(
        "SELECT familiya, ism, custom_id, code_balance, plan, level, xp FROM users WHERE id=?",
        (tg_user["linked_user_id"],)
    ).fetchone()
    conn.close()
    if not u:
        return ""
    plan_labels = {"pro": "PRO", "cyber_pro": "CYBER PRO", "vip": "VIP", "hacker": "MAXSUS", "admin": "ADMIN"}
    plan_text = plan_labels.get(u["plan"], "FREE")
    return (f"👤 *{u['familiya']} {u['ism']}* (#{u['custom_id']})\n"
            f"⚡ {u['code_balance']:,} CODE · 🏅 {plan_text} · Lvl {u['level']} ({u['xp']:,} XP)\n\n").replace(",", " ")


def show_main_menu(chat_id, lang):
    set_tg_state(chat_id, "main", {})
    snapshot = build_profile_snapshot(chat_id)
    tg_send_message(chat_id, snapshot + t(lang, "main_menu"), reply_markup=kb_main_menu(lang))


def _show_payment_and_wait_receipt(chat_id, lang, tg_user, kind, state_data):
    """ID allaqachon eslab qolingan bo'lsa (yoki hozirgina tasdiqlangan bo'lsa),
    to'lov ma'lumotini ko'rsatib, to'g'ridan-to'g'ri chek kutishga o'tadi —
    ID qayta so'ralmaydi."""
    cid = tg_user["linked_custom_id"]
    state_data["custom_id"] = cid
    state_data["site_user_id"] = tg_user["linked_user_id"]
    if kind == "code":
        msg = t(lang, "show_payment_for_code",
                code=state_data["code"], price=state_data["price"], cid=cid,
                uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
        set_tg_state(chat_id, "awaiting_receipt_code", state_data)
    elif kind == "tariff":
        plan_labels = dict(TARIFF_PLANS)
        msg = t(lang, "show_payment_for_tariff",
                name=plan_labels.get(state_data["plan"], state_data["plan"]),
                price=state_data["price"], cid=cid,
                uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
        set_tg_state(chat_id, "awaiting_receipt_tariff", state_data)
    else:  # course
        msg = t(lang, "show_payment_for_course",
                n=len(state_data["courses"]), total=state_data["total"], cid=cid,
                uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
        set_tg_state(chat_id, "awaiting_receipt_course", state_data)
    tg_send_message(chat_id, t(lang, "id_already_linked", cid=cid, name=""))
    tg_send_message(chat_id, msg, reply_markup=kb_cancel_back(lang))
    tg_send_message(chat_id, t(lang, "awaiting_receipt"))


def handle_code_menu(chat_id, lang):
    set_tg_state(chat_id, "choose_code", {})
    tg_send_photo(chat_id, CODE_TANGA_IMAGE, caption=t(lang, "choose_code_pkg"),
                  reply_markup=kb_code_packages(lang))


def handle_tariff_menu(chat_id, lang):
    set_tg_state(chat_id, "choose_tariff", {})
    tg_send_message(chat_id, t(lang, "choose_tariff_title"),
                     reply_markup=kb_tariffs(lang))


def handle_course_menu(chat_id, lang):
    courses = get_paid_courses()
    if not courses:
        tg_send_message(chat_id, t(lang, "no_paid_courses"), reply_markup=kb_main_menu(lang))
        return
    set_tg_state(chat_id, "choose_courses", {"selected": [], "courses": [c["id"] for c in courses]})
    tg_send_message(chat_id, t(lang, "choose_courses_title"), reply_markup=kb_courses(lang, courses, []))


def handle_callback(callback):
    callback_id = callback["id"]
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")
    user_info = callback.get("from", {})
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)

    tg_answer_callback(callback_id)

    if data.startswith("lang:"):
        new_lang = data.split(":", 1)[1]
        if new_lang in TEXTS:
            set_tg_language(chat_id, new_lang)
            lang_display_name = TEXTS[new_lang]["lang_name"]
            tg_send_message(chat_id, t(new_lang, "lang_set", lang_name=lang_display_name))
            show_main_menu(chat_id, new_lang)
        return

    if data == "menu:main":
        show_main_menu(chat_id, lang); return
    if data == "menu:code":
        handle_code_menu(chat_id, lang); return
    if data == "menu:tariff":
        handle_tariff_menu(chat_id, lang); return
    if data == "menu:course":
        handle_course_menu(chat_id, lang); return
    if data == "menu:lang":
        tg_send_message(chat_id, t(lang, "choose_lang"), reply_markup=kb_languages())
        return
    if data == "menu:guide":
        tg_send_photo(chat_id, INSTRUCTIONS_IMAGE, caption=t(lang, "guide_caption"),
                     reply_markup=kb_main_menu(lang))
        return
    if data == "menu:link_profile":
        set_tg_state(chat_id, "awaiting_link_id", {})
        tg_send_message(chat_id, t(lang, "ask_link_id"), reply_markup=kb_cancel_back(lang))
        return
    if data == "menu:my_profile":
        snapshot = build_profile_snapshot(chat_id)
        if not snapshot:
            tg_send_message(chat_id, "🔗 Avval profilingizni ulang.", reply_markup=kb_main_menu(lang))
        else:
            tg_send_message(chat_id, snapshot.strip(), parse_mode="Markdown", reply_markup=kb_main_menu(lang))
        return
    if data == "menu:promo":
        set_tg_state(chat_id, "awaiting_promo_code", {})
        tg_send_message(chat_id, "🎁 Bonus (promo) kodni kiriting:", reply_markup=kb_cancel_back(lang))
        return
    if data == "menu:leaderboard":
        text = build_leaderboard_text(lang)
        tg_send_message(chat_id, text, reply_markup=kb_main_menu(lang))
        return
    if data == "menu:help":
        tg_send_message(chat_id, t(lang, "help_text"), reply_markup=kb_help_menu(lang))
        return
    if data == "menu:change_id":
        unlink_site_user(chat_id)
        tg_send_message(chat_id, t(lang, "id_unlinked"), reply_markup=kb_main_menu(lang))
        return

    # Code paketi tanlandi
    if data.startswith("code:"):
        parts = data.split(":")
        code_amount = int(parts[1])
        price = int(parts[2])
        if tg_user.get("linked_user_id"):
            _show_payment_and_wait_receipt(chat_id, lang, tg_user, "code",
                                           {"code": code_amount, "price": price})
        else:
            set_tg_state(chat_id, "awaiting_id_for_code", {"code": code_amount, "price": price})
            tg_send_message(chat_id, t(lang, "ask_id_for_code"), reply_markup=kb_cancel_back(lang))
        return

    # Tarif tanlandi (Pro/Cyber Pro/VIP/HackerLab)
    if data.startswith("tariff:"):
        parts = data.split(":")
        plan_key = parts[1]
        price_uzs = int(parts[2])
        if tg_user.get("linked_user_id"):
            _show_payment_and_wait_receipt(chat_id, lang, tg_user, "tariff",
                                           {"plan": plan_key, "price": price_uzs})
        else:
            set_tg_state(chat_id, "awaiting_id_for_tariff", {"plan": plan_key, "price": price_uzs})
            tg_send_message(chat_id, t(lang, "ask_id_for_tariff"), reply_markup=kb_cancel_back(lang))
        return

    # YANGI: CODE bilan DARHOL (admin tasdig'isiz), botga xos qo'shimcha
    # chegirmali narxda tarif sotib olish.
    if data.startswith("tariffcode:"):
        parts = data.split(":")
        plan_key = parts[1]
        code_price = int(parts[2])
        if not tg_user.get("linked_user_id"):
            set_tg_state(chat_id, "main", {})
            tg_send_message(chat_id, "🔗 Avval profilingizni ulashingiz kerak (Profil ulash).",
                           reply_markup=kb_main_menu(lang))
            return
        ok, msg = _bot_buy_tariff_with_code(tg_user["linked_user_id"], plan_key, code_price)
        tg_send_message(chat_id, ("✅ " if ok else "❌ ") + msg, reply_markup=kb_main_menu(lang))
        return

    # Kurs tanlash (toggle)
    if data.startswith("course:"):
        cid = int(data.split(":")[1])
        selected = state_data.get("selected", [])
        if cid in selected:
            selected.remove(cid)
        else:
            if len(selected) >= 10:
                tg_answer_callback(callback_id, text=t(lang, "max_courses_reached"), show_alert=True)
                return
            selected.append(cid)
        state_data["selected"] = selected
        set_tg_state(chat_id, "choose_courses", state_data)
        courses = get_paid_courses()
        total = sum(c["code_price"] for c in courses if c["id"] in selected)
        text = (t(lang, "choose_courses_title") + "\n\n" +
                t(lang, "selected_courses", n=len(selected), total=total))
        tg_send_message(chat_id, text, reply_markup=kb_courses(lang, courses, selected))
        return

    if data == "course_action:clear":
        state_data["selected"] = []
        set_tg_state(chat_id, "choose_courses", state_data)
        courses = get_paid_courses()
        tg_send_message(chat_id, t(lang, "choose_courses_title"), reply_markup=kb_courses(lang, courses, []))
        return

    if data == "course_action:done":
        selected = state_data.get("selected", [])
        if not selected:
            tg_answer_callback(callback_id, text=t(lang, "no_courses_selected"), show_alert=True)
            return
        courses = get_paid_courses()
        chosen = [c for c in courses if c["id"] in selected]
        total = sum(c["code_price"] for c in chosen)
        course_state = {"courses": [{"id": c["id"], "title": c["title"], "price": c["code_price"]} for c in chosen],
                        "total": total}
        if tg_user.get("linked_user_id"):
            _show_payment_and_wait_receipt(chat_id, lang, tg_user, "course", course_state)
        else:
            set_tg_state(chat_id, "awaiting_id_for_course", course_state)
            tg_send_message(chat_id, t(lang, "ask_id_for_course"), reply_markup=kb_cancel_back(lang))
        return

    # YANGI: tanlangan kurslarni CODE bilan DARHOL (admin tasdig'isiz),
    # bot orqali qo'shimcha chegirmali narxda sotib olish.
    if data == "course_action:buycode":
        selected = state_data.get("selected", [])
        if not selected:
            tg_answer_callback(callback_id, text=t(lang, "no_courses_selected"), show_alert=True)
            return
        if not tg_user.get("linked_user_id"):
            set_tg_state(chat_id, "main", {})
            tg_send_message(chat_id, "🔗 Avval profilingizni ulashingiz kerak (Profil ulash).",
                           reply_markup=kb_main_menu(lang))
            return
        courses = get_paid_courses()
        chosen = [c for c in courses if c["id"] in selected]
        results = []
        for c in chosen:
            bot_price = max(1, (c["code_price"] or 0) - 1)  # botga xos qo'shimcha 1 CODE chegirma
            ok, msg = _bot_buy_course_with_code(tg_user["linked_user_id"], c["id"], bot_price)
            results.append((c["title"], ok, msg))
        set_tg_state(chat_id, "main", {})
        lines = ["📚 *Natija:*\n"]
        for title, ok, msg in results:
            lines.append(f"{'✅' if ok else '❌'} {title}: {msg}")
        tg_send_message(chat_id, "\n".join(lines), parse_mode="Markdown", reply_markup=kb_main_menu(lang))
        return


def handle_text(chat_id, text, user_info):
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)

    if text.strip().startswith("/start"):
        handle_start(chat_id, user_info); return
    if text.strip() == "/help":
        tg_send_message(chat_id, t(lang, "help_text"), reply_markup=kb_help_menu(lang))
        return
    if text.strip() == "/menu":
        show_main_menu(chat_id, lang); return

    # PROFIL ULASH — 1-qadam: ID kiritish
    # BONUS (PROMO) KOD — DIQQAT: coins_purchase.py Flask ilova kontekstiga
    # (Flask 'g' obyektiga) bog'liq bo'lgani uchun, bot uni TO'G'RIDAN-
    # TO'G'RI chaqirsa "Working outside of application context" xatosi
    # bilan yiqilib qolar edi (bot alohida jarayon, Flask kontekstisiz
    # ishlaydi). Shuning uchun bir xil mantiq shu yerda BOTNING O'Z
    # db_conn() (oddiy sqlite3, Flaskga bog'liq emas) orqali qayta
    # yozilgan — saytdagi bilan bir xil natija, lekin xavfsiz.
    if state == "awaiting_promo_code":
        tg_user_for_promo = get_or_create_tg_user(chat_id)
        if not tg_user_for_promo.get("linked_user_id"):
            tg_send_message(chat_id, "🔗 Avval profilingizni ulashingiz kerak (Profil ulash).",
                           reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return
        ok, msg = _redeem_promo_code_standalone(text.strip(), tg_user_for_promo["linked_user_id"])
        set_tg_state(chat_id, "main", {})
        tg_send_message(chat_id, msg, reply_markup=kb_main_menu(lang))
        return

    if state == "awaiting_link_id":
        cid = text.strip().lstrip("#").strip()
        if not cid.isdigit():
            tg_send_message(chat_id, t(lang, "link_id_not_found"), reply_markup=kb_cancel_back(lang))
            return
        site_user = find_site_user_by_custom_id(cid)
        if not site_user:
            tg_send_message(chat_id, t(lang, "link_id_not_found"), reply_markup=kb_cancel_back(lang))
            return
        set_tg_state(chat_id, "awaiting_link_email", {"custom_id": cid, "site_user_id": site_user["id"]})
        tg_send_message(chat_id, t(lang, "ask_link_email"), reply_markup=kb_cancel_back(lang))
        return

    # PROFIL ULASH — 2-qadam: email tekshirish (ID + email ikkalasi mos kelishi shart)
    if state == "awaiting_link_email":
        # XAVFSIZLIK (yangi qo'shildi): urinishlar sonini VA vaqtini
        # cheklash — avval bu yerda HECH QANDAY cheklov yo'q edi, ya'ni
        # nazariy jihatdan kimdir bir ID uchun ko'plab email urinib
        # ko'rishi mumkin edi. Endi 15 daqiqa ichida 5 martadan ortiq
        # noto'g'ri urinish qilingan bo'lsa, bloklanadi.
        import time as _time
        import json as _json
        attempt_key = f"link_attempts_{chat_id}"
        raw = _bot_state_get(attempt_key)
        now = _time.time()
        if raw:
            try:
                saved = _json.loads(raw)
                count, since = saved["count"], saved["since"]
                if now - since > 900:  # 15 daqiqa o'tgan bo'lsa — hisoblagich tozalanadi
                    count = 0
                    since = now
            except Exception:
                count, since = 0, now
        else:
            count, since = 0, now

        if count >= 5:
            wait_min = max(1, int((900 - (now - since)) / 60))
            tg_send_message(chat_id, f"⛔ Juda ko'p noto'g'ri urinish. {wait_min} daqiqadan so'ng qayta urinib ko'ring.",
                           reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return

        email_input = text.strip().lower()
        site_user = find_site_user_by_id(state_data.get("site_user_id"))
        if not site_user or (site_user.get("email") or "").strip().lower() != email_input:
            _bot_state_set(attempt_key, _json.dumps({"count": count + 1, "since": since}))
            tg_send_message(chat_id, t(lang, "link_mismatch"), reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return
        _bot_state_set(attempt_key, _json.dumps({"count": 0, "since": now}))  # tozalanadi
        
        # Yuborish uchun 6 xonali tasodifiy kod yaratish
        import random
        verify_code = str(random.randint(100000, 999999))
        
        # Email yuborish
        subject = "Cyber Shats - Telegram Profilni Ulash"
        body = f"Sizning telegram profilingizni ulash uchun tasdiqlash kodingiz:\n\n{verify_code}\n\nBu kod 10 daqiqa davomida amal qiladi. Iltimos, bu kodni hech kimga bermang."
        email_sent = send_email(email_input, subject, body)
        
        if not email_sent:
            tg_send_message(chat_id, t(lang, "link_email_sent_error"), reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return

        # Holatni yangilash
        state_data["verify_code"] = verify_code
        state_data["verify_time"] = _time.time()
        set_tg_state(chat_id, "awaiting_link_code", state_data)
        
        tg_send_message(chat_id, t(lang, "ask_link_code", email=email_input), reply_markup=kb_cancel_back(lang))
        return

    if state == "awaiting_link_code":
        import time as _time
        now = _time.time()
        verify_time = state_data.get("verify_time", 0)
        verify_code = state_data.get("verify_code", "")
        
        # 10 daqiqa tekshirish
        if now - verify_time > 600:
            tg_send_message(chat_id, t(lang, "link_code_expired"), reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return
            
        input_code = text.strip()
        if input_code != verify_code:
            tg_send_message(chat_id, t(lang, "link_code_invalid"), reply_markup=kb_cancel_back(lang))
            return
            
        # Muvaffaqiyatli ulash
        site_user = find_site_user_by_id(state_data.get("site_user_id"))
        if not site_user:
            tg_send_message(chat_id, t(lang, "link_id_not_found"), reply_markup=kb_main_menu(lang))
            set_tg_state(chat_id, "main", {})
            return
            
        link_site_user(chat_id, site_user["id"], state_data["custom_id"])
        full_name = f"{site_user.get('familiya','')} {site_user.get('ism','')}".strip()
        set_tg_state(chat_id, "main", {})
        tg_send_message(chat_id, t(lang, "link_success", name=full_name, cid=state_data["custom_id"]),
                        reply_markup=kb_main_menu(lang))
        return

    # ID kutmoqda (code, kurs yoki tarif uchun)
    if state in ("awaiting_id_for_code", "awaiting_id_for_course", "awaiting_id_for_tariff"):
        cid = text.strip().lstrip("#").strip()
        if not cid.isdigit():
            tg_send_message(chat_id,
                "❌ ID noto'g'ri formatda.\n\n"
                "Saytdagi ID raqamingizni kiriting (faqat raqamlar).\n"
                "Masalan: `1342835`\n\n"
                "ID ni saytda Profil → ID raqamingiz bo'limidan topishingiz mumkin.",
                reply_markup=kb_cancel_back(lang))
            return
        site_user = find_site_user_by_custom_id(cid)
        if not site_user:
            tg_send_message(chat_id,
                f"❌ #{cid} ID saytda topilmadi.\n\n"
                "Ehtimoliy sabablar:\n"
                "• ID noto'g'ri kiritilgan\n"
                "• Saytda hali ro'yxatdan o'tilmagan\n\n"
                "Saytdagi ID raqamingizni kiriting (profil sahifasida ko'rinadi):",
                reply_markup=kb_cancel_back(lang))
            return
        # ID tasdiqlandi — DOIMIY saqlaymiz, shunda keyingi xaridlarda qayta so'ralmaydi
        full_name = f"{site_user['ism']} {site_user.get('familiya','')}".strip()
        link_site_user(chat_id, site_user["id"], cid)
        tg_send_message(chat_id, t(lang, "id_remembered", cid=cid, name=full_name))
        # Karta ma'lumotini ko'rsatamiz
        state_data["custom_id"] = cid
        state_data["site_user_id"] = site_user["id"]
        if state == "awaiting_id_for_code":
            msg = t(lang, "show_payment_for_code",
                    code=state_data["code"], price=state_data["price"], cid=cid,
                    uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
            set_tg_state(chat_id, "awaiting_receipt_code", state_data)
        elif state == "awaiting_id_for_tariff":
            plan_labels = dict(TARIFF_PLANS)
            msg = t(lang, "show_payment_for_tariff",
                    name=plan_labels.get(state_data["plan"], state_data["plan"]),
                    price=state_data["price"], cid=cid,
                    uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
            set_tg_state(chat_id, "awaiting_receipt_tariff", state_data)
        else:
            msg = t(lang, "show_payment_for_course",
                    n=len(state_data["courses"]), total=state_data["total"], cid=cid,
                    uzcard=PAYMENT_CARDS["uzum_bank"], humo=PAYMENT_CARDS["uzum_bank"])
            set_tg_state(chat_id, "awaiting_receipt_course", state_data)
        tg_send_message(chat_id, msg, reply_markup=kb_cancel_back(lang))
        tg_send_message(chat_id, t(lang, "awaiting_receipt"))
        return

    if state in ("awaiting_receipt_code", "awaiting_receipt_course", "awaiting_receipt_tariff"):
        tg_send_message(chat_id, t(lang, "receipt_not_image"))
        return

    # Tushunilmagan xabar — odatda foydalanuvchi ADMINGA nimadir yozmoqchi
    # bo'lgani uchun keladi (buyruq emas, erkin matn). Shu sababli buni
    # e'tiborsiz qoldirmasdan, guruhdagi "Admin bilan yozishmalar" bo'limiga
    # VA maxsus admin ID'siga (5856575656) TO'LIQ matni bilan yuboramiz.
    forward_user_message_to_admins(chat_id, tg_user, text)
    tg_send_message(chat_id, t(lang, "unknown_message"), reply_markup=kb_main_menu(lang))


def handle_photo(message):
    chat_id = message["chat"]["id"]
    user_info = message.get("from", {})
    tg_user = get_or_create_tg_user(chat_id, first_name=user_info.get("first_name", ""),
                                     username=user_info.get("username", ""))
    lang = tg_user.get("language", "uz")
    state, state_data = get_tg_state(chat_id)
    if state not in ("awaiting_receipt_code", "awaiting_receipt_course", "awaiting_receipt_tariff"):
        tg_send_message(chat_id, t(lang, "unknown_message"))
        return

    # Eng yuqori sifatli rasm file_id
    photos = message.get("photo", [])
    if not photos:
        tg_send_message(chat_id, t(lang, "receipt_not_image"))
        return
    file_id = photos[-1]["file_id"]

    if state == "awaiting_receipt_code":
        rid = create_purchase_request(
            chat_id=chat_id, tg_user_id=tg_user["id"],
            request_type="code",
            code_amount=state_data.get("code", 0),
            price_uzs=state_data.get("price", 0),
            target_custom_id=state_data.get("custom_id", ""),
            site_user_id=state_data.get("site_user_id"),
            receipt_file_id=file_id
        )
    elif state == "awaiting_receipt_tariff":
        rid = create_purchase_request(
            chat_id=chat_id, tg_user_id=tg_user["id"],
            request_type="tariff",
            plan=state_data.get("plan", ""),
            price_uzs=state_data.get("price", 0),
            target_custom_id=state_data.get("custom_id", ""),
            site_user_id=state_data.get("site_user_id"),
            receipt_file_id=file_id
        )
    else:
        rid = create_purchase_request(
            chat_id=chat_id, tg_user_id=tg_user["id"],
            request_type="course",
            courses_json=json.dumps(state_data.get("courses", [])),
            price_uzs=state_data.get("total", 0),
            target_custom_id=state_data.get("custom_id", ""),
            site_user_id=state_data.get("site_user_id"),
            receipt_file_id=file_id
        )
    set_tg_state(chat_id, "main", {})
    tg_send_message(chat_id, t(lang, "receipt_received"), reply_markup=kb_main_menu(lang))

    # Admin chatga xabar (agar sozlangan bo'lsa)
    if ADMIN_CHAT_ID:
        try:
            kind_labels = {"awaiting_receipt_code": "💎 CODE", "awaiting_receipt_tariff": "🎓 TARIF"}
            kind = kind_labels.get(state, "📚 KURS")
            note = f"🔔 *Yangi to'lov so'rovi #{rid}*\n\nTip: {kind}\nID: #{state_data.get('custom_id')}\nChat: {chat_id}"
            tg_send_message(int(ADMIN_CHAT_ID), note)
        except Exception as e:
            log.error(f"Admin notify error: {e}")

    # Shaxsiy DM — belgilangan 2 ta admin Telegram ID'siga ham to'g'ridan-to'g'ri
    # yuboriladi (guruhga qo'shimcha ravishda), CODE so'rovlarini tezroq
    # ko'rishlari uchun.
    for admin_tg_id in SPECIAL_ADMIN_TG_IDS:
        try:
            kind_labels = {"awaiting_receipt_code": "💎 CODE", "awaiting_receipt_tariff": "🎓 TARIF"}
            kind = kind_labels.get(state, "📚 KURS")
            note = f"🔔 *Yangi to'lov so'rovi #{rid}*\n\nTip: {kind}\nID: #{state_data.get('custom_id')}"
            tg_send_message(admin_tg_id, note)
        except Exception as e:
            log.error(f"Shaxsiy admin DM xatosi ({admin_tg_id}): {e}")

    log.info(f"Purchase request #{rid} created (chat {chat_id}, state {state})")


def _get_code_to_som_rate():
    """DB'dan joriy 1 CODE = necha so'm kursini o'qiydi (statik emas —
    admin panelidan o'zgartirilsa, bot ham DARHOL yangi kursni ishlatadi).
    DIQQAT: bot Flask ilovasidan MUSTAQIL jarayon sifatida ishlaydi,
    shuning uchun db.py (Flask 'g' kontekstiga bog'liq) emas, botning
    o'z db_conn() funksiyasi ishlatiladi."""
    try:
        conn = db_conn()
        row = conn.execute("SELECT value FROM pricing_settings WHERE key='code_to_som_rate'").fetchone()
        conn.close()
        if row and row["value"]:
            return int(row["value"])
    except Exception:
        pass
    return 10000  # standart kurs — DBga ulanib bo'lmasa ham bot ishlashda davom etadi


def try_currency_calc(text: str):
    """Guruhda 'Ncode' yozilsa -> so'mga, '<son> so'm code' yozilsa ->
    CODE'ga aylantirib javob beradi. Hech qanday andozaga mos kelmasa
    None qaytaradi (bot jim turadi, oddiy suhbatga aralashmaydi).

    DIQQAT (tuzatilgan xato): odamlar 'N' bilan 'code' orasiga ko'pincha
    TIRE (-) ham qo'yishadi (masalan '5-code', '10code-') — avvalgi andoza
    faqat bo'sh joy yoki hech narsani kutar edi, TIRE'ni EMAS, shuning
    uchun bunday xabarlarga bot HECH QANDAY javob bermas edi. Endi son va
    "code" orasida — va oxirida — ixtiyoriy tire/bo'sh joy/belgi bo'lishi
    mumkin, hammasi qabul qilinadi."""
    t = text.strip().lower().replace("’", "'").replace("‘", "'")
    rate = _get_code_to_som_rate()

    m1 = re.fullmatch(r"(\d+)\s*[-–—]?\s*code\s*[-–—?!.]?", t)
    if m1:
        n = int(m1.group(1))
        som = n * rate
        return f"⚡ {n} CODE = {som:,} so'm".replace(",", " ")

    m2 = re.search(r"([\d\s]+)\s*[-–—]?\s*so'?m\s*[-–—]?.*code", t)
    if m2:
        digits = re.sub(r"\D", "", m2.group(1))
        if digits:
            som = int(digits)
            code = som / rate
            code_str = f"{code:.2f}".rstrip("0").rstrip(".") if code != int(code) else str(int(code))
            return f"💰 {som:,} so'm = {code_str} CODE".replace(",", " ")

    return None


def _fetch_fund_and_user_stats():
    """G'azna balansi + foydalanuvchi statistikasini o'qiydi.

    MUHIM (tuzatilgan xato): bot jarayoni HAR DEPLOY/QAYTA ISHGA
    TUSHISHDA davriy tekshiruv tsiklini _last_..._check=0 bilan
    boshlaydi (telegram_bot.py'dagi worker() funksiyasi) — demak
    send_daily_report/check_low_treasury_balance DARHOL, yangi
    ochilgan DB ulanishi bilan ishga tushadi. Real production'da
    (screenshot orqali) buning oqibatida bir marta HAMMA son 0/deyarli
    0 (masalan "Jami talabalar: 1") qilib noto'g'ri o'qilgan holat
    kuzatildi — bazaning o'zida esa hech narsa o'zgarmagan edi
    (treasury_fund.updated_at o'sha payt yangilanmagan edi, ya'ni bu
    YOZISH emas, faqat bitta xato O'QISH edi). Bunday "hammasi birdan
    0" natija haqiqiy productionda deyarli imkonsiz (talabalar sonining
    bir zumda 0'ga tushishi mumkin emas) — shuning uchun bitta yangi
    ulanish bilan avtomatik qayta urinib ko'ramiz, xato hali ham
    davom etsa haqiqiy (kutilmagan) natija sifatida qabul qilinadi."""
    def _read_once():
        conn = db_conn()
        try:
            fund = conn.execute("SELECT balance FROM treasury_fund WHERE id=1").fetchone()
            balance = fund["balance"] if fund else 0
            total_users = conn.execute("SELECT COUNT(*) c FROM users WHERE role='student'").fetchone()["c"]
            total_code_in_circulation = conn.execute(
                "SELECT COALESCE(SUM(code_balance),0) s FROM users").fetchone()["s"]
            vip_count = conn.execute("SELECT COUNT(*) c FROM users WHERE plan='vip'").fetchone()["c"]
            pro_count = conn.execute(
                "SELECT COUNT(*) c FROM users WHERE plan IN ('pro','cyber_pro')").fetchone()["c"]
            pending_row = conn.execute(
                "SELECT COUNT(*) c FROM bot_purchase_requests WHERE status='pending'").fetchone()
            pending_n = pending_row["c"] if pending_row else 0
            return dict(balance=balance, total_users=total_users,
                        total_code_in_circulation=total_code_in_circulation,
                        vip_count=vip_count, pro_count=pro_count, pending_n=pending_n)
        finally:
            conn.close()

    stats = _read_once()
    if stats["total_users"] == 0 and stats["balance"] == 0:
        log.warning("Xisobot: birinchi o'qishda shubhali (hammasi 0) natija — yangi ulanish bilan qayta urinilmoqda.")
        stats = _read_once()
    return stats


def build_xisobot_report() -> str:
    """'Xisobot' deb yozilganda guruhga yuboriladigan qisqa moliyaviy xulosa."""
    try:
        stats = _fetch_fund_and_user_stats()
        rate = _get_code_to_som_rate()
        balance = stats["balance"]

        return (
            "📊 *CYBER SHATS — Umumiy Xisobot*\n\n"
            f"💰 G'azna balansi: ⚡ {balance:,} CODE (≈ {balance*rate:,} so'm)\n"
            f"🔄 Foydalanuvchilardagi jami CODE: ⚡ {stats['total_code_in_circulation']:,}\n"
            f"👥 Jami talabalar: {stats['total_users']:,}\n"
            f"👑 VIP: {stats['vip_count']} · PRO/CYBER PRO: {stats['pro_count']}\n"
            f"⏳ Ko'rib chiqilmagan xarid so'rovlari: {stats['pending_n']}\n"
        ).replace(",", " ")
    except Exception as e:
        log.exception(f"Xisobot tuzishda xato: {e}")
        return "⚠️ Xisobot tuzishda xatolik yuz berdi."


_TOPIC_ADMIN_CHAT_ENV = os.environ.get("TG_TOPIC_ADMIN_CHAT", "").strip()


def forward_user_message_to_admins(chat_id, tg_user, text):
    """Foydalanuvchi botga yozgan, lekin biror buyruq/holatga mos
    kelmagan (demak ko'pincha ADMINGA murojaat bo'lgan) xabarni:
    1) guruhdagi 'Admin bilan yozishmalar' bo'limiga, VA
    2) maxsus admin Telegram ID'lariga (shaxsiy DM) — TO'LIQ matni bilan
    yuboradi."""
    name = tg_user.get("first_name") or "Noma'lum"
    username = tg_user.get("username")
    uname_part = f" (@{username})" if username else ""
    note = f"💬 *Foydalanuvchidan xabar*\n\n👤 {name}{uname_part}\nChat ID: `{chat_id}`\n\n📩 \"{text}\""

    if ADMIN_CHAT_ID:
        extra = {"message_thread_id": int(_TOPIC_ADMIN_CHAT_ENV)} if _TOPIC_ADMIN_CHAT_ENV else {}
        try:
            tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=note, parse_mode="Markdown", **extra)
        except Exception as e:
            log.error(f"Guruhga xabar yo'naltirishda xato: {e}")

    for admin_tg_id in SPECIAL_ADMIN_TG_IDS:
        try:
            tg_send_message(admin_tg_id, note)
        except Exception as e:
            log.error(f"Shaxsiy admin DM xatosi ({admin_tg_id}): {e}")


TOPIC_FINANCE_ENV = os.environ.get("TG_TOPIC_FINANCE", "").strip()
TOPIC_NEWS_ENV = os.environ.get("TG_TOPIC_NEWS", "").strip()


def _bot_state_get(key):
    conn = db_conn(); c = conn.cursor()
    row = c.execute("SELECT value FROM bot_state WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def _bot_state_set(key, value):
    conn = db_conn(); c = conn.cursor()
    c.execute("INSERT INTO bot_state (key,value,updated_at) VALUES (?,?,datetime('now')) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
              (key, str(value)))
    conn.commit()
    conn.close()


def _tashkent_now():
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None) + _dt.timedelta(hours=5)


def send_daily_report():
    """1) Har kuni Toshkent vaqti bilan soat 09:00da (yoki bot shu vaqtdan
    keyin birinchi marta tekshirganida) guruhga avtomatik umumiy xisobot
    yuboriladi. Kuniga faqat BIR MARTA (bot_state orqali nazorat)."""
    now = _tashkent_now()
    today_str = now.date().isoformat()
    if now.hour < 9:
        return
    if _bot_state_get("last_daily_report_date") == today_str:
        return
    report = "🌅 *Kunlik avtomatik xisobot*\n\n" + build_xisobot_report()
    _bot_state_set("last_daily_report_date", today_str)
    if ADMIN_CHAT_ID:
        extra = {"message_thread_id": int(TOPIC_FINANCE_ENV)} if TOPIC_FINANCE_ENV else {}
        tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=report, parse_mode="Markdown", **extra)


def check_low_treasury_balance(threshold=100):
    """2) G'azna balansi past bo'lsa (standart: 100 CODE'dan kam) —
    kuniga bir marta ogohlantirish yuboriladi."""
    conn = db_conn(); c = conn.cursor()
    fund = c.execute("SELECT balance FROM treasury_fund WHERE id=1").fetchone()
    conn.close()
    if fund and fund["balance"] == 0:
        # Bitta shubhali "0" o'qish (masalan bot jarayoni endigina qayta
        # ishga tushgan bo'lsa) uchun yolg'on ogohlantirish yubormaslik
        # uchun yangi ulanish bilan qayta tekshiramiz (qarang:
        # _fetch_fund_and_user_stats() docstring).
        conn2 = db_conn(); c2 = conn2.cursor()
        fund = c2.execute("SELECT balance FROM treasury_fund WHERE id=1").fetchone()
        conn2.close()
    if not fund or fund["balance"] >= threshold:
        return
    today_str = _tashkent_now().date().isoformat()
    if _bot_state_get("last_low_balance_alert_date") == today_str:
        return
    _bot_state_set("last_low_balance_alert_date", today_str)
    text = f"⚠️ *G'azna balansi past!*\n\n⚡ Joriy balans: {fund['balance']:,} CODE (chegara: {threshold:,})".replace(",", " ")
    if ADMIN_CHAT_ID:
        extra = {"message_thread_id": int(TOPIC_FINANCE_ENV)} if TOPIC_FINANCE_ENV else {}
        tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=text, parse_mode="Markdown", **extra)


def check_unanswered_requests(hours=2):
    """3) 2 soatdan ko'p ko'rib chiqilmagan CODE/tarif so'rovlari uchun
    guruhga eslatma (har so'rov uchun faqat bir marta — bot_state orqali)."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute(f"""
        SELECT id, request_type, code_amount, price_uzs FROM bot_purchase_requests
        WHERE status='pending' AND datetime(created_at) < datetime('now', '-{hours} hours')
    """).fetchall()
    conn.close()
    if not rows:
        return
    already = _bot_state_get("reminded_request_ids") or ""
    already_ids = set(already.split(",")) if already else set()
    new_ones = [r for r in rows if str(r["id"]) not in already_ids]
    if not new_ones:
        return
    lines = [f"⏳ *{hours} soatdan ko'p javobsiz so'rovlar*\n"]
    for r in new_ones:
        lines.append(f"• #{r['id']} — {r['request_type']} — {r['price_uzs']:,} so'm".replace(",", " "))
    text = "\n".join(lines)
    if ADMIN_CHAT_ID:
        extra = {"message_thread_id": int(TOPIC_FINANCE_ENV)} if TOPIC_FINANCE_ENV else {}
        tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=text, parse_mode="Markdown", **extra)
    all_ids = already_ids | {str(r["id"]) for r in new_ones}
    _bot_state_set("reminded_request_ids", ",".join(list(all_ids)[-200:]))  # oxirgi 200 tasini saqlaymiz


def check_inactive_users(days=7):
    """4) 7+ kun saytga kirmagan, PROFILI ULANGAN foydalanuvchilarga
    botdan 'sog'indik' xabari — har kishiga haftada bir marta."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute(f"""
        SELECT tu.chat_id, tu.language, tu.last_inactivity_notice_at, u.familiya, u.ism
        FROM telegram_users tu JOIN users u ON u.id = tu.linked_user_id
        WHERE tu.linked_user_id IS NOT NULL
          AND (u.last_login_date IS NULL OR date(u.last_login_date) < date('now', '-{days} days'))
    """).fetchall()
    for r in rows:
        last = r["last_inactivity_notice_at"]
        if last:
            try:
                import datetime as _dt
                if (_dt.datetime.now() - _dt.datetime.fromisoformat(last)).days < 7:
                    continue
            except Exception:
                pass
        text = f"👋 Sog'indik, {r['familiya']} {r['ism']}! {days}+ kundan beri saytga kirmadingiz — qaytib, yangiliklarni ko'ring!"
        tg_send_message(r["chat_id"], text, reply_markup=kb_main_menu(r["language"] or "uz"))
        c.execute("UPDATE telegram_users SET last_inactivity_notice_at=datetime('now') WHERE chat_id=?", (r["chat_id"],))
    conn.commit()
    conn.close()


def check_unused_tickets():
    """5) Sandiq chiptalari bor, lekin uzoq vaqt ochilmagan foydalanuvchilarga
    eslatma — haftada bir marta."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute("""
        SELECT tu.chat_id, tu.language, tu.last_tickets_notice_at,
               u.chest_tickets_tariff, u.chest_tickets_id, u.familiya, u.ism
        FROM telegram_users tu JOIN users u ON u.id = tu.linked_user_id
        WHERE tu.linked_user_id IS NOT NULL
          AND (u.chest_tickets_tariff > 0 OR u.chest_tickets_id > 0)
    """).fetchall()
    for r in rows:
        last = r["last_tickets_notice_at"]
        if last:
            try:
                import datetime as _dt
                if (_dt.datetime.now() - _dt.datetime.fromisoformat(last)).days < 7:
                    continue
            except Exception:
                pass
        total = (r["chest_tickets_tariff"] or 0) + (r["chest_tickets_id"] or 0)
        text = f"🎫 {r['familiya']} {r['ism']}, sizda {total} ta ishlatilmagan sandiq chiptasi bor — oching, omadingizni sinang!"
        tg_send_message(r["chat_id"], text, reply_markup=kb_main_menu(r["language"] or "uz"))
        c.execute("UPDATE telegram_users SET last_tickets_notice_at=datetime('now') WHERE chat_id=?", (r["chat_id"],))
    conn.commit()
    conn.close()


def check_unverified_emails():
    """9) Ro'yxatdan o'tib, emailini tasdiqlamagan (va profili ulangan)
    foydalanuvchilarga eslatma — kuniga bir marta."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute("""
        SELECT tu.chat_id, tu.language, tu.last_email_notice_at, u.familiya, u.ism
        FROM telegram_users tu JOIN users u ON u.id = tu.linked_user_id
        WHERE tu.linked_user_id IS NOT NULL AND u.email_verified=0
    """).fetchall()
    for r in rows:
        last = r["last_email_notice_at"]
        if last:
            try:
                import datetime as _dt
                if (_dt.datetime.now() - _dt.datetime.fromisoformat(last)).total_seconds() < 20 * 3600:
                    continue
            except Exception:
                pass
        text = f"📧 {r['familiya']} {r['ism']}, emailingiz hali tasdiqlanmagan — saytga kirib, tasdiqlang."
        tg_send_message(r["chat_id"], text)
        c.execute("UPDATE telegram_users SET last_email_notice_at=datetime('now') WHERE chat_id=?", (r["chat_id"],))
    conn.commit()
    conn.close()


def check_collection_progress_reminder():
    """11) Koleksiyada keyingi bosqichga (masalan 100/200/300/577/699
    ochilishga) yaqin qolgan foydalanuvchilarga eslatma — haftada bir marta."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute("""
        SELECT tu.chat_id, tu.language, tu.last_collection_notice_at,
               u.familiya, u.ism, COUNT(uc.level) as owned
        FROM telegram_users tu
        JOIN users u ON u.id = tu.linked_user_id
        LEFT JOIN user_collection uc ON uc.user_id = u.id
        WHERE tu.linked_user_id IS NOT NULL
        GROUP BY tu.chat_id, tu.language, tu.last_collection_notice_at, u.id, u.familiya, u.ism
        HAVING COUNT(uc.level) > 0 AND COUNT(uc.level) < 106
    """).fetchall()
    for r in rows:
        last = r["last_collection_notice_at"]
        if last:
            try:
                import datetime as _dt
                if (_dt.datetime.now() - _dt.datetime.fromisoformat(last)).days < 7:
                    continue
            except Exception:
                pass
        remaining = 106 - r["owned"]
        text = f"🏆 {r['familiya']} {r['ism']}, koleksiyangizga yana {remaining} ta haykalcha yetmayapti — davom eting!"
        tg_send_message(r["chat_id"], text)
        c.execute("UPDATE telegram_users SET last_collection_notice_at=datetime('now') WHERE chat_id=?", (r["chat_id"],))
    conn.commit()
    conn.close()


def check_expired_id_reservations():
    """ID band qilish (rezervatsiya) muddati (48 soat) tugagan, lekin
    sotib olinmagan bandlarni 'expired' deb belgilaydi — shundan so'ng
    o'sha ID Random'da qayta chiqishi mumkin bo'ladi. Foydalanuvchiga
    profili ulangan bo'lsa xabar ham yuboriladi."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute("""
        SELECT ir.id, ir.user_id, ir.custom_id, tu.chat_id, tu.language
        FROM id_reservations ir
        LEFT JOIN telegram_users tu ON tu.linked_user_id = ir.user_id
        WHERE ir.status='active' AND datetime(ir.expires_at) <= datetime('now')
    """).fetchall()
    for r in rows:
        c.execute("UPDATE id_reservations SET status='expired' WHERE id=?", (r["id"],))
        if r["chat_id"]:
            text = f"⏰ #{r['custom_id']} ID'ni band qilish muddati tugadi — endi boshqalar ham ololadi."
            tg_send_message(r["chat_id"], text)
    conn.commit()
    conn.close()
    if rows:
        log.info(f"{len(rows)} ta ID band qilish muddati tugadi, bo'shatildi.")


def backup_database():
    """8) Kunlik avtomatik zaxira nusxa — database/backups/ papkasiga
    sana bilan nusxalanadi. Eskirgan (30 kundan katta) nusxalar avtomatik
    o'chiriladi, joy tejash uchun."""
    import shutil as _shutil
    import datetime as _dt
    today_str = _tashkent_now().date().isoformat()
    if _bot_state_get("last_backup_date") == today_str:
        return
    backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    dest = os.path.join(backup_dir, f"cyber_shats_{today_str}.db")
    try:
        _shutil.copy2(DB_PATH, dest)
        _bot_state_set("last_backup_date", today_str)
        log.info(f"Kunlik zaxira nusxa yaratildi: {dest}")
        # 30 kundan eski nusxalarni tozalash
        cutoff = _dt.date.today() - _dt.timedelta(days=30)
        for fname in os.listdir(backup_dir):
            if fname.startswith("cyber_shats_") and fname.endswith(".db"):
                try:
                    date_part = fname.replace("cyber_shats_", "").replace(".db", "")
                    if _dt.date.fromisoformat(date_part) < cutoff:
                        os.remove(os.path.join(backup_dir, fname))
                except Exception:
                    pass
    except Exception as e:
        log.error(f"Zaxira nusxa yaratishda xato: {e}")


def check_unanswered_friend_requests(hours=24):
    """7) 24 soatdan ko'p javobsiz qolgan DO'STLIK so'rovlari uchun —
    so'rov OLGAN tomonga (agar profili ulangan bo'lsa) botdan eslatma."""
    conn = db_conn(); c = conn.cursor()
    rows = c.execute(f"""
        SELECT f.id as frid, f.user_a_id, f.user_b_id, f.requested_by,
               tu.chat_id, tu.language,
               sender.familiya as s_fam, sender.ism as s_ism
        FROM friendships f
        JOIN telegram_users tu ON tu.linked_user_id = (
            CASE WHEN f.requested_by = f.user_a_id THEN f.user_b_id ELSE f.user_a_id END
        )
        JOIN users sender ON sender.id = f.requested_by
        WHERE f.status='pending' AND datetime(f.created_at) < datetime('now', '-{hours} hours')
          AND f.id NOT IN (SELECT friendship_rowid FROM friend_request_reminders)
    """).fetchall()
    for r in rows:
        text = f"👋 {r['s_fam']} {r['s_ism']} sizga do'stlik so'rovi yuborgan — hali javob bermadingiz. Do'stlar bo'limiga o'ting!"
        tg_send_message(r["chat_id"], text, reply_markup=kb_main_menu(r["language"] or "uz"))
        c.execute("INSERT OR IGNORE INTO friend_request_reminders (friendship_rowid) VALUES (?)", (r["frid"],))
    conn.commit()
    conn.close()


def check_new_courses():
    """10) Yangi kurs qo'shilganini (qanday usul bilan qo'shilishidan
    qat'iy nazar — admin panel, migratsiya va h.k.) avtomatik aniqlaydi:
    kurslar sonini oldingi tekshiruv bilan solishtiradi, ko'paygan bo'lsa
    — yangi kurslarni topib, guruhga e'lon qiladi."""
    conn = db_conn(); c = conn.cursor()
    current_ids = {r["id"] for r in c.execute("SELECT id FROM courses WHERE is_active=1").fetchall()}
    known_ids_str = _bot_state_get("known_course_ids")
    if known_ids_str is None:
        # Birinchi marta ishga tushganda — hozirgi holatni "bazaviy" deb
        # belgilaymiz (e'lon qilmaymiz, aks holda barcha eski kurslar
        # "yangi" deb e'lon qilinib ketardi).
        _bot_state_set("known_course_ids", ",".join(str(i) for i in current_ids))
        conn.close()
        return
    known_ids = set(known_ids_str.split(",")) if known_ids_str else set()
    new_ids = current_ids - {int(i) for i in known_ids if i}
    if new_ids:
        rows = c.execute(
            f"SELECT title, code_price FROM courses WHERE id IN ({','.join('?'*len(new_ids))})",
            tuple(new_ids)
        ).fetchall()
        lines = ["📚 *Yangi kurs(lar) qo'shildi!*\n"]
        for r in rows:
            price = f"⚡{r['code_price']:,} CODE" if r["code_price"] else "Bepul"
            lines.append(f"• {r['title']} — {price}".replace(",", " "))
        text = "\n".join(lines)
        if ADMIN_CHAT_ID:
            extra = {"message_thread_id": int(TOPIC_NEWS_ENV)} if TOPIC_NEWS_ENV else {}
            tg_request("sendMessage", chat_id=int(ADMIN_CHAT_ID), text=text, parse_mode="Markdown", **extra)
    _bot_state_set("known_course_ids", ",".join(str(i) for i in current_ids))
    conn.close()


def check_and_notify_plan_expirations():
    """Tariflari 24 soat ichida tugaydigan, PROFILI ULANGAN (linked_user_id
    bor) foydalanuvchilarga bot orqali ogohlantirish yuboradi. Har
    foydalanuvchiga kuniga FAQAT BIR MARTA (last_expiry_notice_at orqali
    nazorat qilinadi) — spam bo'lmasligi uchun.

    Bundan tashqari, MUDDATI ALLAQACHON O'TIB KETGAN tariflarni ham
    AVTOMATIK 'free'ga tushiradi — bu saytdagi (auth.py) tekshiruvga
    QO'SHIMCHA ravishda, chunki foydalanuvchi saytga hali kirmagan
    bo'lsa ham (faqat botdan foydalansa ham), tarifi o'z vaqtida
    to'xtatilishi kerak."""
    try:
        conn = db_conn(); c = conn.cursor()

        # 1) Muddati O'TIB KETGAN tariflarni darhol 'free'ga tushirish
        expired = c.execute("""
            SELECT id, plan, familiya, ism FROM users
            WHERE plan IN ('pro','cyber_pro','vip','hacker','admin')
              AND plan_expires_at IS NOT NULL
              AND datetime(plan_expires_at) < datetime('now')
        """).fetchall()
        for u in expired:
            c.execute("UPDATE users SET plan='free', plan_expires_at=NULL WHERE id=?", (u["id"],))
            c.execute(
                "INSERT INTO notifications (user_id, title, body, type) VALUES (?,?,?,?)",
                (u["id"], "Tarif muddati tugadi",
                 f"{u['plan'].upper()} tarifingiz muddati tugadi, hisobingiz FREE tarifga o'tkazildi.", "warn")
            )
        if expired:
            log.info(f"Muddati tugagan {len(expired)} ta tarif avtomatik 'free'ga tushirildi.")

        # 2) 24 soat ICHIDA tugaydiganlarga ogohlantirish
        rows = c.execute("""
            SELECT tu.chat_id, tu.language, tu.last_expiry_notice_at,
                   u.plan, u.plan_expires_at, u.familiya, u.ism
            FROM telegram_users tu
            JOIN users u ON u.id = tu.linked_user_id
            WHERE tu.linked_user_id IS NOT NULL
              AND u.plan IN ('pro','cyber_pro','vip','hacker','admin')
              AND u.plan_expires_at IS NOT NULL
              AND datetime(u.plan_expires_at) BETWEEN datetime('now') AND datetime('now', '+1 day')
        """).fetchall()
        for r in rows:
            last_notice = r["last_expiry_notice_at"]
            if last_notice:
                try:
                    import datetime as _dt
                    if (_dt.datetime.now() - _dt.datetime.fromisoformat(last_notice)).total_seconds() < 20 * 3600:
                        continue
                except Exception:
                    pass
            lang = r["language"] or "uz"
            plan_name = {"pro": "PRO", "cyber_pro": "CYBER PRO", "vip": "VIP", "hacker": "MAXSUS", "admin": "ADMIN"}.get(r["plan"], r["plan"])
            text = (f"⏰ *Tarifingiz tugayapti!*\n\n"
                    f"{r['familiya']} {r['ism']}, sizning *{plan_name}* tarifingiz "
                    f"24 soat ichida tugaydi.\n\nUzaytirish uchun saytga kiring yoki shu botdan foydalaning.")
            tg_send_message(r["chat_id"], text, reply_markup=kb_main_menu(lang))
            c.execute("UPDATE telegram_users SET last_expiry_notice_at=datetime('now') WHERE chat_id=?",
                     (r["chat_id"],))
        conn.commit()
        conn.close()
        if rows:
            log.info(f"Tarif tugash ogohlantirishlari: {len(rows)} ta foydalanuvchiga yuborildi.")
    except Exception as e:
        log.exception(f"Tarif tugash tekshiruvida xato: {e}")


_TOPIC_ID_SALES_ENV = os.environ.get("TG_TOPIC_ID_SALES", "").strip()


def try_id_sale_command(text: str, message_thread_id):
    """FAQAT 'ID Savdolari' bo'limida ishlaydi (xavfsizlik uchun — boshqa
    joyda yozilgan o'xshash matn ID sotuvga qo'shib yubormasin). Andoza:
    'ID 1010101-120code' yoki 'ID 1010101 - 120 code' (bo'sh joylar,
    tire turlari farqi muhim emas)."""
    if not _TOPIC_ID_SALES_ENV or str(message_thread_id) != _TOPIC_ID_SALES_ENV:
        return None
    m = re.search(r"\bID\s*(\d{7})\s*[-–—]\s*(\d+)\s*code\b", text, re.IGNORECASE)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def add_id_to_marketplace(custom_id: str, price: int) -> tuple[bool, str]:
    """Guruhdan kelgan buyruq bilan IDni kuratsiyalangan bozorga qo'shadi.
    Band bo'lgan yoki allaqachon bozorda bo'lgan IDlarni rad etadi."""
    conn = db_conn(); c = conn.cursor()
    try:
        owned = c.execute("SELECT id FROM users WHERE custom_id=?", (custom_id,)).fetchone()
        if owned:
            return False, f"❌ #{custom_id} allaqachon bir foydalanuvchiga tegishli, bozorga qo'shib bo'lmaydi."
        existing = c.execute("SELECT id, status FROM premium_ids WHERE custom_id=?", (custom_id,)).fetchone()
        if existing:
            return False, f"❌ #{custom_id} allaqachon bozorda ({existing['status']})."
        c.execute(
            "INSERT INTO premium_ids (custom_id, id_type, base_price, status) VALUES (?,?,?,'available')",
            (custom_id, "group_listed", price)
        )
        conn.commit()
        return True, f"✅ #{custom_id} ID bozorga qo'shildi — ⚡ {price:,} CODE.".replace(",", " ")
    finally:
        conn.close()


def _redeem_promo_code_standalone(code: str, user_id: int) -> tuple[bool, str]:
    """coins_purchase.redeem_promo_code() bilan BIR XIL mantiq, lekin
    Flask kontekstisiz, botning o'z db_conn() (raw sqlite3) orqali
    ishlaydi — chunki bot mustaqil jarayon, Flask 'g' obyekti yo'q."""
    if not code or not code.strip():
        return False, "Promo kod kiritilmagan."
    code = code.strip().upper()
    conn = db_conn(); c = conn.cursor()
    try:
        promo = c.execute("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code,)).fetchone()
        if not promo:
            return False, "Promo kod topilmadi yoki faol emas."

        if promo["expires_at"]:
            try:
                import datetime as _dt
                exp = _dt.datetime.fromisoformat(promo["expires_at"])
                if _dt.datetime.now() > exp:
                    return False, "Promo kodning muddati tugagan."
            except Exception:
                pass

        if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
            return False, "Promo kod foydalanish limiti tugagan."

        already = c.execute(
            "SELECT id FROM promo_code_uses WHERE promo_id=? AND user_id=?",
            (promo["id"], user_id)).fetchone()
        if already:
            return False, "Siz bu promo kodni allaqachon ishlatgansiz."

        bonus = promo["bonus_code_amount"] or 0
        if bonus <= 0:
            return False, "Bu promo kodda bonus miqdori sozlanmagan."

        c.execute("UPDATE users SET code_balance=code_balance+? WHERE id=?", (bonus, user_id))
        c.execute(
            "INSERT INTO code_transactions (user_id, amount, reason, ref_id) VALUES (?,?,?,?)",
            (user_id, bonus, "promo_code_bonus", promo["id"])
        )
        c.execute("INSERT INTO promo_code_uses (promo_id, user_id) VALUES (?,?)", (promo["id"], user_id))
        c.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE id=?", (promo["id"],))
        conn.commit()
        return True, f"🎁 Promo kod faollashtirildi! +{bonus:,} CODE balansingizga qo'shildi.".replace(",", " ")
    except Exception as e:
        log.exception(f"Standalone promo kod xatosi: {e}")
        return False, "⚠️ Xatolik yuz berdi, saytdan urinib ko'ring."
    finally:
        conn.close()


def handle_group_text(chat_id, text, message_thread_id=None):
    """ADMIN_CHAT_ID guruhida yozilgan xabarlarni qayta ishlaydi — shaxsiy
    (private) chat bilan aralashtirmaydi. Funksiyalar: valyuta hisoblagich,
    'Xisobot' buyrug'i, va 'ID Savdolari' bo'limida ID bozorga qo'shish.
    Boshqa har qanday oddiy suhbatga bot aralashmaydi (jim turadi)."""
    stripped = text.strip()
    extra = {"message_thread_id": message_thread_id} if message_thread_id else {}

    if stripped.lower() in ("xisobot", "hisobot", "/xisobot", "/hisobot"):
        report = build_xisobot_report()
        tg_request("sendMessage", chat_id=chat_id, text=report, parse_mode="Markdown", **extra)
        return

    id_sale = try_id_sale_command(stripped, message_thread_id)
    if id_sale:
        custom_id, price = id_sale
        ok, msg = add_id_to_marketplace(custom_id, price)
        tg_request("sendMessage", chat_id=chat_id, text=msg, **extra)
        return

    calc_result = try_currency_calc(stripped)
    if calc_result:
        tg_request("sendMessage", chat_id=chat_id, text=calc_result, **extra)
        return


def handle_update(update):
    chat_id_for_error = None
    try:
        if "callback_query" in update:
            chat_id_for_error = update["callback_query"]["message"]["chat"]["id"]
            handle_callback(update["callback_query"]); return
        msg = update.get("message")
        if not msg: return
        chat_id = msg["chat"]["id"]
        chat_id_for_error = chat_id
        chat_type = msg["chat"].get("type", "private")
        user_info = msg.get("from", {})
        if "photo" in msg:
            handle_photo(msg); return
        if "text" in msg:
            # ADMIN GURUHIDA yozilgan xabarlar — shaxsiy (private) suhbat
            # holat-mashinasiga UMUMAN kirmaydi, alohida, oddiy funksiya
            # bilan ishlanadi (valyuta hisoblagich + Xisobot).
            if chat_type in ("group", "supergroup") and ADMIN_CHAT_ID and str(chat_id) == ADMIN_CHAT_ID:
                handle_group_text(chat_id, msg["text"], msg.get("message_thread_id"))
                return
            handle_text(chat_id, msg["text"], user_info); return
    except Exception as e:
        log.exception(f"Error handling update: {e}")
        # Foydalanuvchi "jim qolib" botni tashlab ketmasligi uchun xabar yuboramiz
        if chat_id_for_error:
            try:
                tg_send_message(
                    chat_id_for_error,
                    "⚠️ Texnik xatolik yuz berdi. Iltimos /start buyrug'ini qayta yuboring.",
                    reply_markup=None
                )
            except Exception:
                pass


# =================================================================
# MAIN LOOP — uzun polling
# =================================================================
def main():
    if not TOKEN:
        log.error("TELEGRAM_BOT_TOKEN topilmadi. .env faylga qo'shing!")
        return

    from db import USE_POSTGRES
    if not USE_POSTGRES:
        _ensure_bot_schema()
    log.info("CYBER SHATS Telegram bot ishga tushdi...")
    log.info("BOT_CODE_VERSION: 2026-07-22-id-lookup-fix (custom_id + oddiy id fallback bilan)")
    # Webhook'ni bekor qilish (agar oldin sozlangan bo'lsa)
    try:
        requests.get(f"{API_BASE}/deleteWebhook", timeout=10)
    except Exception:
        pass

    # Mini App (Web App) doimiy menyu tugmasini sozlash — bot har safar
    # ishga tushganda AVTOMATIK qayta o'rnatiladi, qo'lda sozlash shart
    # emas. FAQAT https:// manzil bo'lsa ishlaydi (Telegram cheklovi).
    if SITE_BASE_URL.startswith("https://"):
        try:
            r = requests.post(f"{API_BASE}/setChatMenuButton", json={
                "menu_button": {"type": "web_app", "text": "🚀 Ilova",
                                "web_app": {"url": f"{SITE_BASE_URL}/webapp"}}
            }, timeout=10)
            if r.json().get("ok"):
                log.info(f"Mini App menyu tugmasi sozlandi: {SITE_BASE_URL}/webapp")
            else:
                log.warning(f"Mini App menyu tugmasini sozlashda muammo: {r.json()}")
        except Exception as e:
            log.warning(f"Mini App menyu tugmasini sozlashda xato: {e}")
    else:
        log.warning("SITE_BASE_URL https:// bilan boshlanmagani uchun Mini App tugmasi sozlanmadi.")

    offset = 0
    _last_expiry_check = 0
    _last_frequent_check = 0   # 10 daqiqada bir: past balans, javobsiz so'rovlar
    _last_daily_check = 0      # 1 soatda bir: kunlik xisobot (soat 9 tekshiruvi), zaxira, yangi kurs
    _last_weekly_check = 0     # 6 soatda bir: faol emaslar, chiptalar, do'stlik, koleksiya, email

    def _safe_call(fn, label):
        """MUHIM (tuzatilgan JIDDIY XATO): avval BARCHA davriy funksiyalar
        BITTA himoyasiz blok ichida chaqirilardi. Agar ULARDAN BIRI (masalan
        id_reservations jadvali hali mavjud bo'lmagani uchun
        check_expired_id_reservations) xato bersa — QOLGAN FUNKSIYALAR
        chaqirilmasdan qolardi, VA _last_..._check YANGILANMASDI —
        natijada bot HAR ~5 SONIYADA (keyingi poll siklida) xuddi shu
        xatoni QAYTA-QAYTA takrorlab, cheksiz halokat tsikliga (crash
        loop) tushib qolardi (buni haqiqiy log skrinshotida ko'rdik).
        Endi har bir funksiya ALOHIDA himoyalangan — bittasi xato bersa,
        faqat O'SHA BITTASI o'tkazib yuboriladi, qolganlari BARIBIR
        ishlaydi."""
        try:
            fn()
        except Exception as e:
            log.error(f"Davriy tekshiruv xato ({label}): {e}")

    while True:
        try:
            # Tarif tugash ogohlantirishi — har ~10 daqiqada bir marta
            # tekshiriladi (har poll siklida emas, bazaga ortiqcha
            # yuklama bermaslik uchun).
            if time.time() - _last_expiry_check > 600:
                _safe_call(check_and_notify_plan_expirations, "check_and_notify_plan_expirations")
                _last_expiry_check = time.time()

            # Tez-tez tekshiriladigan avtomatlashtirishlar (10 daqiqa) —
            # 'send_daily_report' ATAYLAB shu yerda (1 soat emas, 10 daqiqa)
            # — shunda soat 09:00 bo'lgach, KO'PI BILAN 10 daqiqa ichida
            # xisobot guruhga tushadi, 1 soatgacha kechikmaydi.
            if time.time() - _last_frequent_check > 600:
                _safe_call(check_low_treasury_balance, "check_low_treasury_balance")
                _safe_call(check_unanswered_requests, "check_unanswered_requests")
                _safe_call(check_expired_id_reservations, "check_expired_id_reservations")
                _safe_call(send_daily_report, "send_daily_report")
                _last_frequent_check = time.time()

            # Kuniga bir necha marta tekshiriladiganlar (1 soat) — bular
            # aniq vaqtga bog'liq emas, shuning uchun 1 soat kifoya
            if time.time() - _last_daily_check > 3600:
                _safe_call(backup_database, "backup_database")
                _safe_call(check_new_courses, "check_new_courses")
                _last_daily_check = time.time()

            # Kamdan-kam (6 soat) tekshiriladigan, "sekin" eslatmalar
            if time.time() - _last_weekly_check > 21600:
                _safe_call(check_inactive_users, "check_inactive_users")
                _safe_call(check_unused_tickets, "check_unused_tickets")
                _safe_call(check_unanswered_friend_requests, "check_unanswered_friend_requests")
                _safe_call(check_collection_progress_reminder, "check_collection_progress_reminder")
                _safe_call(check_unverified_emails, "check_unverified_emails")
                _last_weekly_check = time.time()

            r = requests.get(f"{API_BASE}/getUpdates",
                             params={"offset": offset, "timeout": 30}, timeout=40)
            data = r.json()
            if not data.get("ok"):
                # MUHIM: Telegram 409 ("Conflict: terminated by other getUpdates
                # request") qaytarsa — bu degani BIR NECHTA bot nusxasi (masalan
                # bitta noutbukda/serverda, ikkinchisi Railway'da) BIR VAQTDA
                # bitta BOT_TOKEN bilan ishga tushirilgan. Bu holatda bot
                # "ishlab-to'xtab-ishlab" (qotib qolayotgandek) ko'rinadi, chunki
                # ikkala nusxa navbat bilan bir-birining ulanishini uzib qo'yadi.
                # YECHIM: faqat BITTA joyda (yoki faqat Railway'da, yoki faqat
                # lokal kompyuterda — ikkalasida EMAS) ishga tushiring.
                if r.status_code == 409 or "Conflict" in str(data.get("description", "")):
                    log.error(
                        "❌ 409 CONFLICT: Ushbu BOT_TOKEN bilan BOSHQA bir nusxa "
                        "(masalan boshqa serverda yoki lokal kompyuterda) HAM ishlab "
                        "turibdi! Bitta bot faqat BITTA joyda ishga tushirilishi kerak. "
                        "Barcha boshqa ishga tushirilgan nusxalarni to'xtating "
                        "(Railway'da eski deploy, lokal terminal/screen/tmux seansi va h.k.)."
                    )
                    time.sleep(15); continue
                log.warning(f"getUpdates not ok: {data}")
                time.sleep(5); continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)
        except KeyboardInterrupt:
            log.info("Bot to'xtatildi (Ctrl+C)")
            break
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            log.exception(f"Loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    # BARQARORLIK: agar main() ichidagi barcha himoyalarga qaramay biror
    # kutilmagan xato butun jarayonni to'xtatib qo'ysa (masalan xotira
    # yetishmasligi, tarmoq drayveri xatosi va h.k.), bot BUTUNLAY "o'lib"
    # qolmasin — shu tashqi tsikl uni avtomatik qayta ishga tushiradi.
    while True:
        try:
            main()
            break  # main() o'zi normal (Ctrl+C) to'xtagan bo'lsa, chiqamiz
        except Exception as e:
            log.exception(f"Bot kutilmagan xato bilan to'xtadi, 10 soniyadan keyin "
                          f"avtomatik qayta ishga tushiriladi: {e}")
            time.sleep(10)
