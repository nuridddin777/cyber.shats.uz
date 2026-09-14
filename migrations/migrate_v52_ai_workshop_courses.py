# -*- coding: utf-8 -*-
"""
SHATS CYBER — MIGRATE v52: "Sun'iy Intellekt Ustaxonasi" kurs to'plami
================================================================================
5 ta kursdan iborat yangi mini-dastur (ai-ml yo'nalishi ichida):
  1) "Claude orqali dasturlash va undan to'g'ri foydalanish" — 20 dars, TO'LIQ
  2) "AI vositalari: video, taqqoslash va promptlar ustaxonasi" — 20 dars, TO'LIQ
  3-5) Keyingi 3 kurs — "Tez orada" (is_active=0, darslarsiz, faqat joy egallab turadi)

Narx: 40 CODE — Pro/Cyber Pro/VIP/MAXSUS uchun BEPUL (coins.py:buy_course_with_coins
ichidagi reja-tekshiruvi orqali avtomatik).
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

COURSE_1_LESSONS = [
    ("Sun'iy intellekt yordamchilari nima va nega kerak",
     "Sun'iy intellekt (AI) yordamchilari — GPT, Claude, Gemini kabi katta til modellari (LLM) asosida "
     "ishlaydigan tizimlar bo'lib, matn yozish, kod yaratish, tahlil qilish va savollarga javob berishda "
     "yordam beradi. Ular \"fikrlamaydi\" — ular ulkan matn ma'lumotlari asosida keyingi so'zni bashorat "
     "qilishga o'rgatilgan. Shunga qaramay, to'g'ri ishlatilganda dasturchining eng kuchli vositasiga "
     "aylanishi mumkin: rutina ishlarni tezlashtiradi, yangi texnologiyalarni tez o'rganishga yordam beradi, "
     "va kod sifatini oshiradi.\n\nBu kursda siz Claude'dan (Anthropic AI yordamchisi) dasturlashda qanday "
     "to'g'ri va samarali foydalanishni o'rganasiz — shunchaki \"savol berish\" emas, balki professional "
     "ish oqimiga aylantirish."),
    ("Claude bilan tanishuv — imkoniyatlari va cheklovlari",
     "Claude — matn yozish, kod tahlili, hujjatlarni o'qish va murakkab mulohaza yuritish uchun mo'ljallangan "
     "AI yordamchi. U kodni tushuntira oladi, xatolarni topadi, yangi funksiyalar yozadi va hatto butun "
     "loyihalarni rejalashtirishga yordam beradi.\n\nLekin cheklovlarni bilish MUHIM: Claude'ning bilimi "
     "ma'lum bir sanagacha \"muzlatilgan\" (eng so'nggi kutubxona versiyalarini bilmasligi mumkin), u "
     "ishonchli ko'rinsa-da xato qilishi mumkin (\"gallyutsinatsiya\"), va u sizning aniq loyihangiz "
     "kontekstini avtomatik bilmaydi — buni siz tushuntirishingiz kerak. Yaxshi dasturchi — Claude'ni "
     "\"hammasini biladigan sehrgar\" emas, balki \"juda tez, lekin tekshirish kerak bo'lgan yordamchi\" "
     "sifatida ko'radi."),
    ("Birinchi loyihangizni Claude bilan boshlash",
     "Yangi loyihani boshlaganda Claude'dan eng ko'p foyda olish uchun: (1) loyihaning maqsadini aniq "
     "tasvirlab bering, (2) qaysi til/freymvork ishlatmoqchi ekaningizni ayting, (3) kichik qadamlardan "
     "boshlang — butun loyihani bir so'rovda so'ramang.\n\nMisol: \"Menga to'liq internet-do'kon yozib "
     "ber\" — juda keng va noaniq so'rov. Buning o'rniga: \"Flask'da oddiy mahsulotlar ro'yxatini "
     "ko'rsatuvchi sahifa yarataylik, keyin bosqichma-bosqich savat va to'lov qo'shamiz\" — bu ancha "
     "boshqariladigan va sifatli natija beradi."),
    ("Yaxshi promptlar yozish asoslari",
     "Prompt — bu Claude'ga bergan so'rovingiz. Yaxshi prompt uchta narsani o'z ichiga oladi: KONTEKST "
     "(nima ustida ishlayapsiz), MAQSAD (nimaga erishmoqchisiz) va CHEKLOVLAR (qanday talablar bor).\n\n"
     "Yomon prompt: \"Bu kodni tuzat\"\nYaxshi prompt: \"Quyidagi Python funksiyasi ro'yxatdagi juft "
     "sonlarni topishi kerak, lekin u toq sonlarni ham qaytaryapti. Xatoni top va tushuntir, nega yuz "
     "berayotganini ham ayt.\"\n\nAniqlik — eng muhim ko'nikma. Qanchalik aniq so'rasangiz, javob "
     "shunchalik foydali bo'ladi."),
    ("Kod yozishda Claude'dan foydalanish",
     "Claude'dan kod so'raganda: (1) dasturlash tilini aniq belgilang, (2) mavjud kod bazasi bo'lsa, "
     "tegishli qismini ulashing, (3) kutilayotgan natijani (input/output misoli) ko'rsating.\n\nMuhim "
     "odat: Claude yozgan kodni HECH QACHON ko'r-ko'rona ishga tushirmang — avval o'qing, tushuning, "
     "keyin sinab ko'ring. Bu nafaqat xavfsizlik uchun, balki siz ham shu jarayonda o'rganasiz."),
    ("Xatolarni Claude yordamida topish va tuzatish (debugging)",
     "Debugging uchun Claude'ga: (1) to'liq xato xabarini (error message) nusxalab bering, (2) qaysi "
     "qatorda yuz berayotganini ko'rsating, (3) nima kutgan edingiz va nima bo'ldi — ikkalasini ham "
     "ayting.\n\nClaude ko'pincha xatoning ILDIZINI topishga yordam beradi, shunchaki \"tuzatilgan kod\" "
     "berish o'rniga. Undan \"nega bu xato yuz berdi\" deb so'rash — kelajakda xuddi shunday xatolarni "
     "o'zingiz aniqlashni o'rgatadi."),
    ("Kod tushuntirish va o'rganish uchun Claude",
     "Boshqa birov yozgan (yoki eski, o'zingiz unutgan) kodni tushunish kerak bo'lsa, Claude'dan uni "
     "qator-qator tushuntirib berishni so'rang. Bu yangi kutubxona yoki freymvorkni o'rganishning eng "
     "tez yo'llaridan biri — real kod misolida qanday ishlashini ko'rish, faqat mavhum hujjatni o'qish "
     "emas."),
    ("Loyiha arxitekturasini rejalashtirish",
     "Katta loyihani boshlashdan oldin Claude bilan arxitektura haqida \"suhbatlashing\": qaysi "
     "fayllar/modullar kerak, ma'lumotlar bazasi tuzilmasi qanday bo'lishi kerak, qaysi kutubxonalar "
     "mos keladi. Claude turli yondashuvlarning ijobiy va salbiy tomonlarini solishtirib berishi "
     "mumkin — bu qaror qabul qilishni osonlashtiradi."),
    ("Claude Code — terminal orqali dasturlash",
     "Claude Code — bu Claude'ni to'g'ridan-to'g'ri terminal orqali ishlatish imkonini beruvchi vosita: "
     "u fayllarni o'qiy oladi, o'zgartira oladi va buyruqlarni bajara oladi. Bu veb-chatdan farqli "
     "o'laroq, butun loyiha kontekstini \"ko'radi\" va murakkab, ko'p bosqichli vazifalarni avtonom "
     "bajarishi mumkin — masalan butun funksiyani yozib, testdan o'tkazib, xatoni o'zi tuzatishi mumkin."),
    ("Katta loyihalarda Claude bilan ishlash strategiyasi",
     "Katta loyihada Claude'ga BUTUN kodni bir vaqtda ko'rsatish imkonsiz (juda uzun). Buning o'rniga: "
     "loyihani kichik, mustaqil vazifalarga bo'ling, har biri uchun alohida ishlang, va Claude'ga faqat "
     "tegishli fayllarni ko'rsating. Har bir vazifadan keyin natijani tekshiring — bu \"kichik qadamlar, "
     "tez-tez tekshirish\" yondashuvi xatolarni erta topishga yordam beradi."),
    ("Kod review va sifat nazorati",
     "Claude'dan o'z yozgan kodingizni ko'rib chiqishni so'rash foydali odat: xavfsizlik zaifliklari, "
     "samaradorlik muammolari, o'qilishi qiyin joylarni topib berishi mumkin. Lekin yakuniy qaror doim "
     "SIZDA qolishi kerak — Claude tavsiyalarini tanqidiy baholang, ayniqsa xavfsizlik masalalarida."),
    ("Test yozishda AI yordami",
     "Claude funksiyangiz uchun test holatlari (test cases) yozishga yordam beradi, jumladan siz "
     "o'ylamagan \"chekka holatlar\" (edge cases)ni ham taklif qiladi — masalan bo'sh ro'yxat, manfiy "
     "son, juda katta qiymat kabi. Bu kodingizning mustahkamligini sezilarli oshiradi."),
    ("Dokumentatsiya yaratish",
     "Kod yozib bo'lgach, Claude'dan funksiyalar uchun izoh (docstring), README fayl yoki API "
     "hujjatlarini yozishni so'rash vaqtni tejaydi. Lekin hujjat kodning HAQIQATDA nima qilishini "
     "to'g'ri tasvirlashini albatta tekshiring."),
    ("Xavfsizlik — AI yozgan kodni tekshirish",
     "AI yozgan kod har doim ham xavfsiz emas — masalan SQL so'rovlarini noto'g'ri tarzda birlashtirish "
     "(SQL injection zaifligi), parollarni oddiy matn holida saqlash yoki foydalanuvchi kiritgan "
     "ma'lumotni tekshirmasdan ishlatish kabi xatolar uchrashi mumkin. Har doim: kirish ma'lumotlarini "
     "tekshirasizmi, maxfiy kalitlar kodga yozilmaganmi, ruxsatlar to'g'ri tekshirilganmi — shularni "
     "qo'lda ko'rib chiqing."),
    ("Claude'ning \"gallyutsinatsiya\"si — noto'g'ri javoblarni aniqlash",
     "Ba'zida Claude mavjud bo'lmagan funksiya, kutubxona yoki API'ni \"ixtiro qilishi\" mumkin — bu "
     "ishonchli ko'rinadi, lekin noto'g'ri. Buni aniqlash uchun: taniqli bo'lmagan funksiya nomlarini "
     "rasmiy hujjatlardan tekshiring, va kodni albatta ishga tushirib ko'ring — \"ishlaydi\" deb aytilishi "
     "\"haqiqatan ishlaydi\" degani emas."),
    ("Ko'p bosqichli vazifalarni AI bilan bajarish",
     "Murakkab vazifani (masalan \"ma'lumotlar bazasini loyihalash → API yozish → frontend ulash\") "
     "bosqichlarga bo'lib, har bir bosqichda Claude bilan ishlang va natijani tasdiqlagandan keyingina "
     "keyingisiga o'ting. Bu yondashuv xatolarni tez aniqlash va tuzatishni osonlashtiradi."),
    ("AI bilan ishlashda odob-axloq va mas'uliyat",
     "AI yordamchidan foydalanish — bu mas'uliyatni ondan olib tashlash degani emas. Siz yozgan (yoki AI "
     "yordamida yozgan) kod uchun javobgarlik SIZDA qoladi. Shuningdek, boshqalarning kodini yoki "
     "materiallarini AI orqali \"o'zingizniki\" qilib ko'rsatish — noto'g'ri. AI'dan shaffof va "
     "mas'uliyatli foydalaning."),
    ("Amaliy loyiha: to'liq veb-sahifa yaratish",
     "Ushbu amaliyotda siz Claude yordamida boshidan oxirigacha kichik veb-sahifa yaratasiz: HTML "
     "tuzilmasi, CSS bezash, JavaScript interaktivligi. Har bir bosqichda avval o'zingiz reja tuzing, "
     "keyin Claude bilan amalga oshiring — bu haqiqiy ish jarayonini simulyatsiya qiladi."),
    ("Amaliy loyiha: avtomatlashtirish skripti",
     "Kundalik takrorlanadigan vazifani (masalan fayllarni tartiblash, ma'lumotlarni qayta ishlash) "
     "avtomatlashtiruvchi Python skriptini Claude yordamida yozing. Bu — AI yordamchisining eng amaliy "
     "qo'llanilishlaridan biri: real vaqtingizni tejaydigan vosita yaratish."),
    ("Yakuniy amaliyot va sertifikatlash",
     "Kursni yakunlash uchun o'rgangan hamma narsangizni birlashtirib, kichik, lekin to'liq ishlaydigan "
     "loyiha yarating: rejalashtirish, kod yozish, debugging, hujjatlashtirish — barcha bosqichlarni "
     "Claude bilan hamkorlikda, lekin O'ZINGIZ nazorat qilgan holda bajaring."),
]

COURSE_2_LESSONS = [
    ("Sun'iy intellekt olamiga umumiy nazar",
     "Bugungi kunda AI vositalari matn, rasm, video, ovoz va musiqa yaratishga qodir. Bu kursda siz "
     "turli AI vositalarining nimaga qodirligini, ular orasidagi farqni va ulardan qay tarzda amaliy "
     "foydalanishni o'rganasiz — dasturchi bo'lish shart emas, bu ko'nikmalar kontent yaratuvchilar, "
     "marketolog va tadbirkorlar uchun ham foydali."),
    ("Matndan video yaratish — imkoniyatlar",
     "Matndan video yaratuvchi AI vositalar — siz yozgan tavsifga (masalan \"quyosh botayotgan "
     "shahar manzarasi, kamera sekin harakatlanadi\") asoslanib qisqa video klip generatsiya qiladi. "
     "Bu texnologiya reklama, ijtimoiy tarmoq kontenti va prototiplash uchun tobora ko'proq "
     "ishlatilmoqda, garchi hali uzun va murakkab videolar uchun inson tahriri talab qilinsa-da."),
    ("Video generatsiya vositalarini taqqoslash",
     "Turli video-AI vositalari turli kuchli tomonlarga ega: ba'zilari realistik harakatga, ba'zilari "
     "badiiy/animatsion uslubga, ba'zilari esa tezlik va qulaylikka ustuvorlik beradi. Vosita tanlashda "
     "e'tibor bering: video uzunligi cheklovi, chiqish sifati (rezolyutsiya), narx (ba'zilari bepul "
     "tarif taklif qiladi, ba'zilari faqat pullik), va litsenziya shartlari (tijorat maqsadida "
     "ishlatish mumkinmi)."),
    ("Matn-AI vositalarini taqqoslash: qaysi biri nimaga yaxshi",
     "Turli matn-AI yordamchilari turlicha kuchli tomonlarga ega: ba'zilari uzun, chuqur tahlil va "
     "kod yozishda kuchliroq, ba'zilari tezkor, qisqa javoblar uchun qulayroq, ba'zilari esa "
     "ijodiy yozuvda ajralib turadi. Eng muhim maslahat: bitta vositaga \"sodiq\" bo'lib qolmang — "
     "vazifangizga qarab eng mos vositani tanlashni o'rganing, va imkon qadar natijalarni "
     "solishtirib ko'ring."),
    ("Bepul va pullik AI vositalar — narx-sifat tahlili",
     "Ko'pgina AI vositalarning bepul tarifi mavjud, lekin odatda so'rovlar soni yoki sifat "
     "jihatidan cheklangan. Pullik tarifga o'tishdan oldin: (1) haqiqatan ham muntazam "
     "ishlatasizmi, (2) bepul muqobili yetarlimi, (3) narx sizning byudjetingizga mosmi — shu "
     "savollarga javob bering. Talabalar va kichik loyihalar uchun ko'pincha bepul tariflar "
     "yetarli bo'ladi."),
    ("Rasm generatsiya vositalari",
     "Matndan rasm yaratuvchi AI vositalar — tavsifga asoslanib turli uslubda (realistik, "
     "chizma, 3D va h.k.) rasm yaratadi. Bu dizayn, marketing va shaxsiy loyihalar uchun juda "
     "foydali, lekin natija sifat jihatidan promptning aniqligiga bog'liq — shuning uchun keyingi "
     "darslarda prompting san'atini chuqur o'rganamiz."),
    ("Prompting san'ati — asosiy tamoyillar",
     "Yaxshi prompt uchta narsani o'z ichiga oladi: MAVZU (nima tasvirlanishi kerak), USLUB "
     "(qanday ko'rinishda — realistik, chizma, minimalist va h.k.) va DETALLAR (rang, yorug'lik, "
     "kompozitsiya). Masalan \"mushuk\" o'rniga \"kunbotarda, oltin yorug'likda o'tirgan jigarrang "
     "mushuk, yaqindan olingan rasm, yumshoq fon\" — ancha aniq va sifatli natija beradi."),
    ("Rasm uchun professional promptlar yozish",
     "Professional natijalar uchun promptga texnik atamalar qo'shish foydali: kamera burchagi "
     "(\"yuqoridan\", \"yaqindan\"), yorug'lik turi (\"tabiiy\", \"studiya\"), va rang palitrasi. "
     "Shuningdek \"salbiy prompt\" (nima BO'LMASLIGI kerakligini ko'rsatish) ko'plab vositalarda "
     "natijani yanada aniqlashtiradi."),
    ("Video uchun promptlar va ssenariy yozish",
     "Video uchun prompt yozishda harakat va vaqt o'lchovini qo'shish muhim: kamera qanday "
     "harakatlanadi, sahna qanday rivojlanadi. Qisqa, aniq ssenariy (masalan \"3 soniya: quyosh "
     "chiqadi, keyin kamera pastga tushadi\") uzun, murakkab tavsifdan ko'ra ko'proq nazoratni "
     "ta'minlaydi."),
    ("Kadr kompozitsiyasi va vizual uslub",
     "Yaxshi vizual natija uchun fotografiya/dizayn asoslarini bilish AI vositalaridan foydalanishda "
     "ham foydali: uchdan bir qoidasi (rule of thirds), kontrast, rang uyg'unligi. AI vositalar bu "
     "tamoyillarni tushunsa-da, ulardan ATAYLAB foydalanishni so'rash natijani yaxshilaydi."),
    ("AI orqali logotip va brend dizayni",
     "AI vositalar tezkor logotip g'oyalarini generatsiya qilishda yordam beradi, lekin yakuniy, "
     "professional brend identifikatsiyasi uchun odatda inson dizayneri tahriri kerak bo'ladi — "
     "AI'ni \"boshlang'ich nuqta\" sifatida, yakuniy yechim sifatida emas, ishlating."),
    ("Ijtimoiy tarmoq uchun AI kontent yaratish",
     "AI vositalar Instagram, Telegram va boshqa platformalar uchun tezkor rasm/video kontent "
     "yaratishga yordam beradi. Muvaffaqiyat kaliti — bir xil uslub va brendni saqlab qolish uchun "
     "izchil promptlar (\"prompt shabloni\") ishlatish."),
    ("AI ovoz va musiqa generatsiyasi",
     "Matndan ovozga (text-to-speech) va musiqa generatsiya vositalari video kontent, podkast va "
     "taqdimotlar uchun professional audio yaratishga yordam beradi. Ovoz tabiiyligi va musiqa "
     "sifati vositadan vositaga farq qiladi — bir nechtasini sinab ko'rish tavsiya etiladi."),
    ("AI orqali taqdimot (prezentatsiya) tayyorlash",
     "AI vositalar taqdimot matnini, slaydlar tuzilmasini va hatto vizual dizaynni tezkor yaratishga "
     "yordam beradi. Bu ayniqsa vaqt tanqis bo'lgan holatlarda foydali, lekin muhim taqdimotlar uchun "
     "yakuniy tekshiruv va shaxsiylashtirish har doim kerak."),
    ("Matnni AI bilan tahrirlash va yaxshilash",
     "AI vositalar yozgan matningizni grammatik jihatdan tekshirish, ohangini o'zgartirish (rasmiy/"
     "norasmiy) yoki qisqartirish/kengaytirishda yordam beradi. Bu ayniqsa ona tilingiz bo'lmagan "
     "tilda yozayotganda juda foydali ko'nikma."),
    ("AI vositalarini birlashtirib ishlatish (workflow)",
     "Professional natija ko'pincha bir nechta AI vositani ketma-ket ishlatishdan kelib chiqadi: "
     "masalan avval matn-AI bilan ssenariy yozish, keyin rasm-AI bilan vizuallarni yaratish, so'ngra "
     "video-AI bilan animatsiya qilish. Bunday \"workflow\"ni rejalashtirish — vaqtni sezilarli "
     "tejaydi."),
    ("Mualliflik huquqi va AI kontent etikasi",
     "AI yaratgan kontentning mualliflik huquqi holati mamlakat va platformaga qarab farq qiladi — "
     "tijorat maqsadida ishlatishdan oldin har doim vosita shartlarini (litsenziya) tekshiring. "
     "Shuningdek, AI kontentni \"o'z qo'lingiz bilan yaratilgan\" deb yolg'on da'vo qilish — "
     "noto'g'ri va ko'plab platformalarda qoidabuzarlik hisoblanadi."),
    ("Amaliy loyiha: ijtimoiy tarmoq uchun video reklama",
     "Ushbu amaliyotda siz mahsulot yoki xizmat uchun qisqa (10-15 soniyalik) reklama videosi "
     "ssenariysini yozib, AI vositalar yordamida vizual elementlarni rejalashtirasiz — bu darsda "
     "haqiqiy video generatsiya emas, balki to'liq PROMPT va ssenariy rejasi tayyorlaysiz."),
    ("Amaliy loyiha: mahsulot uchun rasmlar to'plami",
     "Xayoliy mahsulot uchun bir xil uslubda 3-5 ta rasm prompti yozing — har biri turli burchak/"
     "kontekstda, lekin bir xil brend uslubini saqlagan holda. Bu vazifa \"izchil prompting\" "
     "ko'nikmasini mustahkamlaydi."),
    ("Yakuniy amaliyot — shaxsiy portfolio yaratish",
     "Kursni yakunlash uchun o'rgangan barcha AI vositalar turlarini (matn, rasm, video, ovoz) "
     "birlashtirib, kichik shaxsiy loyiha (masalan portfolio sahifasi uchun kontent to'plami) "
     "rejasini tuzing va amalga oshiring."),
]

COMING_SOON_COURSES = [
    ("AI bilan mobil ilova yaratish", "Flutter/React Native va AI yordamchilar bilan mobil ilova qurish."),
    ("AI orqali ma'lumotlar tahlili", "ChatGPT/Claude yordamida Excel, statistik tahlil va hisobotlar."),
    ("AI biznes va marketingda", "Marketing strategiyasi, kontent-reja va mijozlar bilan AI yordamida ishlash."),
]


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    direction = c.execute("SELECT id FROM directions WHERE slug='ai-ml'").fetchone()
    if not direction:
        conn.close()
        return
    direction_id = direction[0]

    already = c.execute("SELECT id FROM courses WHERE slug='ai-claude-dasturlash'").fetchone()
    if already:
        conn.close()
        print("  (v52 allaqachon qo'llanilgan, o'tkazib yuborildi)")
        return

    def add_course(slug, title, subtitle, description, level, lessons_spec, active=1):
        c.execute("""INSERT INTO courses (slug, direction_id, title, subtitle, description, level,
                     duration_weeks, lessons_count, students_count, rating, price, icon, is_active,
                     code_price, is_pro_only, is_paid)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (slug, direction_id, title, subtitle, description, level, 5, len(lessons_spec), 0, 4.8,
                   0, "bot", active, 40, 0, 1 if lessons_spec else 0))
        course_id = c.lastrowid
        if not lessons_spec:
            return course_id
        c.execute("INSERT INTO modules (course_id, order_num, title, icon, lessons_count) VALUES (?,?,?,?,?)",
                  (course_id, 1, title, "bot", len(lessons_spec)))
        module_id = c.lastrowid
        for i, (lesson_title, content) in enumerate(lessons_spec, start=1):
            content_html = "<p>" + content.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"
            c.execute("""INSERT INTO lessons (course_id, module_id, order_num, title, duration_seconds,
                         content_html, has_practice) VALUES (?,?,?,?,?,?,?)""",
                      (course_id, module_id, i, lesson_title, 480, content_html, 0))
        return course_id

    add_course(
        "ai-claude-dasturlash",
        "Claude orqali dasturlash va undan to'g'ri foydalanish",
        "AI yordamchidan professional darajada foydalanishni o'rganing",
        "Claude AI yordamida dasturlash, debugging, kod review va real loyihalar ustida ishlashni "
        "amaliy misollar orqali o'rganadigan 20 darslik kurs.",
        "Boshlang'ich", COURSE_1_LESSONS
    )
    add_course(
        "ai-vositalari-ustaxonasi",
        "AI vositalari: video, taqqoslash va promptlar ustaxonasi",
        "Video, rasm va matn AI vositalaridan amaliy foydalanish",
        "Turli AI vositalarini (video, rasm, matn, ovoz generatsiyasi) taqqoslash, professional "
        "promptlar yozish va ularni real loyihalarda qo'llashni o'rganadigan 20 darslik kurs.",
        "Boshlang'ich", COURSE_2_LESSONS
    )
    for title, desc in COMING_SOON_COURSES:
        slug = "ai-tez-orada-" + str(abs(hash(title)) % 100000)
        add_course(slug, title, "Tez orada", desc, "Boshlang'ich", [], active=0)

    conn.commit()
    conn.close()
    print(f"  + 2 ta to'liq AI kurs (40 dars) + {len(COMING_SOON_COURSES)} ta 'tez orada' kurs qo'shildi")
    print("✅ v52 Sun'iy Intellekt Ustaxonasi kurs to'plami — migratsiya muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
