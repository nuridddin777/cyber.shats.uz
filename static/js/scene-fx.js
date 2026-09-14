// CYBER SHATS — fon rasmlar uchun 3D tilt (parallax) va THREAT ranglar almashinuvi
(function () {
    // ---------- 3D TILT: sichqoncha harakatiga qarab fon rasm/kartalar biroz aylanadi ----------
    function initTilt() {
        var scenes = document.querySelectorAll('.tilt-scene');
        scenes.forEach(function (scene) {
            var img = scene.querySelector('.bg-scene img');
            if (!img) return;
            scene.addEventListener('mousemove', function (e) {
                var r = scene.getBoundingClientRect();
                var px = (e.clientX - r.left) / r.width - 0.5;   // -0.5..0.5
                var py = (e.clientY - r.top) / r.height - 0.5;
                var rx = (py * -8).toFixed(2);
                var ry = (px * 10).toFixed(2);
                img.style.transform = 'translateY(-50%) rotateX(' + rx + 'deg) rotateY(' + ry + 'deg) scale(1.03)';
            });
            scene.addEventListener('mouseleave', function () {
                img.style.transform = 'translateY(-50%) rotateX(0deg) rotateY(0deg) scale(1)';
            });
        });

        // Kartalar uchun yengil 3D tilt (tilt-card klassi bor elementlar)
        document.querySelectorAll('.tilt-card').forEach(function (card) {
            card.addEventListener('mousemove', function (e) {
                var r = card.getBoundingClientRect();
                var px = (e.clientX - r.left) / r.width - 0.5;
                var py = (e.clientY - r.top) / r.height - 0.5;
                card.style.transform = 'translateY(-6px) rotateX(' + (py * -8).toFixed(2) + 'deg) rotateY(' + (px * 8).toFixed(2) + 'deg) scale(1.015)';
            });
            card.addEventListener('mouseleave', function () {
                card.style.transform = '';
            });
        });
    }

    // ---------- THREAT ZONE: pastga tushilganda HUD LOW→HIGH, FAOL→ACTIVE bo'lib qiziradi ----------
    function initThreatZone() {
        var zone = document.getElementById('threatZone');
        if (!zone || !('IntersectionObserver' in window)) return;
        var threatVal = document.getElementById('hudThreatVal');
        var fwVal = document.getElementById('hudFirewallVal');

        var obs = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                var active = entry.isIntersecting && entry.intersectionRatio > 0.15;
                document.body.classList.toggle('threat-high', active);
                if (threatVal) threatVal.textContent = active ? 'HIGH' : 'LOW';
                if (fwVal) fwVal.textContent = active ? 'ACTIVE' : 'FAOL';
            });
        }, { threshold: [0, 0.15, 0.5] });

        obs.observe(zone);
    }

    document.addEventListener('DOMContentLoaded', function () {
        initTilt();
        // Butun sayt bitta (oltin) mavzuda bo'lgani uchun THREAT/FIREWALL rangi endi statik.
    });
})();
