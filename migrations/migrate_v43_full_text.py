"""
SHATS CYBER EDU — MIGRATE v43: Mavzular uchun to'liq original matn
================================================================================
Har bir mavzuga (barcha 62 ta, 5-10/11-sinf) 300-500 so'zlik TO'LIQ, original
tushuntirish matni qo'shiladi — bu matn Claude tomonidan mavzu asosida
mustaqil yozilgan (darslik matnidan SO'ZMA-SO'Z KO'CHIRILMAGAN — mualliflik
huquqi qoidalariga ko'ra bu qat'iy taqiqlangan). Maqsad — o'quvchi shu matnni
o'qib, mavzuni chuqurroq tushunib olishi, faqat qisqa sarlavha/tavsif emas.
"""
import sqlite3
import os

DB = os.path.join(os.path.dirname(__file__), "cyber_shats.db")


def _table_exists(c, name):
    return c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def _column_exists(c, table, col):
    c.execute(f"PRAGMA table_info({table})")
    return col in [r[1] for r in c.fetchall()]


# (grade_label, chapter_no) -> full_text
FULL_TEXTS = {

("5-sinf", 1): """Matnli hujjat bilan ishlashni boshlash — bu kompyuterda birinchi qadamlaringizdan biri. Matn muharriri (masalan Microsoft Word) — bu ekranda harf, so'z va jumlalar yozish, ularni tartibga solish va chiroyli ko'rinishga keltirish uchun mo'ljallangan dastur. Avvalo, klaviatura bilan tanishib olish kerak: harflar va raqamlar o'rtadagi asosiy qismda, Enter tugmasi yangi qatorga o'tish uchun, Space (bo'sh joy) so'zlar orasiga bo'shliq qo'yish uchun, Backspace esa oldingi belgini o'chirish uchun ishlatiladi.

Sichqoncha (mouse) yordamida matn ichida istalgan joyga "bosib" o'sha yerga kursor (yozish nuqtasi) qo'yish mumkin. Matnni "belgilash" (select qilish) — bu bironta so'z yoki butun jumlani sichqoncha bilan sudrab, uni ajratib olish degani; belgilangan matnni keyin o'chirish, nusxalash yoki formatlash (ko'rinishini o'zgartirish) mumkin.

Formatlash — bu matnning tashqi ko'rinishini o'zgartirish: shriftni (harf turini) tanlash, o'lchamini kattalashtirish yoki kichraytirish, qalin (bold), qiyshiq (italic) yoki tagiga chiziq (underline) qilib bezash. Rang tanlash orqali matnni yanada jonli qilish mumkin. Bu ko'nikmalar keyinchalik har qanday hisobot, taklifnoma yoki insho yozishda kerak bo'ladi.

Hujjatni saqlash ham muhim ko'nikma — agar hujjatni saqlamasangiz, kompyuter o'chirilganda barcha ishingiz yo'qolib qolishi mumkin. Shuning uchun "Saqlash" (Save) tugmasini vaqti-vaqti bilan bosib turish odatiy holga aylanishi kerak. Hujjatga nom berish ham muhim — nom hujjat mazmunini aks ettirishi kerak, masalan "5-sinf_insho" kabi, shunda uni keyin topish osonroq bo'ladi.

Xavfsizlik qoidalarini ham unutmaslik kerak: kompyuter yonida ovqat yoki ichimlik ushlamaslik, kabellarga tortmaslik, ko'zni charchatmaslik uchun vaqti-vaqti bilan ekrandan uzoqroqqa qarab dam olish tavsiya etiladi. Bu mavzuda o'rgangan barcha ko'nikmalar — matn kiritish, formatlash va saqlash — informatika faniga kirish uchun mustahkam poydevor bo'lib xizmat qiladi.""",

("5-sinf", 2): """Tasvirlar bilan ishlashni boshlash mavzusida siz Rasm (Paint) dasturi yordamida o'z chizmalaringizni yaratishni o'rganasiz. Bu dastur juda sodda va tushunarli interfeysga ega bo'lib, har qanday yoshdagi o'quvchi tezda o'zlashtirib oladi.

Dasturning asosiy uskunalari orasida: qalam (erkin chizish uchun), chiziq (to'g'ri chiziqlar tortish), turli shakllar (to'rtburchak, doira, uchburchak) va to'ldirish (bucket) uskunasi bor. To'ldirish uskunasi yordamida yopiq shaklning ichini bir zumda rang bilan to'ldirish mumkin — bu vaqtni tejaydi va rasmni tekis rangga bo'yaydi.

Ranglar palitrasi dasturning muhim qismi. Har bir rang alohida "quti" ko'rinishida joylashgan bo'lib, uni tanlab, keyin chizish uskunasini ishlatganda o'sha rang qo'llaniladi. Asosiy va qo'shimcha rang tushunchasi ham bor — chap tugma bilan asosiy, o'ng tugma bilan qo'shimcha rangni tanlash mumkin, bu ayniqsa to'ldirishda foydali.

Shakllardan foydalanib murakkabroq rasmlar yasash mumkin: masalan uy chizish uchun to'rtburchak (devor), uchburchak (tom) va to'rtburchak (deraza/eshik)larni birlashtirish kifoya. Bu — geometrik fikrlashni rivojlantiradi, chunki har bir murakkab shakl aslida oddiy shakllardan tashkil topganini tushunib olasiz.

Xato qilib qo'ysangiz, tashvishlanmang — "Undo" (bekor qilish) tugmasi orqali oxirgi amalni bekor qilish, "Redo" orqali esa uni qaytarish mumkin. Bu — istalgan dasturda foydali bo'lgan universal ko'nikma, xatolardan qo'rqmasdan ijodiy ishlash imkonini beradi.

Rasm chizish nafaqat qiziqarli mashg'ulot, balki ijodiy fikrlashni, mayda motorikani va kompyuterdagi asboblardan foydalanish ko'nikmasini rivojlantiradi. Kelajakda bu ko'nikmalar dizayn, taqdimot tayyorlash va hatto professional grafik dasturlar bilan ishlashda asos bo'lib xizmat qiladi.""",

("5-sinf", 3): """Diagrammalar bilan ishlashni boshlash mavzusi ma'lumotlarni tartibga solish va vizual (ko'zga ko'rinadigan) tarzda tasvirlashga bag'ishlangan. Har kuni atrofimizda son-sanoqsiz ma'lumotlar mavjud — masalan sinfdagi o'quvchilarning sevimli fanlari yoki oilada nechta kishi borligi. Bu ma'lumotlarni tushunarli qilish uchun ularni guruhlash va sanash kerak.

Guruhlash — bu o'xshash narsalarni bir toifaga birlashtirish. Masalan, agar sinfda 25 ta o'quvchi bo'lsa, ularni sevimli rangiga qarab guruhlashimiz mumkin: qizil rangni yoqtiradiganlar bir guruh, ko'k rangni yoqtiradiganlar boshqa guruh. Har bir guruhda nechta kishi borligini sanab, natijani jadvalga yozib qo'yish mumkin.

Sanoq jadvali — bu ma'lumotlarni tartibli tarzda hisoblash usuli. Har safar bir kishi/narsa hisoblanganda, jadvalga bitta belgi (chiziqcha yoki nuqta) qo'yiladi. Barcha hisoblash tugagach, har bir guruhdagi belgilar soni sanaladi — bu son o'sha guruhning "chastotasi" (necha marta uchraganini) ko'rsatadi.

Diagramma — bu sonlarni chiziq yoki shakllar orqali ko'rsatish usuli. Eng oddiy diagramma turi — ustunli diagramma, unda har bir guruh uchun bitta ustun chiziladi, ustunning balandligi shu guruhdagi sonni ifodalaydi. Qancha ustun baland bo'lsa, shuncha ko'p narsa bor degani. Diagrammalar sonlarni matn yoki jadvaldan ko'ra tezroq va oson tushunish imkonini beradi — bir qarashda qaysi guruh eng katta, qaysi eng kichik ekanini ko'rish mumkin.

Bu mavzuda o'rganilgan ko'nikmalar — ma'lumot to'plash, guruhlash, sanash va diagramma orqali tasvirlash — nafaqat informatikada, balki matematika, tabiiy fanlar va hatto kundalik hayotda (masalan oilaviy byudjetni rejalashtirishda) foydali bo'ladi. Bu — "ma'lumotlar bilan fikrlash" deb ataluvchi muhim ko'nikmaning boshlanishi.""",

("5-sinf", 4): """Dasturlashni boshlash mavzusida siz Scratch dasturlash muhiti bilan tanishasiz — bu maxsus ravishda bolalar uchun yaratilgan, rangli bloklardan foydalanib dastur tuzish imkonini beruvchi vosita. Scratch'da harflar bilan kod yozish o'rniga, tayyor buyruq bloklarini sudrab-tashlash orqali dastur yaratiladi, bu esa dasturlashning asosiy g'oyalarini oson va qiziqarli tarzda o'rganish imkonini beradi.

Scratch'ning markazida "sprayt" (sprite) turadi — bu ekrandagi belgi yoki obyekt (masalan mushuk, odam, mashina), unga buyruqlar berib harakatlantirish mumkin. Har bir sprayt ekranning istalgan nuqtasida turishi mumkin, uning joylashuvi X va Y koordinatalari orqali aniqlanadi.

Eng oddiy buyruqlar harakat guruhida joylashgan: "X qadam yurish" spraytni oldinga siljitadi, "Y darajaga burilish" esa spraytning yo'nalishini o'zgartiradi. Masalan, agar spraytga "10 qadam yur" desangiz, u joriy yo'nalishi bo'yicha 10 birlik masofaga siljiydi. Agar keyin "90 darajaga buril" desangiz, u soat strelkasi yo'nalishida to'rtdan bir aylanish qiladi.

Bu oddiy buyruqlarni ketma-ket birlashtirib, murakkabroq harakatlar yaratish mumkin — masalan to'rtburchak shaklida yurish uchun "yur-buril" juftligini 4 marta takrorlash kerak (har safar 90 darajaga burilib). Bu — algoritm tushunchasining eng sodda ko'rinishi: aniq bir natijaga erishish uchun ketma-ket bajariladigan buyruqlar zanjiri.

Xatolar bilan ishlash ham dasturlashning muhim qismi — agar sprayt kutilganidek harakat qilmasa, buyruqlar ketma-ketligini qayta ko'rib chiqish va tuzatish kerak bo'ladi. Bu jarayon "debugging" (xatolarni topish va tuzatish) deb ataladi va har qanday dasturchi uchun kundalik ish hisoblanadi.

Scratch orqali o'rganilgan mantiqiy fikrlash, ketma-ketlik va muammoni bo'laklarga bo'lib yechish ko'nikmalari — kelajakda haqiqiy dasturlash tillarini (Python, JavaScript va h.k.) o'rganishda mustahkam zamin bo'lib xizmat qiladi.""",

("5-sinf", 5): """Qidiruv tizimlarida ishlashni boshlash mavzusi internetdan to'g'ri va xavfsiz foydalanishni o'rgatadi. Internet — bu butun dunyo bo'ylab bog'langan kompyuterlar tarmog'i bo'lib, unda millionlab veb-saytlar mavjud. Veb-brauzer (masalan Google Chrome yoki Mozilla Firefox) — bu shu saytlarni ochish va ko'rish uchun ishlatiladigan dastur.

Qidiruv tizimi (masalan Google) — bu internetdagi millionlab sahifalar orasidan kerakli ma'lumotni topishga yordam beruvchi maxsus xizmat. Qidiruv oynasiga so'z yoki jumla yozib, "Qidirish" tugmasini bossangiz, tizim shu so'zlarga oid barcha saytlarni ro'yxat qilib chiqaradi. Qidiruv so'zlarini to'g'ri tanlash — muhim ko'nikma: qanchalik aniq va o'ziga xos so'z yozilsa, natija shunchalik foydali bo'ladi. Masalan "hayvon" deb yozish o'rniga "Amazon o'rmonidagi noyob hayvonlar" deb yozish aniqroq natija beradi.

Internetdagi har bir sayt bir xil ishonchli emas. Ishonchli sayt — bu to'g'ri, tekshirilgan ma'lumot beruvchi manba (masalan davlat ta'lim saytlari, mashhur ensiklopediyalar). Ishonchsiz sayt esa noto'g'ri ma'lumot berishi, ko'p reklama bilan to'lib-toshgan bo'lishi yoki imlo xatolariga to'la bo'lishi mumkin. Har doim topilgan ma'lumotni kamida ikkita boshqa manba bilan solishtirib ko'rish tavsiya etiladi.

Elektron xavfsizlik ham juda muhim mavzu. Internetda shaxsiy ma'lumotlarni (uy manzili, telefon raqami, parollar) hech kimga, hatto tanish ko'ringan odamga ham bermaslik kerak. Agar biror sayt yoki xabar shubhali tuyulsa (masalan sizdan pul yoki shaxsiy ma'lumot so'rasa), buni kattalarga — ota-ona yoki o'qituvchiga — aytish kerak.

Bu mavzuda o'rganilgan ko'nikmalar — to'g'ri qidiruv, manbalarni tekshirish va xavfsizlik qoidalariga rioya qilish — zamonaviy raqamli dunyoda muvaffaqiyatli va xavfsiz harakat qilish uchun zarur bo'lgan "raqamli savodxonlik"ning asosini tashkil qiladi.""",

("5-sinf", 6): """Elektron pochtada ishlashni boshlash mavzusi email — ya'ni internet orqali xat yozish tizimi bilan tanishtiradi. Elektron pochta — bu odamlar orasida tezkor, bepul va istalgan masofaga xat yuborish imkonini beruvchi zamonaviy aloqa vositasi. Oddiy pochta xatidan farqli o'laroq, elektron xat bir necha soniyada manzilga yetib boradi.

Har bir elektron pochta manzili maxsus formatga ega: "foydalanuvchi_nomi@provayder.com" ko'rinishida. "@" belgisi (at deb o'qiladi) foydalanuvchi nomini pochta xizmati nomidan ajratib turadi. Masalan "aliyev.vali@gmail.com" manzilida "aliyev.vali" — bu foydalanuvchining o'zi tanlagan nomi, "gmail.com" esa xatni saqlab, yetkazib beruvchi xizmat (Google'ning pochta xizmati).

Elektron xat yozishda ba'zi odob-axloq qoidalariga rioya qilish kerak: xatni salomlashuv bilan boshlash, aniq va tushunarli tilda yozish, oxirida imzo (ismingiz) qoldirish. Xat mavzusini (subject) ham to'g'ri yozish muhim — bu qabul qiluvchiga xat nima haqida ekanini oldindan bilishga yordam beradi.

Xavfsizlik qoidalari elektron pochtada alohida ahamiyatga ega. Notanish odamdan kelgan xatni ochishdan oldin ehtiyot bo'lish kerak — ba'zi xatlar zararli bo'lishi, kompyuterга virus yuqtirishi yoki shaxsiy ma'lumotlarni o'g'irlashga urinishi mumkin ("fishing" deb ataladigan firibgarlik turi). Agar xat shubhali ko'rinsa (masalan sizdan parol yoki pul so'rasa), uni ochmaslik va kattalarga aytish kerak.

Ilova fayllar (attachment) — bu xatga biriktirilgan qo'shimcha fayllar (rasm, hujjat va h.k.). Notanish jo'natuvchidan kelgan ilovani ochish xavfli bo'lishi mumkin, chunki u zararli dastur bo'lishi ehtimoli bor.

Kuchli parol yaratish ham muhim ko'nikma — parol uzun bo'lishi, harflar, raqamlar va maxsus belgilarni o'z ichiga olishi kerak, shunda uni taxmin qilish qiyinlashadi. Bu mavzuda o'rganilgan bilimlar — email manzili tuzilishi, xat yozish odobi va xavfsizlik qoidalari — zamonaviy raqamli muloqotning muhim asosini tashkil qiladi.""",

("6-sinf", 1): """Hujjatga qayta ishlov berish mavzusi 5-sinfda olingan matn muharriri ko'nikmalarini yanada chuqurlashtiradi. Endi siz nafaqat matn yozish, balki uni professional ko'rinishga keltirishni ham o'rganasiz. Buning uchun shrift, o'lcham, rang va joylashuvni to'g'ri tanlash muhim.

Sarlavha va asosiy matn orasidagi farqni to'g'ri ko'rsatish — yaxshi hujjatning belgisi. Sarlavha odatda kattaroq, qalinroq shriftda yoziladi, shunda o'quvchi hujjatning qaysi qismi eng muhim ekanini darrov ko'radi. Matnni "tekislash" (justify) — bu qatorlarning chap va o'ng chetlarini tekis qilish, hujjatga rasmiy ko'rinish beradi.

Ro'yxatlar (list) — ma'lumotni tartibli ko'rsatishning yana bir usuli. Raqamlangan ro'yxat (1, 2, 3...) qadamlar ketma-ketligini ko'rsatish uchun, nuqtali ro'yxat esa bir-biriga bog'liq bo'lmagan elementlarni sanab o'tish uchun qulay. Masalan retseptdagi qadamlar raqamlangan, kerakli mahsulotlar esa nuqtali ro'yxatda bo'lishi mumkin.

Sahifa maketi (page layout) — hujjatning umumiy tuzilishi: hoshiya (chekka bo'shliqlar), sahifa yo'nalishi (portret — tik, yoki albom — yotiq) va qog'oz o'lchami. To'g'ri tanlangan maket hujjatni o'qishga qulay va chiroyli qiladi.

Bu bilimlar sizga maktab uchun hisobot, insho yoki taqdimot tayyorlashda, kelajakda esa har qanday rasmiy hujjat yozishda foydali bo'ladi. Professional ko'rinishdagi hujjat yozuvchining bilimliligini va e'tiborliligini ko'rsatadi.""",

("6-sinf", 2): """Tasvirga qayta ishlov berish mavzusida siz 5-sinfda o'rgangan oddiy chizish ko'nikmalaringizni kengaytirasiz. Endi tasvirlarni tahrirlash — ya'ni mavjud rasmni o'zgartirish, uning bir qismini kesish, rangini almashtirish kabi murakkabroq amallarni bajarish o'rganiladi.

Kesish (crop) — rasmning faqat kerakli qismini qoldirib, qolganini olib tashlash amali. Bu foydalanuvchiga rasmning diqqat markazini o'zgartirish yoki keraksiz fonni yo'q qilish imkonini beradi. O'lchamni o'zgartirish (resize) esa rasmni kattalashtirish yoki kichraytirish — lekin bunda "nisbatni saqlash" muhim, aks holda rasm cho'zilib yoki torayib, buzilib ko'rinadi.

Qatlamlar (layers) tushunchasi — professional grafik dasturlarning asosiy g'oyasi. Rasmni bir necha "shaffof qog'oz" qatlamlariga bo'lib tasavvur qiling: fon alohida qatlamda, asosiy obyekt alohida, bezaklar yana alohida. Bu har bir qismni boshqalariga tegmasdan alohida tahrirlash imkonini beradi.

Nusxa olish va joylashtirish (copy-paste) — bir shaklni bir necha marta takrorlash uchun ishlatiladi, bu esa naqsh yoki takrorlanuvchi elementlar yaratishda foydali. Murakkab kompozitsiya yaratish uchun turli shakl, chiziq va ranglarni uyg'unlashtirish kerak bo'ladi — bu badiiy did va rejalashtirish ko'nikmasini rivojlantiradi.

Bu bilimlar nafaqat rasm chizishda, balki kelajakda taqdimot, veb-sayt yoki reklama materiali tayyorlashda ham foydali bo'ladigan vizual fikrlash va dizayn asoslarini shakllantiradi.""",

("6-sinf", 3): """Elektron jadvalga qayta ishlov berish — bu sonlar bilan ishlashning kuchli vositasi bilan tanishuv. Elektron jadval (masalan Microsoft Excel) — bu ma'lumotlarni katak (cell)larga joylashtirib, ular ustida avtomatik hisob-kitob qilish imkonini beruvchi dastur. Har bir katak ustun harfi va qator raqami bilan belgilanadi, masalan A1, B2 kabi.

Formula — bu kompyuterga "bu kataklarni hisobla" deb buyruq berish usuli. Formula har doim "=" belgisidan boshlanadi. Masalan "=A1+A2" formulasi A1 va A2 kataklaridagi sonlarni qo'shib, natijani ko'rsatadi. To'rt asosiy amal — qo'shish (+), ayirish (-), ko'paytirish (*) va bo'lish (/) — barchasi formula orqali bajarilishi mumkin.

Formulalarning eng katta afzalligi — avtomatlik. Agar A1 katakdagi son o'zgarsa, unga bog'liq barcha formulalar natijasi ham AVTOMATIK yangilanadi, qayta hisoblash shart emas. Bu xususiyat, masalan, oylik xarajatlarni hisoblashda juda foydali: bironta xarajat o'zgarsa, jami summa o'zi qayta hisoblanadi.

Formulada xato qilish oson — masalan "=" belgisini unutish yoki noto'g'ri katak nomini yozish natijani buzadi. Shuning uchun formulani yozgandan keyin natijani tekshirish muhim odat bo'lishi kerak. Formulalarni bir-biriga bog'lash orqali (bir formula natijasini boshqa formulada ishlatish) murakkabroq hisob-kitoblar (masalan avval jami summa, keyin undan o'rtacha qiymat) qilish mumkin.

Bu ko'nikmalar kelajakda byudjet rejalashtirish, statistik tahlil yoki har qanday sonlar bilan ishlashni talab qiluvchi vazifalarda asos bo'lib xizmat qiladi — elektron jadval zamonaviy ish joyida eng ko'p ishlatiladigan vositalardan biridir.""",

("6-sinf", 4): """Ma'lumotlar bazasiga qayta ishlov berish mavzusi katta hajmdagi ma'lumotlarni tartibli saqlash va boshqarish san'atini o'rgatadi. Ma'lumotlar bazasi — bu jadval ko'rinishida tashkil etilgan, oson qidiriladigan va boshqariladigan ma'lumotlar to'plami. Masalan maktab kutubxonasidagi barcha kitoblar ro'yxati — bu ma'lumotlar bazasiga misol.

Jadval maydonlari (fields) — bu ma'lumotning har bir turi uchun alohida ustun, masalan "Ism", "Familiya", "Yosh". Har bir maydon o'ziga xos TURGA ega bo'lishi kerak: matn turi (ism uchun), son turi (yosh uchun), sana turi (tug'ilgan kun uchun). To'g'ri maydon turini tanlash muhim — masalan yoshni matn sifatida saqlasangiz, u bilan matematik amal bajarib bo'lmaydi.

Yozuv (record) — bu jadvaldagi bitta to'liq qator, masalan bitta o'quvchi haqidagi barcha ma'lumot (ismi, yoshi, sinfi). Ma'lumotlar bazasiga yangi yozuv qo'shish, mavjudini o'zgartirish yoki o'chirish mumkin.

Saralash (sort) — yozuvlarni ma'lum tartibda (masalan yosh bo'yicha o'sish yoki alifbo bo'yicha) joylashtirish. Filtrlash (filter) esa faqat ma'lum shartga mos yozuvlarni ko'rsatish, masalan faqat 12 yoshdan katta o'quvchilarni ko'rsatish. Bu ikki amal katta ma'lumotlar to'plamida kerakli ma'lumotni tezda topish imkonini beradi.

Hisobot (report) — ma'lumotlar bazasidan olingan, tushunarli tarzda taqdim etilgan xulosa, masalan "Sinfimizdagi eng yosh va eng katta yoshli o'quvchi" degan savolga javob beruvchi qisqa jadval.

Bu bilimlar zamonaviy dunyoda juda muhim, chunki deyarli barcha yirik tashkilotlar (maktablar, do'konlar, kasalxonalar) o'z ma'lumotlarini ma'lumotlar bazalarida saqlaydi va boshqaradi.""",

("6-sinf", 5): """Dasturlashni o'rganish mavzusida siz Scratch dasturida "Repeat" (takrorlash) operatori bilan tanishasiz — bu dasturlashning eng kuchli va foydali tushunchalaridan biri. 5-sinfda siz har bir buyruqni alohida-alohida yozgan bo'lsangiz (masalan to'rtburchak chizish uchun 8 ta buyruq), endi "Repeat" yordamida buni ancha qisqa va tushunarli qilib yozish mumkin.

Repeat operatori — bu "ichidagi buyruqlarni N marta takrorla" degan ma'noni bildiradi. Masalan, to'rtburchak chizish uchun avval "10 qadam yur" va "90 darajaga buril" degan ikkita buyruqni yozib, keyin ularni "Repeat 4" blokining ICHIGA joylashtirsangiz, dastur bu ikki buyruqni 4 marta ketma-ket bajaradi — natijada 8 ta alohida buyruq o'rniga atigi 3 ta blok (Repeat + 2 buyruq) yetarli bo'ladi.

Bu tushuncha nafaqat kodni qisqartiradi, balki DASTURNI TUSHUNISHNI ham osonlashtiradi — kimdir sizning dasturingizni ko'rganda, "bu 4 marta takrorlanadi" deb darrov tushunib oladi, har bir buyruqni alohida o'qishga hojat qolmaydi.

Repeat blokidan oldin va keyin ham buyruqlar bo'lishi mumkin — masalan avval spraytni boshlang'ich holatga qaytarish, keyin Repeat bilan asosiy harakatni bajarish, so'ngra natijani e'lon qilish. Bu — dasturning uch bosqichli tuzilishi: tayyorgarlik, asosiy jarayon, yakunlash.

Turli geometrik shakllarni (uchburchak, kvadrat, oltiburchak) chizish uchun Repeat sonini va burilish burchagini to'g'ri hisoblash kerak — bu matematik fikrlashni ham rivojlantiradi, chunki burchaklar yig'indisi doim 360 darajaga teng bo'lishi kerakligini amalda ko'rasiz.

Repeat operatorini o'rganish — kelajakda "for" va "while" tsikllarini (haqiqiy dasturlash tillarida ishlatiladigan takrorlash usullarini) tushunish uchun mustahkam asos yaratadi.""",

("6-sinf", 6): """Internetda ishlashni o'rganish mavzusi veb-brauzerdan samarali va tejamkor foydalanishni chuqurroq o'rgatadi. Veb-brauzer oynasining har bir qismi o'z vazifasiga ega: manzil satri (address bar) — saytning "uy manzili" yozilgan joy, orqaga/oldinga tugmalari — avval ko'rilgan sahifalar orasida yurish uchun, yorliqlar (tabs) esa bir vaqtning o'zida bir nechta saytni ochiq tutish imkonini beradi.

Saytlar orasida navigatsiya (o'tish) — bu havolalar (linklar) orqali amalga oshiriladi. Havola odatda boshqa rangda yoki tagiga chizilgan bo'ladi, uni bosganingizda brauzer sizni boshqa sahifaga olib boradi. Ba'zan bitta saytdan boshqasiga, ba'zan esa bir saytning ichidagi turli bo'limlariga o'tish mumkin.

Yorliqlar (bookmarks) — bu tez-tez ziyorat qiladigan saytlarni "belgilab qo'yish", shunda ularni qayta qidirmasdan, ro'yxatdan bir bosishda ochish mumkin. Foydali saytlarni turkumlarga (masalan "O'quv", "O'yin", "Yangiliklar") bo'lib saqlash qidiruvni yanada osonlashtiradi.

Bir nechta yorliq (tab)da ishlash — zamonaviy internetdan foydalanishning muhim ko'nikmasi. Masalan, bitta yorliqda vazifa matnini o'qib, ikkinchisida qo'shimcha ma'lumot qidirib, natijalarni solishtirish mumkin — bu vaqtni tejaydi.

Internetdan samarali foydalanish uchun aniq reja kerak: avval nima qidirayotganingizni belgilash, keyin mos so'z bilan qidirish, so'ng natijalar orasidan eng ishonchlisini tanlash, va nihoyat topilgan ma'lumotni to'g'ri yozib olish yoki saqlash. Bu tartibli yondashuv sizga o'qishda va kelajakda ish joyida katta yordam beradi, chunki internet — zamonaviy dunyoning eng katta ma'lumot manbai.""",

("6-sinf", 7): """Email (Elektron pochta) dan foydalanishni o'rganish mavzusi 5-sinfda olingan bilimlarni kengaytirib, xat yozish va ilova biriktirish ko'nikmalarini chuqurlashtiradi. Endi siz nafaqat oddiy xat yozish, balki unga fayl (masalan hujjat yoki rasm) biriktirish, va bir nechta odamga bir vaqtda xat yuborishni ham o'rganasiz.

Ilova (attachment) — bu xatga qo'shimcha qilib biriktirilgan fayl. Masalan, o'qituvchingizga uy vazifasini elektron pochta orqali yuborishda, vazifa faylini xatga "biriktirasiz". Bu tugma odatda skrepka belgisi bilan ko'rsatiladi. Ilova hajmi juda katta bo'lmasligi kerak, aks holda xat yuborilmasligi mumkin.

"Cc" (copy) maydoni — bu xatni asosiy qabul qiluvchidan tashqari, yana bir necha kishiga (masalan ota-onangizga yoki boshqa o'qituvchiga) "nusxa" sifatida yuborish uchun ishlatiladi. Bu barcha manfaatdor tomonlarni bir vaqtning o'zida xabardor qilish imkonini beradi, alohida-alohida xat yozishga hojat qolmaydi.

Elektron xat almashish odob-axloqi (etiquette) muhim mavzu: xat aniq va tushunarli bo'lishi, salomlashuv va yakunlovchi so'zlar bilan boshlanib tugashi kerak. Katta harflar bilan yozish (BARCHASI KATTA) qichqirish sifatida qabul qilinishi mumkin, shuning uchun undan saqlanish kerak.

Xavfsizlik masalasi yanada chuqurlashtiriladi: notanish jo'natuvchidan kelgan ilovani ochishdan oldin, jo'natuvchi manzili to'g'ri ekanini, xat mavzusi mantiqiy ekanini tekshirish kerak. Firibgarlar ko'pincha ishonchli tashkilot nomidan soxta xat yuborishadi — bunday xatlarga hech qachon shaxsiy ma'lumot yoki parol yozib yuborilmaydi.

Kelgan xatlarni papkalarga (masalan "Maktab", "Do'stlar") tashkil qilish — pochta qutingizni tartibli saqlash va kerakli xatni tezda topish imkonini beradi. Bu ko'nikmalar kattalar hayotida ham, ish joyida ham doimiy ishlatiladi.""",

("6-sinf", 8): """Multimedia hujjatiga qayta ishlov berish mavzusi matn, tasvir va tovushni birlashtirib, ta'sirchan taqdimot yaratishni o'rgatadi. Multimedia — bu bir necha turdagi ma'lumot (matn, rasm, tovush, video) birgalikda ishlatilishini bildiradi. Yaxshi multimedia mahsuloti auditoriyaga g'oyani nafaqat o'qish, balki ko'rish va eshitish orqali ham yetkazadi, bu esa tushunishni osonlashtiradi.

Taqdimot (prezentatsiya) — bir necha slayd (sahifa)dan iborat multimedia hujjati. Har bir slaydda sarlavha, asosiy matn va tasvir bo'lishi mumkin. Slaydlarni rejalashtirishda muhim qoida — "bir slaydda bitta asosiy g'oya": ko'p matnni bitta slaydga to'ldirish o'rniga, g'oyalarni bir necha slaydga bo'lib, har birini alohida tushuntirish yaxshiroq natija beradi.

Rasm va matn muvofiqligi — tasvir matnni to'ldirishi va tushuntirishi kerak, aks holda u shunchaki bezakka aylanib qoladi. Masalan, hayvon haqida gapirayotganda o'sha hayvonning rasmini qo'yish, matn va tasvirni bir-biriga bog'laydi va yodda qolishini osonlashtiradi.

Tovush qo'shish — taqdimotga fon musiqasi yoki ovozli tushuntirish (izoh) qo'shish mumkin. Biroq, fon musiqasi juda baland bo'lmasligi kerak, aks holda u asosiy ovoz yoki matnni "bosib" qo'yishi mumkin. Ovozli izoh esa taqdimotni tomoshabin o'zi o'qimasdan ham tushunishga yordam beradi.

O'tish effektlari (slaydlar orasidagi animatsiyalar, masalan sirg'alish yoki so'nish) taqdimotni jonli qiladi, lekin ularni haddan tashqari ko'p ishlatish diqqatni chalg'itishi mumkin — shuning uchun me'yorida foydalanish kerak.

Bu ko'nikmalar — matn, rasm va tovushni uyg'unlashtirish — kelajakda maktab loyihalarini taqdim etishda, hatto professional ishda ham (masalan kompaniya taqdimoti tayyorlashda) muhim rol o'ynaydi.""",

("7-sinf", 1): """Matnli hujjatdan maqsadli foydalanish mavzusi hujjat yaratishda "kim uchun" va "nima maqsadda" degan savollarni birinchi o'ringa qo'yishni o'rgatadi. Endi siz shunchaki matn yozish emas, balki ANIQ MAQSAD (masalan reklama varag'i, rasmiy xat, e'lon) uchun hujjat rejalashtirishni o'rganasiz.

Har qanday hujjatni yaratishdan oldin ikkita savolga javob berish kerak: kim buni o'qiydi (auditoriya) va nima uchun (maqsad). Masalan, agar maktab tadbiri uchun reklama varag'i yaratayotgan bo'lsangiz, auditoriyangiz — o'quvchilar va ota-onalar, maqsadingiz — ularni tadbirga taklif qilish va qatnashishga undash.

Auditoriyaga qarab til va uslub o'zgaradi — kichik sinf o'quvchilariga mo'ljallangan xabar sodda va qisqa so'zlar bilan, rasmiy hujjat esa aniq va rasmiy uslubda yozilishi kerak. Bir xil ma'lumotni turli auditoriya uchun turlicha taqdim etish — muloqot mahoratining muhim qismi.

Hujjat maketi (layout) — sarlavha, asosiy matn, tasvir va aloqa ma'lumotlarining sahifada qanday joylashishi. Yaxshi rejalashtirilgan maket o'quvchining diqqatini avval eng muhim ma'lumotga, keyin tafsilotlarga yo'naltiradi.

Formatlash (shrift, rang, o'lcham) orqali ma'lumotning muhimligini ta'kidlash mumkin — masalan sarlavhani katta va qalin qilish, muhim sanani rangli qilish. Lekin haddan tashqari ko'p formatlash effektni kamaytiradi, shuning uchun "kamroq — ko'proq" tamoyiliga amal qilish tavsiya etiladi.

Hujjat tayyor bo'lgach, undan auditoriyaning fikrini so'rash orqali uni yaxshilash mumkin — bu jarayon "fikr-mulohaza aylanishi" (feedback loop) deb ataladi va professional dizaynerlar doimo shu usuldan foydalanadi.""",

("7-sinf", 2): """Multimediadan maqsadli foydalanish mavzusi 6-sinfda o'rganilgan multimedia ko'nikmalarini "aniq auditoriya uchun aniq maqsadda" ishlatishga qaratadi. Endi siz nafaqat chiroyli taqdimot yaratish, balki uni maxsus bir guruh odamlar uchun, ma'lum bir natijaga erishish maqsadida loyihalashni o'rganasiz.

Multimedia mahsuloti yaratishdan oldin reja tuzish muhim: mavzu nima, kimlarga mo'ljallangan, qanday hissiy ta'sir qoldirish kerak (masalan xabardor qilish, ogohlantirish yoki ko'ngil xushlik). Masalan "Xavfsiz internet" mavzusidagi taqdimot kichik sinf o'quvchilari uchun rangli va sodda, o'qituvchilar uchun esa jiddiyroq va statistik ma'lumotlarga boy bo'lishi kerak.

Rasm va matn muvofiqligi yanada chuqurroq o'rganiladi — har bir tanlangan tasvir aynan shu matnni qanday to'ldirishini asoslash kerak. Tasodifiy yoki mavzuga aloqasi bo'lmagan rasmlar auditoriyani chalg'itadi va xabarni zaiflashtiradi.

Tovush elementi ham strategik tarzda rejalashtiriladi — qaysi qismda fon musiqasi kayfiyat yaratish uchun, qaysi qismda ovozli tushuntirish ma'lumot yetkazish uchun kerakligini oldindan belgilash kerak. Bu — multimedia mahsulotini "tasodifiy to'plam" emas, balki "maqsadli asar"ga aylantiradi.

Auditoriyaga moslashtirish — bir xil mavzuni ikki xil auditoriya (masalan bolalar va kattalar) uchun turlicha rang, musiqa va matn uslubida taqdim etishni bildiradi. Bu ko'nikma marketing, ta'lim va jurnalistika каби ko'plab sohalarda talab qilinadi.

Yakuniy loyiha — kirish, bir necha asosiy bo'lim va xulosadan iborat to'liq tuzilgan multimedia mahsuloti bo'lib, unda har bir elementning o'z aniq vazifasi bor. Bu mavzu ijodiy fikrlash bilan strategik rejalashtirishni birlashtirishni o'rgatadi.""",

("7-sinf", 3): """Elektron jadvallardan maqsadli foydalanish mavzusi 6-sinfda o'rganilgan formula bilimlarini REAL HAYOTIY MUAMMOLARNI YECHISHGA qaratadi. Endi elektron jadval shunchaki mashq emas, balki byudjet rejalashtirish kabi amaliy vazifalar uchun vosita sifatida ishlatiladi.

Byudjet jadvali — kirim (pul kelishi) va chiqim (pul sarflanishi)ni tartibli qayd etish usuli. Har bir kunlik yoki haftalik xarajatni alohida qatorga yozib, formula yordamida ularning yig'indisini avtomatik hisoblash mumkin. Bu real hayotda pul boshqaruvining asosiy ko'nikmasidir.

Formulalar zanjiri — bir nechta formulani bir-biriga bog'lash: masalan avval "jami kirim" formulasi, keyin "jami chiqim" formulasi, so'ngra ikkalasining farqi orqali "qolgan mablag'" formulasi hisoblanadi. Bu zanjir orqali murakkab hisob-kitoblarni bosqichma-bosqich, tushunarli tarzda tashkil qilish mumkin.

"Nima bo'lsa-chi" tahlili (what-if analysis) — elektron jadvalning kuchli xususiyati. Agar bironta qiymatni (masalan haftalik kirimni) o'zgartirsangiz, unga bog'liq BARCHA formulalar natijasi avtomatik qayta hisoblanadi. Bu orqali turli stsenariylarni (masalan "agar kirim ikki barobar oshsa nima bo'ladi") tezda tekshirish mumkin, qayta hisoblashga vaqt sarflanmaydi.

Diagramma orqali vizuallashtirish — sonli ma'lumotni (masalan turli xarajat toifalarini) grafik ko'rinishda ko'rsatish, bu esa qaysi toifaga ko'proq pul ketayotganini bir qarashda ko'rish imkonini beradi.

Haftalik jadvaldan oylik rejaga o'tish — kichik masshtabdagi hisob-kitobni kattaroq davrga kengaytirish ko'nikmasi bo'lib, bu real moliyaviy rejalashtirishning asosiy tamoyilidir. Bu bilimlar kelajakda shaxsiy byudjet, oilaviy xarajatlar yoki hatto kichik biznes hisob-kitoblarida foydali bo'ladi.""",

("7-sinf", 4): """Ma'lumotlar bazasidan maqsadli foydalanish mavzusi 6-sinfda olingan ma'lumotlar bazasi bilimlarini ANIQ MAQSAD uchun qo'llashga qaratilgan. Endi siz nafaqat jadval yaratish, balki uni real muammoni (masalan kutubxona boshqaruvi) yechish uchun loyihalashni o'rganasiz.

Maqsadli ma'lumotlar bazasi yaratishning birinchi qadami — qaysi maydonlar kerakligini aniqlash. Kutubxona misolida: "Kitob nomi", "Muallif", "Janr", "Nashr yili", "Band qilinganmi" kabi maydonlar kerak bo'ladi. Har bir maydon uchun to'g'ri MA'LUMOT TURINI tanlash muhim — masalan "Band qilinganmi" uchun matn emas, balki mantiqiy (ha/yo'q) tur qulayroq.

So'rov (query) — ma'lumotlar bazasidan ma'lum shartga mos ma'lumotni ajratib olish usuli. Masalan "faqat fantastika janridagi kitoblarni ko'rsat" degan so'rov, katta ro'yxatdan faqat kerakli qismini ajratib beradi. So'rov yozish — ma'lumotlar bazasi bilan ishlashning eng kuchli ko'nikmalaridan biri.

Saralash (sort) orqali ma'lumotlarni tartiblash — masalan kitoblarni nashr yili bo'yicha eskisidan yangisiga qarab joylashtirish, bu ma'lumotni tahlil qilishni osonlashtiradi va hisobot tayyorlashda foydali.

Ma'lumotlar bazasining REAL FOYDASINI tushunish muhim — masalan yaratilgan kutubxona bazasi kutubxonachiga qaysi kitob band, qaysi bo'sh ekanini bir zumda bilish imkonini beradi, bu esa qo'lda qidirishdan ancha tezroq va aniqroq.

Bu mavzu orqali siz nafaqat texnik ko'nikma, balki "muammoni tizim orqali yechish" fikrlash uslubini ham o'rganasiz — bu zamonaviy dunyoda deyarli barcha sohalarda (tibbiyot, savdo, ta'lim) qo'llaniladigan universal yondashuv.""",

("8-sinf", 1): """Maqsadni amalga oshirishda dasturlashdan foydalanish mavzusi Scratch dasturlashni yangi darajaga — O'ZGARUVCHILAR (variables) tushunchasiga olib chiqadi. O'zgaruvchi — bu dasturda qiymatni saqlab turadigan "quti", masalan o'yinda ochkolar sonini saqlash uchun ishlatiladi.

O'zgaruvchi yaratish uchun avval unga nom berilib (masalan "Ochkolar"), boshlang'ich qiymat (odatda 0) belgilanadi. Keyin dastur davomida bu qiymatni o'zgartirish mumkin — masalan tugma bosilganda "Ochkolar" ga 1 qo'shiladi. Bu — o'yinlar, hisoblagichlar va ko'plab interaktiv dasturlarning asosi.

O'zgaruvchi qiymati vaqt o'tishi bilan o'zgarib boradi — buni "holat" (state) deb atash mumkin. Masalan agar ketma-ket 5 marta amal bajarilsa, har safar o'zgaruvchi qiymati yangilanadi va oxirida umumiy natijani ko'rsatadi. Bu jarayonni jadvalga yozib borish orqali dasturning "ichida" nima bo'layotganini tushunish mumkin.

Ikkita yoki undan ortiq o'zgaruvchidan birgalikda foydalanish murakkabroq dasturlar yaratish imkonini beradi — masalan oddiy o'yinda "Ochkolar" (qancha yutuq) va "Jonlar" (qancha hayot qolgani) alohida-alohida kuzatiladi, ular bir-biriga bog'liq bo'lishi ham mumkin (masalan jonlar tugasa, o'yin tugaydi).

"Faqat shu sprayt uchun" va "barcha spraytlar uchun" o'zgaruvchi turlari orasidagi farqni tushunish muhim — birinchisi faqat bitta belgiga tegishli, ikkinchisi esa dasturdagi barcha spraytlar tomonidan ko'rilishi va o'zgartirilishi mumkin.

Bu bilimlar — o'zgaruvchilar orqali holatni saqlash va boshqarish — kelajakda haqiqiy dasturlash tillarida (Python, JavaScript) ishlatiladigan eng asosiy tushunchalardan biriga zamin yaratadi, chunki deyarli har qanday dastur o'zgaruvchilarsiz ishlay olmaydi.""",

("8-sinf", 2): """Maqsadni amalga oshirish uchun veb-sayt dizaynini yaratish mavzusi sizni HTML (Hyper Text Markup Language) — internetdagi barcha veb-sahifalarning asosi bo'lgan til bilan tanishtiradi. HTML yordamida siz o'z veb-sahifangizni yaratishni, unga matn, sarlavha va havolalar qo'shishni o'rganasiz.

HTML sahifasi maxsus "teg"lardan (belgilardan) tashkil topadi — har bir teg burchakli qavslar ichida yoziladi, masalan sarlavha uchun bitta teg, oddiy matn uchun boshqa teg ishlatiladi. Teglar odatda juft bo'ladi — ochuvchi va yopuvchi teg, ular orasiga mazmun (matn) joylashtiriladi.

Veb-sahifalar orasidagi bog'lanish HAVOLALAR (linklar) orqali amalga oshiriladi. Havola bosilganda brauzer foydalanuvchini boshqa sahifaga olib boradi. Bir necha sahifadan iborat veb-sayt yaratishda, sahifalar orasida to'g'ri havolalar tizimini (navigatsiya) tuzish muhim — foydalanuvchi istalgan sahifadan istalgan boshqa sahifaga oson o'ta olishi kerak.

Navigatsiya menyusi — odatda sahifaning yuqori qismida joylashgan, barcha asosiy sahifalarga havolalarni o'z ichiga olgan qism. Bu foydalanuvchiga saytda "yo'qolib qolmasdan" harakatlanish imkonini beradi.

Tashqi havolalar (boshqa veb-saytlarga olib boruvchi) bilan ichki havolalar (o'z saytingiz ichidagi sahifalarga) orasidagi farqni tushunish kerak — ikkalasi ham foydali, lekin turli maqsadlarda ishlatiladi.

Kichik, ko'p sahifali veb-sayt (masalan "Bosh sahifa", "Men haqimda", "Aloqa") loyihalashda, avval sayt xaritasini (qaysi sahifalar bo'ladi va ular qanday bog'langan) rejalashtirish, keyin har bir sahifani alohida yaratish tavsiya etiladi. Bu bilimlar zamonaviy raqamli dunyoda veb-texnologiyalarning asosini tushunish uchun juda muhim, chunki deyarli har bir tashkilot o'z veb-saytiga ega.""",

("8-sinf", 3): """Kompyuter tarmoqlaridan maqsadli foydalanish mavzusi tarmoqlarning REAL HAYOTDA qanday ishlatilishini chuqurroq o'rgatadi. Tarmoq — bu bir-biriga ulangan kompyuterlar guruhi bo'lib, ular orasida ma'lumot almashinishi mumkin. Eng kichik tarmoq — uy tarmog'i (bir necha qurilma bitta routerga ulangan), eng katta tarmoq esa internetning o'zi.

LAN (Local Area Network) — kichik hududdagi tarmoq, masalan bitta uy yoki maktab binosidagi barcha kompyuterlar. WAN (Wide Area Network) — katta masofalarni qamrab oluvchi tarmoq, masalan butun shahar yoki mamlakat bo'ylab tarqalgan tarmoq. Internet — bu dunyodagi eng katta WAN hisoblanadi.

Uy tarmog'ini tuzish uchun barcha qurilmalar (kompyuter, telefon, smart-TV) routerga simli yoki simsiz (Wi-Fi) tarzda ulanadi. Router — bu tarmoq trafigini boshqaruvchi asosiy qurilma, u internetga ulanishni barcha qurilmalar orasida taqsimlaydi.

Tarmoq xavfsizligi muhim mavzu — kuchli Wi-Fi paroli o'rnatish, tarmoq nomini (SSID) shubhali qilmaslik, va faqat ishonchli qurilmalarni ulash tavsiya etiladi. Himoyalanmagan tarmoq orqali begona odamlar sizning internetdan foydalanishi yoki hatto shaxsiy ma'lumotlaringizga kirishga urinishi mumkin.

Tarmoq resurslarini bo'lishish — masalan bitta printerni bir nechta kompyuter birgalikda ishlatishi, yoki fayllarni umumiy papka orqali almashish — tarmoqning amaliy foydasini ko'rsatadi, bu resurs va vaqtni tejaydi.

Bu bilimlar zamonaviy "ulangan dunyo"da qanday ishlashimizni tushunish uchun zarur — deyarli har bir uy, maktab va tashkilot allaqachon qandaydir tarmoq orqali ishlaydi.""",

("8-sinf", 4): """Maqsadni amalga oshirish uchun video yoki animatsiya yaratish mavzusi ijodiy fikrlashni texnik ko'nikmalar bilan birlashtiradi. Video yoki animatsiya yaratish — bu shunchaki tasvirlarni ketma-ket qo'yish emas, balki ANIQ MAQSAD (masalan biror narsani tushuntirish) uchun rejalashtirilgan jarayon.

Har qanday video loyihasi aniq maqsad va auditoriyani belgilashdan boshlanadi — masalan kichik sinf o'quvchilariga "qo'lni to'g'ri yuvish" haqida video yaratish uchun, avval bu videoning asosiy g'oyasini (nima o'rgatish kerak) aniq belgilash lozim.

Ssenariy taxtasi (storyboard) — videoning har bir qismida NIMA ko'rsatilishini oldindan chizib-rejalashtirish usuli. Bu — filmni suratga olishdan yoki animatsiya yaratishdan OLDIN qilinadigan muhim tayyorgarlik bosqichi, u orqali butun videoning oqimi va mantiqiy ketma-ketligi tekshiriladi.

Ovoz va matn rejasi — har bir kadrga qanday ovozli tushuntirish yoki ekranga chiquvchi matn (subtitr) qo'shilishini belgilash. Bu ma'lumotni tomoshabinga aniq va tushunarli tarzda yetkazishga yordam beradi.

Vaqt taqsimoti — videoning umumiy davomiyligini qismlarga (kirish, asosiy qism, xulosa) bo'lib, har biriga qancha vaqt ajratishni rejalashtirish. Masalan 30 soniyalik videoda kirish uchun 5 soniya, asosiy qism uchun 20 soniya, xulosa uchun 5 soniya ajratilishi mumkin — bu balansni saqlash tomoshabinning diqqatini ushlab turadi.

To'liq video loyihasi hujjati — maqsad, auditoriya, ssenariy taxtasi va vaqt taqsimotini birlashtirgan yakuniy reja, u orqali video yaratish jarayoni tartibli va samarali kechadi. Bu ko'nikmalar zamonaviy raqamli kontentning asosini tashkil qiladi, chunki video — bugungi kunda eng ko'p iste'mol qilinadigan kontent turi.""",

("9-sinf", 1): """Kompyuter tizimining turlari va komponentlari mavzusi kompyuterning "ichida" nima borligini va u qanday ishlashini chuqur tushuntiradi. Har qanday kompyuter tizimi ikki asosiy qismdan iborat: apparat ta'minot (hardware — jismoniy qurilmalar) va dasturiy ta'minot (software — dasturlar).

Protsessor (CPU — Central Processing Unit) — kompyuterning "miyasi", u barcha hisob-kitob va buyruqlarni bajaradi. Protsessorning tezligi qanchalik yuqori bo'lsa, kompyuter buyruqlarni shunchalik tez bajaradi. Zamonaviy protsessorlar sekundiga milliardlab amallarni bajarish qobiliyatiga ega.

Xotira ikki asosiy turga bo'linadi: RAM (Random Access Memory) va ROM (Read Only Memory). RAM — vaqtinchalik xotira, unda hozir ishlatilayotgan dasturlar va ma'lumotlar saqlanadi, lekin kompyuter o'chirilganda RAM'dagi ma'lumot yo'qoladi. ROM esa doimiy xotira, unda kompyuterning eng asosiy, o'zgarmas dasturiy ko'rsatmalari saqlanadi, o'chirilganda ham yo'qolmaydi.

RAM hajmi qanchalik katta bo'lsa, kompyuter bir vaqtning o'zida shunchalik ko'p dastur va ma'lumot bilan ishlashi mumkin, bu esa ishlash tezligiga ijobiy ta'sir qiladi. Zaxira xotira (qattiq disk yoki SSD) esa uzoq muddatli saqlash uchun ishlatiladi — fayllar, dasturlar va operatsion tizimning o'zi shu yerda saqlanadi, bu xotira turi kompyuter o'chirilganda ham ma'lumotni yo'qotmaydi.

Bu barcha komponentlar birgalikda ishlab, kompyuter tizimini tashkil qiladi: protsessor buyruqlarni bajaradi, RAM vaqtinchalik ma'lumotni saqlaydi, zaxira xotira esa uzoq muddatli saqlashni ta'minlaydi. To'g'ri kompyuter tanlash uchun bu komponentlarning har birini tushunish va o'z ehtiyojingizga (masalan o'yin uchunmi, oddiy ish uchunmi) mos konfiguratsiyani tanlash muhim.""",

("9-sinf", 2): """Kiritish va chiqarish qurilmalari mavzusi kompyuter bilan inson orasidagi "muloqot" vositalarini o'rgatadi. Kiritish qurilmasi — bu foydalanuvchidan kompyuterga ma'lumot yoki buyruq yetkazuvchi qurilma (masalan klaviatura, sichqoncha, mikrofon, skaner). Chiqarish qurilmasi esa kompyuterdan foydalanuvchiga natijani yetkazuvchi qurilma (masalan monitor, printer, karnay).

Ba'zi qurilmalar ham kiritish, ham chiqarish vazifasini bajaradi — masalan sensorli ekran (touchscreen): siz unga barmog'ingiz bilan tegib buyruq berasiz (kiritish), u esa natijani ko'rsatadi (chiqarish). Bunday qurilmalar "kiritish-chiqarish" (input-output) qurilmalari deb ataladi.

Har xil vazifa uchun turli kiritish qurilmalari qulayroq: matn terish uchun klaviatura, aniq nuqtani tanlash uchun sichqoncha, rasm chizish uchun grafik planshet, ovoz yozish uchun mikrofon. To'g'ri qurilmani tanlash ish samaradorligini oshiradi.

Chiqarish qurilmalarini tanlashda ham vaziyatga qarab yondashuv kerak — katta zalda taqdimot uchun proyektor (katta ekranga tasvirni proyeksiya qiluvchi qurilma), uy sharoitida esa oddiy monitor yetarli. Rangni aniq chiqarish muhim bo'lgan dizayn ishlarida esa maxsus rangli printerlar ishlatiladi.

Qurilmalarni tanlashda foydalanuvchi ehtiyoji, byudjet va maqsad muhim omillar hisoblanadi. Masalan, ko'zi ojiz odamlar uchun maxsus Brayl printeri (chiqarish) yoki ovozli buyruq beruvchi mikrofon (kiritish) ishlatilishi mumkin — bu texnologiyaning barcha odamlar uchun qulay bo'lishini ta'minlashning muhim jihati (accessibility). Bu bilimlar to'g'ri texnik yechim tanlashda va texnologiyani samarali qo'llashda asos bo'lib xizmat qiladi.""",

("9-sinf", 3): """Xotira qurilmalari va ma'lumot almashish vositalari mavzusi ma'lumotlarni qanday saqlash va bir joydan boshqa joyga ko'chirish mumkinligini chuqur o'rgatadi. Zaxira xotira turlari orasida qattiq disk (HDD), tezkor xotira (SSD), flesh xotira (USB) va bulutli saqlash (cloud storage) farqlanadi.

Qattiq disk (HDD) — an'anaviy, aylanuvchi metall diskka asoslangan xotira, u katta hajmda ma'lumot saqlaydi, lekin nisbatan sekinroq ishlaydi. SSD (Solid State Drive) esa harakatlanuvchi qismlarsiz, elektron chiplarga asoslangan bo'lib, ancha tezroq ishlaydi, lekin narxi qimmatroq.

Zaxira nusxalash (backup) — muhim fayllarning qo'shimcha nusxasini boshqa joyda saqlash, shunda asl fayl yo'qolsa yoki buzilsa ham, ma'lumot saqlanib qoladi. Yaxshi zaxira nusxalash rejasi — qaysi fayllar, qanchalik tez-tez va qayerda (masalan bulutda va tashqi diskda) saqlanishini belgilaydi.

Bulutli saqlash (masalan Google Drive) — internetga ulangan uzoq serverlarda ma'lumot saqlash usuli. Uning afzalligi — istalgan qurilmadan (telefon, kompyuter) kirish imkoniyati va fayl yo'qolish xavfining pastligi, chunki ma'lumot bir necha serverda zaxiralanadi. Mahalliy saqlash (o'z kompyuteringizda) esa internetga bog'liq emas, lekin qurilma buzilsa, ma'lumot yo'qolishi xavfi bor.

Kirish usullari ham muhim tushuncha: bevosita kirish (masalan qattiq diskda) — istalgan faylga to'g'ridan-to'g'ri, tez kirish mumkin; ketma-ket kirish (masalan eski magnit lentada) — faylni topish uchun boshidan охиригача "o'qib chiqish" kerak, bu ancha sekinroq.

Bu bilimlar zamonaviy raqamli dunyoda ma'lumotni xavfsiz va samarali saqlash strategiyasini tushunish uchun zarur — chunki ma'lumot yo'qotish (masalan zaxira nusxasi bo'lmagani uchun) juda katta muammolarga olib kelishi mumkin.""",

("9-sinf", 4): """Kompyuter tarmoqlari va ulardan foydalanish mavzusi tarmoqlarning tuzilishi va ularning zamonaviy hayotdagi rolini chuqur yoritadi. Tarmoq — bu ma'lumot almashish uchun bir-biriga ulangan qurilmalar tizimi. Tarmoqlar hajmiga qarab farqlanadi: LAN (kichik hududiy tarmoq, masalan bitta bino), va WAN (katta hududiy tarmoq, masalan butun mamlakat yoki dunyo — internet).

Internetga ulanishning bir necha usuli mavjud: simli ulanish (Ethernet kabeli orqali, barqaror va tez) va simsiz ulanish (Wi-Fi orqali, qulay, lekin ba'zan sekinroq va kamroq barqaror bo'lishi mumkin). Mobil internet (4G/5G) esa istalgan joyda, kabel yoki Wi-Fi'siz internetga ulanish imkonini beradi.

Tarmoq xavfsizligi — zamonaviy dunyoning eng dolzarb masalalaridan biri. Himoyalanmagan tarmoqqa ulanish orqali begona odamlar sizning ma'lumotlaringizga kirishga urinishi mumkin. Shuning uchun kuchli parollar, ishonchli Wi-Fi tarmoqlaridan foydalanish va jamoat joylaridagi ochiq Wi-Fi'da ehtiyot bo'lish tavsiya etiladi.

Tarmoq orqali turli xizmatlardan foydalanish mumkin: fayl almashish, elektron pochta, video qo'ng'iroqlar, va bulutli xizmatlar. Har bir xizmat o'z protokoliga (qoidalar to'plamiga) ega bo'lib, bu protokollar qurilmalar orasida to'g'ri "til topishishini" ta'minlaydi.

Router — uy yoki ofis tarmog'ining markaziy qurilmasi bo'lib, u internetga ulanishni barcha qurilmalar orasida taqsimlaydi va tarmoq trafigini boshqaradi. To'g'ri sozlangan router tarmoqning tezligi va xavfsizligini ta'minlaydi.

Bu bilimlar zamonaviy "ulangan dunyo"da samarali va xavfsiz ishlash uchun zarur, chunki deyarli barcha zamonaviy texnologiyalar (ish, ta'lim, ko'ngilochar) tarmoqqa bog'liq holda ishlaydi.""",

("9-sinf", 5): """Axborot texnologiyalarining ta'siri mavzusi AKT (axborot-kommunikatsiya texnologiyalari)ning jamiyat, ta'lim va mehnat bozoriga qanday ta'sir qilganini chuqur tahlil qiladi. AKT — kompyuter, internet va raqamli qurilmalarni o'z ichiga olgan keng tushuncha bo'lib, u so'nggi o'n yilliklarda inson hayotini tubdan o'zgartirdi.

Mehnat bozoriga ta'siri ikki tomonlama: ba'zi kasblar avtomatlashtirish tufayli o'zgardi yoki yo'qoldi (masalan qo'lda hisob-kitob qiluvchi buxgalter o'rniga dastur), lekin shu bilan birga ko'plab yangi kasblar paydo bo'ldi (dasturchi, raqamli marketolog, kiberxavfsizlik mutaxassisi). Bu — texnologik taraqqiyotning tabiiy oqibati.

Ta'lim sohasida AKT ta'siri ham katta — masofaviy ta'lim, elektron darsliklar, onlayn kurslar orqali bilim olish endi geografik chegaralarга bog'liq emas. Bu ayniqsa uzoq hududlarda yashovchi yoki jismoniy cheklovga ega o'quvchilar uchun katta imkoniyat yaratadi.

Salbiy ta'sirlar ham mavjud: ekran vaqtining ko'payishi ko'z va mushak-suyak tizimiga salbiy ta'sir qilishi mumkin, ijtimoiy tarmoqlarga ortiqcha berilib ketish esa real muloqotni kamaytirishi mumkin. Shu sababli sog'lom ekran vaqti odatlarini shakllantirish (masalan muntazam tanaffuslar qilish) muhim.

RSI (Repetitive Strain Injury) — uzoq muddat bir xil harakatni (masalan klaviaturada yozish) takrorlashdan kelib chiqadigan mushak-tendon shikastlanishi. Buning oldini olish uchun to'g'ri o'tirish holati, muntazam tanaffuslar va ergonomik jihozlardan foydalanish tavsiya etiladi.

Bu mavzu texnologiyaning ham foyda, ham xavflarini muvozanatli baholashni, va undan ongli tarzda foydalanishni o'rgatadi — bu zamonaviy raqamli fuqarolikning muhim qismidir.""",

("9-sinf", 6): """AKTni tatbiq etish mavzusi axborot texnologiyalarining turli sohalarda amaliy qo'llanilishini o'rgatadi. Har bir soha — sog'liqni saqlash, ta'lim, savdo, transport — AKT yordamida o'z jarayonlarini yaxshilagan va tezlashtirgan.

Sog'liqni saqlashda AKT elektron tibbiy kartalar, masofaviy diagnostika (telemeditsina) va murakkab tibbiy tasvirlarni tahlil qiluvchi dasturlar orqali qo'llaniladi. Bu shifokorlarga tezroq va aniqroq tashxis qo'yishga yordam beradi.

Ekspert tizimlar — bu ma'lum bir soha bo'yicha katta bilim to'plamiga asoslangan, "agar-unda" qoidalari orqali xulosa chiqaruvchi dasturlar. Masalan tibbiyotda alomatlarga qarab mumkin bo'lgan kasalliklarni taklif qiluvchi tizim, yoki qishloq xo'jaligida tuproq holatiga qarab o'g'it tavsiya qiluvchi tizim. Bunday tizimlar inson mutaxassisining bilimini "raqamlashtirib", uni ko'proq odamlarga bir vaqtda taqdim etish imkonini beradi.

Ta'lim boshqaruv tizimlari — elektron kundalik, baholarni kuzatish, davomatni qayd etish kabi funksiyalarni o'z ichiga oladi. Bunday tizim o'quvchi, o'qituvchi va ota-onalar orasida ma'lumot almashishni tezlashtiradi va shaffoflikni oshiradi.

Tanib olish tizimlari (yuz, ovoz, barmoq izi) — xavfsizlik va qulaylik uchun keng qo'llaniladi, masalan telefonni yuz orqali qulfdan chiqarish. Biroq bu texnologiyalar shaxsiy hayotga aralashish xavfini ham keltirib chiqaradi, shuning uchun ularning qanday va qayerda ishlatilishi jamiyatda muhokama qilinishi kerak bo'lgan masala.

Bu mavzu AKTning nafaqat texnik, balki ijtimoiy-axloqiy jihatlarini ham ko'rib chiqishga, va texnologiyani mas'uliyat bilan qo'llashga o'rgatadi.""",

("9-sinf", 7): """Tizimning hayot davri mavzusi yangi dasturiy yoki apparat tizim qanday bosqichlar orqali yaratilishini o'rgatadi. Har qanday muvaffaqiyatli tizim (masalan yangi maktab boshqaruv dasturi) tasodifan emas, balki aniq rejalashtirilgan bosqichlar orqali yaratiladi.

Birinchi bosqich — muammoni tahlil qilish: mavjud tizimdagi kamchiliklarni aniqlash, foydalanuvchilar bilan suhbatlashish (intervyu), va yangi tizimga bo'lgan haqiqiy ehtiyojni tushunish. Bu bosqichda shoshilmasdan, chuqur tahlil qilish keyingi barcha bosqichlarning sifatini belgilaydi.

Ikkinchi bosqich — loyihalash: tizim qanday ishlashi, qanday ma'lumotlar bilan ishlashi va interfeysi qanday bo'lishi rejalashtiriladi. Bu bosqichda texnik-iqtisodiy asoslash ham tayyorlanadi — ya'ni yangi tizim qancha vaqt va xarajat talab qilishi, va bu xarajat oqlanadimi degan savolga javob beriladi.

Uchinchi bosqich — ishlab chiqish (dasturlash) va sinov (testing). Sinov bosqichida tizim turli holatlar (test case) bilan tekshiriladi — masalan turli xil kirish ma'lumotlari bilan sinab ko'rilib, tizim kutilgan natijani berayotganligi tasdiqlanadi. Bu bosqich xatolarni tizim ishga tushirilishidan OLDIN topish imkonini beradi.

To'rtinchi bosqich — joriy etish: tizim haqiqiy foydalanuvchilarga taqdim etiladi. Beshinchi, oxirgi bosqich — qo'llab-quvvatlash va baholash: foydalanuvchilardan fikr-mulohaza olib, tizimni doimiy takomillashtirish.

Bu besh bosqichli tsikl — tahlil, loyihalash, ishlab chiqish/sinov, joriy etish, baholash — dasturiy ta'minot sohasida "tizim hayot davri" (System Development Life Cycle) deb ataladi va deyarli barcha professional IT loyihalarida qo'llaniladi.""",

("9-sinf", 8): """Xavfsizlik texnikasi qoidalari mavzusi kompyuter bilan ishlashda jismoniy va axborot xavfsizligini ta'minlash yo'llarini o'rgatadi. Xavfsizlik ikki katta yo'nalishga bo'linadi: jismoniy xavfsizlik (kabellar, elektr, jihozlar bilan bog'liq) va axborot xavfsizligi (ma'lumot va parollarni himoya qilish).

Jismoniy xavfsizlik qoidalariga quyidagilar kiradi: elektr kabellarini tartibsiz tashlab qo'ymaslik (qoqilib yiqilish xavfi), suyuqlikni kompyuter yaqinida ushlamaslik, va jihozlarni haddan tashqari qizib ketishdan saqlash (shamollatish teshiklarini yopmaslik). Bu oddiy qoidalarga rioya qilish nafaqat jihozlarni, balki insonlarni ham baxtsiz hodisalardan asraydi.

Ergonomika — ish joyini inson tanasiga qulay qilib tashkil etish fani. To'g'ri o'tirish holati (orqa tik, oyoqlar yerga tekis tegib turishi), monitor ko'z darajasida joylashishi, va klaviatura qo'lga qulay balandlikda bo'lishi — bularning barchasi uzoq muddatli sog'liq muammolarining oldini oladi.

Axborot xavfsizligi tomonidan eng muhim qoida — kuchli parol yaratish: parol uzun (kamida 8-10 belgi), harflar (katta va kichik), raqamlar va maxsus belgilar aralashmasidan iborat bo'lishi kerak. Zaif parol (masalan "12345" yoki tug'ilgan sana) osongina taxmin qilinadi va hisobingizni xavf ostiga qo'yadi.

Zararli dastur (malware, virus)lardan himoyalanish uchun antivirus dasturidan foydalanish, dasturiy ta'minotni muntazam yangilab turish, va notanish manbadan yuklab olishdan saqlanish tavsiya etiladi. Zararli dasturlar ko'pincha shubhali havolalar yoki ilova fayllar orqali tarqaladi.

Bu mavzuda o'rganilgan qoidalar — jismoniy va raqamli xavfsizlik — zamonaviy hayotda texnologiyadan xavfsiz foydalanishning ajralmas qismidir, va ular amaliyotda muntazam qo'llanilishi kerak, faqat nazariy bilim sifatida emas.""",

("9-sinf", 9): """Auditoriya mavzusi axborot mahsuloti (hujjat, taqdimot, veb-sayt) yaratishda ANIQ AUDITORIYANI hisobga olishning muhimligini chuqur o'rgatadi. Auditoriya — bu sizning mahsulotingizni ko'rib chiqadigan yoki foydalanadigan odamlar guruhi, va ularning ehtiyoji, bilim darajasi hamda qiziqishlarini tushunish muvaffaqiyatli kommunikatsiyaning kaliti hisoblanadi.

Auditoriya tahlili — maqsadli auditoriyaning yoshi, bilim darajasi, qiziqishlari va ehtiyojlarini oldindan o'rganish jarayoni. Bu jarayon so'rovnoma o'tkazish, mavjud ma'lumotlarni tahlil qilish yoki oddiy kuzatuv orqali amalga oshirilishi mumkin.

Bitta mavzuni turli auditoriya uchun turlicha taqdim etish kerak bo'ladi — masalan "internetdan xavfsiz foydalanish" mavzusi kichik bolalar uchun rangli rasmlar va sodda so'zlar bilan, kattalar uchun esa jiddiyroq statistika va real misollar bilan tushuntirilishi kerak. Bu — bir xil ma'lumotni "tarjima qilish" san'ati.

Mualliflik huquqi — auditoriya bilan ishlashda hisobga olinishi kerak bo'lgan muhim huquqiy masala. Boshqa birovning ijodiy asari (matn, rasm, musiqa)dan foydalanishda uning ruxsatini olish yoki manbani ko'rsatish kerak, aks holda bu qonunga xilof hisoblanadi. Ochiq litsenziya (masalan Creative Commons) ostida chiqarilgan materiallardan esa belgilangan shartlar asosida foydalanish mumkin.

Tarmoq xavfsizligi qoidalarini auditoriyaga (masalan o'quvchilarga) mo'ljallangan poster orqali yetkazish — bu auditoriya tahlili va vizual kommunikatsiyani birlashtirgan amaliy misol, unda til sodda, dizayn esa diqqatni tortuvchi bo'lishi kerak.

Bu mavzu — kim uchun, nima uchun va qanday yetkazish kerakligini oldindan o'ylab ko'rish — professional kommunikatsiya va marketingning asosiy tamoyilidir.""",

("9-sinf", 10): """Kommunikatsiya mavzusi zamonaviy elektron muloqot vositalari va ulardan to'g'ri foydalanish odob-axloqini chuqur yoritadi. Elektron muloqot — email, messenjerlar (Telegram, WhatsApp kabi) va video qo'ng'iroqlar orqali amalga oshiriladigan, masofadan tezkor aloqa qilish usuli.

Rasmiy elektron xat yozishda muayyan tuzilishga rioya qilish kerak: mavzu qatori (subject) xat mazmunini qisqacha aks ettirishi, salomlashuv bilan boshlanishi, aniq va tushunarli asosiy qism, va imzo bilan yakunlanishi kerak. Rasmiy va norasmiy muloqot uslubi orasidagi farqni tushunish — kimga yozayotganingizga qarab tilni moslashtirish muhim ko'nikma.

"To", "Cc" va "Bcc" maydonlari orasidagi farq — elektron xat yozishning muhim texnik jihati. "To" — asosiy qabul qiluvchi, "Cc" (copy) — xatdan xabardor bo'lishi kerak bo'lgan qo'shimcha odamlar (hammaga ko'rinadi), "Bcc" (blind copy) esa — boshqalarga bildirmasdan nusxa yuborish, bunda boshqa qabul qiluvchilar Bcc'dagi odamni ko'rmaydi.

Spam (keraksiz yoki firibgar) xabarlarni tanib olish muhim xavfsizlik ko'nikmasi: shubhali havolalar, imlo xatoларга to'la matn, ortiqcha shoshiltiruvchi til ("hoziroq javob bering!") — bularning barchasi spam yoki firibgarlik belgilari bo'lishi mumkin.

Guruh muloqoti (masalan sinf uchun Telegram guruhi) tashkil etishda aniq qoidalar belgilash foydali — kim a'zo bo'la oladi, qanday mavzularda yozish mumkin, va nizolarni qanday hal qilish kerak.

Internetdan foydalanishning afzallik (tezkor aloqa, ma'lumotga oson kirish) va kamchiliklari (haddan tashqari ko'p vaqt sarflash, ishonchsiz ma'lumot xavfi) o'rtasida muvozanatni tushunish — bu mavzuning yakuniy va eng muhim xulosasidir.""",

("9-sinf", 11): """Fayllar boshqaruvi mavzusi kompyuterdagi fayl va papkalarni tartibli saqlash san'atini chuqur o'rgatadi. Yaxshi tashkil etilgan fayl tizimi vaqtni tejaydi va kerakli hujjatni tezda topish imkonini beradi, tartibsiz saqlangan fayllar esa vaqt o'tishi bilan katta muammoga aylanadi.

Papka (folder/directory) ierarxiyasi — fayllarni mantiqiy guruhlarga bo'lib, ichma-ich papkalarga joylashtirish. Masalan "Fanlar" papkasi ichida har bir fan uchun alohida papka, ular ichida esa chorak yoki mavzu bo'yicha kichikroq papkalar bo'lishi mumkin. Bu tuzilma qandaydir faylni qidirishda "yo'l xaritasi" vazifasini bajaradi.

Fayl nomlash qoidalari muhim ahamiyatga ega: fayl nomi uning mazmunini aks ettirishi, sana yoki versiya raqamini o'z ichiga olishi mumkin (masalan "hisobot_2026-05-01_v2"). Noaniq nomlar ("hujjat1", "yangi") vaqt o'tishi bilan qaysi fayl nima ekanini unutishga olib keladi.

Fayl kengaytmalari (extension) — nuqtadan keyingi harflar (masalan .docx, .jpg, .pdf) — fayl turini bildiradi va qaysi dastur uni ochishi kerakligini kompyuterga aytadi. Masalan .jpg — rasm fayli, .docx — Word hujjati, .pdf — universal hujjat formati, ko'plab qurilmalarda bir xil ko'rinishda ochiladi.

Fayllarni turli formatlarda saqlash imkoniyati foydali — masalan bitta hujjatni tahrirlash uchun .docx formatida, boshqalar bilan bo'lishish uchun esa .pdf formatida saqlash mumkin, chunki PDF format hujjat ko'rinishini o'zgartirmasdan saqlaydi.

Fayllarni siqish (compression, masalan ZIP formatiga) — fayl hajmini kichraytirib, uni tezroq yuborish yoki kamroq joy egallashini ta'minlaydi, bu ayniqsa katta hajmli fayllarni internet orqali yuborishda foydali.""",

("9-sinf", 12): """Tasvirlar mavzusi 6-sinfda boshlangan grafik bilimlarni professional darajaga olib chiqadi — raster va vektor grafika orasidagi farqni chuqur tushuntiradi. Raster tasvir (masalan .jpg, .png) piksellar (kichik rangli kvadratchalar)dan tashkil topgan, kattalashtirilganda "dog'lanib" ko'rinadi. Vektor tasvir esa matematik formulalar (chiziq va egri chiziqlar) asosida qurilgan bo'lib, istalgancha kattalashtirilsa ham sifatini yo'qotmaydi.

Tasvirni tahrirlash uskunalari kengaytiriladi: kesish, o'lcham o'zgartirish (nisbatni saqlagan holda), rang tuzatish (yorqinlik, kontrast) kabi amallar professional darajada o'rganiladi. Nisbatni saqlamasdan kattalashtirilgan rasm cho'zilib, tabiiy ko'rinishini yo'qotadi — bu keng tarqalgan xato.

Rang chuqurligi, yorqinlik va kontrast tushunchalari — tasvirning vizual sifatini belgilaydigan asosiy parametrlar. Yorqinlik rasmning umumiy "yorug'lik" darajasini, kontrast esa eng och va eng to'q qismlar orasidagi farqni bildiradi. Bu ikkalasini to'g'ri sozlash rasmni yanada ta'sirchan qiladi.

Fayl hajmini kamaytirish (siqish) — veb-saytlarda tasvirlardan foydalanishda muhim, chunki katta hajmli rasmlar sahifa yuklanish tezligini sekinlashtiradi. Sifatni sezilarli darajada yo'qotmasdan hajmni kamaytirish — muhim texnik ko'nikma.

Auditoriyaga moslashtirish — bir xil tasvirni turli maqsad (masalan bolalar jurnali uchun yorqin va quvnoq, ilmiy maqola uchun aniq va rasmiy) uchun turlicha tahrirlash kerakligini anglatadi. Bu mavzu vizual savodxonlikni — tasvirlarni tanqidiy baholash va ularni maqsadga muvofiq yaratish qobiliyatini — rivojlantiradi, bu zamonaviy raqamli dunyoda muhim ko'nikma hisoblanadi.""",

("9-sinf", 13): """Loyihalash mavzusi hujjat yoki sahifa maketini oldindan rejalashtirish san'atini o'rgatadi — bu professional dizaynerlarning eng asosiy ko'nikmalaridan biri. Har qanday yaxshi hujjat tasodifan emas, balki diqqat bilan o'ylangan loyihalash jarayonidan so'ng yaratiladi.

Sahifa yo'nalishi — portret (tik, balandligi kengligidan katta) yoki albom (yotiq, kengligi balandligidan katta). Reklama varag'i yoki rasmiy xat odatda portret yo'nalishda, keng jadval yoki diagramma esa albom yo'nalishda qulayroq ko'rinadi.

Loyihalash jarayonida har bir hujjat turi uchun maxsus savollarga javob berish kerak: nechta tasvir kerak, qanday shrift mos keladi, qancha bo'sh joy (oq maydon) qoldirish kerak. Bo'sh joy — bu shunchaki "ishlatilmagan" maydon emas, balki hujjatni "nafas oldiruvchi", ko'zga yengil qabul qilinadigan qiluvchi muhim dizayn elementi.

Ustunlar (columns) — gazeta yoki jurnal uslubidagi hujjatlarda matnni bir necha vertikal qismga bo'lish, bu o'qishni osonlashtiradi, chunki inson ko'zi tor ustunlarni keng qatorlarga qaraganda tezroq o'qiydi.

Ustlavha (header) va taglavha (footer) — har bir sahifaning yuqori va pastki qismida takrorlanadigan elementlar (masalan sahifa raqami, sana, hujjat nomi). Bular hujjatni professional va izchil ko'rinishga keltiradi.

Auditoriyaga mos rang va shrift tanlash — bolalar uchun yorqin ranglar va o'yinqaroq shriftlar, biznes hamkorlar uchun esa jiddiy va rasmiy ranglar mosroq. Bu mavzu — vizual qarorlarni auditoriya va maqsadga asoslanib qabul qilishni o'rgatadi, bu esa professional dizaynning yuragi hisoblanadi.""",

("9-sinf", 14): """Uslublar mavzusi hujjatlarda IZCHILLIKNI (bir xillikni) ta'minlash uchun "stil" (uslub) tushunchasini chuqur o'rgatadi. Korporativ stil — bu tashkilotning barcha hujjatlarida bir xil rang, shrift va logotipdan foydalanish orqali yaratiladigan yagona, tanib olinadigan ko'rinish.

Har bir tashkilot yoki brend o'zining o'ziga xos stiliga ega — masalan bir xil ikki-uch rang, bitta asosiy shrift va logotip barcha hujjat, veb-sayt hamda reklamalarida takrorlanadi. Bu izchillik odamlarga brendni tezda tanib olishga yordam beradi, hatto matnni o'qimasdan turib ham.

Stil qo'llanmasi (style guide) — tashkilotning rasmiy hujjatlarida foydalaniladigan aniq ranglar (masalan HEX kod bilan), shriftlar va logotip qoidalarini yozib qo'yilgan qisqa hujjat. Bu qo'llanma barcha xodimlar bir xil ko'rinishdagi materiallarni yaratishini ta'minlaydi, hattoki turli odamlar turli vaqtda ishlasa ham.

Izchil va izchil bo'lmagan hujjatlar orasidagi farq katta ta'sirga ega — agar bir tashkilotning turli hujjatlarida turlicha rang va shriftlar ishlatilsa, bu tashkilotning "tartibsiz" yoki professional bo'lmagan taassurot qoldiradi. Aksincha, izchil stil ishonch va professionallik hissini kuchaytiradi.

Shablon (template) — oldindan tayyorlangan, stil elementlarini o'z ichiga olgan hujjat asosi, unga faqat matnни o'zgartirib, tayyor va izchil hujjat yaratish mumkin. Bu vaqtni tejaydi va har safar dizaynni qaytadan o'ylab topishga hojat qoldirmaydi.

Bu mavzu — vizual izchillikning ahamiyati va uni qanday yaratish mumkinligi — professional hujjat dizayni va brendlashning asosiy tamoyillaridan biridir.""",

("9-sinf", 15): """Xatolarni tekshirish mavzusi hujjat va dasturlardagi xatolarni aniqlash hamda tuzatish usullarini chuqur o'rgatadi. Xato turlari xilma-xil bo'lishi mumkin: imlo xatosi (noto'g'ri yozilgan so'z), punktuatsiya xatosi (noto'g'ri tinish belgilari), mantiqiy xato (matn ichidagi ziddiyat) va ma'lumot xatosi (noto'g'ri raqam yoki fakt).

Tasdiqlash qoidalari (validation rules) — bu elektron formalarda kiritilgan ma'lumot to'g'ri formatda ekanligini avtomatik tekshirish usuli. Masalan, "yosh" maydoniga faqat 0 dan 120 gacha bo'lgan sonlar kiritilishi mumkin degan qoida o'rnatilsa, tizim noto'g'ri qiymat (masalan manfiy son yoki matn) kiritilganda xato xabarini ko'rsatadi.

Avtomatik tuzatish (autocorrect) — matn muharrirlarining foydali, lekin ba'zan noqulay xususiyati. U ba'zan to'g'ri yozilgan, lekin dastur tanimagan so'zlarni "tuzatib", aslida xato qilib qo'yishi mumkin. Shuning uchun avtomatik tuzatishga to'liq ishonmasdan, matnni qo'lda ham tekshirib chiqish tavsiya etiladi.

Ma'lumotlarni tasdiqlash testi — turli xil qiymatlar (ba'zilari to'g'ri, ba'zilari noto'g'ri) bilan tizimni sinash orqali, tizim xatolarni to'g'ri aniqlab, rad etayotganini tekshirish jarayoni. Bu dasturiy ta'minot sifatini ta'minlashning muhim usuli.

Matnni diqqat bilan qayta o'qish (proofreading) — professional hujjat tayyorlashning ajralmas qismi. Ko'pincha o'zimiz yozgan matndagi xatoni ko'rmaymiz, chunki miyamiz "kutilgan" matnni o'qiydi. Shuning uchun matnni ovoz chiqarib o'qish yoki boshqa odamdan tekshirtirish foydali usul hisoblanadi.

Bu mavzu — xatolarning turli ko'rinishlarini tanib olish va ularni tizimli tarzda topib tuzatish — har qanday sifatli ish (hujjat, dastur, hisobot) yaratishning ajralmas qismidir.""",

("9-sinf", 16): """Grafik va xaritalar mavzusi sonli ma'lumotlarni vizual (ko'rinadigan) tarzda tasvirlashning turli usullarini chuqur o'rgatadi. To'g'ri diagramma turini tanlash — ma'lumotni tushunarli qilib ko'rsatishning kaliti hisoblanadi, chunki har bir diagramma turi ma'lum bir ma'lumot xarakteriga mos keladi.

Ustunli diagramma — turli toifalarni solishtirish uchun ideal (masalan turli fanlarga ajratilgan vaqt). Chiziqli diagramma — vaqt o'tishi bilan o'zgarishni ko'rsatish uchun qulay (masalan oylik harorat o'zgarishi). Doiraviy (pirog) diagramma esa butunning qismlarga bo'linishini foizlarda ko'rsatadi (masalan byudjetning qaysi qismi qanday xarajatga ketishi).

Diagrammaning har bir qismi o'z vazifasiga ega: sarlavha diagrammaning nima haqida ekanini bildiradi, o'qlar (axis) o'lchov birliklarini ko'rsatadi, afsona (legend) esa turli ranglar nimani anglatishini tushuntiradi. Bu elementlarsiz diagramma tushunarsiz bo'lib qoladi.

Ikkilamchi o'q (secondary axis) — bir diagrammada ikki xil o'lchamdagi ma'lumotni (masalan harorat gradusda va yog'ingarchilik millimetrda) birgalikda ko'rsatish kerak bo'lganda ishlatiladi, chunki ular turli shkalada o'lchanadi va bitta o'qqa sig'dirib bo'lmaydi.

Trend (moyillik) tahlili — vaqt davomida to'plangan ma'lumotning umumiy yo'nalishini (ko'tarilish, tushish yoki barqarorlik) aniqlash. Bu tahlil kelajakni bashorat qilishda yoki qaror qabul qilishda foydali, masalan xarajatlarning oshib borayotganini erta payqash imkonini beradi.

Bu mavzu — ma'lumotni to'g'ri diagramma orqali "hikoya qilib berish" san'ati — statistika va ma'lumotlar tahlili sohasining muhim asosidir.""",

("9-sinf", 17): """Hujjatlar bilan ishlash mavzusi matn muharriri imkoniyatlaridan foydalanib professional darajadagi hujjat tayyorlashni chuqur o'rgatadi. Sahifa maketi elementlari — hoshiya (chekka bo'shliq), kolontitul (ustlavha/ostlavha) va sahifa yo'nalishi — hujjatning umumiy tuzilishini belgilaydi.

Jadval loyihalash — ma'lumotlarni qator va ustunlarga tartibli joylashtirish, masalan haftalik dars jadvali. To'g'ri loyihalangan jadval ma'lumotni tez va oson tushunish imkonini beradi, xaotik joylashtirilgan ma'lumot esa chalkashlik keltirib chiqaradi.

Pochta orqali birlashtirish (mail merge) — bir xil shablon xatni ko'p odamga, har biriga shaxsiylashtirilgan ma'lumot (ism, sana) bilan avtomatik yuborish texnologiyasi. Masalan, 100 kishiga taklifnoma yuborish kerak bo'lsa, har birining ismini qo'lda yozish o'rniga, ma'lumotlar ro'yxati va shablon birlashtirilib, avtomatik ravishda 100 ta shaxsiylashtirilgan xat yaratiladi.

Ustunli hujjat maketi — gazeta yoki jurnal uslubidagi, matnni bir necha vertikal ustunga bo'lgan tuzilma, bu o'qishni tezlashtiradi va professional ko'rinish beradi.

Muqova maydoni (gutter) — kitob yoki broshyura kabi tikiladigan hujjatlarda, tikish joyi uchun qo'shimcha bo'sh joy qoldirish, aks holda tikilgan qism matnni "yeb qo'yishi" mumkin.

Bu bilimlar — sahifa tuzilishi, jadval, mail merge va maxsus maketlash usullari — real hayotda professional hisobot, kitobcha yoki ommaviy xat-xabar tayyorlashda keng qo'llaniladi va zamonaviy ofis ishining muhim qismini tashkil etadi.""",

("9-sinf", 18): """Ma'lumotlarni boshqarish mavzusi ma'lumotlar bazasi asoslarini yanada chuqur — relyatsion (bog'langan jadvallar) tizimlar darajasida o'rgatadi. Oddiy faylli baza (bitta katta jadval)dan farqli o'laroq, relyatsion baza ma'lumotni bir necha bog'langan jadvalga bo'lib saqlaydi, bu esa takrorlanishни kamaytiradi va ma'lumot izchilligini oshiradi.

Masalan, kutubxona bazasida "Kitoblar" va "Mualliflar" alohida jadvallarda saqlansa, bir muallifning bir necha kitobi bo'lsa ham, muallif ma'lumoti FAQAT BIR MARTA yoziladi, kitoblar jadvalida esa unga "havola" qilinadi. Bu — ma'lumotlar bazasi loyihalashning muhim tamoyili.

Ma'lumotlarni saralash va qidirish — katta hajmdagi ma'lumot orasidan kerakli qismini tez topish imkonini beradigan asosiy amallar. Saralash ma'lumotni tartibga soladi (masalan alifbo bo'yicha), qidirish (filtrlash) esa faqat ma'lum shartga mos yozuvlarni ajratib ko'rsatadi.

GIGO tamoyili ("Garbage In, Garbage Out" — kirishda axlat, chiqishda axlat) — agar ma'lumotlar bazasiga noto'g'ri ma'lumot kiritilsa (masalan yosh o'rniga ism yozilsa), undan olinadigan har qanday hisobot yoki tahlil ham noto'g'ri bo'ladi. Shuning uchun ma'lumot kiritishda aniqlik va tekshiruv juda muhim.

Hisobot (report) — ma'lumotlar bazasidan olingan, muayyan savolga javob beruvchi, tushunarli tarzda taqdim etilgan xulosa. Masalan "eng ko'p o'qilgan 5 kitob" hisoboti — katta ma'lumotlar to'plamidan foydali xulosa chiqarish imkonini beradi.

Bu mavzu — ma'lumotlarni tizimli, takrorlanishsiz va ishonchli tarzda saqlash hamda ulardan foydali xulosalar chiqarish — zamonaviy axborot tizimlarining yuragi hisoblanadi.""",

("9-sinf", 19): """Taqdimot mavzusi ta'sirchan va professional taqdimot (prezentatsiya) tayyorlash hamda uni namoyish etish mahoratini chuqur o'rgatadi. Yaxshi taqdimot tasodifan yaratilmaydi — u aniq reja, tuzilma va mashq natijasida yuzaga keladi.

Taqdimot rejasi — har bir slaydda nima bo'lishini oldindan belgilash. Yaxshi taqdimotda har bir slayd bitta asosiy g'oyaga bag'ishlanadi, ortiqcha ma'lumot bilan "to'ldirilmaydi". Bu tomoshabinning diqqatini har safar bitta muhim fikrga jamlash imkonini beradi.

Master-slayd (asosiy shablon) — barcha slaydlarda takrorlanadigan elementlarni (shrift, rang, logotip, sahifa raqami) bir marta belgilab qo'yish, shunda har bir yangi slaydda bu elementlar avtomatik takrorlanadi. Bu vaqtni tejaydi va taqdimotning izchil ko'rinishini ta'minlaydi.

Obyektlarni joylashtirish (matn, tasvir, sarlavha) — slayd maketini rejalashtirishning muhim qismi. Yaxshi joylashtirilgan slayd ko'zga yoqimli va ma'lumotni mantiqiy tartibda taqdim etadi, tartibsiz joylashtirilgan elementlar esa chalkashlik va professional bo'lmagan taassurot qoldiradi.

Auditoriyaga mos taqdimot uslubi — bolalar uchun yorqin ranglar va katta matn, kattalar/mutaxassislar uchun esa jiddiy ranglar va batafsil ma'lumot mosroq. Bir xil taqdimotni turli auditoriya uchun moslashtira olish — muhim ko'nikma.

Taqdimotni sinash (rehearsal) — namoyish etishdan oldin matn hajmi, shrift o'lchami, rang kontrasti va umumiy vaqtni tekshirish, bu orqali taqdimot kunida kutilmagan muammolarning oldi olinadi. Bu mavzu — vizual dizayn bilan og'zaki mahoratni birlashtirib, ta'sirchan taqdimot yaratish san'atini o'rgatadi.""",

("9-sinf", 20): """Ma'lumotlar tahlili mavzusi elektron jadvallarda murakkab formula, funksiya va diagrammalar yordamida chuqur tahlil qilishni o'rgatadi. Ma'lumot modeli — real hayotiy vaziyatni (masalan uy byudjeti) elektron jadval orqali tasvirlash uchun, qanday ma'lumotlar kerak va ular qanday bog'langanligini aniqlash jarayoni.

Formulalar rejasi — model uchun kerak bo'ladigan hisob-kitoblarni (jami xarajat, qolgan mablag', foiz nisbati) oldindan belgilash. Bu reja keyinchalik haqiqiy formulalarni yozishda yo'l-yo'riq bo'lib xizmat qiladi, xatoliklarning oldini oladi.

Sinov qiymatlari (test values) — yaratilgan modelni turli xil kirish ma'lumotlari (masalan turli daromad darajalari) bilan sinab ko'rish, natijalar mantiqan to'g'ri chiqayotganini tasdiqlash jarayoni. Bu dasturiy ta'minot sinovidagi kabi, elektron jadval modelining ham to'g'riligini tekshirish usuli.

Ma'lumotlarni saralash va filtrlash — katta hajmdagi jadvaldan (masalan butun sinf baholari) faqat kerakli qismini (masalan eng yuqori 5 ta natija yoki muvaffaqiyatsiz natijalar) ajratib olish imkonini beradi. Bu katta ma'lumotlar to'plamida tezkor tahlil qilish uchun zarur.

Katta jadvalni ko'rish qulayligi uchun maxsus usullar mavjud: sarlavha qatorini "muzlatish" (freeze) — pastga aylantirilganda ham sarlavha ko'rinib turishi, va keraksiz ustunlarni vaqtincha yashirish. Bu usullar katta hajmdagi ma'lumot bilan ishlashni sezilarli darajada osonlashtiradi.

Bu mavzu — elektron jadvalni oddiy hisoblagichdan chuqur tahlil vositasiga aylantirish — real biznes va ilmiy tahlilda keng qo'llaniladigan muhim ko'nikmadir.""",

("9-sinf", 21): """Veb-saytlar yaratish mavzusi HTML asoslari yordamida oddiy veb-sahifa tuzishni va uni tushunishni chuqur o'rgatadi. Veb-sahifa uch asosiy "qatlam"dan iborat: kontent (HTML — matn va tuzilma), taqdimot (CSS — ko'rinish, ranglar, shriftlar) va funksionallik (JavaScript — interaktivlik). Har bir qatlam o'z vazifasiga javob beradi, bu esa veb-sahifani tartibli va boshqarish oson qiladi.

Sodda veb-sahifa maketi — sarlavha (header), navigatsiya menyusi, asosiy matn (content), rasm va pastki qism (footer)dan tashkil topadi. Bu tuzilma deyarli barcha veb-saytlarda takrorlanadi, chunki u foydalanuvchiga tanish va tushunarli tajriba beradi.

Navigatsiya sxemasi (sayt xaritasi) — bir necha sahifadan iborat veb-sayt uchun, sahifalar orasidagi havolalarni oldindan rejalashtirish. Masalan "Bosh sahifa", "Men haqimda" va "Aloqa" sahifalari orasida qanday o'tish mumkinligini chizib ko'rsatish, saytni loyihalashning muhim bosqichi.

URL (veb-manzil) va IP-manzil orasidagi farq — URL inson uchun o'qish oson bo'lgan manzil (masalan google.com), IP-manzil esa kompyuterlar tushunadigan raqamli manzil. DNS (Domain Name System) xizmati URL'ni avtomatik IP-manzilga aylantiradi, bu jarayon foydalanuvchiga ko'rinmaydi, lekin har bir veb-sahifaga kirishda sodir bo'ladi.

Veb-saytni sinovdan o'tkazish — chop etishdan oldin barcha havolalar ishlayotganini, sahifa turli qurilma o'lchamlarida (telefon, kompyuter) to'g'ri ko'rinayotganini va imlo xatolari yo'qligini tekshirish. Bu bosqich veb-saytning professional va ishonchli ko'rinishini ta'minlaydi.

Bu mavzu — internetning "qanday ishlashini" tushunish va o'z veb-sahifasini yaratish — zamonaviy raqamli savodxonlikning eng muhim ko'nikmalaridan biridir.""",

("10-11-sinf", 1): """Bilimlar bazasi mavzusi ma'lumot, axborot va bilim tushunchalari orasidagi nozik, lekin muhim farqlarni chuqur tahlil qiladi. Ma'lumot (data) — bu xom, hali ishlov berilmagan raqam yoki fakt (masalan "25"). Axborot (information) — bu ma'lumotga kontekst berilganda paydo bo'ladi (masalan "harorat 25 daraja"). Bilim (knowledge) esa axborotni tushunish va undan xulosa yoki qaror chiqarish natijasida shakllanadi (masalan "25 daraja — issiq kiyim kerak emas").

Bu uch bosqichli zanjirni tushunish — zamonaviy axborot asridagi eng muhim tushunchalardan biri, chunki ko'plab tizimlar (sun'iy intellektdan tortib oddiy hisobotgacha) aynan shu jarayon — xom ma'lumotdan foydali bilimga o'tish — asosida quriladi.

Statik manba — vaqt o'tishi bilan o'zgarmaydigan axborot manbai (masalan bosma kitob, chop etilgan ensiklopediya). Dinamik manba esa muntazam yangilanib turadi (masalan yangiliklar sayti, ijtimoiy tarmoq). Har ikkalasining o'z afzalliklari bor: statik manba barqaror va tekshirilgan, dinamik manba esa dolzarb va yangi.

Manba tanlashda ishonchlilik va tezkorlik o'rtasida muvozanat topish kerak — tezkor yangilanadigan manbalar ko'pincha yetarlicha tekshirilmagan bo'lishi mumkin, shuning uchun muhim qarorlar (masalan sog'liq bo'yicha) uchun bir necha manbani solishtirib ko'rish tavsiya etiladi.

Bir kunlik shaxsiy axborot manbalari auditi — kun davomida foydalanilgan barcha manbalarni (darslik, sayt, ilova) ro'yxatga olish va ularni statik/dinamik toifasiga ajratish orqali, o'z axborot iste'moli odatlarini anglash mumkin. Bu — zamonaviy "axborot savodxonligi"ning muhim mashqidir, u orqali odam qaysi ma'lumotga qanchalik ishonish kerakligini ongli tarzda baholay oladi.""",

("10-11-sinf", 2): """Texnik va dasturiy ta'minot mavzusi kompyuter tizimining ikki asosiy qismi — apparat (hardware) va dasturiy (software) ta'minot orasidagi chuqur o'zaro bog'liqlikni tahlil qiladi. Apparat ta'minot — jismonan ushlab ko'rish mumkin bo'lgan qismlar (protsessor, xotira, disk), dasturiy ta'minot esa bu jismoniy qismlarga "nima qilish kerakligini" aytuvchi ko'rsatmalar to'plami.

Dasturiy ta'minot ikki katta toifaga bo'linadi: tizimli dasturiy ta'minot (operatsion tizim — Windows, macOS, Linux kabi, u apparat va boshqa dasturlar orasidagi "vositachi") va amaliy dasturiy ta'minot (foydalanuvchi to'g'ridan-to'g'ri ishlatadigan dasturlar — matn muharriri, brauzer, o'yinlar).

Turli foydalanuvchi turlari uchun turli apparat konfiguratsiyasi kerak bo'ladi: dizayner uchun kuchli video karta va katta xotira, dasturchi uchun tez protsessor va ko'p RAM, oddiy ofis xodimi uchun esa o'rtacha konfiguratsiya yetarli. To'g'ri konfiguratsiyani tanlash — vazifaga mos xarajat va samaradorlik nisbatini topish demakdir.

Dasturiy ta'minotni muntazam yangilab turish nafaqat yangi funksiyalar, balki XAVFSIZLIK tuzatishlarini ham o'z ichiga oladi — eski, yangilanmagan dastur zararli dasturlar uchun "ochiq eshik" bo'lib qolishi mumkin. Shuning uchun avtomatik yangilanishni yoqib qo'yish tavsiya etiladi.

Apparat-dasturiy ta'minot mos kelishi — muhim amaliy masala: zamonaviy, resurs talab qiluvchi dastur eski, past quvvatli kompyuterda sekin ishlaydi yoki umuman ishlamaydi. Har bir dastur o'zining "minimal talablari"ga ega, va kompyuter shu talablarga javob berishi kerak. Bu mavzu — texnologiyani tanlashda apparat va dasturiy ta'minotni birgalikda ko'rib chiqish zarurligini o'rgatadi.""",

("10-11-sinf", 3): """Kuzatuv va boshqaruv mavzusi sensorlar yordamida atrof-muhitni avtomatik kuzatish va boshqarish tizimlarini chuqur tahlil qiladi. Sensor — bu atrof-muhitdagi fizik o'zgarishni (harorat, yorug'lik, harakat, bosim) aniqlab, uni elektron signalga aylantiruvchi qurilma. Zamonaviy dunyoda sensorlar deyarli har qanday "aqlli" qurilmaning yuragi hisoblanadi.

Faqat kuzatuvchi tizim (masalan oddiy termometr) atrof-muhit haqida ma'lumot beradi, lekin hech narsani o'zgartirmaydi. Kuzatuv+boshqaruv tizimi (masalan termostat) esa sensordan olingan ma'lumotga qarab AVTOMATIK harakat qiladi — masalan harorat pasaysa, isitgichni o'zi yoqadi. Bu farqni tushunish — avtomatlashtirilgan tizimlarning asosiy mantig'ini anglash demakdir.

Avtoturargoh to'sig'i — kuzatuv va boshqaruv tizimining oddiy, kundalik misoli: sensor mashinani aniqlaydi (kuzatuv), so'ngra tizim to'siqni avtomatik ochadi (boshqaruv). Bu jarayonni bosqichma-bosqich tahlil qilish — sensor signali qanday qarorga aylanishini tushunishga yordam beradi.

Sanoat sharoitida sensorlar xavfsizlikni ta'minlashda hayotiy ahamiyatga ega — masalan kimyoviy zavodda gaz oqimi yoki harorat me'yoridan oshib ketsa, tizim avtomatik ogohlantiruvchi signal beradi yoki jarayonni to'xtatadi, bu insonlar hayotini xavfdan asraydi.

"Aqlli uy" tushunchasi — turar joyda bir necha sensor asosidagi avtomatlashtirish (harorat, yorug'lik, xavfsizlik) birlashtirilib, uy egasi hayotini qulayroq va xavfsizroq qilishni anglatadi. Bu mavzu — kelajakning "aqlli" texnologiyalari qanday ishlashini tushunish uchun zamin yaratadi, chunki sensorlar asosidagi avtomatlashtirish tibbiyotdan qishloq xo'jaligigacha ko'plab sohalarda tobora keng qo'llanilmoqda.""",

("10-11-sinf", 4): """Elektron xavfsizlik, salomatlik va xavfsizlik mavzusi raqamli dunyoda o'zini har tomonlama himoya qilish bo'yicha chuqur bilim beradi. Elektron xavfsizlik ijtimoiy tarmoqlarda shaxsiy ma'lumotni himoya qilishdan boshlanadi — telefon raqami, uy manzili va moliyaviy ma'lumotlarni faqat ishonchli, zaruriy holatlarda ulashish tavsiya etiladi.

Ekran vaqtining ko'zga va mushak-suyak tizimiga ta'siri jiddiy sog'liq masalasi hisoblanadi. Uzoq muddat ekranga tikilish ko'z charchashi (digital eye strain)ga olib kelishi mumkin, buning oldini olish uchun "20-20-20 qoidasi" tavsiya etiladi: har 20 daqiqada, 20 soniya davomida, 20 fut (taxminan 6 metr) uzoqlikdagi narsaga qarash.

Jismoniy xavfsizlik — kompyuter xonasidagi kabellar, elektr rozetkalari va jihozlarning to'g'ri joylashuvini tekshirish, bu baxtsiz hodisalarning oldini oladi. Ergonomik ish joyi (to'g'ri stul balandligi, monitor masofasi) uzoq muddatli sog'liq muammolarining oldini oladi.

Fishing (firibgar) xabarlarni tanib olish — zamonaviy elektron xavfsizlikning eng muhim ko'nikmalaridan biri. Firibgar xabarlar odatda shoshiltiruvchi til, shubhali havolalar va imlo xatolariga ega bo'ladi, va ular ishonchli tashkilot (bank, ijtimoiy tarmoq) nomidan yuborilgandek ko'rinadi. Bunday xabarlarga shaxsiy ma'lumot yoki parol hech qachon yuborilmasligi kerak.

Sog'lom ish tartibi — muntazam tanaffuslar, ko'z mashqlari va jismoniy harakatni o'z ichiga olgan kunlik reja — uzoq muddatda sog'liqni saqlashning kaliti hisoblanadi. Bu mavzu texnologiyadan foydalanishning ijobiy tomonlarini saqlab qolgan holda, uning salbiy ta'sirlarini minimallashtirish strategiyalarini o'rgatadi.""",

("10-11-sinf", 5): """Raqamli tengsizlik mavzusi texnologiyaga teng bo'lmagan kirish imkoniyati muammosini ijtimoiy-iqtisodiy nuqtai nazardan chuqur tahlil qiladi. Raqamli tengsizlik (digital divide) — bu turli guruhlar (shahar/qishloq, boy/kambag'al, turli mamlakatlar) orasida internet va texnologiyaga kirish imkoniyatidagi farqni bildiradi.

Bu tafovutning sabablari xilma-xil: infratuzilma yetishmasligi (qishloq hududlarda internet kabel yo'qligi), moliyaviy imkoniyat (qurilma va internet narxi baland bo'lishi), va raqamli savodxonlik darajasi (texnologiyadan qanday foydalanishni bilmaslik).

Raqamli tengsizlikning oqibatlari jiddiy: internetga kirish imkoniyati past bo'lgan insonlar zamonaviy ta'lim resurslaridan (onlayn kurslar, elektron darsliklar) foydalana olmaydi, bu esa ularning bilim olish imkoniyatini cheklaydi. Xuddi shunday, ko'plab zamonaviy ish o'rinlari raqamli ko'nikmalarni talab qiladi, va bu ko'nikmalarga ega bo'lmagan odamlar mehnat bozorida qoloqlashib qolishi mumkin.

Mamlakat yoki mintaqa darajasida raqamli tengsizlikni tahlil qilish — internetdan foydalanish foizini turli hududlar (shahar/qishloq) yoki yosh guruhlari orasida solishtirish orqali amalga oshiriladi. Bunday tahlil davlat siyosatini shakllantirishda muhim rol o'ynaydi.

Tafovutni kamaytirish uchun bir necha yechim mavjud: jamoat internet markazlari (kutubxona yoki maktablarda bepul internet), arzon qurilmalar dasturlari, va raqamli savodxonlik bo'yicha o'quv kurslari. Internet tezligi bilan foydalanuvchi tajribasi (video ko'rish sifati, sahifa yuklanish tezligi) orasidagi bog'liqlikni tushunish — nima uchun sifatli infratuzilma muhimligini yanada aniq ko'rsatadi. Bu mavzu — texnologiyaning barcha uchun teng imkoniyat yaratishi kerakligi haqidagi muhim ijtimoiy masalani ko'tarib chiqadi.""",

("10-11-sinf", 6): """Tarmoqlardan foydalanish mavzusi kompyuter tarmoqlarining amaliy, kundalik hayotdagi qo'llanilishini chuqur ko'rib chiqadi. Fayl almashish — tarmoqning eng keng tarqalgan qo'llanilishlaridan biri: umumiy tarmoq papkasi, bulutli xizmat (Google Drive kabi) yoki elektron pochta orqali fayllarni boshqalar bilan bo'lishish mumkin, har birining o'z afzalliklari bor.

Masofaviy ishlash (remote work) — uydan turib ish yoki maktab tarmog'idagi resurslarga xavfsiz ulanish imkoniyatini bildiradi. Bu odatda VPN (Virtual Private Network) texnologiyasi orqali amalga oshiriladi, u masofaviy ulanishni shifrlangan, xavfsiz "tunnel" orqali ta'minlaydi, hatto ochiq internet orqali bo'lsa ham.

Bulutli xizmatlarning mahalliy saqlashga nisbatan afzalliklari ko'p: istalgan qurilmadan kirish imkoniyati, avtomatik zaxira nusxalash, va bir necha odam bilan bir vaqtda hamkorlikda ishlash imkoniyati. Biroq bulutli xizmat internetga bog'liqligi va uzoq muddatli obuna to'lovi talab qilishi mumkinligi kabi kamchiliklarga ham ega.

Tarmoq resurslarini bo'lishish — masalan bitta printerni ofisdagi bir nechta kompyuter birgalikda ishlatishi — tarmoqning amaliy iqtisodiy foydasini ko'rsatadi, chunki har bir kompyuterga alohida printer sotib olish shart emas.

Xavfsiz masofaviy kirish rejasi tuzishda VPN ishlatish, kuchli parol siyosati o'rnatish va faqat zarur xodimlarga kirish huquqini berish каби choralar muhim. Bu mavzu — tarmoqlarning nazariy tuzilishidan amaliy, real hayotiy foydalanish stsenariylariga o'tishni, va bu jarayonda xavfsizlikni saqlab qolish zarurligini o'rgatadi.""",

("10-11-sinf", 7): """Ekspert tizimlar mavzusi sun'iy intellektning dastlabki va muhim shakli bo'lgan ekspert tizimlarning tuzilishi va ishlash mexanizmini chuqur tahlil qiladi. Ekspert tizim — bu ma'lum bir tor soha (masalan tibbiy tashxis yoki qishloq xo'jaligi) bo'yicha inson mutaxassisining bilimini "raqamlashtirib", undan xulosa chiqaruvchi dastur.

Ekspert tizimning ikki asosiy qismi bor: bilim bazasi (knowledge base) — sohaga oid faktlar va "agar-unda" qoidalari to'plami, va xulosa chiqarish mexanizmi (inference engine) — foydalanuvchi javoblariga qarab bilim bazasidagi qoidalarni qo'llab, yakuniy xulosaga kelish tizimi.

Xulosa chiqarish jarayoni bosqichma-bosqich amalga oshadi: tizim foydalanuvchiga savol beradi, javobga qarab keyingi mos qoidani tanlaydi, va shu tarzda savol-javob zanjiri orqali oxir-oqibat aniq xulosaga (masalan mumkin bo'lgan tashxis) yetib keladi. Bu jarayon "qaror daraxti" ko'rinishida tasvirlanishi mumkin.

Ekspert tizim va inson mutaxassisi orasidagi taqqoslash qiziq xulosalarga olib keladi: ekspert tizim charchamaydi, bir vaqtning o'zida ko'plab so'rovga javob bera oladi va izchil natija beradi, lekin inson mutaxassisiga xos moslashuvchanlik, ijodkorlik va murakkab, "qoidaga sig'maydigan" holatlarni tushunish qobiliyatiga ega emas.

O'z ekspert tizimini loyihalash — tanlangan tor sohada (masalan "qaysi sport turi menga mos") savollar, qoidalar va mumkin bo'lgan xulosalarni oldindan rejalashtirishni talab qiladi. Bu mavzu — zamonaviy sun'iy intellekt tizimlarining ildizlarini, va murakkab bilimni tizimli qoidalarga aylantirish jarayonini chuqur tushunishga yordam beradi.""",

("10-11-sinf", 8): """Elektron jadvallar mavzusi murakkab formula, funksiya va shartli formatlashdan foydalanib, elektron jadvalda chuqur ma'lumot tahlilini o'rgatadi. IF (agar) funksiyasi — elektron jadvaldagi eng kuchli vositalardan biri, u ma'lum shart bajarilsa bir natija, bajarilmasa boshqa natija ko'rsatish imkonini beradi (masalan "agar ball 60 dan katta bo'lsa 'o'tdi', aks holda 'qoldi'").

SUM (yig'indi) va AVERAGE (o'rtacha) — eng ko'p ishlatiladigan statistik funksiyalar bo'lib, katta hajmdagi sonlar ustida tez hisob-kitob qilish imkonini beradi. Bu funksiyalar qo'lda hisoblashga qaraganda ancha tez va xatosiz natija beradi, ayniqsa yuzlab-minglab qiymat bilan ishlaganda.

Shartli formatlash (conditional formatting) — katakning qiymatiga qarab uning tashqi ko'rinishini (rang, shrift) avtomatik o'zgartirish, masalan past ballarni qizil, yuqori ballarni yashil rangda ko'rsatish. Bu vizual signal orqali ma'lumotni tezda tahlil qilish imkonini beradi, raqamlarni birma-bir o'qishga hojat qolmaydi.

Ko'p shartli IF formulasi — bir nechta IF funksiyasini ichma-ich joylashtirib, bir nechta natija variantini (masalan A, B, C, D baholarini) hisoblash imkonini beradi. Bu — "qaror daraxti" mantig'ining elektron jadvaldagi amaliy ko'rinishi.

To'liq tahlil jadvali yaratish — jami, o'rtacha, eng yuqori va eng past qiymatlarni bir vaqtda hisoblab, shartli formatlash bilan boyitilgan, professional darajadagi ma'lumot tahlili hisobotini yaratishni anglatadi. Bu mavzu — elektron jadvalni oddiy hisob-kitob vositasidan kuchli tahlil vositasiga aylantiradigan bilimlarni o'rgatadi, bu ko'nikmalar moliya, ta'lim va biznesning ko'plab sohalarida talab qilinadi.""",

("10-11-sinf", 9): """Ma'lumotlar bazasi va fayl konsepsiyalari mavzusi relyatsion ma'lumotlar bazasining chuqur tuzilishini — jadvallar orasidagi bog'lanishlarni va so'rov tuzishni professional darajada o'rgatadi. Relyatsion baza g'oyasi — ma'lumotni bir necha bog'langan jadvalga bo'lib saqlash, bu takrorlanishни kamaytiradi va ma'lumot izchilligini ta'minlaydi.

Birlamchi kalit (primary key) — har bir jadvaldagi yozuvni noyob tarzda aniqlaydigan maydon (masalan o'quvchi ID raqami). Tashqi kalit (foreign key) esa bir jadvaldagi maydonni boshqa jadvalning birlamchi kaliti bilan bog'laydi, masalan "O'quvchilar" jadvalidagi "sinf ID" maydoni "Sinflar" jadvalining birlamchi kalitiga ishora qiladi.

So'rov (query) tuzish — ma'lumotlar bazasidan ma'lum shartga mos ma'lumotni ajratib olish san'ati. Murakkab so'rovlar bir necha jadvaldan ma'lumotni birlashtirib, foydali xulosa chiqarishga imkon beradi — masalan "ma'lum sinfdagi barcha o'quvchilarning o'rtacha bahosi" kabi savolga javob berish.

Ma'lumotlar takrorlanishi muammosi — agar bog'lovchi jadvallar ishlatilmasa (oddiy faylli baza), bir xil ma'lumot (masalan sinf nomi) har bir o'quvchi qatorida qayta-qayta yozilishi kerak bo'ladi. Bu nafaqat joy isrofi, balki ma'lumotni yangilashda xatolik xavfini ham oshiradi (masalan sinf nomi o'zgarganda, uni BARCHA qatorlarda yangilash kerak bo'ladi).

Mini ma'lumotlar bazasi loyihasi — bir necha bog'langan jadval (masalan O'quvchilar, Sinflar, Baholar)dan iborat tizimni ER diagramma (Entity-Relationship diagram) orqali vizual tasvirlash, bu murakkab tizimlarni loyihalashning standart usuli hisoblanadi. Bu mavzu — zamonaviy dasturiy tizimlarning "orqa tomonida" qanday ma'lumotlar saqlanishini chuqur tushunishga yordam beradi.""",

("10-11-sinf", 10): """Tovush va videoni tahrirlash mavzusi audio va video fayllar bilan professional darajada ishlashni o'rgatadi. Audio kesish — uzun yozuvdan faqat kerakli qismini ajratib olish jarayoni, bu podkast, video yoki musiqiy loyihalarda keng qo'llaniladi. Aniq boshlanish va tugash nuqtalarini belgilash — tovush sifatini saqlab qolgan holda kerakli qismni ajratib olishning kaliti.

Video kesish va birlashtirish — bir necha qisqa video parchasini (masalan kirish, asosiy qism, xulosa) mantiqiy ketma-ketlikda birlashtirish jarayoni. Har bir parcha orasidagi o'tish silliq va tabiiy bo'lishi uchun, kesish nuqtalarini diqqat bilan tanlash kerak.

Fon musiqasi va asosiy ovoz (nutq) orasidagi balans — video sifatining muhim ko'rsatkichi. Agar fon musiqasi juda baland bo'lsa, u asosiy nutqni "bosib qo'yadi" va tomoshabin uchun tushunish qiyinlashadi. Professional videolarda odatda nutq ovozi fon musiqasidan sezilarli darajada balandroq bo'ladi.

Effekt va o'tishlar (transitions) — video bo'limlari orasidagi vizual o'zgarishlar (so'nish, sirg'alish kabi), ular videoga professional va silliq ko'rinish beradi. Biroq har bir o'tish o'ziga xos "kayfiyat" yaratadi, shuning uchun kontekstga mos effektni tanlash muhim — masalan jiddiy mavzuda o'yinqaroq o'tish effekti mos kelmaydi.

To'liq video tahrirlash rejasi — kesish, birlashtirish, musiqa va effektlarni bitta izchil vaqt chizig'i (timeline) asosida rejalashtirishni anglatadi. Bu mavzu — zamonaviy raqamli kontent yaratishning texnik asoslarini o'rgatadi, bu ko'nikmalar ta'lim, marketing va ijtimoiy tarmoqlar uchun kontent yaratishda keng talab qilinadi.""",

("10-11-sinf", 11): """Yangi texnologiyalar mavzusi sun'iy intellekt, virtual reallik va boshqa zamonaviy texnologiyalarning jamiyatga ta'sirini chuqur tahlil qiladi. Sun'iy intellekt (SI) — kompyuterlarga inson kabi "fikrlash" va qaror qabul qilish qobiliyatini berishga qaratilgan texnologiya, u bugungi kunda ovozli yordamchilar, tavsiya tizimlari (masalan video platformalardagi "sizga tavsiya etamiz" funksiyasi) kabi ko'plab kundalik ilovalarda ishlatiladi.

Virtual reallik (VR) foydalanuvchini to'liq raqamli muhitga "cho'ktiradi" (masalan maxsus ko'zoynak orqali butunlay boshqa dunyoga tushib qolgandek tuyg'u), kengaytirilgan reallik (AR) esa real dunyo ustiga raqamli ma'lumot qo'shadi (masalan telefon kamerasi orqali ko'chada turgan binoga qo'shimcha ma'lumot chiqishi). Bu ikki texnologiya turli sohalarda — ta'lim, o'yin, tibbiyot — qo'llaniladi.

Har qanday yangi texnologiya foyda va xavf tomonlariga ega. Masalan yuzni tanish tizimi xavfsizlikni oshiradi, lekin shaxsiy hayotga aralashish (privacy) muammosini ham keltirib chiqaradi. Yangi texnologiyani baholashda faqat uning imkoniyatlarini emas, balki ijtimoiy-axloqiy oqibatlarini ham ko'rib chiqish muhim.

Kelajak texnologiyasi haqida fikr yuritish — hozirgi trendlarga asoslanib, 10 yildan keyin hayotimizni qanday o'zgartirishi mumkinligini bashorat qilish mashqi. Bu jarayon tanqidiy va ijodiy fikrlashni birlashtirishni talab qiladi.

Bu mavzu — texnologik taraqqiyotni passiv kuzatuvchi sifatida emas, balki uning imkoniyatlari va xavflarini ongli baholovchi faol fikrlovchi sifatida yondashishga o'rgatadi, bu zamonaviy raqamli fuqarolikning muhim qismidir.""",

("10-11-sinf", 12): """Axborot texnologiyalarining o'rni va jamiyatdagi ta'siri mavzusi AKTning kasblar, ta'lim va kundalik hayotga ta'sirini yanada chuqur, tanqidiy nuqtai nazardan tahlil qiladi. AKT ta'sirida ko'plab an'anaviy kasblar o'zgardi yoki yo'qoldi (masalan qo'lda hisob yurituvchi buxgalter), lekin shu bilan birga raqamli marketing, dasturlash, kiberxavfsizlik kabi butunlay yangi kasblar paydo bo'ldi.

Ta'limdagi o'zgarishlar sezilarli: masofaviy ta'lim va elektron darsliklar geografik chegaralarni yo'qotdi, bu ayniqsa uzoq hududlardagi yoki maxsus ehtiyojga ega o'quvchilar uchun katta imkoniyat. Biroq bu o'zgarish real muloqot va amaliy tajribaning kamayishi kabi yangi muammolarni ham keltirib chiqardi.

AKTning ijobiy va salbiy ta'sirlarini muvozanatli baholash muhim: ijobiy tomondan — tezkor aloqa, ma'lumotga oson kirish, ish samaradorligining oshishi; salbiy tomondan — ekran vaqtining ko'payishi, ijtimoiy tarmoqqa qaramlik xavfi, va shaxsiy ma'lumotlar xavfsizligi masalalari.

Oilaviy hayotga ta'siri ham sezilarli — aloqa (video qo'ng'iroqlar orqali uzoqdagi qarindoshlar bilan bog'lanish), xarid qilish (onlayn do'konlar) va bilim olish (onlayn kurslar) tarzi tubdan o'zgardi. Bu o'zgarishlarni shaxsiy tajriba orqali tahlil qilish — mavzuni real hayot bilan bog'lash imkonini beradi.

Kelajak bashorati — keyingi 10 yilda AKT jamiyatni yana qanday o'zgartirishi mumkinligi haqida, hozirgi trendlarga asoslangan holda, asoslangan taxmin qilish. Bu mavzu — texnologiyaning jamiyatga chuqur va ko'p qirrali ta'sirini tanqidiy tahlil qilish qobiliyatini rivojlantiradi, bu zamonaviy fuqaro uchun muhim fikrlash ko'nikmasidir.""",

("10-11-sinf", 13): """Tarmoqlar mavzusi kompyuter tarmoqlarining chuqur texnik tuzilishini — topologiyalar, protokollar va qurilmalarni professional darajada tahlil qiladi. Tarmoq topologiyasi — qurilmalarning bir-biriga qanday ulanganligini ko'rsatuvchi sxema. Yulduz (star) topologiyada barcha qurilmalar markaziy qurilmaga (masalan switch) ulanadi — bu ishonchli, chunki bitta qurilma buzilsa, faqat o'sha aloqa uziladi. Shina (bus) topologiyada esa barcha qurilmalar bitta umumiy kabelga ulanadi — bu sodda, lekin kabel buzilsa butun tarmoq ishdan chiqishi mumkin.

Protokollar — qurilmalar orasida ma'lumot almashish qoidalari to'plami. HTTP (HyperText Transfer Protocol) veb-sahifalarni ko'rish uchun, HTTPS esa uning xavfsiz, shifrlangan versiyasi (bank yoki shaxsiy ma'lumot kiritiladigan saytlarda ishlatiladi). FTP (File Transfer Protocol) esa fayllarni serverlar orasida ko'chirish uchun ishlatiladi.

Tarmoq qurilmalari orasidagi farq: router tarmoqlar orasida yo'l ko'rsatadi (masalan uy tarmog'ini internetga ulaydi), svich (switch) esa bir tarmoq ichidagi qurilmalarni bir-biriga ulaydi, modem esa raqamli signalni tarmoq kabeli orqali uzatish uchun signalga aylantiradi.

IP-manzil — internetga ulangan har bir qurilmaning noyob "raqamli manzili", MAC-manzil esa qurilmaning tarmoq kartasiga "zavoddan" berilgan, o'zgarmas noyob identifikatori. Ikkalasi ham qurilmani aniqlash uchun ishlatiladi, lekin turli darajada (IP — tarmoq darajasida, MAC — jismoniy qurilma darajasida).

Maktab kabi ko'p xonali muassasa uchun tarmoq topologiyasini loyihalash — turli xonalarni (kompyuter xonasi, kutubxona, ma'muriyat) samarali va ishonchli tarzda bog'lashni talab qiladi. Bu mavzu — internetning "orqa tomonida" qanday texnik tuzilma yotishini chuqur tushunishga yordam beradi.""",

("10-11-sinf", 14): """Loyiha boshqaruvi mavzusi har qanday murakkab ishni muvaffaqiyatli amalga oshirish uchun zarur bo'lgan rejalashtirish va boshqarish ko'nikmalarini o'rgatadi. Har bir loyiha (kichik tadbirdan tortib katta qurilishgacha) bajarilishi kerak bo'lgan aniq vazifalar ro'yxatidan boshlanadi.

Vazifalar ketma-ketligi — qaysi vazifa qaysinisidan OLDIN bajarilishi kerakligini aniqlash. Masalan, tadbir uchun joy band qilinmasdan turib, mehmonlarni taklif qilib bo'lmaydi. Bu bog'liqliklarni aniqlash — loyihaning real vaqt jadvalini tuzishning asosidir.

Resurs va muddat taqsimoti — har bir vazifaga kim mas'ul ekanini va uni bajarish uchun qancha vaqt kerakligini aniqlash. To'g'ri taqsimlangan resurslar loyihaning o'z vaqtida va sifatli bajarilishini ta'minlaydi.

Kritik yo'l (critical path) — loyihadagi eng uzun, kechiktirib bo'lmaydigan vazifalar zanjiri. Agar kritik yo'ldagi biror vazifa kechiksa, BUTUN loyiha kechikadi. Kritik bo'lmagan vazifalarda esa biroz "zaxira vaqt" (slack) bor — ular biroz kechiksa ham, loyihaning umumiy muddatiga ta'sir qilmaydi. Kritik yo'lni aniqlash — loyiha menejerining eng muhim vazifalaridan biri, chunki u qaysi vazifalarga eng ko'p e'tibor qaratish kerakligini ko'rsatadi.

To'liq loyiha rejasi — vazifalar, ketma-ketlik, resurslar va kritik yo'lni birlashtirgan, odatda Gantt diagrammasi (vaqt chizig'ida vazifalarni ko'rsatuvchi grafik) ko'rinishida taqdim etiladigan hujjat. Bu mavzu — nafaqat IT sohasida, balki har qanday murakkab tashabbusni (tadbir tashkil etishdan katta qurilishgacha) muvaffaqiyatli boshqarish uchun zarur bo'lgan universal ko'nikmalarni o'rgatadi.""",

("10-11-sinf", 15): """Tizimdan foydalanish sikli mavzusi yangi tizimni eskisi o'rniga qanday joriy etish mumkinligi bo'yicha to'rt asosiy strategiyani chuqur tahlil qiladi. To'g'ridan-to'g'ri (direct) usul — eski tizimni bir zumda o'chirib, yangisini darhol ishga tushirish. Bu eng tez, lekin eng xavfli usul, chunki agar yangi tizimda muammo chiqsa, orqaga qaytish imkoni yo'q.

Parallel usul — eski va yangi tizimni bir muddat BIRGALIKDA ishlatish, natijalarni solishtirib, yangi tizim to'g'ri ishlayotganiga ishonch hosil qilingandan keyingina eskisidan voz kechish. Bu usul xavfsiz, lekin ikkala tizimni bir vaqtda yuritish qo'shimcha resurs va vaqt talab qiladi.

Bosqichma-bosqich (phased) usul — yangi tizimni qismlarga bo'lib, asta-sekin joriy etish, masalan avval bitta bo'lim, keyin boshqa bo'limlarga o'tkazish. Pilot usul esa yangi tizimni avval kichik bir guruh yoki bo'limda sinab ko'rish, muvaffaqiyatli bo'lsa butun tashkilotga joriy etish.

Har bir usulning xavf darajasi turlicha: to'g'ridan-to'g'ri usul eng yuqori xavfli, parallel usul eng past xavfli, lekin eng qimmat va sekin. Tanlov tizimning muhimligi, tashkilotning resurslari va xavfga tayyorligiga bog'liq.

Maktabda yangi elektron kundalik tizimini joriy etish uchun eng mos usulni tanlash — real vaziyatga misol: agar xato jiddiy oqibatlarga olib kelmasa (masalan ba'zi ma'lumot vaqtincha ko'rinmasligi), bosqichma-bosqich yoki pilot usul yetarli bo'lishi mumkin. Bu mavzu — o'zgarishlarni boshqarishning muhim tamoyili: har qanday katta o'zgarish o'ylab, xavfni hisobga olgan holda amalga oshirilishi kerak, aks holda kutilmagan muammolar butun tizimni izdan chiqarishi mumkin.""",

("10-11-sinf", 16): """Grafik yaratish mavzusi vektor va raster grafikaning chuqur farqlarini hamda professional grafik dizayn asoslarini o'rgatadi. Vektor grafika matematik formulalar (nuqta, chiziq, egri chiziq koordinatalari) asosida quriladi, shuning uchun istalgancha kattalashtirilsa ham sifatini yo'qotmaydi — bu xususiyat uni logotip va illyustratsiyalar uchun ideal qiladi. Raster grafika esa piksellardan tashkil topgan bo'lib, kattalashtirilganda "dog'lanib" ko'rinadi, lekin fotosuratlar uchun tabiiy tanlov hisoblanadi.

Vektor logotip yaratish — oddiy geometrik shakllar (doira, to'rtburchak, uchburchak)ni birlashtirib, istalgan o'lchamda aniq ko'rinadigan belgi yasashni o'rgatadi. Bu jarayon murakkab dizaynlarning aslida sodda shakllardan tashkil topganini tushunishga yordam beradi.

Rang rejimlari orasidagi farq muhim texnik bilim: RGB (Red, Green, Blue) — ekranlar uchun mo'ljallangan, yorug'lik asosidagi rang tizimi, CMYK (Cyan, Magenta, Yellow, Key/qora) esa chop etish (printer) uchun mo'ljallangan, siyoh asosidagi tizim. Ekranda chiroyli ko'ringan rang, agar noto'g'ri rejimda chop etilsa, qog'ozda boshqacha ko'rinishi mumkin — shuning uchun maqsadga qarab to'g'ri rejimni tanlash muhim.

Murakkab dizaynlarda qatlamlar (fon, asosiy matn, dekorativ elementlar) alohida boshqarilib, keyin birlashtiriladi — bu har bir elementni mustaqil tahrirlash imkonini beradi, butun kompozitsiyani buzmasdan.

To'liq grafik loyihasi (masalan tadbir posteri) — o'lcham, rang palitrasi, shrift va tarkibni birlashtirgan yakuniy dizayn rejasini anglatadi. Bu mavzu professional grafik dizaynerlar ishlatadigan asosiy tushuncha va vositalarni tanishtiradi, bu ko'nikmalar marketing, nashriyot va raqamli san'at sohalarida keng qo'llaniladi.""",

("10-11-sinf", 17): """Animatsiya mavzusi harakatni jonlantirishning ikki asosiy texnikasi — kadr-bakadr va tween animatsiyani chuqur o'rgatadi. Kadr-bakadr (frame-by-frame) animatsiya — har bir alohida holatni qo'lda chizib, ularni tez ketma-ketlikda ko'rsatish orqali harakat illyuziyasini yaratish usuli. Bu — an'anaviy multfilmlarning asosiy texnikasi bo'lib, ko'p mehnat talab qiladi, lekin to'liq nazorat imkonini beradi.

Tween animatsiya (tweening — "orasida" so'zidan) — dasturchi faqat BOSHLANG'ICH va OXIRGI holatni belgilaydi, kompyuter esa ular orasidagi barcha oraliq kadrlarni AVTOMATIK hisoblab chiqadi. Bu usul ancha tezroq va samaraliroq, zamonaviy animatsiya dasturlarining aksariyati shu texnikaga asoslangan.

Kadr tezligi (frame rate, FPS — Frames Per Second) — sekundiga necha kadr ko'rsatilishini bildiradi. Yuqori FPS (masalan 60) harakatni silliq va tabiiy qiladi, past FPS (masalan 12) esa "sakrab-sakrab" harakat taassurotini beradi. Kino va o'yinlarda odatda yuqori FPS ishlatiladi, eski multfilmlarda esa past FPS keng tarqalgan edi.

Oddiy belgi (sprite) animatsiyasi — masalan yurish harakatini yaratish uchun, oyoqlarning turli holatlarini ifodalovchi bir necha kadrni ketma-ket almashtirib ko'rsatish kerak bo'ladi. Bu kadrlarning to'g'ri ketma-ketligi va vaqt oralig'i — harakatning tabiiy ko'rinishini ta'minlaydi.

To'liq animatsion loyiha — barcha kadrlar, harakatlar va ularning vaqt taqsimotini birlashtirgan, odatda vaqt chizig'i (timeline) ko'rinishida rejalashtirilgan yakuniy asar. Bu mavzu animatsiyaning texnik asoslarini o'rgatadi, bu bilimlar o'yin sanoati, reklama va ta'lim kontenti yaratishda keng qo'llaniladi.""",

("10-11-sinf", 18): """Xatlarni birlashtirish (Mail Merge) mavzusi bitta shablon hujjatni ko'plab odamga, har biriga shaxsiylashtirilgan ma'lumot bilan avtomatik yuborish texnologiyasini chuqur o'rgatadi. Bu texnologiya vaqtni sezilarli darajada tejaydi — masalan 100 kishiga alohida-alohida taklifnoma yozish o'rniga, bitta shablon va ma'lumotlar ro'yxatini birlashtirib, avtomatik ravishda 100 ta shaxsiylashtirilgan hujjat yaratish mumkin.

Ma'lumotlar manbasi — odatda jadval ko'rinishida saqlanadigan, har bir qabul qiluvchi haqidagi ma'lumotlar (ism, manzil va h.k.). Shablon hujjat esa umumiy matnni o'z ichiga oladi, unda ma'lum joylarga "o'zgaruvchi maydonlar" (masalan {Ism}) belgilanadi — bu maydonlar birlashtirish jarayonida har bir kishi uchun tegishli ma'lumot bilan avtomatik almashtiriladi.

Birlashtirish jarayoni natijasida — ma'lumotlar manbasidagi har bir qatordan bitta shaxsiylashtirilgan hujjat yaratiladi. Masalan, agar manbada 5 kishi bo'lsa, natijada 5 ta turli, lekin bir xil shablonga asoslangan hujjat hosil bo'ladi.

Ma'lumotlar manbasidagi xatoning ta'siri katta bo'lishi mumkin — agar bironta ism noto'g'ri yozilgan bo'lsa, o'sha kishiga yuboriladigan hujjatda ham xato bo'ladi. Shuning uchun birlashtirishdan OLDIN ma'lumotlar manbasini diqqat bilan tekshirish muhim.

Katta hajmli xat birlashtirish (masalan 100 kishiga taklifnoma) — ma'lumot tayyorlash, shablon yaratish, birlashtirish va natijalarni tekshirish kabi bosqichlarni o'z ichiga olgan tartibli jarayonni talab qiladi. Bu mavzu — ofis avtomatlashtirishning kuchli va amaliy vositasini o'rgatadi, bu ko'nikma marketing, ta'lim muassasalari va davlat idoralarida keng qo'llaniladi.""",

("10-11-sinf", 19): """Veb uchun dasturlash mavzusi JavaScript tili yordamida veb-sahifalarga INTERAKTIVLIK qo'shishni o'rgatadi. Agar HTML sahifaning tuzilishini va CSS uning ko'rinishini belgilasa, JavaScript sahifaga "hayot" beradi — foydalanuvchi harakatlariga (tugma bosish, ma'lumot kiritish) javob berish imkonini yaratadi.

O'zgaruvchi — dasturda qiymatni saqlovchi "quti". JavaScript'da o'zgaruvchi e'lon qilish uchun maxsus kalit so'z (masalan "var" yoki "let") ishlatiladi, so'ng unga nom va boshlang'ich qiymat beriladi. Masalan, foydalanuvchi yoshini saqlash uchun "yosh" nomli o'zgaruvchi yaratilishi mumkin.

Taqqoslash operatorlari (>, <, >=, <=) — ikki qiymatni solishtirib, natija sifatida "to'g'ri" yoki "noto'g'ri" (true/false) qaytaradi. Masalan "yosh > 18" ifodasi, agar yosh o'zgaruvchisi 18 dan katta bo'lsa "to'g'ri" natija beradi.

Shart (if) operatori — dasturga "agar shart bajarilsa, bir amalni bajar, aks holda boshqasini bajar" deb buyruq berish imkonini beradi. Bu — dasturlashning eng asosiy mantiqiy tuzilmalaridan biri, deyarli har qanday interaktiv dastur shart operatorlarisiz ishlay olmaydi.

Arifmetik hisoblash zanjiri — bir necha o'zgaruvchini birlashtirib, natijani yangi o'zgaruvchiga saqlash (masalan ikkita sonni qo'shib, natijani uchinchi o'zgaruvchiga yozish). Oddiy interaktiv veb-sahifa — foydalanuvchi ma'lumot kiritganda (masalan yoshini), JavaScript shu ma'lumotni tekshirib (shart operatori orqali), mos javob ko'rsatadigan (masalan "kattasiz" yoki "yoshsiz") to'liq mantiqni anglatadi. Bu mavzu — zamonaviy veb-saytlarning "aqlli", interaktiv qismi qanday ishlashini, va dasturlashning eng asosiy tushunchalarini (o'zgaruvchi, taqqoslash, shart) amaliy misolda tushuntiradi.""",

}



def migrate(db_path=None):
    conn = sqlite3.connect(db_path or DB)
    c = conn.cursor()

    if not _table_exists(c, "edu_curriculum_topics"):
        conn.close()
        return

    if not _column_exists(c, "edu_curriculum_topics", "full_text"):
        c.execute("ALTER TABLE edu_curriculum_topics ADD COLUMN full_text TEXT DEFAULT ''")

    for (grade_label, chapter_no), text in FULL_TEXTS.items():
        c.execute(
            "UPDATE edu_curriculum_topics SET full_text=? WHERE grade_label=? AND chapter_no=?",
            (text, grade_label, chapter_no)
        )

    conn.commit()
    conn.close()
    print(f"✅ v43 Mavzular uchun to'liq matn ({len(FULL_TEXTS)} ta) muvaffaqiyatli!")


if __name__ == "__main__":
    migrate()
