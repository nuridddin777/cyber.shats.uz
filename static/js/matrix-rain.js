// CYBER SHATS — Matritsa kodi yomg'iri (fon effekti)
(function () {
    const canvas = document.getElementById('matrix-canvas');
    if (!canvas) return;

    // "Kam harakat afzal" (prefers-reduced-motion) yoqilgan bo'lsa — animatsiyani
    // butunlay o'chiramiz, canvas'ni yashiramiz. Foydalanuvchi harakat sezgirligini hurmat qilamiz.
    const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
        canvas.style.display = 'none';
        return;
    }

    const ctx = canvas.getContext('2d');
    let w, h, columns, drops;

    // SHATS CYBER VIP foydalanuvchilar uchun qora-yashil o'rniga tilla/sariq fon effekti
    const isVip = document.body.classList.contains('vip-theme');
    // MAXSUS (hacker) foydalanuvchilar uchun binafsha-qora, faqat 1-9 raqamlari, ko'zga yumshoq
    const isHacker = document.body.classList.contains('hacker-theme');
    // Boshqa QORA fonli temalar (Cyber Pro, eksklyuziv Garage/Qashqirlar Makoni) —
    // bularga ham qorong'i uslub kerak, aks holda och (oq fon uchun) effekt
    // ularning qora fonida deyarli ko'rinmay, kontrastsiz bo'lib qoladi.
    const isDarkTier = document.body.classList.contains('cyber-pro-theme') ||
                        document.body.classList.contains('exclusive-cars') ||
                        document.body.classList.contains('exclusive-wolfpack');

    // XAVFSIZLIK/DIZAYN: endi FAQAT ikkilik (binar) 0 va 1 raqamlari tushadi —
    // avvalgi aralash harf/katakana/belgilar olib tashlandi.
    const chars = '01';

    let trailColor, charColor, fontSize, interval;
    if (isHacker) {
        trailColor = 'rgba(10,4,20,0.14)';   // sekinroq, yumshoqroq iz — ko'zni charchatmasin
        charColor = 'rgba(168,85,247,0.55)'; // pastroq kontrastli binafsha
        fontSize = 15;
        interval = 75; // sekinroq animatsiya
    } else if (isVip) {
        trailColor = 'rgba(20,8,8,0.12)';
        charColor = '#ff3030';
        fontSize = 14;
        interval = 45;
    } else if (isDarkTier) {
        trailColor = 'rgba(6,7,10,0.10)';
        charColor = 'rgba(255,255,255,0.16)';
        fontSize = 14;
        interval = 45;
    } else {
        // DIQQAT: bu yerda avval trailColor deyarli QORA edi (rgba(0,0,16,...))
        // — bu ESKI (qora) dizaynga mo'ljallangan edi. Sayt endi OQ+KO'K yorug'
        // temaga o'tgani sababli, bu qora rang har freymda biroz to'planib,
        // BUTUN SAYTNI XIRALASHTIRIB, kulrang-xira ko'rinish yaratardi — bu
        // aynan foydalanuvchi ko'rgan "yuvilib ketgan" muammo edi. Endi och
        // (deyarli oq) trail + yumshoq ko'k belgilar ishlatiladi.
        trailColor = 'rgba(246,249,253,0.12)';
        charColor = 'rgba(37,99,235,0.22)';
        fontSize = 14;
        interval = 45;
    }

    // Kam quvvatli/eski qurilmalarda animatsiyani sekinlashtiramiz (ko'rsatkich: kam CPU yadrosi)
    const isLowPower = navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 2;
    if (isLowPower) interval = Math.round(interval * 1.8);

    function resize() {
        w = canvas.width = window.innerWidth;
        h = canvas.height = window.innerHeight;
        // MAXSUS uchun ustunlar siyrakroq — zichlik pasayadi, ko'z charchamaydi
        const gap = isHacker ? 26 : (isLowPower ? 22 : 16);
        columns = Math.floor(w / gap);
        drops = new Array(columns).fill(1);
        window._matrixGap = gap;
    }
    window.addEventListener('resize', resize);
    resize();

    // Sahifa faol emas (boshqa tab ochilgan) bo'lsa chizishni to'xtatib, batareyani tejaymiz
    let isPageVisible = true;
    document.addEventListener('visibilitychange', function () {
        isPageVisible = document.visibilityState === 'visible';
    });

    function draw() {
        if (!isPageVisible) return;
        ctx.fillStyle = trailColor;
        ctx.fillRect(0, 0, w, h);
        ctx.fillStyle = charColor;
        ctx.font = fontSize + 'px monospace';
        const gap = window._matrixGap || 16;
        for (let i = 0; i < drops.length; i++) {
            // MAXSUS: har ustunda tasodifiy o'tkazib yuborish — yanada siyrak, tinch ko'rinish
            if (isHacker && Math.random() > 0.55) { drops[i]++; continue; }
            const text = chars[Math.floor(Math.random() * chars.length)];
            ctx.fillText(text, i * gap, drops[i] * gap);
            if (drops[i] * gap > h && Math.random() > 0.975) drops[i] = 0;
            drops[i]++;
        }
    }
    setInterval(draw, interval);
})();
