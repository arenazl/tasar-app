# TasAR — Landing

Landing estática (HTML + Tailwind via CDN, sin build). Posicionamiento: la suite
inmobiliaria que cubre todo el ciclo — **captar, gestionar, atender y cerrar** — en
un solo lugar.

Fuente display: **Funnel Display 900** (Google Fonts).
Fuente cuerpo: **Inter**.
Datos/monoespaciado: **JetBrains Mono**.

## Secciones

1. Nav (Ingresar / Solicitar demo)
2. Hero — "Todo el ciclo de tu inmobiliaria, en una sola suite." + diagrama del ciclo Captar→Gestionar→Atender→Cerrar (sin cifras)
3. El ciclo — las 4 etapas explicadas
4. Módulos — las 4 patas: Tasación express, CRM y pipeline, DMO, Bot de WhatsApp
5. Bot de WhatsApp — conversación de ejemplo (marcada como ilustrativa, no real)
6. Demo — bloque "Solicitá una demo", sin montos (demo-first) + qué incluye la suite
7. FAQ
8. Footer

## Reglas de contenido

- Sin cifras inventadas: nada de listings/avisos/zonas/porcentajes sin fuente real (regla dura 11).
- Sin montos de precio: pricing = CTA "Solicitar demo". Los planes se publican cuando el dueño defina montos.
- Sin emojis: solo iconos SVG inline (regla dura 12).
- La conversación del bot es un ejemplo ilustrativo, rotulado como tal.

## CTAs

- **Solicitar demo** → `mailto:hola@tasar.app`
- **Crear una cuenta** → `/registro` (registro self-service + wizard post-registro, `frontend/src/pages/Registro.tsx`, WO F5-03)
- **Ingresar** → `/login`

## Abrir

Doble click en `index.html`, o servir con:

```powershell
npx serve .
```
