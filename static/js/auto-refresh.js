/**
 * CYBER SHATS — Ro'yxat sahifalari uchun XAVFSIZ, HODISAGA ASOSLANGAN
 * avtomatik yangilanish.
 *
 * MUHIM O'ZGARISH: avval bu skript sahifani "har N soniyada" DOIM qayta
 * yuklardi — bu backend'ga keraksiz ortiqcha yuklama berardi (har bir ochiq
 * sahifa hech qanday yangi ma'lumot bo'lmasa ham butun sahifani qayta so'rar
 * edi). Endi bu FAQAT haqiqatan yangi bildirishnoma/so'rov aniqlanganda
 * (voice-notifications.js'ning yengil 15-soniyalik so'rovi orqali) ishga
 * tushadi — ya'ni backend'ga qo'shimcha yuk YO'Q, faqat haqiqiy hodisaga
 * javoban sahifa yangilanadi.
 *
 * Xavfsizlik: agar foydalanuvchi formaga yozayotgan bo'lsa yoki biror narsa
 * ochiq bo'lsa — yangilanmaydi (ma'lumot yo'qolmasin uchun).
 *
 * ISHLATISH: <body>ga (yoki istalgan konteynerga) data-autorefresh="1"
 * qo'yiladi — shunda shu sahifa "jonli" deb belgilanadi va yangi hodisa
 * aniqlanganda avtomatik yangilanadi.
 */
(function () {
    "use strict";

    function findHost() {
        return document.querySelector("[data-autorefresh]");
    }

    var host = findHost();
    if (!host) return;

    function isSafeToRefresh() {
        var active = document.activeElement;
        if (active) {
            var tag = active.tagName;
            if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return false;
            if (active.isContentEditable) return false;
        }
        if (document.querySelector("details[open]")) return false;
        if (document.hidden) return false;
        return true;
    }

    // voice-notifications.js yangi bildirishnoma/so'rov ko'rgan zahoti shu
    // funksiyani chaqiradi — faqat SHUNDAGINA (kerak bo'lgandagina) yangilanadi.
    window.__csTriggerAutoRefresh = function () {
        if (isSafeToRefresh()) {
            window.location.reload();
        }
        // Agar hozir xavfsiz bo'lmasa (masalan forma to'ldirilmoqda),
        // shunchaki hech narsa qilmaymiz — keyingi hodisada yana urinib ko'radi,
        // majburan yangilab foydalanuvchi ma'lumotini yo'qotmaymiz.
    };
})();
