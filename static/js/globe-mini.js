// CYBER SHATS — Hero bo'limlardagi kichik aylanuvchi globe (avto-ishga tushish)
// DIQQAT: ekrandan tashqariga chiqqanda (masalan pastga skroll qilinganda)
// render avtomatik TO'XTAYDI — aks holda ko'rinmasa ham fonda WebGL ishlab,
// past quvvatli telefonlarda saytni sekinlashtirar edi.
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-globe]').forEach(function (el) {
        var speed = parseFloat(el.getAttribute('data-speed')) || 0.0022;
        var cameraZ = parseFloat(el.getAttribute('data-camera-z')) || 5.4;
        var instance = csCreateGlobe(el.id, { speed: speed, cameraZ: cameraZ });
        if (!instance || !('IntersectionObserver' in window)) return;
        var observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    instance.resume ? instance.resume() : null;
                } else {
                    instance.stop();
                }
            });
        }, { threshold: 0.05 });
        observer.observe(el);
    });
});
