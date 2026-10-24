// Service Worker — FinanceTracker PWA & Push Notifications (v2.2.0)
const CACHE_NAME = 'finance-tracker-v2.2.0';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/login.html',
  '/register.html',
  '/manifest.json',
  '/assets/css/style.css',
  '/assets/js/app.js',
  '/assets/js/auth.js',
  '/assets/icons/icon-192.png',
  '/assets/icons/icon-512.png',
  '/assets/icons/icon.svg',
  'https://cdn.jsdelivr.net/npm/chart.js'
];

// Instalação: pré-cache de ativos estáticos essenciais
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] Falha ao cachear ativos estáticos:', err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Ativação: remoção de caches antigos
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
      );
    }).then(() => self.clients.claim())
  );
});

// Interceptação de requisições de rede (Network First com fallback de Cache para API / Cache First para assets)
self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);

  // Não interferir com requisições POST/PUT/DELETE
  if (event.request.method !== 'GET') {
    return;
  }

  // Rotas de API: Network First com fallback se offline
  if (requestUrl.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Clona e salva em cache apenas se resposta válida
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseClone));
          }
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Assets estáticos: Stale-While-Revalidate
  event.respondWith(
    caches.match(event.request).then(cachedResponse => {
      const fetchPromise = fetch(event.request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});

// Gestão de Notificações Web Push em Segundo Plano (Background Push)
self.addEventListener('push', event => {
  let data = {
    title: 'FinanceTracker Alerta',
    body: 'Você tem movimentações financeiras ou contas a vencer.',
    icon: '/assets/icons/icon-192.png',
    badge: '/assets/icons/icon-192.png',
    tag: 'finance-reminder',
    url: '/'
  };

  if (event.data) {
    try {
      data = Object.assign(data, event.data.json());
    } catch (e) {
      data.body = event.data.text();
    }
  }

  const options = {
    body: data.body,
    icon: data.icon || '/assets/icons/icon-192.png',
    badge: data.badge || '/assets/icons/icon-192.png',
    vibrate: [200, 100, 200],
    data: { url: data.url || '/' },
    actions: [
      { action: 'open', title: 'Visualizar Dashboard' },
      { action: 'dismiss', title: 'Fechar' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

// Clique na notificação: focar ou abrir a aplicação
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});

// Mensagens internas enviadas pelo front-end para agendamento local de lembrete
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SCHEDULE_LOCAL_NOTIFICATION') {
    const { title, body, delayMs, url } = event.data;
    setTimeout(() => {
      self.registration.showNotification(title, {
        body,
        icon: '/assets/icons/icon-192.png',
        badge: '/assets/icons/icon-192.png',
        vibrate: [150, 80, 150],
        data: { url: url || '/' }
      });
    }, delayMs || 1000);
  }
});
