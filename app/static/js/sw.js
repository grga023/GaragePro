/* GaragePro service worker — installability + fast static assets + offline shell.
 * Strategy:
 *   - static assets (/static/...)  -> cache-first (fast, works offline)
 *   - everything else (pages/API)  -> network-first (respects auth, never stale)
 * Bump CACHE when the shell changes to purge old entries.
 */
const CACHE = "garagepro-v1";
const PRECACHE = [
  "/static/css/bootstrap.min.css",
  "/static/js/bootstrap.bundle.min.js",
  "/static/js/theme.js",
  "/static/img/favicon.png",
  "/static/img/icon-192.png",
  "/static/img/apple-touch-icon.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting())
      .catch(() => {})
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.startsWith("/static/")) {
    // Cache-first for static assets (versioned URLs bust naturally).
    event.respondWith(
      caches.match(req).then((cached) =>
        cached ||
        fetch(req).then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          return res;
        }).catch(() => cached)
      )
    );
    return;
  }

  // Network-first for pages/API so authenticated content is never stale;
  // fall back to cache only when offline.
  event.respondWith(fetch(req).catch(() => caches.match(req)));
});
