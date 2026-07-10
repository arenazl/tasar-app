// TasAR Service Worker — Web Push + click handler (WO F3-03)

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

self.addEventListener('push', (event) => {
  let data = { title: 'TasAR', body: 'Tenés una notificación nueva' }
  try {
    if (event.data) data = event.data.json()
  } catch (e) {
    if (event.data) data.body = event.data.text()
  }

  const title = data.title || 'TasAR'
  const options = {
    body: data.body || '',
    tag: data.tag || 'tasar-default',
    data: { url: data.url || '/bandeja' },
    renotify: true,
    requireInteraction: false,
  }

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const targetUrl = event.notification.data?.url || '/bandeja'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Si ya hay una pestaña abierta en el origen, navegar ahí.
      for (const client of clientList) {
        const url = new URL(client.url)
        if (url.origin === self.location.origin) {
          client.focus()
          if ('navigate' in client) {
            return client.navigate(targetUrl)
          }
          return
        }
      }
      // Sino abrir una nueva.
      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl)
      }
    })
  )
})
