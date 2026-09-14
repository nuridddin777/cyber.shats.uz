# Xavfsizlik va tekshiruv hisoboti — 2026-07-15

Ushbu fayl shu sanada o'tkazilgan to'liq loyiha tekshiruvi va kiritilgan
xavfsizlik yaxshilanishlarini hujjatlashtiradi.

## 1) Nima tekshirildi (funksionallik)

- **Python sintaksisi**: barcha `.py` fayllar (`ast.parse`) — xatosiz ✅
- **Jinja shablon sintaksisi**: `templates/` ichidagi barcha `.html` fayllar — xatosiz ✅
- **Ilova ishga tushishi**: `app.py` to'liq yuklandi, 349 route ro'yxatdan o'tdi ✅
- **Tugma/havola bog'lanishi**: shablonlardagi barcha `url_for(...)` chaqiruvlari
  (100+ shablon, 349 route bo'yicha) haqiqiy route nomlariga solishtirildi —
  **0 ta buzilgan havola/tugma topildi** ✅
- **Har bir sahifa jonli test qilindi**: mehmon, oddiy talaba va admin sifatida
  barcha GET sahifalar (parametrsiz va parametrli) so'raldi — **0 ta server
  xatosi (500)** ✅
- **To'liq login → dashboard va register oqimlari** — ishlaydi ✅
- **To'lov webhook'lari (Click/Payme/Uzum)** — signature tekshiruvi bilan
  ishlayotgani tasdiqlandi ✅

Xulosa: loyihaning FUNKSIONAL qismi (backend routing, shablonlar, tugmalar,
formalar) yaxshi holatda, sinish/buzilish topilmadi.

## 2) Xavfsizlikda topilgan va TUZATILGAN muammolar

1. **CSRF (Cross-Site Request Forgery) himoyasi yo'q edi** — asosiy
   ilovada (`app.py`, 142 ta POST route) hech qanday CSRF tokeni
   tekshirilmagan edi (faqat `edu_orgs` blueprint'ida bor edi).
   → Yangi `csrf_protect.py` moduli qo'shildi: har bir sessiya uchun
   tasodifiy token, barcha holat-o'zgartiruvchi so'rovlarda (`POST/PUT/
   PATCH/DELETE`) tekshiriladi. `base.html`ga JS qo'shildi — barcha
   formalar va `fetch()` so'rovlariga tokenni **avtomatik** qo'shadi,
   shuning uchun 80+ shablonni qo'lda o'zgartirish shart bo'lmadi.
   To'lov agregatorlari webhook'lari (`/payment/webhook/*`) va
   `edu_orgs` (o'zining CSRF tizimi bor) ataylab istisno qilindi.

2. **Sessiya cookie sozlamalari kuchaytirildi**: `HttpOnly=True`,
   `SameSite=Lax` yoqildi. `Secure` — production HTTPS'da
   `FORCE_HTTPS_COOKIES=1` orqali yoqiladi (lokal http test buzilmasligi
   uchun standart holatda o'chiq).

3. **Xavfsizlik HTTP sarlavhalari qo'shildi** (`after_request`):
   `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`,
   `Referrer-Policy`, `Permissions-Policy`.

4. **To'lov imzolarini solishtirish** (Click/Payme/Uzum) `==` o'rniga
   `hmac.compare_digest` bilan almashtirildi — timing-attack xavfini
   yo'qotadi. Xuddi shu tuzatish `edu_orgs` CSRF tekshiruviga ham
   qo'llanildi.

5. **Global rate-limit va IP-bloklash** endi faqat login sahifasida emas,
   BARCHA so'rovlarda ishlaydi (`before_request`), statik fayllar bundan
   mustasno.

## 3) Ataylab qo'shilmagan narsa (va sababi)

- `security.py` ichidagi tayyor SQLi/XSS **naqsh skaneri** (`scan_request`)
  global qo'llanilmadi. Sabab: bu platforma kod bajarish (`code_runner.py`),
  Hacker Lab va kiberxavfsizlik darslari bilan ishlaydi — talabalar dars
  doirasida "SELECT", "`<script>`", "eval(" kabi so'zlarni yozishi TABIIY.
  Global auto-blok (6 soatga IP bloklash bilan) haqiqiy talabalarni
  bloklab qo'yishi mumkin edi. Kerak bo'lsa, buni faqat tor his-tuygu
  maydonlarida (masalan sof "Aloqa" formasi) qo'lda ulash mumkin.
- Qattiq **Content-Security-Policy** headeri qo'shilmadi — sayt cdnjs
  (three.js) va ko'plab inline `<script>/<style>` ishlatadi; noto'g'ri CSP
  butun dizayn/animatsiyalarni (jumladan tugmalarni) buzib qo'yishi mumkin
  edi. Buni xavfsiz joriy qilish uchun avval barcha inline skriptlarni
  nonce/hash bilan belgilash kerak — bu alohida, katta hajmli ish.

## 4) Allaqachon YAXSHI qilingan narsalar (o'zgartirilmadi)

- Parollar `werkzeug.security` bilan to'g'ri hash qilingan (hech qayerda
  ochiq parol saqlanmaydi).
- Barcha SQL so'rovlar parametrlashtirilgan (`?` placeholder) — SQL
  in'ektsiya deyarli yo'q (bir nechta joyda ustun nomi f-string bilan
  qo'shilgan, lekin har doim qattiq belgilangan whitelist/lug'atdan
  olinadi, foydalanuvchi kiritmasidan emas).
- Fayl yuklash (`hacker_lab`, `social`, va h.k.) xavfsiz: kengaytma
  whitelist, UUID nom, path-traversal yo'q.
- **Barcha** `/admin/*` route'lari `@admin_required` bilan, `/treasury/*`
  route'lari `@treasury_login_required` bilan izchil himoyalangan —
  tekshiruv davomida bittasi ham ochiq qolib ketmagan.
- Login'da brute-force himoyasi (urinishlar hisoblanadi, hisob va IP
  bloklanadi) ishlab turibdi.

## 5) Production'ga chiqarishdan oldin ALBATTA qiling

- `.env` faylidagi `SECRET_KEY`ni tasodifiy va uzun qiymatga almashtiring
  (hozirgi qiymat ishlatilsa ham standart emas, lekin serverni almashtirsangiz
  yangilang).
- `FORCE_HTTPS_COOKIES=1` ni `.env`ga qo'shing (agar HTTPS orqali xizmat
  ko'rsatilsa — bu SHART, aks holda sessiya cookie'lari HTTP orqali ham
  ketishi mumkin).
- `FLASK_DEBUG` muhit o'zgaruvchisi HECH QACHON `1`ga o'rnatilmasin.
- `.env` faylini `.gitignore`ga qo'shib, hech qachon ochiq repozitoriyga
  yuklamang (ichida bot tokeni, AI kaliti, SMTP paroli bor).
