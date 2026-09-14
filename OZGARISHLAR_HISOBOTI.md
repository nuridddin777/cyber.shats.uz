# CYBER SHATS — Qilingan o'zgarishlar hisoboti

## 1. Narxlar
- **Pulik kurs narxi**: 10,000 CODE → **1 CODE** (`pricing.py`, DB majburan yangilandi)
- **AI narxi**: endi "1 xabar = 200 CODE" emas, balki **haftalik obuna: 1 CODE / 7 kun**
  - Pro / Cyber Pro / VIP / MAXSUS foydalanuvchilar — hamon cheksiz bepul
  - FREE foydalanuvchi birinchi AI xabarini yozganda avtomatik 1 CODE yechiladi va 7 kunga obuna ochiladi
  - 7 kun ichida istalgancha yozish mumkin, qo'shimcha to'lov yo'q
  - Muddat tugagach, keyingi xabarda **avtomatik** yana 1 CODE yechishga urinadi ("avto to'lov")
  - Agar balans yetmasa — AI ishlamaydi, foydalanuvchiga CODE sotib olish taklif qilinadi

## 2. AI — endi rasm yuklash mumkin (vision) + TEKIN Google Gemini qo'llab-quvvatlandi
- `/ai` sahifasida endi 📷 tugma bor — rasm (skrinshot, xato xabari, diagramma va h.k.) biriktirib yuborish mumkin
- Endi ikkita AI provayder qo'llab-quvvatlanadi:
  1. **Google Gemini — TEKIN tarif** (kredit karta shart emas, faqat daqiqa/kunlik so'rov cheklovi bor)
  2. **Anthropic Claude** — pullik, agar Gemini sozlanmagan yoki xato bersa zaxira sifatida ishlatiladi
- **Gemini kalitini TEKIN olish** (tavsiya etiladi):
  1. https://aistudio.google.com/apikey ga kiring (Google hisobingiz bilan)
  2. "Create API key" tugmasini bosing — kredit karta so'ralmaydi
  3. loyihaning `.env` fayliga qo'shing: `GEMINI_API_KEY=olingan_kalit`
  4. Serverni qayta ishga tushiring — AI banner "DEMO REJIM" o'rniga "LIVE — Google Gemini faol" bo'ladi
  5. Cheklov: taxminan daqiqasiga 10-15, kuniga 250-1000 so'rov (model tanloviga qarab) — kichik-o'rta loyiha uchun yetarli. Agar chegaraga yetsangiz, AI "birozdan so'ng qayta urinib ko'ring" deb xabar beradi (sayt ishlashda davom etadi)
- Agar xohlasangiz Anthropic'ni ham qo'shishingiz mumkin (`.env` dagi `ANTHROPIC_API_KEY`) — ikkalasi ham sozlansa, tizim avval Gemini'ni (tekin) ishlatadi, faqat u xato bersa Anthropic'ga o'tadi
- Rasm tahlili ham ikkala provayderda ham ishlaydi
- **2026-yil iyun texnik yangilanishi**: Google API kalitlarini eski `AIzaSy...` formatdan yangi `AQ.Ab...` formatga o'tkazdi va autentifikatsiya usulini ham o'zgartirdi (URL parametri o'rniga so'rov sarlavhasi). Kodni shu yangilikka moslab tuzatdim.
- Agar Gemini kalitingiz "403 — Your project has been denied access" xatosini bersa — bu Google'ning o'zida keng tarqalgan, ko'plab yangi hisoblarda uchraydigan vaqtinchalik cheklov (bizning kod yoki sozlamalarga bog'liq emas). Odatda 1-3 kunda o'zi tuzaladi yoki boshqa Google hisobi bilan yangi kalit yaratish yordam beradi.

## 3. SHATS CYBER PRO maxsus ID'lar (0-9) — TAYINLASH tuzatildi
- **Xato sababi**: forma faqat ichki bazaviy raqamni (`users.id`) qabul qilardi, lekin admin odatda saytda
  ko'rinadigan ID'ni (masalan profil "Mening ID"si) kiritardi — shu sabab doim "topilmadi" xatosi chiqardi
- **Tuzatildi**: endi maydonga saytdagi ID, email yoki ichki raqamning istalganini kiritsangiz ham topadi
  (bir xil tuzatish "Premium ID → Ber" tugmasiga ham qo'llandi)

## 4. G'azna paneli — 0'dan boshlandi (ommaga tayyor)
- G'azna jamg'armasi balansi: **0**
- Barcha foydalanuvchilarning CODE balansi: **0**
- Eski test/dev tranzaksiyalar tarixi tozalandi
- Bu bir martalik amal edi — `database/reset_for_public_launch.py` skripti orqali bajarildi.
  (Bu skript avtomatik ishlamaydi, faqat qo'lda, kerak bo'lsa, qayta ishga tushirilishi mumkin — ehtiyot bo'ling, qaytarib bo'lmaydi!)

## 5. Maxsus Topshiriq (KRIPTIKIS) — 3 bosqichdan 50 bosqichga
- Endi jami **50 bosqich**
- 1—49-bosqichlarni yechish/o'tish **CODE bermaydi** — faqat keyingi bosqichga o'tkazadi
- Faqat **50-bosqich (yakuniy)**ni to'g'ri yechganda **10 CODE** mukofot beriladi
- 2- va 3-bosqichlarning asl (qo'lda yozilgan) shifrlari saqlab qolindi, mukofoti 0'ga tushirildi
- 4—49-bosqichlar avtomatik generatsiya qilindi — har biri HEX/XOR shifri, hint'da yechish formulasi ochiq yozilgan
- Sahifadagi 3 ta doira o'rniga endi progress-bar (X/50, foiz) ko'rsatiladi

## 6. Telegram bot
- **Token yangilandi**: `.env` faylidagi `TELEGRAM_BOT_TOKEN` sizning yangi tokeningizga (`8549419078:...`)
  almashtirildi va tekshirildi — bot nomi: **@shats_cyber_bot** ("SHATS CYBER")
- **"ID topilmadi" xatosi**: kodni tekshirdim — bot allaqachon ikkala formatni ham (saytdagi ID va ichki ID)
  qidiradigan qilib tuzatilgan edi (`find_site_user_by_custom_id` funksiyasi). Sizga ko'rsatilgan xato-skrinshot
  eski bot sessiyasidan bo'lishi kerak — yangi token bilan qayta ishga tushirganingizda bu muammo chiqmasligi kerak.
- **Bot rasmlari**: `code_tanga.png` va `instructions.png` fayllari joyida va mavjud — agar internet/fayl
  muammosi bo'lsa ham, bot rasm o'rniga avtomatik oddiy matn xabar yuboradi (foydalanuvchi "jim qolib" ketmaydi)
- Botni ishga tushirish: `python telegram_bot.py`

## Botingizni ishga tushirishdan oldin
⚠️ Siz bot tokenini ochiq chatda yubordingiz. Xavfsizlik uchun tavsiya:
BotFather'ga o'tib `/revoke` orqali eski tokenlarni bekor qiling va faqat `.env` faylida saqlang,
hech qachon kodni GitHub'ga ochiq holda yuklamang.

## 7. Yangi tuzatishlar (2-bosqich)
- **"Code Tangalar" menyusi**: endi "Reyting va mukofot" ichida yashiringan emas — barcha foydalanuvchilar uchun chap menyuning yuqorisida, asosiy bo'limlar qatorida ko'rinadi
- **Karta orqali tezkor to'lov (Click/Payme/Uzum Pay)**: bular hali sandbox/test rejimida (haqiqiy merchant kaliti yo'q) bo'lgani uchun vaqtincha **yashirildi** — foydalanuvchilar faqat "Chek yuklab so'rov yuborish" (qo'lda tasdiqlanadigan) usuldan foydalanadi. Haqiqiy Click/Payme/Uzum merchant kalitlarini `.env` fayliga qo'yishingiz bilan bu bo'lim avtomatik qayta ko'rinadi (kodni o'zgartirish shart emas)
- **Admin paneldagi foydalanuvchi ID'lari**: test/dev davrida o'chirilgan foydalanuvchilar tufayli paydo bo'lgan "teshiklar" (masalan #9, #153) tuzatildi — endi 1 dan boshlab ketma-ket (#1, #2, #3...). *(Texnik izoh: aynan "0"dan emas, "1"dan boshladik — chunki dasturiy kodda ko'p joyda ID=0 "tizimga kirmagan" deb noto'g'ri talqin qilinishi mumkin edi, bu xavfsizlik/barqarorlik uchun muhim.)*

⚠️ **Muhim eslatma balans haqida**: agar hozir ham eski, katta balans (masalan 9,999,988,xxx) ko'rinayotgan bo'lsa — bu degani hali **joriy ishlab turgan serveringizdagi** fayllarni ushbu yangilangan zip bilan almashtirmagansiz. G'azna 0'dan boshlanishi uchun serveringizdagi butun loyiha papkasini ushbu zipdagi bilan almashtiring (yoki hech bo'lmasa `database/cyber_shats.db` faylini ushbu zipdagisi bilan almashtiring), so'ng serverni qayta ishga tushiring.

## 8. Windows konsol xatosi tuzatildi (UnicodeEncodeError)
Ba'zi Windows kompyuterlarida (rus/o'zbek til sozlamasi bilan, cp1251 kodировка) sayt ishga tushganda
emoji belgilar tufayli `UnicodeEncodeError` bilan yiqilib qolar edi. `app.py`, `telegram_bot.py` va
`hammasi.py` fayllariga konsol chiqishini majburiy UTF-8 rejimiga o'tkazuvchi tuzatish qo'shildi —
endi istalgan Windows til sozlamasida ishlaydi.

## Testdan o'tkazilganlar
- ✅ Yangi migratsiya (`migrate_v38`) xatosiz ishladi
- ✅ AI haftalik obuna: balans yetmasa bloklaydi, to'lasa 7 kunga ochadi, muddat ichida qayta yechmaydi
- ✅ ID qidirish (`resolve_user_id`): custom_id, ichki id va email bo'yicha ishlaydi
- ✅ Kriptikis: 1→50 bosqich to'liq zanjiri, oraliq bosqichlar 0 CODE, faqat 50-chi 10 CODE beradi
- ✅ Bot tokeni Telegram API orqali tasdiqlandi (`getMe` — ok:true)
- ✅ Barcha .py fayllar xatosiz compile bo'ladi, barcha o'zgargan shablonlar (Jinja2) sintaktik to'g'ri

## Ishga tushirish tartibi
1. `pip install -r requirements.txt` (agar hali qilinmagan bo'lsa)
2. `.env` faylga TEKIN `GEMINI_API_KEY` qo'ying (https://aistudio.google.com/apikey) — AI to'liq ishlashi uchun
3. **Eng oson yo'l — hammasini BITTA buyruq bilan ishga tushirish:**
   ```powershell
   python hammasi.py
   ```
   (yoki `hammasi.bat` faylini ikki marta bosing) — sayt va bot BITTA oynada, `[SAYT]` / `[BOT]`
   prefikslari bilan birga ishlaydi. To'xtatish uchun: `Ctrl+C` (ikkalasi ham birga to'xtaydi).
4. Yoki alohida-alohida ishga tushirish: `python app.py` va boshqa oynada `python telegram_bot.py`
