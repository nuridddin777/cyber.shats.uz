"""
CYBER SHATS — BIRLASHTIRILGAN ISHGA TUSHIRISH (bot + veb-sayt BITTA jarayonda)
================================================================================
MUHIM SABAB (Railway'da "ID topilmadi" xatosining ASOSIY manbai bo'lishi
mumkin): agar Telegram bot (telegram_bot.py) va veb-sayt (app.py) Railway'da
IKKITA ALOHIDA xizmat (service) sifatida ishga tushirilsa, ularning har biri
o'zining ALOHIDA, bir-biridan mustaqil fayl tizimiga (filesystem) ega bo'ladi.
SQLite bazasi (database/cyber_shats.db) oddiy FAYL bo'lgani uchun, ikkala
xizmat aslida IKKITA BUTUNLAY BOSHQA-BOSHQA nusxa bilan ishlaydi:
  - Veb-saytda ro'yxatdan o'tgan foydalanuvchi shu saytning faylida saqlanadi
  - Bot esa O'ZINING (bo'sh yoki eskirgan) faylidan qidiradi
  - Natija: bot uchun bunday foydalanuvchi "hech qachon mavjud bo'lmagan"
    bo'lib ko'rinadi — garchi u saytda haqiqatan ham ro'yxatdan o'tgan bo'lsa ham.

YECHIM: bot va veb-saytni BITTA jarayonda (bitta Railway xizmatida) ishga
tushiramiz — shunda ikkalasi ham AYNAN BITTA database/cyber_shats.db fayliga
ulanadi, va bu muammo BUTUNLAY yo'qoladi.

TEZLIK HAQIDA: Flask'ning o'zidagi "dev server" (`python run_all.py`) faqat
sinov uchun mo'ljallangan — bir vaqtning o'zida bitta so'rovni qayta ishlaydi
(agar threaded=True qo'yilmasa) va yuklama ostida sekinlashadi. SHU SABABLI
loyiha "sekinlashib qolgan" bo'lishi mumkin edi. Haqiqiy tezlik uchun
GUNICORN (production darajasidagi WSGI server) orqali ishga tushirish TAVSIYA
ETILADI — bir nechta so'rovni chinakam parallel qayta ishlaydi.

ISHLATISH (ikkala usul ham botni ishga tushiradi, ikkalasi ham bitta bazaga
ulanadi):

  1) Oddiy (kichik loyihalar uchun yetarli):
       python run_all.py

  2) Tezroq, PRODUCTION uchun tavsiya etiladigan (gunicorn kerak: requirements.txt'da bor):
       gunicorn --workers 1 --threads 8 --timeout 60 run_all:app

     MUHIM: --workers albatta 1 bo'lishi kerak! Agar 1 dan ko'p worker
     ishlatilsa, HAR BIR worker o'zining Telegram bot nusxasini ishga
     tushiradi — bu esa "409 Conflict" xatosiga (bot qotib qolishga) olib
     keladi. Ko'proq parallellik uchun --workers emas, --threads sonini
     oshiring (masalan --threads 16).

Railway'da Procfile orqali (allaqachon sozlangan):
    web: gunicorn --workers 1 --threads 8 --timeout 60 run_all:app
"""
import os
import threading
import logging

log = logging.getLogger("run_all")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

_bot_thread_started = False
_bot_thread_lock = threading.Lock()


def _run_bot_forever():
    """Telegram botni alohida (fon) oqimda, o'zining ichki avtomatik-qayta-
    ishga-tushirish himoyasi bilan ishga tushiradi. Bu funksiya HECH QACHON
    qaytmaydi (telegram_bot.py o'zining tashqi while-True qatlamiga ega)."""
    import telegram_bot
    while True:
        try:
            telegram_bot.main()
            break  # main() o'zi tinch to'xtagan bo'lsa (masalan token yo'q)
        except Exception as e:
            log.exception(f"[BOT] Kutilmagan xato, 10 soniyadan keyin qayta ishga tushiriladi: {e}")
            import time
            time.sleep(10)


def _start_bot_thread_once():
    """Botni fon oqimida ISHGA TUSHIRADI — lekin faqat BIR MARTA (thread-safe).
    Bu funksiya modul import qilinganda ham (gunicorn orqali) chaqiriladi,
    shuning uchun qulf (lock) bilan himoyalangan."""
    global _bot_thread_started
    with _bot_thread_lock:
        if _bot_thread_started:
            return
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        if not bot_token:
            log.warning("TELEGRAM_BOT_TOKEN topilmadi — bot ISHGA TUSHIRILMAYDI, faqat veb-sayt ishlaydi.")
            _bot_thread_started = True
            return
        log.info("Telegram bot fon oqimida ishga tushirilmoqda (bitta jarayon, bitta baza)...")
        bot_thread = threading.Thread(target=_run_bot_forever, daemon=True, name="telegram-bot")
        bot_thread.start()
        _bot_thread_started = True


# ---------------------------------------------------------------------
# MODUL DARAJASIDA ishga tushirish — bu gunicorn "run_all:app" orqali
# import qilinganda HAM avtomatik ishlaydi (faqat `python run_all.py`
# qilib to'g'ridan-to'g'ri ishga tushirilgandagina emas).
# ---------------------------------------------------------------------
_start_bot_thread_once()

import app as webapp
app = webapp.app  # gunicorn shu nomni ("run_all:app") qidiradi


def main():
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    log.info(f"Veb-sayt ishga tushirilmoqda (port={port})...")
    # threaded=True: bir vaqtda bir nechta so'rovni PARALLEL qayta ishlash
    # uchun (avval bitta so'rov tugagunча boshqasi kutib turardi — sayt
    # "sekin" ishlayotgandek tuyulishining asosiy sababi shu edi).
    # Eslatma: gunicorn ishlatilsa, bu funksiya umuman chaqirilmaydi —
    # gunicorn yuqoridagi `app` obyektini o'zi to'g'ridan-to'g'ri ishga
    # tushiradi, ancha tezroq va barqarorroq.
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)


if __name__ == "__main__":
    main()
