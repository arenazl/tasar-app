import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import 'leaflet/dist/leaflet.css';
import { setupVersionCheck } from './lib/versionCheck';

// Service Worker: Web Push (WO F3-03) + network-first para navegaciones (WO
// F4-04, auto-update sin reinstalar — base-compartida/6-GUIA-PWA.md Nivel 2).
// Registro temprano, best-effort: no rompe nada si el browser no soporta SW.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((e) => {
      console.warn('[sw] registro fallido:', e);
    });
  });
}

// Auto-update de la PWA sin reinstalar (WO F4-04, Nivel 1: version.json).
setupVersionCheck();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
