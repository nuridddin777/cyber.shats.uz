/**
 * CYBER SHATS V1.3 — Bildirishnoma tizimi (ODDIY SIGNAL, gapirmaydi)
 *
 * MUHIM O'ZGARISH: avval bildirishnoma kelganda matnni OVOZDA O'QIB BERARDI
 * (Text-to-Speech) — bu og'ir va keraksiz edi. Endi oddiy telefonga SMS
 * kelganidagi kabi QISQA SIGNAL (bip) chalinadi, hech narsa aytilmaydi.
 *
 * Foydalanuvchi sahifaga bossanidan keyin signal yoqiladi (brauzer xavfsizlik
 * qoidasi). Pastki o'ng burchakda doimo turuvchi tugma orqali yoqish/o'chirish
 * mumkin. Holat localStorage'da saqlanadi:
 *   cs_sound_pref = "on" / "off" / "" (boshlang'ich, foydalanuvchi hali tanlamagan)
 */
(function() {
    'use strict';

    var pollIntervalMs = 15000;
    var seenNotifIds = new Set();
    var seenAnnIds = new Set();
    var audioCtx = null;

    function isLoggedIn() {
        return document.body.classList.contains('has-sidebar') ||
               document.querySelector('[data-current-user]') !== null ||
               document.body.classList.contains('treasury-session');
    }
    if (!isLoggedIn()) return;

    var isTreasury = document.body.classList.contains('treasury-session');

    // ---- Sozlamalar (localStorage) ----
    // DIQQAT: avval standart holat "off" edi (foydalanuvchi махсус tugmani
    // BOSMAGUNCHA ovoz hech qachon yoqilmasdi — juda ko'p odam bu tugmani
    // sezmay qolardi). Endi standart holat "ON" — brauzer talabiga ko'ra
    // ovoz FAQAT foydalanuvchi sahifa bilan birinchi marta o'zaro
    // ta'sirlashgandan keyin ishlaydi, shuning uchun BIRINCHI bosish/teginish
    // paytida (istalgan joyga, махсус tugmaga emas) avtomatik "ochamiz".
    function getPref() { var v = localStorage.getItem('cs_sound_pref'); return v === null ? 'on' : v; }
    function setPref(v) { localStorage.setItem('cs_sound_pref', v); }
    function isSoundOn() { return getPref() !== 'off'; }

    function unlockAudioOnce() {
        try {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (audioCtx.state === 'suspended') audioCtx.resume();
        } catch (e) {}
        document.removeEventListener('click', unlockAudioOnce);
        document.removeEventListener('touchstart', unlockAudioOnce);
        document.removeEventListener('keydown', unlockAudioOnce);
    }
    if (isSoundOn()) {
        document.addEventListener('click', unlockAudioOnce, { once: true });
        document.addEventListener('touchstart', unlockAudioOnce, { once: true });
        document.addEventListener('keydown', unlockAudioOnce, { once: true });
    }

    // ---- Toast konteyner ----
    var container = document.createElement('div');
    container.id = 'voice-notif-container';
    container.style.cssText =
        'position:fixed; top:76px; right:16px; z-index:9999; ' +
        'display:flex; flex-direction:column-reverse; gap:8px; width:320px; max-width:calc(100vw - 32px); ' +
        'pointer-events:none;';
    document.body.appendChild(container);
    var MAX_VISIBLE_TOASTS = 3;

    // ---- O'ng pastdagi doimiy boshqaruv tugmasi ----
    var ctrlBtn = document.createElement('button');
    ctrlBtn.id = 'cs-sound-toggle';
    ctrlBtn.title = 'Signal bildirishnomalari';
    ctrlBtn.style.cssText =
        'position:fixed; bottom:20px; right:20px; z-index:9998; ' +
        'width:50px; height:50px; border-radius:50%; cursor:pointer; ' +
        'border:0; font-size:22px; ' +
        'box-shadow:0 4px 16px rgba(0,0,0,.3); ' +
        'transition:transform .15s, box-shadow .15s;';
    ctrlBtn.onmouseenter = function() { ctrlBtn.style.transform = 'scale(1.08)'; };
    ctrlBtn.onmouseleave = function() { ctrlBtn.style.transform = 'scale(1)'; };
    document.body.appendChild(ctrlBtn);

    function refreshBtn() {
        if (isSoundOn()) {
            ctrlBtn.style.background = 'linear-gradient(135deg,#2563eb,#1d4ed8)';
            ctrlBtn.style.color = '#fff';
            ctrlBtn.innerHTML = '🔔';
            ctrlBtn.title = 'Signal yoqilgan — o\'chirish uchun bosing';
        } else {
            ctrlBtn.style.background = 'rgba(100,116,139,.85)';
            ctrlBtn.style.color = '#fff';
            ctrlBtn.innerHTML = '🔕';
            ctrlBtn.title = 'Signal o\'chirilgan — yoqish uchun bosing';
        }
    }

    ctrlBtn.addEventListener('click', function() {
        if (isSoundOn()) {
            setPref('off');
            refreshBtn();
            showToast('Signal', 'Signal bildirishnomalar o\'chirildi', 'info', null);
        } else {
            setPref('on');
            try {
                if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                if (audioCtx.state === 'suspended') audioCtx.resume();
            } catch(e) {}
            refreshBtn();
            showToast('Signal', 'Signal bildirishnomalar yoqildi', 'success', 'notification');
            checkAnnouncements();
            checkNotifications();
            // Saytdan chiqib ketganda ham bildirishnoma kelishi uchun Web Push so'raymiz
            if (window.CyberShatsPush && window.CyberShatsPush.isSupported) {
                window.CyberShatsPush.subscribe().then(function(ok) {
                    if (ok) {
                        showToast('Push bildirishnoma', 'Saytdan chiqib ketsangiz ham xabar olasiz', 'success', null);
                    }
                });
            }
        }
    });
    refreshBtn();

    // ---- Toast kartochka ----
    function showToast(title, body, type, soundType) {
        var card = document.createElement('div');
        var colors = {
            announcement: { bg:'linear-gradient(135deg,#ffb238,#c98a1f)', text:'#1a1200', border:'#ffb238' },
            urgent:       { bg:'linear-gradient(135deg,#ff4d4d,#c9242c)', text:'#fff', border:'#ff3b3b' },
            success:      { bg:'rgba(20,26,34,.97)', text:'#eef1f6', border:'#ff3b3b' },
            error:        { bg:'rgba(20,26,34,.97)', text:'#eef1f6', border:'#ff5555' },
            info:         { bg:'rgba(20,26,34,.97)', text:'#eef1f6', border:'#8a8a92' }
        };
        var style = colors[type] || colors.info;
        card.style.cssText =
            'background:' + style.bg + '; color:' + style.text + '; ' +
            'padding:12px 14px; border-radius:10px; border-left:3px solid ' + style.border + '; ' +
            'box-shadow:0 6px 20px rgba(0,0,0,.35); font-size:12.5px; ' +
            'animation:csSlideIn .25s ease-out; width:100%; box-sizing:border-box; cursor:pointer; ' +
            'pointer-events:auto;';
        card.innerHTML =
            '<div style="font-weight:700; margin-bottom:3px; display:flex; justify-content:space-between; gap:8px;">' +
                '<span>' + esc(title) + '</span><span style="opacity:.5; font-weight:400;">✕</span></div>' +
            (body ? '<div style="font-size:11.5px; opacity:.85; line-height:1.4;">' + esc(body) + '</div>' : '');
        card.onclick = function() { fadeOut(card); };
        container.appendChild(card);
        // Bir vaqtda ko'pi bilan MAX_VISIBLE_TOASTS ta ko'rinadi — ortiqchasi
        // (eng eskisi) darhol olib tashlanadi, ekran to'lib ketmasin.
        while (container.children.length > MAX_VISIBLE_TOASTS) {
            fadeOut(container.firstElementChild);
        }

        // Faqat qisqa signal (SMS uslubidagi bip) — gapirmaydi, matn o'qilmaydi.
        if (isSoundOn() && soundType) {
            playBeep(soundType);
        }
        setTimeout(function() { fadeOut(card); }, 6000);
    }

    function fadeOut(el) {
        el.style.transition = 'opacity .3s, transform .3s';
        el.style.opacity = '0';
        el.style.transform = 'translateX(20px)';
        setTimeout(function() { if (el.parentNode) el.parentNode.removeChild(el); }, 300);
    }
    function esc(s) {
        if (!s) return '';
        return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    // ---- Ovoz signali (Web Audio) — oddiy SMS-uslubidagi qisqa "bip" ----
    function playBeep(type) {
        if (!isSoundOn()) return;
        try {
            if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            if (audioCtx.state === 'suspended') audioCtx.resume();
            var osc = audioCtx.createOscillator();
            var gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);
            // Mayinroq, sokinroq ohang — kamroq baland chastota, sekinroq fade-in/out
            var freq = type === 'announcement' ? 660 : (type === 'urgent' ? 880 : 520);
            osc.frequency.value = freq;
            osc.type = 'sine';
            var now = audioCtx.currentTime;
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.08, now + 0.08);  // sekin ko'tariladi
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.6); // sekin pasayadi
            osc.start(now);
            osc.stop(now + 0.6);
        } catch(e) {}
    }

    // ---- Polling: e'lonlar va bildirishnomalar (oddiy foydalanuvchi) ----
    var isFirstAnnCheck = true, isFirstNotifCheck = true;

    function checkAnnouncements() {
        if (isTreasury) return;
        fetch('/api/announcements/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.announcements) return;
                var hadNew = false;
                var isFirst = isFirstAnnCheck;
                isFirstAnnCheck = false;
                d.data.announcements.forEach(function(a) {
                    if (seenAnnIds.has(a.id)) return;
                    seenAnnIds.add(a.id);
                    // BIRINCHI tekshiruvda (sahifa endi ochilganda) eski
                    // e'lonlarni "toast bombasi" qilib ko'rsatmaymiz — lekin
                    // "o'qilgan" deb ham belgilamaymiz (qo'ng'iroq belgisida
                    // hali ham ko'rinib tursin). Faqat SHU DAQIQADAN keyin
                    // kelgan haqiqiy yangi e'lonlar toast bo'lib chiqadi.
                    if (isFirst) {
                        return;
                    }
                    hadNew = true;
                    var soundType = a.priority === 'urgent' ? 'urgent' : 'announcement';
                    var toastType = a.priority === 'urgent' ? 'urgent' : 'announcement';
                    showToast('📢 ' + a.title, a.body, toastType, soundType);
                    fetch('/api/announcements/' + a.id + '/seen',
                          { method:'POST', credentials:'same-origin' });
                });
                if (hadNew && window.__csTriggerAutoRefresh) window.__csTriggerAutoRefresh();
            }).catch(function() {});
    }
    function checkNotifications() {
        if (isTreasury) {
            checkTreasuryNotifications();
            return;
        }
        fetch('/api/notifications/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.notifications) return;
                var hadNew = false;
                var isFirst = isFirstNotifCheck;
                isFirstNotifCheck = false;
                d.data.notifications.forEach(function(n) {
                    if (seenNotifIds.has(n.id)) return;
                    if (n.type === 'announcement') return;
                    seenNotifIds.add(n.id);
                    // Xuddi shu mantiq — sahifa birinchi ochilganda to'plangan
                    // eski bildirishnomalar hammasi birdan chiqmasin, lekin
                    // "o'qilgan" deb ham belgilanmasin (qo'ng'iroqda ko'rinsin).
                    if (isFirst) {
                        return;
                    }
                    hadNew = true;
                    var ttype = n.type === 'error' ? 'error' :
                                (n.type === 'success' ? 'success' : 'info');
                    showToast('🔔 ' + n.title, n.body, ttype, 'notification');
                    fetch('/api/notifications/' + n.id + '/read',
                          { method:'POST', credentials:'same-origin' });
                });
                if (hadNew && window.__csTriggerAutoRefresh) window.__csTriggerAutoRefresh();
            }).catch(function() {});
    }

    // ---- G'azna uchun: yangi bot to'lov so'rovlari haqida signal ----
    function checkTreasuryNotifications() {
        fetch('/api/treasury/notifications/pending', { credentials:'same-origin' })
            .then(function(r) { return r.json(); })
            .then(function(d) {
                if (!d.success || !d.data || !d.data.items) return;
                var hadNew = false;
                d.data.items.forEach(function(n) {
                    if (seenNotifIds.has('t' + n.id)) return;
                    seenNotifIds.add('t' + n.id);
                    hadNew = true;
                    showToast('🔔 ' + n.title, n.body, 'info', 'notification');
                });
                if (hadNew && window.__csTriggerAutoRefresh) window.__csTriggerAutoRefresh();
            }).catch(function() {});
    }

    var styleEl = document.createElement('style');
    styleEl.textContent =
        '@keyframes csSlideIn {' +
        '  from { opacity:0; transform:translateX(50px); }' +
        '  to { opacity:1; transform:translateX(0); }' +
        '}';
    document.head.appendChild(styleEl);

    setTimeout(function() {
        checkAnnouncements();
        checkNotifications();
    }, 2500);
    setInterval(checkAnnouncements, pollIntervalMs);
    setInterval(checkNotifications, pollIntervalMs);

    document.addEventListener('visibilitychange', function() {
        if (!document.hidden) {
            checkAnnouncements();
            checkNotifications();
        }
    });
})();
