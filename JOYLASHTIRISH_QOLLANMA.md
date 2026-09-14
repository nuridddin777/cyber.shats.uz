# CYBER SHATS — O'zgarishlarni serverga qanday joylash kerak

## 🚀 YANGI: Telegram Mini App (to'liq ilova sahifasi)

Endi botda oddiy tugmalar o'rniga **to'liq ilova sahifasi** ochiladigan
"🚀 Ilova" tugmasi bor (bot pastidagi doimiy menyu tugmasi + asosiy
menyudagi birinchi tugma). Bu ishlashi uchun **`.env` faylidagi
`SITE_BASE_URL` HAQIQIY https:// manzilingiz bilan to'g'ri bo'lishi
SHART**:

```
SITE_BASE_URL=https://cyber.shats.uz
```

**MUHIM**: Telegram Mini App'lar FAQAT `https://` (SSL/HTTPS) bilan
ishlaydi — agar serveringizda SSL sozlanmagan bo'lsa, "🚀 Ilova" tugmasi
Telegram tomonidan ko'rsatilmaydi (avtomatik yashiriladi, bot
buzilmaydi, faqat bu funksiya ishlamaydi). SSL sozlangach, botni qayta
ishga tushirsangiz, tugma o'zi qayta paydo bo'ladi.

## 📢 Telegram guruh bo'limlari (topics) — SOZLANGAN VA TEST QILINGAN

`.env` faylida quyidagi 3 ta bo'lim ID'si allaqachon yozilgan (2026-08-21
kuni yaratilgan va haqiqiy test xabarlari bilan tasdiqlangan):

```
TG_TOPIC_FINANCE=53       # CODE xaridlari + tarif sotuvlari
TG_TOPIC_ID_SALES=54      # ID savdolari
TG_TOPIC_NEWS=55          # Yangi ro'yxatdan o'tganlar
```

Bular — guruhingizdagi (`SHATS CYBER TNB`) 3 ta yangi bo'lim: **"💰 CODE va
Tarif Xisobotlari"**, **"🆔 ID Savdolari"**, **"🎉 Yangi Ro'yxatdan
O'tganlar"**. Agar bo'limlarni o'chirib/qayta yaratsangiz, yangi
`message_thread_id`larni guruh sozlamalaridan olib, shu joyga yozing.

## 🛡️ YANGI: ma'lumotlar bazasi endi AVTOMATIK himoyalangan

**Muhim yangilik**: avval har safar yangi zip serverga qo'yilganda, ichidagi
`database/cyber_shats.db` fayli (sinov muhitidagi baza) SERVERDAGI HAQIQIY,
foydalanuvchilar ro'yxatdan o'tgan bazani ustidan yozib yuborishi mumkin edi.

**Endi bu tuzatildi**: zip ichida baza umuman `cyber_shats.db` nomi bilan
KELMAYDI — u `database/cyber_shats.db.SEED` (zararsiz namunaviy fayl) nomi
bilan keladi. Sayt ishga tushganda:

- Agar serveringizda **HAQIQIY baza allaqachon bo'lsa** — unga HECH QANDAY
  tarzda tegilmaydi, garchi siz butun papkani ustidan almashtirsangiz ham.
- Faqat **haqiqatan ham birinchi marta o'rnatilayotgan** bo'lsa (baza umuman
  yo'q bo'lsa) — o'shandagina namunaviy bazadan nusxa olinadi.

Ya'ni endi **zipni to'g'ridan-to'g'ri, hech narsadan qo'rqmasdan, butun
papkani almashtirib qo'yishingiz mumkin** — foydalanuvchilaringiz hech qachon
yo'qolmaydi. (Sinab ko'rish uchun: sayt konsolida `[BOOTSTRAP]` bilan
boshlanuvchi qatorni qidiring — u aynan nima bo'lganini ko'rsatadi.)

## ⚠️ MUHIM: cyber.shats.uz hali YANGILANMAGAN

Agar siz `cyber.shats.uz` saytini brauzerda ochib tekshirsangiz — u yerda hali
**ESKI kod** ishlab turibdi. Men bergan barcha o'zgarishlar (dizayn, yo'nalish
tanlash, amaliy mashqlar, AI, admin tizimi va h.k.) faqat **shu zip fayl
ichida** — ular hali sizning haqiqiy serveringizga YUKLANMAGAN.

Zip faylni ochib, shunchaki serverga "qo'yish" YETARLI EMAS — quyidagi
qadamlarni bajarish kerak:

## Joylashtirish qadamlari

1. **Zip faylni serveringizga yuklang** (masalan `/var/www/cyber-shats` yoki
   joriy loyiha papkangiz o'rniga) va oching (`unzip cyber-shats.zip`).

2. **Muhit fayli (`.env`)ni tekshiring** — eski serveringizda ishlatilayotgan
   `.env` faylini (SMTP, GEMINI_API_KEY, ANTHROPIC_API_KEY va boshqa maxfiy
   kalitlar) yangi papkaga ko'chiring — zip ichidagi `.env` faqat NAMUNA.

3. **Kutubxonalarni yangilang:**
   ```
   pip install -r requirements.txt --upgrade
   ```

4. **Serverni qayta ishga tushiring** (masalan systemd, gunicorn yoki
   `python3 app.py`) — bazaviy migratsiyalar (v45–v49) ilova ishga
   tushganda AVTOMATIK bajariladi, qo'lda hech narsa ishga tushirish shart
   emas.

5. **Brauzer keshini tozalang** (Ctrl+Shift+R / Cmd+Shift+R) — CSS fayllar
   o'zgargani uchun eski kesh yangi ranglarni ko'rsatmasligi mumkin.

6. Endi `cyber.shats.uz`ni qayta oching — barcha o'zgarishlar (kulrang+qizil
   dizayn, yo'nalish tanlash, amaliy mashqlar, AI, 3 darajali admin) ko'rinishi
   kerak.

## Agar hosting-provayder orqali joylashtirilsa

Agar loyiha Render/Railway/VPS kabi joyda git orqali deploy qilinsa — zip
ichidagi fayllarni git repo-ingizga commit qilib, push qilishingiz kifoya,
qolgani avtomatik ishlaydi.

## ⚠️ MUHIM: Telegram bot alohida, DOIMIY ishlab turishi kerak

Ko'p uchraydigan chalkashlik: **`app.py` (asosiy sayt) ishga tushishi —
Telegram botning ham ishlashini anglatmaydi!** Bular ikkita ALOHIDA
dastur:

- `app.py` — veb-sayt (brauzerda ochiladigan qism)
- `telegram_bot.py` — Telegram bot (foydalanuvchi botga yozganda javob
  beradigan, guruhga bildirishnoma yuboradigan qism)

Agar botga yozganingizda javob kelmasa yoki guruhga bildirishnomalar
tushmasa — buning eng ehtimoliy sababi: **`telegram_bot.py` serveringizda
ishlab turmagan**. Uni sayt bilan bir vaqtda, lekin ALOHIDA doimiy jarayon
sifatida ishga tushirish kerak:

```bash
# Sinov uchun (terminal ochiq turishi kerak):
python3 telegram_bot.py

# Doimiy ishlashi uchun (systemd misoli, Linux serverda):
sudo tee /etc/systemd/system/shats-telegram-bot.service << 'SVCEOF'
[Unit]
Description=CYBER SHATS Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/cyber-shats
ExecStart=/usr/bin/python3 telegram_bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable shats-telegram-bot
sudo systemctl start shats-telegram-bot

# Holatini tekshirish:
sudo systemctl status shats-telegram-bot
```

Agar Render/Railway kabi platforma ishlatilsa — u yerda **ikkinchi,
alohida "Worker" (background service)** yaratib, `python3 telegram_bot.py`
buyrug'ini shu workerga bering (web service emas — u faqat `app.py` uchun).


## Savol tug'ilsa

Aynan qaysi usulda (VPS/systemd, Render, Railway, boshqa) joylashtirilganini
ayting — sizga mos aniq buyruqlarni yozib beraman.
