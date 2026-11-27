// Focus : fonctionne hors connexion une fois ouvert une première fois.
const CACHE = 'focus-v15';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-180.png', './icon-192.png', './icon-512.png', './audio/index.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
const fresh = (req, key) => fetch(req).then(r => { if (r.ok) { const c = r.clone(); caches.open(CACHE).then(x => x.put(key || req, c)); } return r; })
  .catch(() => caches.match(key || req));
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // La page et la liste des voix : réseau d'abord (mises à jour), cache si hors ligne.
  if (req.mode === 'navigate') { e.respondWith(fresh(req, './index.html')); return; }
  if (url.pathname.endsWith('/audio/index.json')) { e.respondWith(fresh(req)); return; }
  // Le reste (enregistrements, icônes, polices) : cache d'abord, puis réseau.
  if (url.origin !== self.location.origin && !url.hostname.includes('fonts.g')) return;
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {
    if (r.ok) { const c = r.clone(); caches.open(CACHE).then(x => x.put(req, c)); }
    return r;
  })));
});
