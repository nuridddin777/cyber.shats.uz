"""
SHATS CYBER EDU — MIGRATE v41: 9-sinf — 2-21-boblar uchun amaliylar
================================================================================
v40 migratsiyasida faqat 1-bob uchun 5 ta amaliy (pilot namuna) qo'shilgan
edi. Ushbu migratsiya qolgan 20 bobning (2-21) har biriga xuddi shu andozada
5 tadan amaliy topshiriq qo'shadi:

  - order_no=1  -> Standart tarifda ham ko'rinadi (is_pro_only=0)
  - order_no=2-5 -> faqat Pro tarifda ko'rinadi (is_pro_only=1), har biriga
                    rasm/diagramma tavsiyasi biriktirilgan

DIQQAT: barcha topshiriqlar original — darslik matnidan SO'ZMA-SO'Z
ko'chirilmagan, faqat bobning mavzusi (sarlavhasi va umumiy yo'nalishi)
asosida mustaqil ishlab chiqilgan amaliy mashqlar.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")

# chapter_no -> [(order_no, title, is_pro, instructions, image_hint), ...]
CHAPTER_PRACTICALS = {
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


def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    exists = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='edu_curriculum_topics'"
    ).fetchone()
    if not exists:
        conn.close()
        return  # v40 hali ishga tushmagan

    for chapter_no, practicals in CHAPTER_PRACTICALS.items():
        topic = c.execute(
            "SELECT id FROM edu_curriculum_topics WHERE subject_key='informatika' AND grade_label='9-sinf' AND chapter_no=?",
            (chapter_no,)
        ).fetchone()
        if not topic:
            continue  # v40 mos bobni yaratmagan bo'lsa, o'tkazib yuboramiz
        topic_id = topic[0]
        for order_no, title, is_pro, instructions, image_hint in practicals:
            c.execute("""INSERT OR IGNORE INTO edu_curriculum_practicals
                (topic_id, order_no, title, instructions, image_hint, is_pro_only)
                VALUES (?,?,?,?,?,?)""",
                (topic_id, order_no, title, instructions, image_hint or "", 1 if is_pro else 0))

    # DATA TOZALASH: oldingi (xatolik bilan) ishga tushirilgan versiyalarda
    # is_pro_only ustuniga 0/1 o'rniga order_no dan olingan xom qiymat
    # (0,1,2,3,4) yozilgan bo'lishi mumkin edi — buni qat'iy 0/1 ga keltiramiz.
    c.execute("UPDATE edu_curriculum_practicals SET is_pro_only=1 WHERE is_pro_only<>0")

    conn.commit()
    conn.close()
    print("✅ v41 9-sinf — 2-21-boblar uchun amaliylar (jami 100 ta) muvaffaqiyatli qo'shildi!")
if __name__ == "__main__":
    migrate()
