"""
SHATS CYBER EDU — MIGRATE v40: O'quv dasturi (Mundarija) — mavzular va amaliylar
================================================================================
Bu migratsiya Edu tashkilotlari (maktab/texnikum/o'quv markazi) uchun FANGA OID
mundarija (sinf/kurs bo'yicha mavzular) va har bir mavzuga tegishli amaliy
topshiriqlar katalogini BITTA joyda, TO'LIQ holda qo'shadi.

QAMROV (barcha rasmiy "yangi darslik" seriyasi asosida, yuklangan asl PDF
darsliklardan):
  - 5-sinf   : 6 modul  (Word/Paint/diagramma/Scratch/qidiruv/email asoslari)
  - 6-sinf   : 8 modul  (hujjat/tasvir/jadval/baza/Scratch-Repeat/internet/email/multimedia)
  - 7-sinf   : 4 modul  ("On Track Stage 1" — maqsadli matn/multimedia/jadval/baza)
  - 8-sinf   : 4 modul  ("On Track Stage 2" — Scratch o'zgaruvchi/veb-sayt/tarmoq/video)
  - 9-sinf   : 21 bob   (Cambridge IGCSE ICT — kompyuter tizimlaridan veb-saytgacha)
  - 10-11-sinf: 19 bob  (Cambridge A-Level asosidagi — bilim bazasidan veb dasturlashgacha;
                          BU KITOB TEXNIKUM 1-2-KURS "Informatika asoslari" sifatida ham
                          ishlatiladi, shuning uchun applies_to_org_types="maktab,texnikum")

JAMI: 62 mavzu (topic), 310 ta amaliy topshiriq (har mavzuda 5 tadan: 1 tasi
Standart tarifda ham ko'rinadi, qolgan 4 tasi + rasm/diagramma tavsiyasi faqat
Pro tarifda ko'rinadi).

  - edu_curriculum_topics      : sinf/kurs, fan, bob/modul raqami, sarlavha,
                                  qisqacha original tavsif (darslikdan SO'ZMA-SO'Z
                                  KO'CHIRILMAGAN — mualliflik huquqi sababli faqat
                                  mavzu nomi va Claude tomonidan qayta yozilgan
                                  qisqa tavsif saqlanadi)
  - edu_curriculum_practicals  : har mavzu uchun amaliy topshiriqlar (original,
                                  Claude tomonidan yozilgan mashqlar — darslik
                                  matni EMAS). order_no=1 har doim Standart
                                  tarifda ham ko'rinadi; order_no 2-5 faqat
                                  Pro tarifda (has_advanced_labs=1) ko'rinadi.

TARIF BO'YICHA KIRISH (texnik topshiriq bo'yicha):
  - Standart tarif -> har mavzuga 1 ta amaliy
  - Pro tarif      -> har mavzuga 5 tagacha amaliy + rasm/diagramma tavsiyasi
  - "Markaz Pro" bo'lsa -> BUTUN tashkilot (o'qituvchi VA o'quvchilarning
    barchasi) avtomatik Pro darajasidagi mazmunni ko'radi — bu ALOHIDA
    bayroq talab qilmaydi, chunki kirish nazorati org_id -> tarif orqali
    ishlaydi (edu_orgs.get_org_tariff), foydalanuvchi darajasida EMAS.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

GRADE9_TOPICS = [
    (1, "Kompyuter tizimining turlari va komponentlari",
     "Kompyuter tizimlarining asosiy qurilma qismlari — protsessor, xotira turlari (RAM/ROM) va ularning vazifalari haqida."),
    (2, "Kiritish va chiqarish qurilmalari",
     "Kompyuterga ma'lumot kiritish va undan natija olish uchun ishlatiladigan qurilmalar turlari va ularni to'g'ri tanlash mezonlari."),
    (3, "Xotira qurilmalari va ma'lumot almashish vositalari",
     "Zaxira xotira turlari (qattiq disk, flesh xotira, bulutli saqlash) va ma'lumotlarni tashish/almashish usullari."),
    (4, "Kompyuter tarmoqlari va ulardan foydalanish",
     "Lokal va global tarmoqlar, internetga ulanish usullari, tarmoq xavfsizligi asoslari."),
    (5, "Axborot texnologiyalarining ta'siri",
     "AKTning jamiyat, ta'lim va mehnat bozoriga ijobiy hamda salbiy ta'sirlari."),
    (6, "AKTni tadbiq etish",
     "Turli soha (sog'liqni saqlash, ta'lim, savdo)larda axborot texnologiyalarini joriy etish misollari."),
    (7, "Tizimning hayot davri",
     "Dasturiy/apparat tizimini loyihalash, joriy etish, sinash va qo'llab-quvvatlash bosqichlari."),
    (8, "Xavfsizlik texnikasi qoidalari",
     "Kompyuter bilan ishlashda jismoniy va axborot xavfsizligi qoidalari, ergonomika."),
    (9, "Auditoriya",
     "Axborot mahsulotini tayyorlashda maqsadli auditoriyani aniqlash va unga moslashtirish."),
    (10, "Kommunikatsiya",
     "Elektron muloqot vositalari (email, messenjerlar) va ulardan samarali foydalanish odob-axloqi."),
    (11, "Fayllar boshqaruvi",
     "Fayl va papkalarni tashkil qilish, nomlash qoidalari, fayl formatlari."),
    (12, "Tasvirlar",
     "Raster va vektor tasvirlar, ularni yaratish va tahrirlash dasturlari bilan ishlash."),
    (13, "Loyihalash",
     "Hujjat/sahifa maketini rejalashtirish va loyihalash tamoyillari."),
    (14, "Uslublar",
     "Matn va hujjatlarda uslublar (stillar) yordamida bir xillikni ta'minlash."),
    (15, "Xatolarni tekshirish",
     "Hujjat va dasturlardagi xatolarni aniqlash hamda tuzatish usullari."),
    (16, "Grafik va xaritalar",
     "Ma'lumotlarni diagramma, grafik va sxema ko'rinishida vizual tasvirlash."),
    (17, "Hujjatlar bilan ishlash",
     "Matn muharriri imkoniyatlaridan foydalanib professional hujjat tayyorlash."),
    (18, "Ma'lumotlarni boshqarish",
     "Ma'lumotlar bazasi asoslari — jadval, so'rov va hisobotlar bilan ishlash."),
    (19, "Taqdimot",
     "Ta'sirli taqdimot (prezentatsiya) tayyorlash va uni namoyish etish mahorati."),
    (20, "Ma'lumotlar tahlili",
     "Elektron jadvallarda formula, funksiya va diagrammalar yordamida ma'lumotlarni tahlil qilish."),
    (21, "Veb-saytlar yaratish",
     "HTML asoslari yordamida oddiy veb-sahifa tuzish va uni brauzerda ko'rish."),
]
# ------------------------------------------------------------------
# 5-sinf (6 modul) — boshlang'ich daraja: Word, Paint, ma'lumot
# guruhlash, Scratch bilan tanishuv, qidiruv tizimlari, email asoslari
# ------------------------------------------------------------------
GRADE5_TOPICS = [
    (1, "Matnli hujjat bilan ishlashni boshlash",
     "Microsoft Word dasturida sichqoncha va klaviatura yordamida matn kiritish, belgilash va oddiy tahrirlash asoslari."),
    (2, "Tasvirlar bilan ishlashni boshlash",
     "Microsoft Paint dasturida chizish uskunalari (chiziq, shakllar, ranglar) yordamida oddiy rasm yaratish."),
    (3, "Diagrammalar bilan ishlashni boshlash",
     "Ma'lumotlarni guruhlash, sanash va oddiy jadval/diagramma ko'rinishida tasvirlash asoslari."),
    (4, "Dasturlashni boshlash",
     "Scratch dasturida sprayt (belgi)ni harakatlantirish — oldinga yurish, burilish kabi oddiy buyruqlar bilan tanishuv."),
    (5, "Qidiruv tizimlarida ishlashni boshlash",
     "Veb-brauzer va qidiruv tizimidan foydalanish, ishonchli natijalarni tanlash va elektron xavfsizlik asoslari."),
    (6, "Elektron pochtada ishlashni boshlash",
     "Email manzili tushunchasi, elektron xat yozish va emaildan xavfsiz foydalanish qoidalari."),
]

CHAPTER_PRACTICALS_5 = {
    1: [
        (1, "Birinchi hujjatim", 0,
         "Matn muharriri dasturida yangi hujjat oching. Ism-familiyangiz, sinfingiz va bugungi sanani yozing. Sichqoncha bilan "
         "bitta so'zni belgilashni mashq qiling.", None),
        (2, "Sichqoncha mashqi jurnali", 1,
         "Sichqoncha ko'rsatkichini ekranning 4 burchagiga (yuqori-chap, yuqori-o'ng, past-chap, past-o'ng) navbat bilan olib "
         "borib, har safar nima o'zgarganini kuzatib, daftarga yozing.",
         "diagram: ekran va 4 burchakka ko'rsatkich harakati sxemasi"),
        (3, "Klaviatura tugmalari xaritasi", 2,
         "Klaviaturadagi harflar, raqamlar va maxsus tugmalarni (Enter, Space, Backspace, Shift) alohida guruhlarga ajratib, "
         "har biri nima uchun ishlatilishini yozing.",
         "diagram: klaviatura tugmalari guruhlari (rangli belgilangan zonalar)"),
        (4, "Kichik hikoya yozish", 3,
         "5-6 jumladan iborat kichik hikoya yozing, so'ng kamida 2 ta so'zni qalin (bold) va 1 ta so'zni rangli qilib bezang.",
         "diagram: yakuniy hujjatning ekran surati (skrinshot) tavsiyasi"),
        (5, "Xavfsizlik posteri", 4,
         "Kompyuter bilan ishlashda xavfsizlik qoidalaridan (ichimlik to'kmaslik, kabellarga tegmaslik) 5 bandli rangli "
         "poster matnini tayyorlang.",
         "diagram: xavfsizlik qoidalari posterining oddiy maketi"),
    ],
    2: [
        (1, "Birinchi rasmim", 0,
         "Rasm dasturida chiziq va shakl uskunalaridan foydalanib, oddiy uy yoki quyosh rasmini chizing.", None),
        (2, "Ranglar palitrasi tajribasi", 1,
         "5 xil rangdan foydalanib, oddiy manzara (masalan bog') chizing va har bir rangni nima uchun tanlaganingizni yozing.",
         "diagram: chizilgan manzaraning skrinshoti"),
        (3, "Shakllardan uy yasash", 2,
         "Faqat to'g'ri to'rtburchak, uchburchak va doira shakllaridan foydalanib, uy tasvirini yasang.",
         "diagram: uch xil shakldan yasalgan uy chizmasi namunasi"),
        (4, "Undo/Redo mashqi", 3,
         "Rasm chizayotganda ataylab xato qiling, so'ng Undo (bekor qilish) va Redo (qaytarish) tugmalarini necha marta "
         "bosganingizni va natijasini yozing.",
         "diagram: Undo/Redo tugmalari va ularning ta'siri sxemasi"),
        (5, "Mening portretim", 4,
         "O'zingizning oddiy portretingizni (yuz, ko'z, soch) chizing, kamida 4 xil rang va 3 xil shakldan foydalaning.",
         "diagram: yakuniy portret rasmining namunasi"),
    ],
    3: [
        (1, "Sinfdoshlarni guruhlash", 0,
         "Sinfdoshlaringizni (yoki oilangiz a'zolarini) sevimli rangi bo'yicha guruhlarga ajrating va har bir guruhda "
         "nechta kishi borligini sanang.", None),
        (2, "Sanoq jadvali", 1,
         "10 ta xayoliy yoki haqiqiy meva/sabzavotni ro'yxatga oling, ularni turiga ko'ra guruhlab, sanoq jadvali "
         "(har biriga belgi qo'yib sanash) tuzing.",
         "diagram: sanoq jadvali namunasi (belgilar bilan)"),
        (3, "Ikki xil guruhlash usuli", 2,
         "Bitta narsalar to'plamini (masalan kitoblar) ikki xil mezon bo'yicha (rang va hajm) guruhlang, natijalarni "
         "taqqoslang.",
         "diagram: bir xil ma'lumotni ikki xil guruhlash sxemasi"),
        (4, "Oddiy ustunli diagramma", 3,
         "Sanoq jadvalingizdagi ma'lumotlardan foydalanib, qog'ozda oddiy ustunli diagramma chizing (har ustun bitta "
         "guruhni ifodalaydi).",
         "diagram: qo'lda chizilgan ustunli diagramma namunasi"),
        (5, "Diagrammani tushuntirish", 4,
         "Chizgan diagrammangizga qarab, qaysi guruh eng katta, qaysi guruh eng kichik ekanini va nima uchun bu ma'lumot "
         "foydali ekanini 3-4 jumla bilan yozing.",
         "diagram: diagramma + xulosa matni birgalikda joylashgan poster"),
    ],
    4: [
        (1, "Spraytni harakatlantirish", 0,
         "Scratch dasturida (yoki qog'ozda algoritm sifatida) spraytni 10 qadam oldinga yurgizadigan oddiy dastur/algoritm "
         "tuzing.", None),
        (2, "Burilish mashqi", 1,
         "Spraytni to'g'ri to'rtburchak shaklida yuritadigan algoritm yozing: yur-buril-yur-buril (4 marta 90 daraja "
         "burilish bilan).",
         "diagram: to'g'ri to'rtburchak yo'nalishi bo'ylab sprayt harakati sxemasi"),
        (3, "Turli qadam sonlari tajribasi", 2,
         "Sprayt qadamini 10, 50 va 100 qilib sinab ko'ring (yoki tasavvur qiling) va har birida sprayt qanchalik uzoqqa "
         "borishini taqqoslang.",
         "diagram: turli qadam sonlarida sprayt yo'lini solishtiruvchi chizma"),
        (4, "Burchaklar jadvali", 3,
         "0°, 90°, 180°, 270° burchaklarning har biri spraytni qaysi tomonga burishini jadvalga tushiring.",
         "diagram: burchaklar aylanasi (0-360 daraja belgilangan)"),
        (5, "Kichik sayohat algoritmi", 4,
         "Spraytni kvadrat shaklida ikki marta aylantiradigan (8 ta buyruqdan iborat) to'liq algoritm yozing.",
         "diagram: sprayt bosib o'tadigan yo'lning to'liq sxemasi"),
    ],
    5: [
        (1, "Xavfsiz qidiruv so'zlari", 0,
         "Bironta mavzu (masalan 'oq ayiqlar') bo'yicha ma'lumot topish uchun 3 ta turli qidiruv so'z birikmasini yozing "
         "va qaysi biri eng aniq natija berishi mumkinligini bashorat qiling.", None),
        (2, "Ishonchli va ishonchsiz sayt belgilari", 1,
         "Ishonchli veb-sayt va ishonchsiz/xavfli veb-saytni ajratib turadigan 6 ta belgini (masalan imlo xatolari, "
         "reklama ko'pligi) ro'yxatlang.",
         "diagram: ishonchli va ishonchsiz sayt belgilarini solishtiruvchi jadval"),
        (3, "Qidiruv natijalarini baholash", 2,
         "Xayoliy qidiruv natijalari ro'yxatini (5 ta sayt nomi) tuzing va har birini 'ishonaman' yoki 'ishonmayman' deb "
         "belgilab, sababini yozing.",
         "diagram: qidiruv natijalari ro'yxati va ishonch darajasi belgilari"),
        (4, "Elektron xavfsizlik qoidalari", 3,
         "Internetdan foydalanishda bolalar uchun xavfsizlik bo'yicha 6 bandli qoidalar ro'yxatini tuzing.",
         "diagram: elektron xavfsizlik qoidalari posteri"),
        (5, "Mavzuni tadqiq qilish rejasi", 4,
         "O'zingiz tanlagan mavzu (masalan sevimli hayvon) haqida ma'lumot to'plash uchun 4 bosqichli tadqiqot rejasi "
         "(nima qidiraman -> qayerdan -> qanday tekshiraman -> qanday yozib olaman) tuzing.",
         "diagram: tadqiqot rejasining 4 bosqichli oqim sxemasi"),
    ],
    6: [
        (1, "Email manzili qismlari", 0,
         "'ism.familiya@gmail.com' kabi namunaviy email manzilini qismlarga ajrating (foydalanuvchi nomi, @ belgisi, "
         "provayder) va har biri nima anglatishini yozing.", None),
        (2, "Xavfsiz email qoidalari", 1,
         "Notanish odamdan kelgan xatga qanday munosabatda bo'lish kerakligi bo'yicha 6 bandli xavfsizlik qo'llanmasi "
         "tuzing.",
         "diagram: 'xat keldi -> tanishmi? -> ha/yo'q' qaror sxemasi"),
        (3, "Namunaviy xat yozish", 2,
         "Sinfdoshingizga (xayoliy) tug'ilgan kun tabrigi bilan qisqa, odobli elektron xat matnini yozing (salomlashuv "
         "va imzo bilan).",
         "diagram: namunaviy elektron xatning tuzilishi (sarlavha, matn, imzo)"),
        (4, "Ilova fayl xavfsizligi", 3,
         "Notanish odamdan kelgan ilova (attachment) faylni ochish xavfli bo'lishi mumkin bo'lgan 4 ta sababni yozing.",
         "diagram: ilova fayl belgisi (skrepka) va xavfsizlik ogohlantirish sxemasi"),
        (5, "Parol xavfsizligi asoslari", 4,
         "Email hisobingiz uchun kuchli parol yaratish qoidalaridan (uzunlik, raqam, harf aralashmasi) 5 bandli ro'yxat "
         "tuzing (haqiqiy parolingizni yozmang).",
         "diagram: kuchli va zaif parol namunalarini solishtiruvchi jadval"),
    ],
}
# ------------------------------------------------------------------
# 6-sinf (8 modul) — Word/Paint/Excel/Access asoslari, Scratch bilan
# takrorlash (repeat) operatori, internet, email, multimedia
# ------------------------------------------------------------------
GRADE6_TOPICS = [
    (1, "Hujjatga qayta ishlov berish",
     "Matn hujjatini formatlash, tahrirlash va professional ko'rinishga keltirish bo'yicha kengaytirilgan ko'nikmalar."),
    (2, "Tasvirga qayta ishlov berish",
     "Rasm dasturida tasvirlarni tahrirlash, qatlamlar va murakkabroq chizish uskunalaridan foydalanish."),
    (3, "Elektron jadvalga qayta ishlov berish",
     "Elektron jadvalda kataklarga formula kiritish (qo'shish, ayirish, ko'paytirish, bo'lish) asoslari."),
    (4, "Ma'lumotlar bazasiga qayta ishlov berish",
     "Oddiy ma'lumotlar bazasi jadvalini yaratish, maydon turlarini belgilash va yozuvlar kiritish."),
    (5, "Dasturlashni o'rganish",
     "Scratch dasturida 'Repeat' (takrorlash) operatoridan foydalanib, algoritmlarni qisqartirish."),
    (6, "Internetda ishlashni o'rganish",
     "Veb-brauzer imkoniyatlari, saytlar orasida navigatsiya va internetdan samarali foydalanish."),
    (7, "Email (Elektron pochta) dan foydalanishni o'rganish",
     "Elektron xat yozish, ilova biriktirish va xat almashish odob-axloqi bo'yicha kengaytirilgan ko'nikmalar."),
    (8, "Multimedia hujjatiga qayta ishlov berish",
     "Matn, tasvir va tovushni birlashtirgan multimedia taqdimotini yaratish asoslari."),
]

CHAPTER_PRACTICALS_6 = {
    1: [
        (1, "Hujjatni formatlash", 0,
         "Oldindan yozilgan (yoki o'zingiz yozgan) 6-7 jumlalik matnni oling: sarlavhani kattaroq va qalin, asosiy "
         "matnni tekis (justify) qilib formatlang.", None),
        (2, "Shrift va rang tanlovi", 1,
         "Bitta hujjatda 3 xil shrift turi va 3 xil rangni sinab ko'ring, qaysi kombinatsiya o'qish uchun eng qulay "
         "ekanini tanlab, sababini yozing.",
         "diagram: turli shrift/rang kombinatsiyalarini solishtiruvchi jadval"),
        (3, "Ro'yxatlar bilan ishlash", 2,
         "Kunlik ish rejangizni raqamlangan (numbered) ro'yxat va nuqtali (bulleted) ro'yxat ko'rinishida ikki xil "
         "formatda yozing.",
         "diagram: raqamlangan va nuqtali ro'yxatni solishtiruvchi namuna"),
        (4, "Sahifa maketi sozlash", 3,
         "Hujjat uchun hoshiya (margin), sahifa yo'nalishi (portret/albom) va qog'oz o'lchamini tanlab, nima uchun "
         "shunday tanlaganingizni yozing.",
         "diagram: sahifa maketi elementlari (hoshiya, yo'nalish) sxemasi"),
        (5, "To'liq rasmiylashtirilgan hujjat", 4,
         "Sarlavha, kirish, 2 ta bo'lim va xulosadan iborat to'liq rasmiylashtirilgan qisqa hisobot (masalan 'Mening "
         "sevimli fanim') tayyorlang.",
         "diagram: yakuniy hujjatning tuzilma sxemasi (sarlavha->bo'lim->xulosa)"),
    ],
    2: [
        (1, "Tasvirni tahrirlash mashqi", 0,
         "Oddiy chizilgan rasmni oling, uning bir qismini kesib (crop) oling va rangini o'zgartiring.", None),
        (2, "Qatlamlar bilan ishlash g'oyasi", 1,
         "Bitta manzara rasmini fon, asosiy obyekt va bezaklar kabi 3 ta 'qatlam'ga bo'lib tasavvur qiling va har "
         "qaysi qatlamda nima borligini yozing.",
         "diagram: 3 qatlamli rasm tuzilishi sxemasi (fon-obyekt-bezak)"),
        (3, "Murakkab shakl yasash", 2,
         "Kamida 5 xil shakl va chiziq turidan foydalanib, murakkabroq kompozitsiya (masalan shahar manzarasi) "
         "chizing.",
         "diagram: yakuniy kompozitsiya rasmining namunasi"),
        (4, "Nusxa olish va joylashtirish", 3,
         "Bitta kichik shaklni nusxalab (copy-paste), uni 4 marta turli joylarga joylashtirib, naqsh (pattern) hosil "
         "qiling.",
         "diagram: nusxalangan shakllardan hosil bo'lgan naqsh namunasi"),
        (5, "Auditoriyaga mos rasm", 4,
         "Bitta rasmni ikki xil maqsad uchun (masalan tug'ilgan kun otkritkasi va maktab e'loni) ikki xil uslubda "
         "tahrirlashni rejalashtiring.",
         "diagram: bitta asl rasm -> ikki tahrirlangan versiya sxemasi"),
    ],
    3: [
        (1, "Oddiy formulalar", 0,
         "Elektron jadvalda 5 ta katakka son yozing va 6-katakka ularning yig'indisini hisoblovchi formula (=A1+A2+...) "
         "yozing.", None),
        (2, "To'rt amal mashqi", 1,
         "Bitta jadvalda qo'shish, ayirish, ko'paytirish va bo'lish formulalarining har biridan kamida 2 tadan "
         "misol yozing.",
         "diagram: 4 amal va ularning formula belgilari jadvali"),
        (3, "Oylik xarajat jadvali", 2,
         "5 kunlik xayoliy xarajatlaringizni jadvalga kiriting va formula yordamida umumiy xarajatni hisoblang.",
         "diagram: xarajat jadvali va jami qatorining sxemasi"),
        (4, "Formula xatosini topish", 3,
         "3 ta formuladan iborat kichik jadval tuzing, birida ataylab xato qiling (masalan = belgisisiz), so'ng "
         "xatoni toping va tuzating.",
         "diagram: to'g'ri va xato formulalarni solishtiruvchi jadval"),
        (5, "Formuladan formulaga bog'lanish", 4,
         "Bitta katakning natijasini boshqa formulada ishlatadigan (masalan jami -> o'rtacha hisoblash) ikki "
         "bosqichli hisoblash zanjiri tuzing.",
         "diagram: katak -> katak formulalar bog'lanish zanjiri"),
    ],
    4: [
        (1, "Oddiy ma'lumotlar bazasi jadvali", 0,
         "Sinfdoshlaringiz uchun 'Ism', 'Familiya', 'Yosh' maydonlaridan iborat jadval yarating va 5 ta yozuv "
         "kiriting.", None),
        (2, "Maydon turlari", 1,
         "Jadvalingizga 'Tug'ilgan sana' (sana turi), 'Balandlik' (son turi) va 'Izoh' (matn turi) maydonlarini "
         "qo'shing, har biri uchun to'g'ri maydon turini tanlang.",
         "diagram: maydon nomi -> maydon turi jadvali"),
        (3, "Yozuvlarni saralash", 2,
         "Jadvalingizni yosh bo'yicha o'sish tartibida saralang (qo'lda yoki dastur yordamida), natijani yozing.",
         "diagram: saralashdan oldin va keyingi jadval holati"),
        (4, "Oddiy qidiruv (filter)", 3,
         "Jadvalingizdan faqat ma'lum yoshdan katta bo'lganlarni ajratib olish (filtrlash) mezonini yozing.",
         "diagram: filtrlash sharti va natija jadvali"),
        (5, "Kichik hisobot", 4,
         "Ma'lumotlar bazangizdan foydalanib 'Sinfimizdagi eng yosh va eng katta yoshli o'quvchi' hisobotini "
         "tuzing.",
         "diagram: hisobot maketi (sarlavha + natija jadvali)"),
    ],
    5: [
        (1, "Repeat operatoridan foydalanish", 0,
         "Spraytni 5 marta 10 qadamdan yuritadigan (jami 50 qadam) 'Repeat' operatorli algoritm yozing.", None),
        (2, "Kvadrat chizish algoritmi", 1,
         "'Repeat 4' operatori bilan (yur-buril juftligini 4 marta takrorlab) kvadrat shaklini chizadigan algoritm "
         "tuzing.",
         "diagram: Repeat operatori ichidagi buyruqlar va hosil bo'lgan kvadrat"),
        (3, "Repeatdan oldin va keyin buyruqlar", 2,
         "Repeat blokidan OLDIN bitta buyruq, Repeat ICHIDA ikkita buyruq, Repeat dan KEYIN bitta buyruq bo'lgan "
         "algoritm yozing.",
         "diagram: oldin-ichida-keyin uch qismli algoritm sxemasi"),
        (4, "Sekinlashtirish (Wait) mashqi", 3,
         "Takrorlanuvchi harakat juda tez ketayotgan bo'lsa, orasiga 'Wait' (kutish) buyrug'ini qo'shish g'oyasini "
         "sxema orqali tushuntiring.",
         "diagram: Wait buyrug'i bilan va u bo'lmagan holatni solishtirish"),
        (5, "Ko'pburchak generatori", 4,
         "Uchburchak, kvadrat va oltiburchak chizish uchun Repeat sonlarini (3, 4, 6) va burilish burchaklarini "
         "(120°, 90°, 60°) hisoblab jadvalga yozing.",
         "diagram: uchburchak, kvadrat, oltiburchak va ularning Repeat/burchak qiymatlari"),
    ],
    6: [
        (1, "Brauzer elementlari", 0,
         "Veb-brauzer oynasidagi asosiy elementlarni (manzil satri, orqaga/oldinga tugmalari, yorliqlar) topib, "
         "har biri nima uchun kerakligini yozing.", None),
        (2, "Saytlar orasida navigatsiya", 1,
         "3 ta turli veb-sayt (yoki xayoliy sahifalar)ni ochib, ular orasida qanday o'tish mumkinligini (havolalar, "
         "orqaga tugmasi) tasvirlab yozing.",
         "diagram: 3 sahifa orasidagi navigatsiya oqimi"),
        (3, "Yorliqlar (bookmarks) bilan ishlash", 2,
         "Foydali deb hisoblagan 5 ta sayt (o'quv, o'yin, yangilik) ro'yxatini tuzing va ularni yorliqlarga qo'shish "
         "rejasini yozing.",
         "diagram: yorliqlar ro'yxati kategoriya bo'yicha guruhlangan"),
        (4, "Bir nechta yorliq (tab)da ishlash", 3,
         "Bir vaqtda 3 ta turli sahifani ochib, ular orasida qanday almashish qulayligini tushuntiring.",
         "diagram: 3 ta ochiq yorliq va ular orasida almashish sxemasi"),
        (5, "Internetdan samarali foydalanish rejasi", 4,
         "Uy vazifasi uchun kerakli ma'lumotni topish uchun internetdan foydalanish bosqichlarini (qidirish -> "
         "tanlash -> o'qish -> yozib olish) rejalashtiring.",
         "diagram: internetdan foydalanish 4 bosqichli oqim sxemasi"),
    ],
    7: [
        (1, "Xat yozish va ilova biriktirish", 0,
         "Sinfdoshingizga (xayoliy) uy vazifasi haqida qisqa xat yozing va unga (tasavvuran) bitta fayl "
         "biriktirilganini eslatib o'ting.", None),
        (2, "Xat almashish odob-axloqi", 1,
         "Yaxshi va yomon email misolini yozing: biri odobli/aniq, ikkinchisi beodob/tushunarsiz — farqni "
         "tushuntiring.",
         "diagram: yaxshi va yomon xat namunalarini solishtiruvchi jadval"),
        (3, "Guruh xati (cc) stsenariysi", 2,
         "3 kishiga bir vaqtda xat yuborish kerak bo'lgan holatni tasvirlang va nima uchun 'cc' maydoni foydali "
         "ekanini tushuntiring.",
         "diagram: bitta xat -> uchta qabul qiluvchiga (cc) yuborilishi sxemasi"),
        (4, "Ilova fayl xavfsizligi (kengaytirilgan)", 3,
         "Notanish jo'natuvchidan kelgan ilova faylni ochishdan oldin tekshirish kerak bo'lgan 5 ta belgini "
         "ro'yxatlang.",
         "diagram: xavfsiz va xavfli ilova fayl belgilari jadvali"),
        (5, "Elektron xat arxivi rejasi", 4,
         "Kelgan xatlarni papkalarga (masalan 'Maktab', 'Do'stlar', 'Muhim') qanday tashkil qilishni rejalashtiring.",
         "diagram: pochta qutisi papkalar tuzilmasi"),
    ],
    8: [
        (1, "Matn, rasm va tovushni birlashtirish g'oyasi", 0,
         "Bitta mavzu (masalan 'Mening sevimli hayvonim') uchun qaysi qismda matn, qaysi qismda rasm bo'lishini "
         "rejalashtirib yozing.", None),
        (2, "Multimedia slaydi maketi", 1,
         "3 slaydlik oddiy taqdimot rejasini tuzing: har slaydda sarlavha, matn va rasm qayerda joylashishini "
         "eskiz qiling.",
         "diagram: 3 slaydning maketi (sarlavha, matn, rasm zonalari)"),
        (3, "Tovush qo'shish rejasi", 2,
         "Taqdimotingizga fon musiqasi yoki ovozli izoh qo'shish kerak bo'lsa, qaysi slaydlarda va nima uchun "
         "kerakligini yozing.",
         "diagram: slayd -> tovush turi (musiqa/izoh) jadvali"),
        (4, "O'tish effektlari tanlovi", 3,
         "Slaydlar orasidagi o'tish effektlarining (masalan sirg'alish, so'nish) auditoriyaga qanday ta'sir "
         "qilishini solishtiring.",
         "diagram: turli o'tish effektlarini tasvirlaydigan sxema"),
        (5, "To'liq multimedia loyihasi", 4,
         "5 slaydlik to'liq multimedia taqdimoti rejasini (mavzu, har slayd mazmuni, tovush/rasm rejasi bilan) "
         "yozing.",
         "diagram: 5 slaydlik taqdimotning to'liq tuzilma sxemasi"),
    ],
}
# ------------------------------------------------------------------
# 7-sinf (4 modul, "On Track Stage 1") — maqsadli/vazifaga yo'naltirilgan
# matn, multimedia, elektron jadval va ma'lumotlar bazasidan foydalanish
# ------------------------------------------------------------------
GRADE7_TOPICS = [
    (1, "Matnli hujjatdan maqsadli foydalanish",
     "Aniq bir maqsad (masalan reklama varag'i, xat) uchun matn hujjatini rejalashtirish va yaratish."),
    (2, "Multimediadan maqsadli foydalanish",
     "Aniq auditoriya uchun matn, rasm, tovush va videoni birlashtirgan multimedia mahsuloti yaratish."),
    (3, "Elektron jadvallardan maqsadli foydalanish",
     "Real hayotiy masalani (masalan byudjet) yechish uchun elektron jadval va formulalardan foydalanish."),
    (4, "Ma'lumotlar bazasidan maqsadli foydalanish",
     "Aniq maqsad uchun ma'lumotlar bazasi jadvalini loyihalash, to'ldirish va undan so'rov (query) orqali "
     "ma'lumot olish."),
]

CHAPTER_PRACTICALS_7 = {
    1: [
        (1, "Maqsadli hujjat rejasi", 0,
         "Maktab tadbiri uchun reklama varag'i (flyer) yaratish maqsadida: auditoriya kim, qanday ma'lumot bo'lishi "
         "kerakligini rejalashtirib yozing.", None),
        (2, "Auditoriyaga mos til va uslub", 1,
         "Bitta xabarni (masalan 'Kutubxonaga kitob qaytaring') ikki xil auditoriya — kichik sinf o'quvchilari va "
         "o'qituvchilar — uchun ikki xil uslubda yozing.",
         "diagram: bitta xabar -> ikki auditoriya -> ikki uslub sxemasi"),
        (3, "Reklama varag'i maketi", 2,
         "Reklama varag'ida sarlavha, asosiy matn, rasm va aloqa ma'lumotlari qayerda joylashishini eskiz qilib "
         "chizing.",
         "diagram: reklama varag'i maketining eskizi"),
        (4, "Formatlash bilan ta'sir kuchaytirish", 3,
         "Bir xil matnni ikki xil formatlash (shrift, rang, o'lcham) bilan yozing va qaysi biri ko'proq e'tibor "
         "tortishini solishtiring.",
         "diagram: ikki xil formatlangan matnni solishtiruvchi jadval"),
        (5, "Auditoriya fikrini so'rash rejasi", 4,
         "Tayyorlagan hujjatingiz haqida auditoriyadan fikr olish uchun 4 ta baholash savoli tuzing.",
         "diagram: hujjat -> auditoriya fikri -> yaxshilash aylanmasi"),
    ],
    2: [
        (1, "Multimedia mahsuloti rejasi", 0,
         "Sinfdoshlaringiz uchun 'Xavfsiz internet' mavzusida qisqa multimedia taqdimoti (matn+rasm) rejasini "
         "tuzing.", None),
        (2, "Rasm va matn muvofiqligi", 1,
         "3 ta rasm tanlang (yoki tasavvur qiling) va har biriga mos qisqa matn yozing — rasm va matn bir-birini "
         "qanday to'ldirishini tushuntiring.",
         "diagram: rasm-matn juftliklari sxemasi"),
        (3, "Tovush qo'shish rejasi", 2,
         "Multimedia mahsulotingizga qaysi joyda fon musiqasi, qaysi joyda ovozli tushuntirish bo'lishi kerakligini "
         "rejalashtiring.",
         "diagram: mahsulot bo'limlari va ularga mos tovush turlari jadvali"),
        (4, "Auditoriyaga moslashtirish", 3,
         "Bitta multimedia mahsulotini ikki xil auditoriya (bolalar va kattalar) uchun ikki xil rang/musiqa "
         "uslubida moslashtirishni rejalashtiring.",
         "diagram: ikki auditoriya uchun ikki uslub taqqoslashi"),
        (5, "To'liq multimedia loyihasi", 4,
         "5 qismdan iborat (kirish, 3 asosiy bo'lim, xulosa) to'liq multimedia loyihasi rejasini, har qismga "
         "matn/rasm/tovush taqsimoti bilan yozing.",
         "diagram: 5 qismli multimedia loyihasining to'liq tuzilmasi"),
    ],
    3: [
        (1, "Oddiy byudjet jadvali", 0,
         "Bir haftalik xayoliy cho'ntak pulingizni (kirim/chiqim) elektron jadvalga kiriting va jami qolgan "
         "mablag'ni formula bilan hisoblang.", None),
        (2, "Formulalar zanjiri", 1,
         "Byudjet jadvalingizga 'jami kirim', 'jami chiqim' va 'farq' (jami kirim - jami chiqim) formulalarini "
         "qo'shing.",
         "diagram: kirim/chiqim/farq formulalari orasidagi bog'lanish"),
        (3, "Turli stsenariylarni sinash", 2,
         "Agar haftalik kirimingiz 2 barobar ko'paysa, jadvalingizdagi natijalar qanday o'zgarishini hisoblab "
         "yozing (bu — 'nima bo'lsa-chi' tahlili).",
         "diagram: asl va o'zgartirilgan stsenariy natijalarini solishtirish"),
        (4, "Diagramma bilan vizuallashtirish", 3,
         "Byudjet jadvalingizdagi kirim va chiqim toifalarini oddiy doiraviy yoki ustunli diagrammada "
         "tasvirlang.",
         "diagram: kirim/chiqim toifalarini ko'rsatuvchi diagramma"),
        (5, "Oylik byudjet rejasi", 4,
         "Haftalik jadvalingizni asos qilib, 4 haftalik (oylik) byudjet rejasini tuzing va oy oxirida qancha "
         "mablag' qolishini hisoblang.",
         "diagram: 4 haftalik byudjet jadvali va oylik jami"),
    ],
    4: [
        (1, "Maqsadli ma'lumotlar bazasi jadvali", 0,
         "Sinf kutubxonasi uchun 'Kitob nomi', 'Muallif', 'Janr' maydonlaridan iborat jadval yarating va 6 ta "
         "yozuv kiriting.", None),
        (2, "Maydon turlarini to'g'ri tanlash", 1,
         "Jadvalingizga 'Nashr yili' (son) va 'Band qilinganmi' (mantiqiy/ha-yo'q) maydonlarini qo'shing, har biri "
         "uchun mos maydon turini tanlang.",
         "diagram: maydon nomi -> tanlangan maydon turi jadvali"),
        (3, "So'rov (query) tuzish", 2,
         "Jadvalingizdan faqat bitta janrdagi kitoblarni ajratib olish uchun qanday so'rov (filtr sharti) "
         "yozish kerakligini tavsiflang.",
         "diagram: so'rov sharti va natija jadvali"),
        (4, "Saralangan hisobot", 3,
         "Kitoblaringizni nashr yili bo'yicha (eskisidan yangisiga) saralab, hisobot ko'rinishida taqdim eting.",
         "diagram: saralangan hisobot jadvali"),
        (5, "Ma'lumotlar bazasi maqsadga muvofiqligi", 4,
         "Yaratgan ma'lumotlar bazangiz kutubxonachiga qanday yordam berishini (masalan qaysi kitob band, qaysi "
         "bo'sh ekanini bilish) 4-5 jumlada tushuntiring.",
         "diagram: ma'lumotlar bazasi -> kutubxonachi foydasi sxemasi"),
    ],
}
# ------------------------------------------------------------------
# 8-sinf (4 modul, "On Track Stage 2") — Scratch o'zgaruvchilari, HTML
# veb-sayt, kompyuter tarmoqlari, video/animatsiya yaratish
# ------------------------------------------------------------------
GRADE8_TOPICS = [
    (1, "Maqsadni amalga oshirishda dasturlashdan foydalanish",
     "Scratch dasturida o'zgaruvchilar (variable) yaratish va ulardan foydalangan holda oddiy o'yin mantig'ini tuzish."),
    (2, "Maqsadni amalga oshirish uchun veb-sayt dizaynini yaratish",
     "HTML tilida oddiy veb-sahifa yaratish va sahifalar orasida havolalar (linklar) orqali bog'lash."),
    (3, "Kompyuter tarmoqlaridan maqsadli foydalanish",
     "Kompyuter tarmoqlari turlari, ulardan foydalanish maqsadlari va tarmoq xavfsizligi asoslari."),
    (4, "Maqsadni amalga oshirish uchun video yoki animatsiya yaratish",
     "Aniq maqsad (masalan tushuntirish videosi) uchun qisqa video yoki animatsiya loyihalash va yaratish."),
]

CHAPTER_PRACTICALS_8 = {
    1: [
        (1, "Oddiy hisoblagich o'zgaruvchisi", 0,
         "Scratch (yoki qog'ozdagi algoritm)da 'Ochkolar' nomli o'zgaruvchi yarating, uni 0 dan boshlab, tugma "
         "bosilganda +1 qo'shadigan algoritm yozing.", None),
        (2, "O'zgaruvchi qiymatlarini kuzatish", 1,
         "O'zgaruvchiga ketma-ket 5 ta amal (qo'shish, ayirish) bajarilganda uning qiymati qanday o'zgarib "
         "borishini jadvalga yozing.",
         "diagram: o'zgaruvchi qiymatining amal-ba-amal o'zgarish jadvali"),
        (3, "Ikkita o'zgaruvchili o'yin g'oyasi", 2,
         "'Ochkolar' va 'Jonlar' (health) nomli ikkita o'zgaruvchidan foydalanadigan oddiy o'yin g'oyasini "
         "tasvirlab yozing (qachon ochko qo'shiladi, qachon jon kamayadi).",
         "diagram: ikkita o'zgaruvchi va ular o'rtasidagi o'zaro ta'sir sxemasi"),
        (4, "For this Sprite vs For all Sprites", 3,
         "Bitta o'zgaruvchi faqat bitta spraytga tegishli bo'lishi va boshqasi barcha spraytlarga tegishli bo'lishi "
         "orasidagi farqni misol bilan tushuntiring.",
         "diagram: 'faqat shu sprayt' va 'barcha spraytlar' o'zgaruvchi doirasi sxemasi"),
        (5, "To'liq ochko tizimli o'yin algoritmi", 4,
         "Boshidan oxirigacha to'liq oddiy o'yin algoritmini yozing: o'zgaruvchi yaratish -> boshlang'ich qiymat "
         "-> shart bajarilganda o'zgartirish -> natijani ko'rsatish.",
         "diagram: to'liq o'yin algoritmining oqim sxemasi"),
    ],
    2: [
        (1, "Birinchi HTML sahifam", 0,
         "Oddiy matn muharririda .html fayl yarating: sarlavha va 2-3 jumlalik matndan iborat sodda veb-sahifa "
         "kodini yozing.", None),
        (2, "Ikki sahifani bog'lash", 1,
         "'Bosh sahifa' va 'Men haqimda' nomli ikkita HTML sahifa rejasini tuzing va ular orasida havola qanday "
         "ishlashini tushuntiring.",
         "diagram: ikki sahifa va ular orasidagi havola (link) sxemasi"),
        (3, "Sayt navigatsiya menyusi", 2,
         "3-4 sahifadan iborat kichik veb-sayt uchun yuqori qismda joylashadigan navigatsiya menyusi rejasini "
         "chizing.",
         "diagram: navigatsiya menyusi va sahifalar ro'yxati"),
        (4, "Tashqi havola qo'shish", 3,
         "O'z sahifangizdan boshqa (tashqi) veb-saytga o'tuvchi havola qo'shish kerak bo'lgan holatni tasvirlang "
         "va nima uchun kerakligini yozing.",
         "diagram: ichki va tashqi havolalarni farqlaydigan sxema"),
        (5, "To'liq mini-sayt rejasi", 4,
         "3 sahifalik (Bosh sahifa, Ma'lumot, Aloqa) to'liq mini-sayt uchun har sahifaning mazmuni va ular "
         "orasidagi barcha havolalar rejasini tuzing.",
         "diagram: 3 sahifali sayt xaritasi (site map)"),
    ],
    3: [
        (1, "Tarmoq turlari ro'yxati", 0,
         "Uy, maktab va shahar miqyosidagi tarmoqlarga misollar toping va ularni LAN yoki WAN sifatida "
         "belgilang.", None),
        (2, "Tarmoqqa ulanish sxemasi", 1,
         "Uyingizdagi barcha internetga ulangan qurilmalarni va ular routerga qanday ulanishini (simli/simsiz) "
         "sxema qilib chizing.",
         "diagram: uy tarmog'i sxemasi (router va unga ulangan qurilmalar)"),
        (3, "Tarmoq xavfsizligi choralari", 2,
         "Uy Wi-Fi tarmog'ini himoyalash uchun 6 ta chora (kuchli parol, tarmoq nomini yashirish va h.k.) "
         "ro'yxatlang.",
         "diagram: tarmoq xavfsizligi choralari cheklisti"),
        (4, "Fayl almashish stsenariysi", 3,
         "Sinfdoshingiz bilan katta hajmli faylni tarmoq orqali almashish uchun qanday usullar (umumiy papka, "
         "bulutli xizmat) borligini solishtiring.",
         "diagram: fayl almashish usullarini solishtiruvchi jadval"),
        (5, "Tarmoqdan foydalanish maqsadlari xaritasi", 4,
         "Maktab tarmog'idan turli maqsadlarda (o'qish, chop etish, aloqa) qanday foydalanish mumkinligini "
         "aqliy xarita (mind map) ko'rinishida tuzing.",
         "diagram: 'maktab tarmog'i' markazida, atrofida foydalanish maqsadlari"),
    ],
    4: [
        (1, "Video/animatsiya maqsadi rejasi", 0,
         "Kichik sinf o'quvchilariga 'Qo'lni to'g'ri yuvish' mavzusida qisqa video/animatsiya yaratish maqsadida "
         "asosiy g'oyani yozing.", None),
        (2, "Ssenariy taxtasi (storyboard)", 1,
         "Video/animatsiyangiz uchun 5 ta kadrdan iborat ssenariy taxtasi (har kadrda nima ko'rsatiladi) "
         "chizing.",
         "diagram: 5 kadrlik ssenariy taxtasi (storyboard) eskizi"),
        (3, "Ovoz va matn rejasi", 2,
         "Har bir kadrga qanday ovozli izoh yoki ekranga chiquvchi matn (subtitr) bo'lishini rejalashtirib "
         "yozing.",
         "diagram: kadr -> ovoz/matn taqsimoti jadvali"),
        (4, "Vaqt taqsimoti", 3,
         "30 soniyalik videoning har bir qismiga (kirish, asosiy qism, xulosa) qancha vaqt ajratishni "
         "rejalashtiring.",
         "diagram: 30 soniyalik video vaqt chizig'i (timeline)"),
        (5, "To'liq video loyihasi hujjati", 4,
         "Maqsad, auditoriya, ssenariy taxtasi va vaqt taqsimotini birlashtirgan to'liq video loyihasi "
         "hujjatini tuzing.",
         "diagram: to'liq video loyihasi hujjatining tuzilmasi"),
    ],
}
# ------------------------------------------------------------------
# 10-11-sinf (19 bob, Cambridge A-Level asosidagi) — maktabning yuqori
# sinflari VA texnikum 1-2-kurs "Informatika asoslari" sifatida ishlatiladi
# (applies_to_org_types = "maktab,texnikum")
# ------------------------------------------------------------------
GRADE1011_TOPICS = [
    (1, "Bilimlar bazasi",
     "Ma'lumot, axborot va bilim tushunchalari orasidagi farq; statik va dinamik axborot manbalarini taqqoslash."),
    (2, "Texnik va dasturiy ta'minot",
     "Kompyuter tizimlarining apparat (hardware) va dasturiy (software) qismlari, ularning turlari va vazifalari."),
    (3, "Kuzatuv va boshqaruv",
     "Sensorlar yordamida atrof-muhitni kuzatish va avtomatik boshqarish tizimlari (sanoat, transport, uy)."),
    (4, "Elektron xavfsizlik, salomatlik va xavfsizlik",
     "Internetdan xavfsiz foydalanish, uzoq muddatli kompyuter ishlatishning sog'liqqa ta'siri va jismoniy xavfsizlik."),
    (5, "Raqamli tengsizlik",
     "Texnologiyaga teng bo'lmagan kirish imkoniyati (raqamli tafovut) va uning ijtimoiy-iqtisodiy sabab-oqibatlari."),
    (6, "Tarmoqlardan foydalanish",
     "Tarmoqlarning amaliy qo'llanilishi — fayl almashish, masofaviy ishlash, bulutli xizmatlar."),
    (7, "Ekspert tizimlar",
     "Bilim bazasi va xulosa chiqarish mexanizmiga asoslangan ekspert tizimlarning tuzilishi va qo'llanilishi."),
    (8, "Elektron jadvallar",
     "Murakkab formulalar, funksiyalar va shartli formatlash yordamida elektron jadvalda chuqur tahlil qilish."),
    (9, "Ma'lumotlar bazasi va fayl konsepsiyalari",
     "Relyatsion ma'lumotlar bazasi tuzilishi, jadvallar orasidagi bog'lanishlar va so'rovlar (query) tuzish."),
    (10, "Tovush va videoni tahrirlash",
     "Audio va video fayllarni kesish, birlashtirish va effektlar qo'shish orqali tahrirlash asoslari."),
]

CHAPTER_PRACTICALS_1011_PART1 = {
    1: [
        (1, "Ma'lumot, axborot, bilim zanjiri", 0,
         "Bitta oddiy misol (masalan termometr o'lchovi) uchun: xom ma'lumot, undan olingan axborot va undan "
         "chiqarilgan bilim/qaror nima ekanini alohida-alohida yozing.", None),
        (2, "Statik va dinamik manbalar taqqoslash", 1,
         "Statik manbaga (masalan bosma kitob) va dinamik manbaga (masalan yangiliklar sayti) misol toping va "
         "ularni yangilanish tezligi, ishonchlilik bo'yicha taqqoslang.",
         "diagram: statik va dinamik manbalarni solishtiruvchi jadval"),
        (3, "O'z hayotingizdagi axborot manbalari auditi", 2,
         "Bir kun davomida foydalangan barcha axborot manbalaringizni (kitob, sayt, ilova) ro'yxatga oling va "
         "har birini statik/dinamik deb belgilang.",
         "diagram: bir kunlik axborot manbalari vaqt chizig'i"),
        (4, "Ishonchlilik va eskirish tahlili", 3,
         "Dinamik manbaning tezkorligi bilan xato ehtimoli orasidagi bog'liqlikni (tezroq yangilansa, xato "
         "ehtimoli oshishi mumkin) misol bilan tushuntiring.",
         "diagram: tezlik va ishonchlilik orasidagi bog'liqlik grafigi"),
        (5, "Qaror qabul qilishda manba tanlash", 4,
         "Muhim qaror (masalan sog'liq bo'yicha) qabul qilishda qaysi turdagi manbadan (statik/dinamik) "
         "foydalanish maqsadga muvofiqligini asoslab yozing.",
         "diagram: qaror turi -> mos manba turi jadvali"),
    ],
    2: [
        (1, "Apparat va dasturiy ta'minot ro'yxati", 0,
         "O'z kompyuteringizdagi 5 ta apparat qismini (protsessor, RAM va h.k.) va 5 ta dasturiy ta'minotni "
         "(operatsion tizim, brauzer va h.k.) alohida ro'yxatga oling.", None),
        (2, "Tizimli va amaliy dasturiy ta'minot", 1,
         "Operatsion tizim (tizimli DT) va matn muharriri (amaliy DT) orasidagi farqni, har biri nima uchun "
         "kerakligini tushuntirib yozing.",
         "diagram: tizimli va amaliy dasturiy ta'minotni solishtiruvchi jadval"),
        (3, "Qurilma tanlash stsenariysi", 2,
         "3 xil foydalanuvchi (dizayner, dasturchi, ofis xodimi) uchun mos apparat konfiguratsiyasini (protsessor, "
         "RAM, disk) tavsiya qiling.",
         "diagram: foydalanuvchi turi -> tavsiya etilgan konfiguratsiya jadvali"),
        (4, "Dasturiy ta'minot yangilanishi rejasi", 3,
         "Dasturiy ta'minotni muntazam yangilab turish nima uchun xavfsizlik va ishlash tezligiga foydali "
         "ekanini misollar bilan tushuntiring.",
         "diagram: yangilanmagan va yangilangan tizimni solishtiruvchi sxema"),
        (5, "Apparat-dasturiy ta'minot mos kelishi", 4,
         "Zamonaviy dastur eski (past quvvatli) kompyuterda ishlamasligi mumkinligini misol bilan tushuntirib, "
         "minimal talablar tushunchasini yoriting.",
         "diagram: dastur talablari va kompyuter imkoniyatlarini solishtirish"),
    ],
    3: [
        (1, "Sensorlar ro'yxati", 0,
         "Atrofingizdagi (uy, maktab, ko'cha) kamida 6 ta sensor asosidagi qurilmani toping va har biri nimani "
         "kuzatishini yozing.", None),
        (2, "Kuzatuv va boshqaruv farqi", 1,
         "Faqat kuzatuv qiluvchi tizim (masalan termometr) bilan kuzatib, avtomatik boshqaruv ham qiluvchi tizim "
         "(masalan termostat) orasidagi farqni tushuntiring.",
         "diagram: kuzatuv-only va kuzatuv+boshqaruv tizimlarini solishtirish"),
        (3, "Avtoturargoh to'sig'i algoritmi", 2,
         "Avtoturargoh to'sig'ining sensor orqali qanday ishlashini (mashina keldi -> sensor aniqladi -> to'siq "
         "ochildi) bosqichma-bosqich yozing.",
         "diagram: avtoturargoh to'sig'i ishlash algoritmi oqim sxemasi"),
        (4, "Sanoat xavfsizligida sensorlar", 3,
         "Kimyoviy zavodda sensorlar qanday xavfsizlikni ta'minlashi mumkinligini (gaz oqimi, harorat kuzatuvi) "
         "misol bilan tushuntiring.",
         "diagram: zavod sensorlari va ular kuzatadigan parametrlar sxemasi"),
        (5, "O'z 'aqlli uyim' loyihasi", 4,
         "Uyingiz uchun 4 ta sensor asosidagi avtomatlashtirish g'oyasini (masalan harorat, yorug'lik) "
         "loyihalashtiring — har biri qanday ishlashini yozing.",
         "diagram: 'aqlli uy' sensorlari va ular boshqaradigan qurilmalar sxemasi"),
    ],
    4: [
        (1, "Elektron xavfsizlik qoidalari", 0,
         "Ijtimoiy tarmoqlarda shaxsiy ma'lumotni himoya qilish bo'yicha 6 bandli qoidalar ro'yxati tuzing.", None),
        (2, "Ekran vaqti va sog'liq", 1,
         "Uzoq muddat ekran oldida o'tirishning ko'z va mushak-suyak tizimiga ta'sirini, buning oldini olish "
         "choralari bilan birga yozing.",
         "diagram: to'g'ri o'tirish holati va ekran masofasi sxemasi"),
        (3, "Jismoniy xavfsizlik auditi", 2,
         "Kompyuter xonasidagi kabellar, rozetkalar va jihozlar joylashuvini tekshirib, xavfsizlik "
         "tavsiyalarini yozing.",
         "diagram: xavfsiz kompyuter xonasi maketining sxemasi"),
        (4, "Onlayn xavflarni tanib olish", 3,
         "Fishing (firibgar) xabar va haqiqiy xabarni ajratib turadigan 6 ta belgini ro'yxatlang.",
         "diagram: haqiqiy va firibgar xabarni solishtiruvchi jadval"),
        (5, "Sog'lom ish tartibi rejasi", 4,
         "Kompyuterda uzoq ishlash uchun sog'lom kunlik tartib (tanaffuslar, ko'z mashqlari) rejasini tuzing.",
         "diagram: kunlik ish-tanaffus jadvali (soatlar bo'yicha)"),
    ],
    5: [
        (1, "Raqamli tengsizlik misollari", 0,
         "Internetga teng bo'lmagan kirish imkoniyatiga misollar (qishloq va shahar, turli mamlakatlar) "
         "toping va sabablarini yozing.", None),
        (2, "Tafovutning oqibatlari", 1,
         "Internetga kirish imkoniyati past bo'lgan insonlar ta'lim va ish topishda qanday qiyinchiliklarga "
         "duch kelishi mumkinligini tushuntiring.",
         "diagram: internetga kirish -> ta'lim/ish imkoniyatlari bog'liqligi sxemasi"),
        (3, "Mamlakat darajasida tahlil", 2,
         "O'z mamlakatingizdagi (yoki mintaqangizdagi) raqamli tafovut jabhalarini (shahar/qishloq, yosh guruhlari) "
         "aniqlab, qisqa tahlil yozing.",
         "diagram: internetdan foydalanish foizini solishtiruvchi ustunli diagramma"),
        (4, "Tafovutni kamaytirish yechimlari", 3,
         "Raqamli tafovutni kamaytirish uchun 5 ta amaliy yechim (masalan jamoat internet markazlari) "
         "taklif qiling.",
         "diagram: muammo -> taklif etilgan yechim jadvali"),
        (5, "Tezlik va tajriba bog'liqligi", 4,
         "Yuqori tezlikdagi internetga ega foydalanuvchi va past tezlikdagi foydalanuvchining onlayn tajribasini "
         "(video ko'rish, o'qish) solishtiring.",
         "diagram: internet tezligi va foydalanuvchi tajribasi bog'liqligi grafigi"),
    ],
    6: [
        (1, "Tarmoq orqali fayl almashish", 0,
         "Sinfdoshingiz bilan fayl almashish uchun mavjud 3 ta usulni (umumiy papka, bulutli xizmat, email) "
         "solishtiring.", None),
        (2, "Masofaviy ishlash sxemasi", 1,
         "Uydan turib maktab tarmog'idagi resurslarga (masalan fayl serveri) qanday xavfsiz ulanish mumkinligini "
         "tasvirlab yozing.",
         "diagram: masofaviy ulanish (uy -> internet -> maktab tarmog'i) sxemasi"),
        (3, "Bulutli xizmatlar afzalligi", 2,
         "Bulutli saqlash xizmatining (masalan Google Drive) mahalliy saqlashga nisbatan 4 ta afzalligini "
         "yozing.",
         "diagram: bulutli va mahalliy saqlashni solishtiruvchi jadval"),
        (4, "Tarmoq resurslarini bo'lishish", 3,
         "Ofis tarmog'ida bitta printerni bir nechta kompyuter qanday birgalikda ishlatishi mumkinligini "
         "tushuntiring.",
         "diagram: bir nechta kompyuter -> tarmoq -> umumiy printer sxemasi"),
        (5, "Xavfsiz masofaviy kirish rejasi", 4,
         "Tashkilot xodimlari uyidan ish tarmog'iga xavfsiz kirishi uchun (VPN, parol siyosati) qoidalar "
         "ro'yxatini tuzing.",
         "diagram: xavfsiz masofaviy kirish qadamlari sxemasi"),
    ],
    7: [
        (1, "Ekspert tizim g'oyasi", 0,
         "Bironta sohada (masalan kasal tashxisi) ekspert tizim qanday yordam berishi mumkinligini qisqa "
         "misol bilan tasvirlang.", None),
        (2, "Bilim bazasi va qoidalar", 1,
         "O'zingiz tanlagan sohada (masalan o'simlik parvarishi) 6 ta 'agar-unda' qoidasidan iborat oddiy bilim "
         "bazasi yozing.",
         "diagram: agar-unda qoidalari zanjiri (qaror daraxti)"),
        (3, "Xulosa chiqarish jarayoni", 2,
         "Foydalanuvchi kiritgan javoblar asosida ekspert tizim qanday xulosaga kelishini bosqichma-bosqich "
         "misol bilan ko'rsating.",
         "diagram: savol-javob -> xulosa oqim sxemasi"),
        (4, "Ekspert tizim vs inson mutaxassis", 3,
         "Ekspert tizimning inson mutaxassisga nisbatan afzallik va kamchiliklarini (tezlik, tajriba, "
         "moslashuvchanlik) solishtiring.",
         "diagram: ekspert tizim va inson mutaxassisni solishtiruvchi jadval"),
        (5, "O'z ekspert tizimingiz loyihasi", 4,
         "Kichik sohada (masalan 'qaysi sport turi menga mos') to'liq oddiy ekspert tizim loyihasini (savollar "
         "+ qoidalar + mumkin bo'lgan xulosalar) tuzing.",
         "diagram: to'liq ekspert tizim sxemasi (savollar -> qoidalar -> xulosalar)"),
    ],
    8: [
        (1, "Murakkab formula yozish", 0,
         "Elektron jadvalda IF (agar) funksiyasidan foydalanib, 'agar ball 60 dan katta bo'lsa o'tdi, aks holda "
         "qoldi' formulasini yozing.", None),
        (2, "SUM va AVERAGE funksiyalari", 1,
         "10 ta sondan iborat ustun uchun yig'indi (SUM) va o'rtacha (AVERAGE) qiymatlarni hisoblovchi "
         "formulalarni yozing.",
         "diagram: SUM va AVERAGE formulalarining natijalari jadvali"),
        (3, "Shartli formatlash rejasi", 2,
         "Ballar ustunida 60 dan past qiymatlarni qizil, 90 dan yuqorilarni yashil rangda avtomatik "
         "belgilash qoidasini tavsiflang.",
         "diagram: shartli formatlash natijasi (rangli katakchalar) namunasi"),
        (4, "Ko'p shartli IF formulasi", 3,
         "Ballarga qarab 'A', 'B', 'C', 'D' baholarini beruvchi ko'p bosqichli IF formulasi mantig'ini "
         "yozing.",
         "diagram: ball oralig'i -> baho qaror daraxti"),
        (5, "To'liq tahlil jadvali", 4,
         "Sinfning 10 ta xayoliy bahosidan iborat jadval tuzing: jami, o'rtacha, eng yuqori, eng past va "
         "shartli formatlash bilan to'liq tahlil qiling.",
         "diagram: to'liq baho tahlili jadvali va uning barcha formulalar sxemasi"),
    ],
    9: [
        (1, "Relyatsion jadvallar g'oyasi", 0,
         "'O'quvchilar' va 'Sinflar' nomli ikkita jadval yarating, ular orasida qaysi maydon orqali "
         "bog'lanishi mumkinligini aniqlang.", None),
        (2, "Birlamchi va tashqi kalit", 1,
         "'O'quvchilar' jadvalidagi birlamchi kalit (primary key) va 'Sinflar' jadvaliga bog'lovchi tashqi "
         "kalit (foreign key) tushunchalarini misol bilan tushuntiring.",
         "diagram: ikki jadval va ularni bog'lovchi kalit chizig'i"),
        (3, "So'rov (query) tuzish", 2,
         "Ma'lum bir sinfdagi barcha o'quvchilarni chiqaruvchi so'rov shartini yozing.",
         "diagram: so'rov sharti va natija jadvali"),
        (4, "Ma'lumotlar takrorlanishi muammosi", 3,
         "Agar 'Sinflar' ma'lumoti har bir o'quvchi qatorida takrorlansa (oddiy faylli baza), qanday muammolar "
         "yuzaga kelishini tushuntiring.",
         "diagram: takrorlangan va relyatsion tuzilishni solishtiruvchi sxema"),
        (5, "To'liq mini ma'lumotlar bazasi loyihasi", 4,
         "3 ta bog'langan jadvaldan (masalan O'quvchilar, Sinflar, Baholar) iborat mini ma'lumotlar bazasi "
         "sxemasini loyihalang.",
         "diagram: 3 jadval va ularning bog'lanish sxemasi (ER diagramma)"),
    ],
    10: [
        (1, "Audio kesish rejasi", 0,
         "5 daqiqalik xayoliy audio yozuvdan faqat kerakli 30 soniyalik qismini qanday ajratib olish "
         "kerakligini bosqichma-bosqich yozing.", None),
        (2, "Video kesish va birlashtirish", 1,
         "3 ta qisqa video parchasini (kirish, asosiy qism, xulosa) qanday ketma-ket birlashtirish "
         "kerakligini rejalashtiring.",
         "diagram: 3 video parchasining birlashtirish ketma-ketligi"),
        (3, "Fon musiqasi va ovoz balansi", 2,
         "Videoga fon musiqasi qo'shilganda, asosiy nutq ovozi bosilib qolmasligi uchun qanday balans "
         "kerakligini tushuntiring.",
         "diagram: ovoz va musiqa balansini ko'rsatuvchi shkala"),
        (4, "Effekt va o'tishlar rejasi", 3,
         "Video bo'limlari orasida qanday o'tish effektlari (so'nish, sirg'alish) qo'llash mumkinligini va "
         "har biri qachon mos kelishini yozing.",
         "diagram: video bo'limlari va ular orasidagi o'tish effektlari"),
        (5, "To'liq video tahrirlash rejasi", 4,
         "1 daqiqalik tushuntirish videosi uchun to'liq tahrirlash rejasini (kesish, birlashtirish, musiqa, "
         "effekt) yozing.",
         "diagram: 1 daqiqalik video uchun to'liq tahrirlash vaqt chizig'i (timeline)"),
    ],
}
GRADE1011_TOPICS_PART2 = [
    (11, "Yangi texnologiyalar",
     "Sun'iy intellekt, virtual/kengaytirilgan reallik va boshqa zamonaviy texnologiyalarning jamiyatga ta'siri."),
    (12, "Axborot texnologiyalarining o'rni va jamiyatdagi ta'siri",
     "AKTning kasblar, ta'lim va kundalik hayotga ta'siri, ijobiy va salbiy oqibatlari."),
    (13, "Tarmoqlar",
     "Tarmoq topologiyalari, protokollar va tarmoq qurilmalarining chuqurlashtirilgan tahlili."),
    (14, "Loyiha boshqaruvi",
     "Loyihani rejalashtirish, vazifalarni taqsimlash va kritik yo'l (critical path) tushunchasi."),
    (15, "Tizimdan foydalanish sikli",
     "Yangi tizimni joriy etish usullari (to'g'ridan-to'g'ri, parallel, bosqichma-bosqich, pilot)."),
    (16, "Grafik yaratish",
     "Vektor va raster grafika, murakkab tasvir va chizmalar yaratish uskunalari."),
    (17, "Animatsiya",
     "Kadr-bakadr va tween animatsiya texnikalari, harakatni jonlantirish asoslari."),
    (18, "Xatlarni birlashtirish",
     "Ma'lumotlar manbasi va shablon hujjatni birlashtirib, shaxsiylashtirilgan xatlar (mail merge) yaratish."),
    (19, "Veb uchun dasturlash",
     "JavaScript tilida o'zgaruvchilar, shartlar va oddiy interaktiv veb-sahifa mantig'ini yozish."),
]

CHAPTER_PRACTICALS_1011_PART2 = {
    11: [
        (1, "Yangi texnologiyalar ro'yxati", 0,
         "So'nggi 5 yilda paydo bo'lgan (yoki mashhur bo'lgan) 5 ta yangi texnologiyani (SI, VR va h.k.) "
         "ro'yxatga oling va har biri nima uchun ishlatilishini yozing.", None),
        (2, "SI kundalik hayotda", 1,
         "Sun'iy intellekt ishlatiladigan 5 ta kundalik ilova/xizmatni (ovozli yordamchi, tavsiya tizimi) "
         "toping va ular qanday ishlashini qisqacha tushuntiring.",
         "diagram: SI ilovalari va ular bajaradigan vazifalar jadvali"),
        (3, "VR va AR farqi", 2,
         "Virtual reallik (VR) va kengaytirilgan reallik (AR) orasidagi farqni, har biriga misol bilan "
         "tushuntiring.",
         "diagram: VR va AR tajribasini solishtiruvchi sxema"),
        (4, "Texnologiya etikasi muhokamasi", 3,
         "Yangi texnologiya (masalan yuzni tanish tizimi)ning foyda va xavf tomonlarini taqqoslovchi jadval "
         "tuzing.",
         "diagram: foyda va xavf tomonlarini ko'rsatuvchi ikki ustunli jadval"),
        (5, "Kelajak texnologiyasi loyihasi", 4,
         "10 yildan keyin hayotimizni o'zgartirishi mumkin bo'lgan xayoliy texnologiya g'oyasini tasvirlab, "
         "u qanday ishlashini yozing.",
         "diagram: taklif etilgan texnologiyaning ishlash sxemasi"),
    ],
    12: [
        (1, "AKT ta'sir qilgan kasblar", 0,
         "AKT sabab o'zgargan yoki yo'qolgan 5 ta kasbni toping va har biriga nima bo'lganini qisqa yozing.", None),
        (2, "Ta'limdagi o'zgarishlar", 1,
         "AKT ta'limga qanday ta'sir qilganini (masofaviy ta'lim, elektron darsliklar) 5 ta misol bilan "
         "yoriting.",
         "diagram: an'anaviy va AKT-asosidagi ta'limni solishtiruvchi jadval"),
        (3, "Ijobiy va salbiy ta'sirlar", 2,
         "AKTning jamiyatga ijobiy va salbiy ta'sirini har biridan 4 tadan yozib, taqqoslovchi jadval "
         "tuzing.",
         "diagram: ijobiy/salbiy ta'sirlarni ko'rsatuvchi ikki ustunli jadval"),
        (4, "O'z oilangizda AKT ta'siri", 3,
         "AKT oilangizning kundalik hayotini (aloqa, xarid, o'qish) qanday o'zgartirganini shaxsiy misollar "
         "bilan yozing.",
         "diagram: AKTdan oldin va keyin oilaviy hayot taqqoslash sxemasi"),
        (5, "Kelajak bashorati", 4,
         "Keyingi 10 yilda AKT jamiyatni yana qanday o'zgartirishi mumkinligi haqida asoslangan bashorat "
         "yozing.",
         "diagram: joriy holat -> kutilayotgan o'zgarish yo'nalishi sxemasi"),
    ],
    13: [
        (1, "Tarmoq topologiyalari", 0,
         "Yulduz (star) va shina (bus) topologiyalarining sxemasini chizib, har birining 1 ta afzalligini "
         "yozing.", None),
        (2, "Protokollar ro'yxati", 1,
         "HTTP, HTTPS va FTP protokollarining har biri nima uchun ishlatilishini jadvalga yozing.",
         "diagram: protokol nomi -> vazifasi jadvali"),
        (3, "Tarmoq qurilmalari vazifalari", 2,
         "Router, svich va modem qurilmalarining har biri tarmoqda qanday vazifani bajarishini "
         "solishtiring.",
         "diagram: uchta qurilma va ularning tarmoqdagi o'rni sxemasi"),
        (4, "IP manzil va MAC manzil farqi", 3,
         "IP manzil va MAC manzil orasidagi farqni, har biri nima uchun kerakligini tushuntirib yozing.",
         "diagram: IP va MAC manzillarni solishtiruvchi jadval"),
        (5, "Maktab tarmog'i topologiyasi loyihasi", 4,
         "Maktab uchun bir nechta xona (kompyuter xonasi, kutubxona, ma'muriyat)ni bog'laydigan tarmoq "
         "topologiyasini loyihalashtiring.",
         "diagram: maktab tarmog'ining to'liq topologiya sxemasi"),
    ],
    14: [
        (1, "Loyiha vazifalari ro'yxati", 0,
         "Kichik loyiha (masalan sinf bayrami tashkil etish) uchun bajarilishi kerak bo'lgan 6 ta vazifani "
         "ro'yxatga oling.", None),
        (2, "Vazifalar ketma-ketligi", 1,
         "6 ta vazifangizni qaysi tartibda bajarilishi kerakligini (qaysi vazifa qaysinisidan oldin) "
         "belgilab, ketma-ketlik sxemasini chizing.",
         "diagram: vazifalar ketma-ketligi (oqim) sxemasi"),
        (3, "Resurs va muddat taqsimoti", 2,
         "Har bir vazifaga kim mas'ul bo'lishi va necha kun kerak bo'lishini jadvalga yozing.",
         "diagram: vazifa -> mas'ul -> muddat jadvali"),
        (4, "Kritik yo'l aniqlash", 3,
         "Loyihangizdagi qaysi vazifalar zanjiri 'kritik yo'l' (kechiktirilsa butun loyiha kechikadigan "
         "vazifalar) ekanini aniqlang.",
         "diagram: kritik yo'lni belgilagan vazifalar tarmoq sxemasi"),
        (5, "To'liq loyiha rejasi", 4,
         "Vazifalar, ketma-ketlik, resurslar va kritik yo'lni birlashtirgan to'liq loyiha boshqaruvi "
         "hujjatini tuzing.",
         "diagram: to'liq loyiha jadvali (Gantt diagrammasiga o'xshash)"),
    ],
    15: [
        (1, "Joriy etish usullari ro'yxati", 0,
         "Yangi tizimni joriy etishning 4 usulini (to'g'ridan-to'g'ri, parallel, bosqichma-bosqich, pilot) "
         "nomlab, qisqacha ta'riflang.", None),
        (2, "Har usulning xavf darajasi", 1,
         "4 usulning har birini xavf darajasi (yuqori/o'rta/past) bo'yicha baholab, sababini yozing.",
         "diagram: usul -> xavf darajasi jadvali"),
        (3, "Maktab uchun eng mos usul", 2,
         "Maktabda yangi elektron kundalik tizimini joriy etish uchun qaysi usul eng mos ekanini tanlab, "
         "asoslang.",
         "diagram: tanlangan usulning bosqichlari sxemasi"),
        (4, "Parallel joriy etish stsenariysi", 3,
         "Eski va yangi tizim bir vaqtda ishlatilganda (parallel usul) qanday afzallik va qiyinchiliklar "
         "bo'lishini yozing.",
         "diagram: eski va yangi tizim parallel ishlash sxemasi"),
        (5, "To'liq joriy etish rejasi", 4,
         "Tanlagan usulingiz bo'yicha bosqichma-bosqich to'liq joriy etish rejasini (kim, qachon, nima "
         "qiladi) tuzing.",
         "diagram: to'liq joriy etish reja-jadvali"),
    ],
    16: [
        (1, "Vektor va raster taqqoslash", 0,
         "Vektor va raster grafikaning har biriga misol toping va kattalashtirilganda nima farq "
         "borligini yozing.", None),
        (2, "Logotip loyihasi (vektor)", 1,
         "O'zingiz uchun (yoki xayoliy klub uchun) oddiy geometrik shakllardan iborat vektor logotip "
         "eskizini chizing.",
         "diagram: vektor logotipning eskizi (asosiy shakllar bilan)"),
        (3, "Rang rejimlari", 2,
         "RGB va CMYK rang rejimlarining har biri qachon (ekran uchun/chop etish uchun) ishlatilishini "
         "tushuntiring.",
         "diagram: RGB va CMYK rang doiralarini solishtiruvchi sxema"),
        (4, "Murakkab chizma qatlamlari", 3,
         "Murakkab poster uchun fon, asosiy matn, dekorativ elementlar qatlamlarini rejalashtiring.",
         "diagram: poster qatlamlari sxemasi (fon-matn-dekor)"),
        (5, "To'liq grafik loyihasi", 4,
         "Maktab tadbiri uchun to'liq grafik dizayn (poster) rejasini — o'lcham, ranglar, shriftlar, "
         "tarkib bilan — tuzing.",
         "diagram: to'liq poster maketining eskizi"),
    ],
    17: [
        (1, "Kadr-bakadr animatsiya g'oyasi", 0,
         "Oddiy sakrayotgan to'p animatsiyasi uchun 4 ta ketma-ket kadr eskizini chizing.", None),
        (2, "Tween animatsiya tushunchasi", 1,
         "Boshlang'ich va oxirgi holat berilganda, oraliq kadrlar avtomatik hosil bo'lishi (tweening) "
         "g'oyasini misol bilan tushuntiring.",
         "diagram: boshlang'ich va oxirgi kadr + oraliq kadrlar sxemasi"),
        (3, "Harakat tezligi (frame rate)", 2,
         "Sekin va tez animatsiya orasidagi farqni kadrlar sonining animatsiya sekundiga nisbati orqali "
         "tushuntiring.",
         "diagram: past va yuqori kadr tezligini solishtiruvchi sxema"),
        (4, "Oddiy belgi animatsiyasi rejasi", 3,
         "Oddiy belgi (masalan sprayt)ning yurish animatsiyasi uchun kerakli kadrlar ketma-ketligini "
         "rejalashtiring.",
         "diagram: yurish animatsiyasi kadrlari ketma-ketligi"),
        (5, "To'liq qisqa animatsiya loyihasi", 4,
         "10 soniyalik qisqa animatsion hikoya uchun barcha kadrlar, harakatlar va vaqt taqsimotini "
         "o'z ichiga olgan to'liq reja tuzing.",
         "diagram: 10 soniyalik animatsiya vaqt chizig'i (timeline)"),
    ],
    18: [
        (1, "Ma'lumotlar manbasi va shablon g'oyasi", 0,
         "5 kishilik ma'lumotlar ro'yxati (ism, manzil) va ularga yuboriladigan umumiy shablon xat "
         "matnini tayyorlang.", None),
        (2, "Shablon ichidagi o'zgaruvchi maydonlar", 1,
         "Shablon xatingizda qaysi so'zlar (ism, sana) har kishi uchun avtomatik almashtirilishi "
         "kerakligini belgilang.",
         "diagram: shablon matni va unda belgilangan o'zgaruvchi maydonlar"),
        (3, "Birlashtirish natijasi", 2,
         "5 kishilik ma'lumotlar manbasi va shablon birlashtirilganda hosil bo'ladigan 5 ta "
         "shaxsiylashtirilgan xatning namunasini (kamida 2 tasini to'liq) yozing.",
         "diagram: manba + shablon -> shaxsiylashtirilgan xatlar oqimi"),
        (4, "Xato ma'lumot ta'siri", 3,
         "Agar ma'lumotlar manbasida bitta ism noto'g'ri yozilgan bo'lsa, bu qanday xato natijaga olib "
         "kelishini misol bilan ko'rsating.",
         "diagram: xato ma'lumot -> xato natija zanjiri"),
        (5, "Katta hajmli xat birlashtirish rejasi", 4,
         "100 kishiga taklifnoma yuborish uchun mail merge jarayonini bosqichma-bosqich (ma'lumot "
         "tayyorlash -> shablon -> birlashtirish -> tekshirish) rejalashtiring.",
         "diagram: mail merge to'liq jarayon sxemasi"),
    ],
    19: [
        (1, "O'zgaruvchi e'lon qilish", 0,
         "JavaScript'da ism va yosh saqlaydigan ikkita o'zgaruvchi e'lon qiling (var ism = \"...\"; "
         "var yosh = ...;) va ularning qiymatlarini yozing.", None),
        (2, "Taqqoslash operatorlari jadvali", 1,
         "'>', '<', '>=', '<=' operatorlarining har biri uchun 2 tadan misol (to'g'ri va xato natijali) "
         "yozing.",
         "diagram: taqqoslash operatorlari va ularning natijalari jadvali"),
        (3, "Oddiy shart (if) mantig'i", 2,
         "'Agar yosh 18 dan katta bo'lsa \"kattasiz\", aks holda \"yoshsiz\"' mantig'ini so'z bilan "
         "yozing (kod sintaksisi shart emas).",
         "diagram: yosh -> shart -> natija qaror daraxti"),
        (4, "Arifmetik hisoblash zanjiri", 3,
         "Ikki o'zgaruvchini qo'shib, natijani uchinchi o'zgaruvchiga yozadigan (firstNumber + "
         "secondNumber = result) hisoblash zanjirini tushuntiring.",
         "diagram: ikki o'zgaruvchi -> qo'shish -> natija o'zgaruvchisi sxemasi"),
        (5, "Oddiy interaktiv sahifa g'oyasi", 4,
         "Foydalanuvchi yoshini kiritganda 'kattasiz' yoki 'yoshsiz' deb javob beradigan oddiy veb-sahifa "
         "mantig'ini boshidan oxirigacha rejalashtiring.",
         "diagram: foydalanuvchi kiritishi -> JavaScript tekshiruvi -> natija ko'rsatish oqimi"),
    ],
}
CHAPTER_PRACTICALS_9 = {
    1: [
    (1, "Kompyuterim komponentlari daftarchasi", 0,
     "O'zingiz foydalanayotgan (yoki maktab) kompyuterini ochmasdan turib, "
     "unga tegishli hujjatlar (quti, sayt, 'Tizim haqida' oynasi) yordamida "
     "quyidagi ma'lumotlarni jadval qilib yozing: protsessor modeli, RAM hajmi "
     "(GB), qattiq disk/SSD hajmi. Har bir qiymat oldiga u ROM'mi yoki RAM'mi, "
     "vaqtinchalimi yoki doimiymi — belgilab qo'ying.", None),
    (2, "RAM va ROM taqqoslash sxemasi", 1,
     "Qog'ozda yoki chizish dasturida ikkita ustunli jadval chizing: 'RAM' va "
     "'ROM'. Har biriga kamida 4 ta xususiyat yozing (masalan: o'chganda "
     "ma'lumot yo'qoladimi, hajmi kattami, narxi qanday, vazifasi nima). "
     "Pastga o'zingiz PC/noutbukingizdagi RAM hajmini yozib, nima uchun "
     "ko'proq RAM tezroq ishlashga yordam berishini 3-4 gapda tushuntiring.",
     "diagram: RAM va ROM taqqoslash sxemasi (ikki ustunli jadval, oq-qora chizma)"),
    (3, "Kiritish/chiqarish qurilmalari auditi", 2,
     "O'z uyingiz yoki maktabingizdagi kamida 8 ta elektron qurilmani ro'yxatga "
     "oling (masalan sichqoncha, printer, veb-kamera, telefon ekrani...). Har "
     "birini 'faqat kiritish', 'faqat chiqarish' yoki 'ham kiritish, ham "
     "chiqarish' toifasiga ajrating va sababini yozing.",
     "diagram: kiritish/chiqarish qurilmalarining oqim sxemasi (qurilma -> CPU -> qurilma)"),
    (4, "Mikroprotsessor izlanishi", 3,
     "Uyingizda (yoki tanish oilada) mikroprotsessor bilan boshqariladigan "
     "kamida 3 ta maishiy jihoz toping (kir yuvish mashinasi, mikroto'lqinli "
     "pech, televizor pulti va h.k.). Har biri uchun: mikroprotsessor qanday "
     "vazifani bajaradi va u ishlamasa nima bo'ladi — deb yozing.",
     "diagram: bitta maishiy jihoz ichidagi mikroprotsessor joylashuvi (soddalashtirilgan sxema)"),
    (5, "Xotira ierarxiyasi posteri", 4,
     "A4 varaqda (yoki taqdimot slaydida) 'Xotira ierarxiyasi' posterini "
     "tuzing: eng tezdan eng sekiningacha — protsessor registri, RAM, SSD/HDD, "
     "tashqi flesh xotira. Har bosqich oldiga taxminiy hajim va tezlik "
     "haqida 1 gap yozing.",
     "diagram: xotira ierarxiyasi piramidasi (tepada tez/kichik, pastda sekin/katta)"),
    ],
    2: [
        (1, "Kiritish/chiqarish jadvali", 0,
         "Sinfingizdagi kompyuter xonasida (yoki uyingizda) mavjud kamida 10 ta qurilmani ro'yxatga oling. Har birini 'kiritish', "
         "'chiqarish' yoki 'ikkalasi ham' ustuniga joylashtiring va nima uchun aynan shu toifaga tegishli ekanini 1 jumlada izohlang.", None),
        (2, "Klaviatura turlarini taqqoslash", 1,
         "QWERTY, konseptual va ergonomik klaviaturalarni taqqoslovchi jadval tuzing: har biri qayerda (qanday sharoitda) "
         "qulayroq ishlatilishini, kamida 2 tadan afzallik/kamchilikni yozing.",
         "diagram: uchta klaviatura turining soddalashtirilgan chizmasi yonma-yon"),
        (3, "Sensorli va an'anaviy kiritish qurilmalari", 2,
         "Sensorli ekran, sichqoncha va trekbolni tezlik, aniqlik va charchash darajasi bo'yicha 1 dan 5 gacha baholab, "
         "jadval tuzing. Qaysi vazifa uchun qaysi qurilma qulayroq ekanini (masalan chizish, matn terish, o'yin) yozing.",
         "diagram: uch qurilmani solishtiruvchi radar (yulduzsimon) diagramma"),
        (4, "Chiqarish qurilmasi tanlash stsenariysi", 3,
         "Uchta stsenariy uchun (katta zalda taqdimot, uy kinoteatri, dizaynerning aniq rang chiqarish ehtiyoji) eng mos "
         "chiqarish qurilmasini tanlang va sababini yozing (masalan proyektor, monitor, maxsus printer).",
         "diagram: stsenariy -> tavsiya etilgan qurilma oqim sxemasi"),
        (5, "O'z ish stolim uchun qurilma to'plami posteri", 4,
         "O'zingiz orzu qilgan ish stoli uchun kiritish va chiqarish qurilmalari to'plamini tanlang (kamida 6 ta), har birini "
         "nima uchun tanlaganingizni yozing va posterga joylashtiring.",
         "diagram: ish stoli va unga ulangan qurilmalar sxemasi (yuqoridan ko'rinish)"),
    ],
    3: [
        (1, "Xotira turlari solishtiruvi", 0,
         "Magnitli, optik va qattiq holatdagi (SSD/flesh) ma'lumot tashuvchilarni jadvalga soling: har biriga misol qurilma, "
         "taxminiy hajm va asosiy kamchiligini yozing.", None),
        (2, "Zaxira nusxalash rejasi", 1,
         "O'zingizning shaxsiy fayllaringiz (rasm, hujjat, loyihalar) uchun zaxira nusxalash rejasi tuzing: qaysi fayllar, "
         "qaysi tashuvchida (bulut, tashqi disk, flesh) va qancha muddatda saqlanishi kerakligini jadval qilib yozing.",
         "diagram: fayl turi -> tashuvchi -> saqlash muddati oqim sxemasi"),
        (3, "Portativ xotira qurilmalari auditi", 2,
         "Uyingizdagi barcha ma'lumot tashuvchi qurilmalarni (flesh, tashqi disk, xotira kartasi va h.k.) ro'yxatga oling, "
         "har birining taxminiy hajmini va nima uchun ishlatilishini yozing.",
         "diagram: qurilmalar hajmini solishtiruvchi ustunli diagramma"),
        (4, "Bevosita kirish vs ketma-ket kirish", 3,
         "Qattiq diskdagi bevosita kirish (indeks orqali) va eski magnit lentadagi ketma-ket kirish usullarini taqqoslang: "
         "har birida faylni topish necha qadam talab qilishini oddiy misol bilan tushuntiring.",
         "diagram: bevosita kirish va ketma-ket kirish jarayonlarining ikkita sxemasi"),
        (5, "Bulutli saqlash vs mahalliy saqlash", 4,
         "Bulutli saqlash (Google Drive kabi) va mahalliy tashuvchida saqlashni tezlik, xavfsizlik, narx va internetga "
         "bog'liqlik mezonlari bo'yicha taqqoslovchi jadval tuzing va xulosa chiqaring.",
         "diagram: bulutli vs mahalliy saqlashni solishtiruvchi taqqoslash jadvali"),
    ],
    4: [
        (1, "Uy tarmog'im sxemasi", 0,
         "Uyingizdagi (yoki maktabingizdagi) internetga ulangan barcha qurilmalarni ro'yxatga oling (telefon, noutbuk, "
         "smart-TV va h.k.) va ularning routerga qanday ulanishini (Wi-Fi yoki kabel) belgilang.", None),
        (2, "LAN, WLAN, WAN farqi", 1,
         "LAN, WLAN va WAN tarmoqlarini geografik qamrov, tezlik va tipik qo'llanish sohasi bo'yicha taqqoslovchi jadval "
         "tuzing, har biriga real hayotdan misol keltiring.",
         "diagram: LAN ichida WLAN, undan tashqarida WAN — konsentrik doiralar sxemasi"),
        (3, "Router yo'nalish jadvali simulyatsiyasi", 2,
         "Oddiy qog'oz sxemasida 4 ta 'router' va ular orasidagi bog'lanishlarni chizing, so'ng bitta ma'lumot paketi "
         "A nuqtadan D nuqtaga necha xil yo'l bilan borishi mumkinligini ko'rsating.",
         "diagram: 4 ta tugun (router) va ular orasidagi bog'lanishlar grafigi"),
        (4, "Wi-Fi va Bluetooth qamrovi taqqoslash", 3,
         "Wi-Fi va Bluetooth texnologiyalarini masofa, tezlik va energiya sarfi bo'yicha solishtiring, har biri uchun "
         "kundalik hayotdan 2 tadan foydalanish misolini yozing.",
         "diagram: Wi-Fi va Bluetooth qamrov radiusini solishtiruvchi doiralar"),
        (5, "Xavfsiz internetga ulanish cheklist", 4,
         "Jamoat Wi-Fi tarmog'idan foydalanishda xavfsizlikni ta'minlash uchun 8 bandli cheklist (tekshiruv ro'yxati) "
         "tuzing (masalan: VPN, HTTPS, avtomatik ulanishni o'chirish va h.k.).",
         "diagram: xavfsiz ulanish qadamlarining bosqichma-bosqich sxemasi"),
    ],
    5: [
        (1, "AT kasblarga ta'siri jadvali", 0,
         "5 ta kasbni tanlang (masalan hisobchi, haydovchi, sotuvchi) va AT/avtomatlashtirish ularga qanday ta'sir "
         "qilganini (yo'qolgan, o'zgargan yoki yangi paydo bo'lgan) jadvalga yozing.", None),
        (2, "RSI profilaktikasi rejasi", 1,
         "Kompyuterda uzoq ishlashdan kelib chiqadigan mushak-suyak muammolarining (RSI) oldini olish uchun kunlik "
         "ish tartibi (masalan har 30 daqiqada tanaffus) rejasini tuzing.",
         "diagram: to'g'ri o'tirish holati va monitor balandligi sxemasi"),
        (3, "Mikroprotsessorli uy jihozlari xaritasi", 2,
         "Uyingizdagi mikroprotsessor bilan boshqariladigan kamida 5 ta jihozni toping va har biri qanday vazifani "
         "avtomatlashtirganini yozing.",
         "diagram: uy xonalari va ulardagi 'aqlli' jihozlar xaritasi"),
        (4, "Ish soatlari modelining o'zgarishi", 3,
         "Masofaviy ishlash (remote work) ijobiy va salbiy tomonlarini kamida 4 tadan sanab, o'z oilangizdagi yoki "
         "tanishlaringizdagi bir misol bilan tasdiqlang.",
         "diagram: an'anaviy ofis va masofaviy ish tartibini solishtiruvchi jadval"),
        (5, "Sog'liq va ekran vaqti kuzatuvi", 4,
         "1 hafta davomida kuniga ekran oldida o'tkazgan vaqtingizni kuzatib jadval tuzing, so'ng haftalik statistikani "
         "diagrammada tasvirlang va xulosa yozing.",
         "diagram: haftalik ekran vaqti ustunli diagrammasi"),
    ],
    6: [
        (1, "AKT qo'llanilgan sohalar ro'yxati", 0,
         "Bank, tibbiyot, ta'lim va savdo sohalaridan har biriga AKT qanday joriy etilganiga 1 tadan real misol toping "
         "va qisqacha yozing.", None),
        (2, "Ekspert tizim stsenariysi", 1,
         "O'zingiz tanlagan sohada (masalan kasal tashxisi yoki yo'l harakati) oddiy 'ekspert tizim' qoidalarini "
         "(agar-unda ko'rinishida, kamida 5 qoida) yozing.",
         "diagram: agar-unda qoidalar zanjiri (qaror daraxti)"),
        (3, "Maktab boshqaruv tizimi loyihasi", 2,
         "O'z maktabingiz uchun elektron kundalik/boshqaruv tizimida bo'lishi kerak bo'lgan 6 ta asosiy funksiyani "
         "(masalan baholar, davomat, jadval) ro'yxatlang va har biri kimga foydali ekanini yozing.",
         "diagram: tizim foydalanuvchilari (o'quvchi/o'qituvchi/ota-ona) va funksiyalar sxemasi"),
        (4, "Tanib olish tizimlari kundalik hayotda", 3,
         "Yuzni, ovozni yoki barmoq izini tanish tizimlaridan foydalanadigan kamida 4 ta ilova/qurilmani toping, "
         "ularning afzallik va xavflarini yozing.",
         "diagram: tanib olish jarayoni (kirish -> tahlil -> qaror) oqimi"),
        (5, "Nazorat va kuzatuv tizimi etikasi", 4,
         "Jamoat joylaridagi video kuzatuv tizimlarining foyda va zararlarini (xavfsizlik vs shaxsiy hayot) taqqoslovchi "
         "jadval tuzing va o'z fikringizni asoslab yozing.",
         "diagram: foyda va zarar tomonlarini ko'rsatuvchi ikki ustunli taqqoslash"),
    ],
    7: [
        (1, "Tizim hayot davri bosqichlari", 0,
         "Tizimning hayot davri bosqichlarini (tahlil, loyihalash, ishlab chiqish, joriy qilish, baholash) ketma-ket "
         "sxema qilib chizing va har biriga 1 jumlali izoh yozing.", None),
        (2, "Muammoni tahlil qilish intervyusi", 1,
         "Maktabingizdagi biror muammoni (masalan kutubxona kitob berish jarayoni) tanlang va uni yaxshilash uchun "
         "5 ta intervyu savoli tuzing.",
         "diagram: muammo -> savollar -> yechim yo'nalishi sxemasi"),
        (3, "Texnik-iqtisodiy asoslash qisqa hisoboti", 2,
         "Tanlagan muammoingiz uchun qisqa texnik-iqtisodiy asoslash (nima uchun, qancha vaqt, taxminiy xarajat) "
         "hisobotini yozing.",
         "diagram: muammo-yechim-natija uch bosqichli sxema"),
        (4, "Sinov rejasi tuzish", 3,
         "O'zingiz loyihalashtirgan (yoki xayoliy) dastur uchun 5 ta sinov holatini (test case) yozing: nima "
         "kiritiladi va nima kutiladi.",
         "diagram: kirish -> jarayon -> kutilgan natija jadvali"),
        (5, "Baholash so'rovnomasi", 4,
         "Yangi tizim ishga tushirilgandan keyin foydalanuvchilardan fikr olish uchun 6 ta savoldan iborat "
         "baholash so'rovnomasi tuzing.",
         "diagram: baholash jarayonining aylanma (feedback loop) sxemasi"),
    ],
    8: [
        (1, "Kompyuter xonasi xavfsizlik auditi", 0,
         "Maktabingiz (yoki uyingiz) kompyuter xonasidagi kabellar, elektr rozetkalari va jihozlar joylashuvini "
         "tekshirib, kamida 5 ta xavfsizlik tavsiyasini yozing.", None),
        (2, "Shaxsiy ma'lumotlarni himoya qilish qo'llanmasi", 1,
         "Ijtimoiy tarmoqlarda shaxsiy ma'lumotni oshkor qilmaslik bo'yicha 8 bandli qo'llanma (masalan telefon "
         "raqami, manzil, joylashuvni ulashmaslik) tuzing.",
         "diagram: 'ulashish mumkin/mumkin emas' ma'lumotlar ro'yxati sxemasi"),
        (3, "Parol xavfsizligi tekshiruvi", 2,
         "Kuchli va zaif parolga misollar yozing (haqiqiy parolingizni YOZMANG), kuchli parol yaratish qoidalarini "
         "(uzunlik, belgilar, takrorlanmaslik) ro'yxatlang.",
         "diagram: kuchli va zaif parol xususiyatlarini solishtiruvchi jadval"),
        (4, "Elektr xavfsizligi cheklisti", 3,
         "Kompyuter va elektr jihozlaridan foydalanishda xavfsizlik qoidalaridan 10 bandli tekshiruv ro'yxati "
         "(cheklist) tuzing.",
         "diagram: xavfsizlik cheklisti — belgilash katakchalari bilan"),
        (5, "Zararli dastur (malware) himoyasi rejasi", 4,
         "Kompyuteringizni viruslar va zararli dasturlardan himoya qilish uchun 6 qadamli reja tuzing (antivirus, "
         "yangilanishlar, shubhali havolalarga bosmaslik va h.k.).",
         "diagram: himoya qatlamlari (antivirus, fayervol, ehtiyotkorlik) piramidasi"),
    ],
    9: [
        (1, "Auditoriya profili", 0,
         "O'zingiz tayyorlamoqchi bo'lgan taqdimot uchun maqsadli auditoriyaning yoshi, qiziqishlari va bilim "
         "darajasini tavsiflovchi qisqa profil yozing.", None),
        (2, "Auditoriya tahlil so'rovnomasi", 1,
         "Auditoriyangiz haqida ma'lumot to'plash uchun 6 ta savoldan iborat so'rovnoma tuzing (yosh, qiziqish, "
         "avvalgi bilim darajasi haqida).",
         "diagram: so'rovnoma -> tahlil -> taqdimotga moslashtirish oqimi"),
        (3, "Mualliflik huquqi holatlari tahlili", 2,
         "3 ta stsenariy yozing: birida mualliflik huquqi buzilgan, birida to'g'ri iqtibos keltirilgan, birida "
         "ochiq litsenziyadan foydalanilgan — har birini izohlang.",
         "diagram: 'ruxsat etilgan' va 'taqiqlangan' foydalanish holatlari jadvali"),
        (4, "Auditoriyaga moslashtirilgan 2 versiya", 3,
         "Bitta mavzuni (masalan 'internetdan xavfsiz foydalanish') ikki xil auditoriya uchun — kichik yoshdagi "
         "bolalar va kattalar uchun — ikki xil uslubda qisqa tavsiflang.",
         "diagram: bitta mavzu -> ikki auditoriya -> ikki uslub sxemasi"),
        (5, "Tarmoq xavfsizligi qoidalari posteri", 4,
         "Maktab tarmog'idan foydalanish qoidalari bo'yicha auditoriyaga (o'quvchilarga) mo'ljallangan rangli "
         "poster matnini tuzing (5-6 qoida).",
         "diagram: tarmoq xavfsizligi qoidalari posterining maketi"),
    ],
    10: [
        (1, "Email odob-axloqi qo'llanmasi", 0,
         "Rasmiy elektron xat yozish qoidalaridan (mavzu qatori, salomlashuv, imzo) 6 bandli qo'llanma tuzing va "
         "namunaviy xat yozing.", None),
        (2, "Spamni aniqlash belgilari", 1,
         "Spam (keraksiz/firibgar) xabarlarni aniqlashga yordam beradigan 8 ta belgini ro'yxatlang (masalan "
         "shubhali havola, imlo xatolari, shoshiltirish).",
         "diagram: ishonchli va spam xabarni solishtiruvchi ikki ustunli jadval"),
        (3, "Email guruhi tashkil etish rejasi", 2,
         "Sinf uchun email guruhi (yoki messenjer guruhi) tashkil etish rejasini tuzing: kim a'zo bo'ladi, qanday "
         "qoidalar bo'ladi, nima uchun kerak.",
         "diagram: guruh tuzilishi (admin, a'zolar) sxemasi"),
        (4, "cc va bcc dan foydalanish stsenariylari", 3,
         "3 ta stsenariy yozing: qachon oddiy qabul qiluvchi, qachon cc, qachon bcc dan foydalanish kerakligini "
         "misollar bilan tushuntiring.",
         "diagram: To/Cc/Bcc maydonlarining farqini ko'rsatuvchi sxema"),
        (5, "Internetning afzallik va kamchiliklari xaritasi", 4,
         "Internetdan foydalanishning kamida 5 ta afzalligi va 5 ta kamchiligini aqliy xarita (mind map) "
         "ko'rinishida tuzing.",
         "diagram: 'Internet' markazida, atrofida afzallik/kamchilik shoxlari"),
    ],
    11: [
        (1, "Fayl kengaytmalari lug'ati", 0,
         "css, csv, gif, htm, jpg, pdf, png, rtf, txt, zip kengaytmalarining har biri qaysi turdagi fayl uchun "
         "ishlatilishini jadvalga yozing.", None),
        (2, "Papka ierarxiyasi loyihasi", 1,
         "O'z maktab fanlaringiz uchun mantiqiy papka/katalog tuzilmasini (masalan Fan -> Chorak -> Mavzu) "
         "chizing va nima uchun shunday tuzilganini izohlang.",
         "diagram: papka daraxti (papka ichida pastki papkalar)"),
        (3, "Fayl nomlash qoidalari", 2,
         "Yaxshi fayl nomlash qoidalaridan (sana, versiya, mazmunni aks ettirish) 6 bandli ro'yxat tuzing va "
         "3 ta yomon nomni to'g'ri nomga o'zgartirib ko'rsating.",
         "diagram: 'yomon nom' va 'yaxshi nom' misollarini solishtiruvchi jadval"),
        (4, "Fayl formatlari va eksport", 3,
         "Bitta hujjatni qanday formatlarda saqlash mumkinligini (.docx, .pdf, .txt, .rtf) va har biri qachon "
         "kerak bo'lishini jadvalga yozing.",
         "diagram: bitta hujjat -> turli formatlarga eksport sxemasi"),
        (5, "Fayl siqish (compression) tajribasi", 4,
         "Fayllarni ZIP formatida siqish nima uchun kerakligini, qanday holatlarda foydali (yuborish, saqlash) "
         "ekanini misollar bilan yozing.",
         "diagram: siqilmagan va siqilgan fayl hajmini solishtiruvchi ustunli diagramma"),
    ],
    12: [
        (1, "Tasvir tahrirlash asoslari ro'yxati", 0,
         "Tasvirni kesish (crop), o'lchamini o'zgartirish (resize) va aylantirish (rotate) amallarining har biri "
         "qachon kerak bo'lishini misollar bilan tushuntiring.", None),
        (2, "Tasvir nisbatlari (aspect ratio) tajribasi", 1,
         "Bitta tasvirni nisbatini saqlagan va saqlamagan holda kattalashtirish natijasi qanday farq qilishini "
         "chizib (yoki tavsiflab) ko'rsating.",
         "diagram: to'g'ri va noto'g'ri nisbatda cho'zilgan tasvir taqqoslash sxemasi"),
        (3, "Rang, yorqinlik va kontrast sozlamalari", 2,
         "Rang chuqurligi, yorqinlik va kontrast tushunchalarini har biriga oddiy misol (masalan tungi va kunduzgi "
         "surat) bilan tushuntirib yozing.",
         "diagram: past/yuqori kontrast va yorqinlikni solishtiruvchi shkalalar"),
        (4, "Fayl hajmini kamaytirish stsenariysi", 3,
         "Veb-saytga yuklash uchun katta hajmli suratni qanday qilib sifatini unchalik yo'qotmasdan kichraytirish "
         "mumkinligi bo'yicha qadamlar rejasini yozing.",
         "diagram: asl va siqilgan tasvir hajmini solishtiruvchi jadval"),
        (5, "Tasvirni auditoriyaga moslashtirish", 4,
         "Bitta tasvirni ikki xil maqsad uchun (bolalar jurnali va ilmiy maqola) qanday tahrirlashni tavsiya "
         "qilasiz — rang, kontrast, kesish jihatidan farqlarni yozing.",
         "diagram: bitta asl tasvir -> ikki tahrirlangan versiya sxemasi"),
    ],
    13: [
        (1, "Hujjat maketi tanlash", 0,
         "3 xil hujjat turi (reklama varag'i, rasmiy xat, hisobot) uchun eng mos sahifa yo'nalishini (albom/kitob) "
         "va sababini yozing.", None),
        (2, "Loyihalash savollari jadvali", 1,
         "13.01-jadval uslubida, o'zingiz tanlagan 3 ta hujjat turi (masalan afisha, taklifnoma, hisobot) uchun "
         "tasvirlar soni, shrift va bo'sh joy tavsiyalarini jadvalga yozing.",
         "diagram: hujjat turlari va ularning maket xususiyatlari jadvali"),
        (3, "Ustunlar bilan maket loyihasi", 2,
         "Gazeta uslubidagi ikki-ustunli maketning eskizini (matn qayerda, tasvir qayerda) qog'ozda chizing.",
         "diagram: ikki ustunli gazeta maketining eskizi"),
        (4, "Ustlavha va taglavha rejasi", 3,
         "Rasmiy hisobot uchun ustlavha (sarlavha) va taglavha (sahifa raqami, sana) qismida nima bo'lishi "
         "kerakligini yozing.",
         "diagram: sahifa maketi — ustlavha, asosiy matn, taglavha zonalari"),
        (5, "Auditoriyaga mos rang va shrift tanlovi", 4,
         "3 xil auditoriya (bolalar, biznes hamkorlar, ilmiy jamoat) uchun mos rang palitrasi va shrift uslubini "
         "tanlab, sababini yozing.",
         "diagram: auditoriya -> rang palitra -> shrift uslubi jadvali"),
    ],
    14: [
        (1, "Korporativ stil elementlari", 0,
         "O'zingiz yaxshi bilgan bir brend (masalan maktabingiz yoki mashhur kompaniya)ning logotipi, ranglari va "
         "shriftini tasvirlab, ular qanday 'izchil stil' hosil qilishini yozing.", None),
        (2, "O'z 'brendim' stil qo'llanmasi", 1,
         "O'zingiz uchun (yoki xayoliy klub uchun) 3 ta asosiy rang, 1 shrift va logotip g'oyasidan iborat kichik "
         "stil qo'llanmasi (style guide) tuzing.",
         "diagram: rang palitrasi + shrift namunasi + logotip eskizi"),
        (3, "Izchil vs izchil bo'lmagan hujjatlar", 2,
         "Bir xil kompaniyaning ikki hujjatini xayolan tasvirlang: biri izchil stilda, biri turlicha ranglar/"
         "shriftlar bilan — farqni va uning ta'sirini yozing.",
         "diagram: izchil va izchil bo'lmagan hujjatni solishtiruvchi sxema"),
        (4, "Shablon (template) yaratish rejasi", 3,
         "Maktab uchun xat blankasi shablonida bo'lishi kerak bo'lgan elementlarni (logotip, rang, shrift, "
         "joylashuv) ro'yxatlang.",
         "diagram: xat blankasi shablonining maketi"),
        (5, "Brend tanish tajribasi", 4,
         "5 ta mashhur brendning faqat rangi yoki logotip shakli orqali tanib olish mumkinligini tekshiring — "
         "qaysi elementlar eng ko'p yodda qolishini yozing.",
         "diagram: brend -> asosiy rang -> tanib olish qulayligi jadvali"),
    ],
    15: [
        (1, "Xato turlari ro'yxati", 0,
         "Hujjatda uchraydigan xato turlarini (imlo, punktuatsiya, mantiqiy, ma'lumot xatosi) misollar bilan "
         "ro'yxatlang.", None),
        (2, "Tasdiqlash qoidalari loyihasi", 1,
         "Onlayn ro'yxatdan o'tish shaklida telefon raqami, email va yosh maydonlari uchun tasdiqlash (validation) "
         "qoidalarini yozing (masalan yosh 0-120 oralig'ida bo'lishi kerak).",
         "diagram: forma maydoni -> tasdiqlash qoidasi -> xato xabari jadvali"),
        (3, "Matnni tekshirish mashqi", 2,
         "O'zingiz yozgan qisqa matnni (5-6 jumla) tayyorlang, so'ng imlo va grammatika xatolarini qo'lda "
         "belgilab, to'g'ri variantini yozing.",
         "diagram: asl matn va tuzatilgan matnni solishtiruvchi ikki ustun"),
        (4, "Autocorrect xatolari kolleksiyasi", 3,
         "Avtomatik tuzatish (autocorrect) funksiyasi noto'g'ri ishlagan holatlarga 4 ta misol toping yoki "
         "o'ylab toping va nima uchun xato yuz berganini tushuntiring.",
         "diagram: yozilgan so'z -> autocorrect natijasi -> to'g'ri so'z jadvali"),
        (5, "Ma'lumotlar tasdiqlash test rejasi", 4,
         "Elektron jadvaldagi 'yosh' ustuni uchun 5 ta test qiymati (ba'zilari to'g'ri, ba'zilari noto'g'ri) "
         "yozing va har biri qabul qilinishi yoki rad etilishini ko'rsating.",
         "diagram: test qiymatlari va ular natijasi jadvali (o'tdi/o'tmadi)"),
    ],
    16: [
        (1, "Diagramma turini tanlash", 0,
         "Ustunli, doiraviy (pirog) va chiziqli diagrammalarning har biri qanday ma'lumot uchun eng mos "
         "ekanini 1 tadan misol bilan tushuntiring.", None),
        (2, "O'z ma'lumotlarim bilan diagramma rejasi", 1,
         "Sinfdoshlaringiz orasida kichik so'rov o'tkazing (masalan sevimli fan), natijalarni jadvalga yozing va "
         "qanday diagramma bilan ko'rsatish maqsadga muvofiqligini asoslang.",
         "diagram: so'rov natijalari ustunli diagrammasi"),
        (3, "Diagramma elementlari sxemasi", 2,
         "Sarlavha, o'qlar, yorliqlar va afsona (legend) — diagrammaning har bir qismi nima uchun kerakligini "
         "misol bilan tushuntiring.",
         "diagram: belgilangan qismlari (sarlavha, o'qlar, afsona) bilan namuna diagramma"),
        (4, "Ikkilamchi o'q qo'shish stsenariysi", 3,
         "Har xil o'lchamdagi ikki ma'lumot to'plamini (masalan harorat va yog'ingarchilik) bitta grafikda "
         "ko'rsatish uchun ikkinchi o'q nega kerakligini tushuntiring.",
         "diagram: ikkita o'qli (chap va o'ng) grafik sxemasi"),
        (5, "Trend (moyillik) tahlili", 4,
         "Xayoliy 6 oylik ma'lumot (masalan oylik xarajat) jadvalini tuzing va uning ko'tarilish/tushish "
         "moyilligini grafik ko'rinishida tasvirlab, xulosa yozing.",
         "diagram: 6 oylik chiziqli trend grafigi"),
    ],
    17: [
        (1, "Sahifa maketi elementlari", 0,
         "Hoshiya, kolontitul (ustlavha/ostlavha) va sahifa yo'nalishi (portret/albom) tushunchalarini o'z "
         "so'zingiz bilan misollar bilan tushuntiring.", None),
        (2, "Jadval loyihalash", 1,
         "O'z dars jadvalingizni (haftalik) professional ko'rinishdagi jadval sifatida loyihalashtiring — "
         "ustunlar, qatorlar va sarlavhalarni rejalashtiring.",
         "diagram: haftalik dars jadvali maketi"),
        (3, "Pochta orqali birlashtirish (mail merge) rejasi", 2,
         "Sinfdoshlaringizga shaxsiylashtirilgan taklifnoma yuborish uchun kerak bo'ladigan ma'lumotlar "
         "manbasi (ism, sana, joy) va shablon matnini rejalashtiring.",
         "diagram: ma'lumotlar manbasi + shablon -> shaxsiylashtirilgan hujjatlar oqimi"),
        (4, "Ustunli hujjat maketi", 3,
         "Gazeta uslubidagi 2 ustunli maqola maketini eskiz qilib chizing, sarlavha va rasm joyini belgilang.",
         "diagram: 2 ustunli maqola maketi eskizi"),
        (5, "Muqova maydoni bilan kitobcha loyihasi", 4,
         "Qattiq muqovaga tikiladigan kichik kitobcha (masalan sinf jurnali) uchun muqova maydoni va "
         "hoshiyalarni hisobga olgan holda sahifa o'lchamlarini rejalashtiring.",
         "diagram: muqova maydoni bilan sahifa maketi sxemasi"),
    ],
    18: [
        (1, "Oddiy faylli vs relyatsion ma'lumotlar bazasi", 0,
         "Oddiy faylli va relyatsion ma'lumotlar bazasi orasidagi farqni o'z so'zingiz bilan, kiyim javoni "
         "misolidan foydalanmasdan, boshqa bir misol bilan tushuntiring.", None),
        (2, "O'z ma'lumotlar bazam jadvali", 1,
         "Sinf kutubxonasi uchun oddiy ma'lumotlar bazasi jadvalini loyihalashtiring: maydonlar (kitob nomi, "
         "muallif, holat) va 5 ta namunaviy yozuv kiriting.",
         "diagram: kutubxona jadvali sxemasi (ustunlar va qatorlar)"),
        (3, "Ma'lumotlarni saralash va qidirish stsenariysi", 2,
         "18-mashqdagi kutubxona jadvalidan foydalanib, 'muallif bo'yicha saralash' va 'faqat band kitoblarni "
         "qidirish' vazifalarini qanday bajarish mumkinligini yozing.",
         "diagram: saralangan va filtrlangan jadval ko'rinishlari"),
        (4, "GIGO (kirishda axlat, chiqishda axlat) misoli", 3,
         "Noto'g'ri kiritilgan ma'lumot (masalan yosh o'rniga ism yozilgan) qanday noto'g'ri hisobot yoki xato "
         "natijaga olib kelishini misol bilan tushuntiring.",
         "diagram: noto'g'ri kirish -> noto'g'ri chiqish oqim sxemasi"),
        (5, "Hisobot loyihasi", 4,
         "Kutubxona jadvalingizdan 'eng ko'p o'qilgan 5 kitob' hisobotini qanday tuzish mumkinligini "
         "rejalashtiring — qaysi maydonlar kerak, qanday tartiblanadi.",
         "diagram: jadval -> filtr/saralash -> hisobot oqimi"),
    ],
    19: [
        (1, "Taqdimot rejasi", 0,
         "O'zingiz tanlagan mavzu bo'yicha 5 slaydlik taqdimot rejasini (har slaydda nima bo'lishini) qisqacha "
         "yozing.", None),
        (2, "Master-slayd elementlari", 1,
         "Master-slaydda belgilanadigan doimiy elementlarni (shrift, rang, logotip, sahifa raqami) ro'yxatlang "
         "va nima uchun bu elementlar har bir slaydda avtomatik takrorlanishi qulayligini tushuntiring.",
         "diagram: master-slayd va undan foydalanuvchi slaydlar sxemasi"),
        (3, "Obyektlarni joylashtirish maketi", 2,
         "Bitta slayd uchun matn, tasvir va sarlavha qayerda joylashishini ko'rsatuvchi eskiz chizing.",
         "diagram: slayd maketi eskizi (sarlavha, matn, tasvir zonalari)"),
        (4, "Auditoriyaga mos taqdimot uslubi", 3,
         "Bitta mavzuni ikki xil auditoriya (yosh bolalar va katta yoshli mutaxassislar) uchun ikki xil "
         "taqdimot uslubida (rang, shrift, matn hajmi) qanday moslashtirish kerakligini yozing.",
         "diagram: ikki auditoriya uchun ikki xil slayd uslubi taqqoslash"),
        (5, "Taqdimotni sinash cheklisti", 4,
         "Taqdimotni ko'rsatishdan oldin tekshirish uchun 8 bandli cheklist tuzing (matn hajmi, shrift o'lchami, "
         "rang kontrasti, vaqt va h.k.).",
         "diagram: taqdimotni sinash cheklisti (belgilash katakchalari bilan)"),
    ],
    20: [
        (1, "Ma'lumot modeli g'oyasi", 0,
         "Oddiy real hayotiy muammo (masalan uy byudjeti) uchun qanday ma'lumotlar kerak bo'lishini va ularni "
         "qanday jadvalga joylashtirish mumkinligini yozing.", None),
        (2, "Formulalar rejasi", 1,
         "Uy byudjeti jadvali uchun kerak bo'ladigan formulalarni (jami xarajat, qolgan mablag', foiz) so'z "
         "bilan tavsiflab yozing (formula sintaksisi shart emas).",
         "diagram: jadval ustunlari va ular orasidagi formula bog'lanishlari"),
        (3, "Sinov rejasi (test qiymatlari)", 2,
         "20-mashqdagi model uchun 4 ta turli xil kirish qiymati (masalan turli daromad darajalari) bilan "
         "sinab, natijalar to'g'ri chiqishini tekshiring.",
         "diagram: kirish qiymatlari va kutilgan natijalar jadvali"),
        (4, "Ma'lumotlarni saralash va filtrlash stsenariysi", 3,
         "Katta jadvaldan (masalan sinfdagi barcha o'quvchilarning baholari) 'eng yuqori 5 ta natija' va "
         "'muvaffaqiyatsiz natijalar' ni qanday ajratib olish mumkinligini yozing.",
         "diagram: asl jadval -> filtrlangan natija jadvali"),
        (5, "Katta jadvalni ko'rish qulayligi", 4,
         "Katta hajmli jadvalda sarlavha qatorini 'muzlatish' (freeze) va ustunlarni yashirish nima uchun "
         "foydali ekanini tushuntiring va o'z misolingizni yozing.",
         "diagram: muzlatilgan sarlavha bilan katta jadval ko'rinishi"),
    ],
    21: [
        (1, "Veb-sahifa uch qatlami", 0,
         "Kontent, taqdimot (uslub) va funksional qatlamlarning har biri nima uchun javob berishini o'z "
         "so'zingiz bilan, oddiy veb-sahifa misolida tushuntiring.", None),
        (2, "Sodda veb-sahifa maketi", 1,
         "O'zingiz haqingizda (yoki sinfingiz haqida) sodda bir sahifalik veb-sayt uchun tarkib rejasini "
         "(sarlavha, menyu, asosiy matn, rasm, footer) eskiz qilib chizing.",
         "diagram: veb-sahifa maketi eskizi (header, menyu, kontent, footer)"),
        (3, "Navigatsiya sxemasi", 2,
         "3-4 sahifadan iborat (Bosh sahifa, Men haqimda, Aloqa) kichik veb-sayt uchun sahifalar orasidagi "
         "havolalar (navigatsiya) sxemasini chizing.",
         "diagram: sahifalar va ular orasidagi havolalar grafigi (site map)"),
        (4, "URL va domen tushunchalari", 3,
         "URL manzil va IP manzil orasidagi farqni, DNS qanday ishlashini o'z so'zingiz bilan (texnik "
         "atamalarni sodda tilga o'girib) tushuntiring.",
         "diagram: brauzer -> DNS so'rovi -> IP manzil -> sayt jarayoni"),
        (5, "Veb-saytni sinovdan o'tkazish cheklisti", 4,
         "Tayyor veb-saytni chop etishdan oldin tekshirish uchun 8 bandli cheklist tuzing (havolalar ishlaydimi, "
         "turli ekranlarda ko'rinishi, imlo xatolari va h.k.).",
         "diagram: veb-sayt sinov cheklisti (belgilash katakchalari bilan)"),
    ],
}

def _table_exists(c, name):
    return c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    # ------------------------------------------------------------------
    # 1) Mavzular (mundarija) jadvali
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_curriculum_topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_key TEXT NOT NULL DEFAULT 'informatika',
        grade_label TEXT NOT NULL,             -- '5-sinf', '9-sinf', '10-11-sinf' ...
        applies_to_org_types TEXT NOT NULL,     -- 'maktab' yoki 'maktab,texnikum' ...
        chapter_no INTEGER NOT NULL,
        title TEXT NOT NULL,
        summary TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(subject_key, grade_label, chapter_no)
    )""")

    # ------------------------------------------------------------------
    # 2) Amaliy topshiriqlar jadvali
    # ------------------------------------------------------------------
    c.execute("""CREATE TABLE IF NOT EXISTS edu_curriculum_practicals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER NOT NULL,
        order_no INTEGER NOT NULL,       -- 1..5
        title TEXT NOT NULL,
        instructions TEXT NOT NULL,
        image_hint TEXT DEFAULT '',      -- Pro uchun rasm/diagramma tavsiyasi (matn ko'rinishida)
        is_pro_only INTEGER DEFAULT 0,   -- order_no=1 -> 0, 2-5 -> 1
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(topic_id, order_no),
        FOREIGN KEY(topic_id) REFERENCES edu_curriculum_topics(id)
    )""")

    if not _table_exists(c, "edu_curriculum_topics"):
        conn.close()
        return

    # ==================================================================
    # SEED: barcha sinflar (5,6,7,8,9,10-11) uchun mavzular va amaliylar
    # ==================================================================
    # 10-11-sinf 19 bobli bo'lgani uchun ikki qismga (PART1: 1-10, PART2: 11-19)
    # bo'lib yozilgan — shu yerda birlashtiramiz.
    practicals_1011_full = dict(CHAPTER_PRACTICALS_1011_PART1)
    practicals_1011_full.update(CHAPTER_PRACTICALS_1011_PART2)
    topics_1011_full = list(GRADE1011_TOPICS) + list(GRADE1011_TOPICS_PART2)

    grades_final = [
        ("5-sinf", "maktab", GRADE5_TOPICS, CHAPTER_PRACTICALS_5),
        ("6-sinf", "maktab", GRADE6_TOPICS, CHAPTER_PRACTICALS_6),
        ("7-sinf", "maktab", GRADE7_TOPICS, CHAPTER_PRACTICALS_7),
        ("8-sinf", "maktab", GRADE8_TOPICS, CHAPTER_PRACTICALS_8),
        ("9-sinf", "maktab", GRADE9_TOPICS, CHAPTER_PRACTICALS_9),
        ("10-11-sinf", "maktab,texnikum", topics_1011_full, practicals_1011_full),
    ]

    for grade_label, org_types, topics_list, practicals_dict in grades_final:
        topic_ids = {}
        for chapter_no, title, summary in topics_list:
            c.execute("""INSERT OR IGNORE INTO edu_curriculum_topics
                (subject_key, grade_label, applies_to_org_types, chapter_no, title, summary, sort_order)
                VALUES ('informatika',?,?,?,?,?,?)""",
                (grade_label, org_types, chapter_no, title, summary, chapter_no))
            row = c.execute(
                "SELECT id FROM edu_curriculum_topics WHERE subject_key='informatika' AND grade_label=? AND chapter_no=?",
                (grade_label, chapter_no)
            ).fetchone()
            topic_ids[chapter_no] = row[0]

        for chapter_no, practicals in practicals_dict.items():
            topic_id = topic_ids.get(chapter_no)
            if not topic_id:
                continue
            for order_no, title, is_pro, instructions, image_hint in practicals:
                c.execute("""INSERT OR IGNORE INTO edu_curriculum_practicals
                    (topic_id, order_no, title, instructions, image_hint, is_pro_only)
                    VALUES (?,?,?,?,?,?)""",
                    (topic_id, order_no, title, instructions, image_hint or "", 1 if is_pro else 0))

    # DATA TOZALASH: is_pro_only har doim qat'iy 0/1 bo'lishini ta'minlaymiz
    # (eski versiyalarda order_no dan olingan xom qiymat yozilgan bo'lishi mumkin edi).
    c.execute("UPDATE edu_curriculum_practicals SET is_pro_only=1 WHERE is_pro_only<>0")

    conn.commit()
    conn.close()
    print("✅ v40 O'quv dasturi (5,6,7,8,9,10-11-sinf — 62 mavzu, 310 ta amaliy) muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
