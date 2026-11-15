// Service worker – pozwala „zainstalować” aplikację na telefonie.
// Świadomie NIE przechowujemy danych w pamięci telefonu (poufność):
// zapisujemy tylko stronę „Brak połączenia”.
const CACHE = "posadzki-v1";
const OFFLINE = "{{ offline_url }}";

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.add(OFFLINE)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((klucze) => Promise.all(klucze.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (e.request.mode === "navigate") {
    e.respondWith(fetch(e.request).catch(() => caches.match(OFFLINE)));
  }
});
