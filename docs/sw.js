/* Service worker de l'application installee.

   Une seule regle : LE RESEAU D'ABORD. A chaque ouverture, la page est
   redemandee au serveur (en revalidant le cache HTTP de GitHub Pages, qui
   sinon peut servir une version de 10 minutes) : l'app montre donc toujours
   les donnees de la derniere collecte, exactement comme le navigateur.
   Ce qui est recu est garde en memoire ; sans reseau (metro, avion), l'app
   affiche la derniere version vue au lieu d'une page d'erreur. La date
   "Donnees du ..." en haut de page dit alors de quand elles datent.

   Seules les ressources du site lui-meme passent ici. Les polices Google
   vont directement au reseau : hors ligne, la police systeme prend le relais. */
const CACHE = 'sub4-v2';

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(
  caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim())));

self.addEventListener('fetch', e => {
  const r = e.request;
  if (r.method !== 'GET' || new URL(r.url).origin !== location.origin) return;
  e.respondWith(
    fetch(r, {cache: 'no-cache'})
      .then(rep => {
        if (rep.ok) {
          const copie = rep.clone();
          caches.open(CACHE).then(c => c.put(r, copie));
        }
        return rep;
      })
      .catch(() => caches.match(r).then(m => m
        || (r.mode === 'navigate' ? caches.match('./') : undefined)
        || Response.error())));
});
