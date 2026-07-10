/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_NAME: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Leaflet.heat no tiene tipos oficiales — declaramos el módulo
declare module 'leaflet.heat';

// Inyectada por vite.config.ts (define) — versión de build para el auto-update
// de la PWA (base-compartida/6-GUIA-PWA.md).
declare const __APP_VERSION__: string;
