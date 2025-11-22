// Service Worker for Cruzy Coffee Co. PWA
const CACHE_NAME = 'cruzy-coffee-v1';
const urlsToCache = [
  '/',
  '/static/css/styles.css',
  '/static/js/cart.js',
  '/static/img/coffee_logo.png',
  '/machines',
  '/beans',
  '/accessories',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css'
];

// Install Service Worker
self.addEventListener('install', event => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Service Worker: Caching files');
        return cache.addAll(urlsToCache);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate Service Worker
self.addEventListener('activate', event => {
  console.log('Service Worker: Activating...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cache => {
          if (cache !== CACHE_NAME) {
            console.log('Service Worker: Clearing old cache');
            return caches.delete(cache);
          }
        })
      );
    })
  );
  return self.clients.claim();
});

// Fetch Strategy: Network First, fallback to Cache
self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Clone the response
        const responseClone = response.clone();
        
        // Cache the fetched response
        caches.open(CACHE_NAME).then(cache => {
          cache.put(event.request, responseClone);
        });
        
        return response;
      })
      .catch(() => {
        // If network fails, try cache
        return caches.match(event.request);
      })
  );
});

// Background Sync (for future cart sync feature)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-cart') {
    console.log('Service Worker: Syncing cart data');
    // Add cart sync logic here
  }
});

// Push Notifications (for future order updates)
self.addEventListener('push', event => {
  const options = {
    body: event.data ? event.data.text() : 'New update from Cruzy Coffee!',
    icon: '/static/img/pwa-icon-192.png',
    badge: '/static/img/pwa-icon-192.png',
    vibrate: [200, 100, 200],
    tag: 'cruzy-notification',
    actions: [
      { action: 'view', title: 'View Order' },
      { action: 'close', title: 'Close' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('Cruzy Coffee Co.', options)
  );
});

// Notification Click Handler
self.addEventListener('notificationclick', event => {
  event.notification.close();
  
  if (event.action === 'view') {
    event.waitUntil(
      clients.openWindow('/orders')
    );
  }
});