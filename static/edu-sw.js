/**
 * SHATS CYBER EDU — Service Worker (PWA o'rnatilishi uchun)
 * Scope: /edu2/ (shu fayl /edu2/sw.js manzilida serverdan beriladi, shuning
 * uchun brauzer avtomatik ravishda faqat /edu2/ ostidagi sahifalarni qamraydi).
 *
 * Oddiy "network-first, cache-fallback" strategiyasi: internet bo'lsa har
 * doim eng yangi sahifa ko'rsatiladi (ma'lumotlar HECH QACHON eskirib
 * qolmaydi/"qotib qolmaydi"), internet uzilganda esa oxirgi ko'rilgan
 * sahifa keshdan ko'rsatiladi.
 */
const CACHE_NAME = "shats-edu-v1";

self.addEventListener("install", function (event) {
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (names) {
      return Promise.all(
        names.filter(function (n) { return n !== CACHE_NAME; })
             .map(function (n) { return caches.delete(n); })
      );
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  if (event.request.method !== "GET") return;
  if (!event.request.url.includes("/edu2/")) return;

  event.respondWith(
    fetch(event.request)
      .then(function (response) {
        var copy = response.clone();
        caches.open(CACHE_NAME).then(function (cache) {
          cache.put(event.request, copy);
        });
        return response;
      })
      .catch(function () {
        return caches.match(event.request);
      })
  );
});
