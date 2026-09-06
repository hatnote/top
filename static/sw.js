/* Top 100 service worker.
 *
 * Network-first for pages, on purpose: the whole point of this site is *today's*
 * chart, so a cached page must never beat a fresh one. The cache exists only so
 * the installed app stays usable with no connection, and so Chrome/Edge treat
 * the site as installable (beforeinstallprompt still requires a fetch handler).
 *
 * Bump VERSION to evict every old cache on the next deploy.
 */
var VERSION = 'top-v5';
var SHELL = VERSION + '-shell';
var RUNTIME = VERSION + '-runtime';
var OFFLINE_URL = '/offline.html';

// best-effort extras; a 404 on any of these must not break installation
var PRECACHE = [
  '/css/chart.css',
  '/css/fonts.css',
  '/js/top.js',
  '/img/icon-192.png',
  '/img/w.png',
  '/manifest.json'
];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(SHELL).then(function (cache) {
      // the offline page is the one hard requirement
      return cache.add(OFFLINE_URL).then(function () {
        return Promise.all(PRECACHE.map(function (url) {
          return cache.add(url).catch(function () { /* non-fatal */ });
        }));
      });
    }).then(function () {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (key) {
        if (key !== SHELL && key !== RUNTIME) { return caches.delete(key); }
        return null;
      }));
    }).then(function () {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function (event) {
  var req = event.request;
  if (req.method !== 'GET') { return; }

  var url = new URL(req.url);
  // article thumbnails live on upload.wikimedia.org: never our business to cache
  if (url.origin !== self.location.origin) { return; }

  if (req.mode === 'navigate') {
    // `cache: 'reload'` is the whole point: a plain fetch(req) is still served by
    // the browser's HTTP cache (nginx sends `expires 1h`), which would let an
    // installed app show an hour-old chart. Go to the wire, every time.
    event.respondWith(
      fetch(req.url, {cache: 'reload', credentials: 'same-origin'}).then(function (res) {
        // a redirected response cannot be returned for a navigation
        if (res.redirected) { return Response.redirect(res.url, 302); }
        var copy = res.clone();
        caches.open(RUNTIME).then(function (cache) { cache.put(req, copy); });
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || caches.match(OFFLINE_URL);
        });
      })
    );
    return;
  }

  // static assets: serve from cache at once, revalidate in the background.
  // 'no-cache' forces a conditional request, so a redeployed css/js file is
  // picked up on the next load instead of sitting behind nginx's 1h expiry.
  event.respondWith(
    caches.match(req).then(function (hit) {
      var net = fetch(req.url, {cache: 'no-cache', credentials: 'same-origin'})
        .then(function (res) {
          if (res && res.status === 200) {
            var copy = res.clone();
            caches.open(RUNTIME).then(function (cache) { cache.put(req, copy); });
          }
          return res;
        }).catch(function () { return hit; });
      return hit || net;
    })
  );
});
