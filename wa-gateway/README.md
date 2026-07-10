# tasar-wa-gateway

Gateway WhatsApp **unico** (Baileys / WhatsApp Web no-oficial) para la suite
inmobiliaria **TasAR**. Una sola instancia atiende multiples **tenants**; cada
tenant = un **workspace** de la suite. Cada tenant mantiene su propia sesion
Signal + auth-state persistido en la suite.

Portado de `SalesBot/baileys` (WO F0-05). El repo donante `d:\Code\baileys-gateway`
queda **jubilado**.

> NOTA DE ESTADO (WO F0-05): en este WO NO se levanta el gateway real contra
> WhatsApp (requiere un numero + deploy). La aceptacion funcional plena (QR,
> mensaje entrante/saliente) queda para Infra/dev tras la etapa E1. Lo entregado
> aca es el servicio + su contrato.

---

## Arquitectura

```
WhatsApp  <—Signal—>  wa-gateway (Node/Baileys)  <—HTTP X-API-Key—>  suite TasAR (FastAPI)
                          │
                          ├─ auth-state:   GET/PUT/DELETE  {SUITE_API_URL}/api/wa-auth/{slug}-{key}
                          ├─ bootstrap:    GET             {SUITE_API_URL}/api/wa/tenants
                          └─ entrantes:    POST            {WEBHOOK_URL}  (contrato de abajo)

frontend (admin)  —JWT→  suite  —X-API-Key→  wa-gateway  /tenants/:slug/(status|start|stop|qr)
```

El frontend NUNCA habla directo con el gateway (expondria el secreto). Pega a la
suite con JWT y la suite reenvia al gateway con `X-API-Key` (router `wa_gateway.py`).

---

## Endpoints HTTP del gateway

Todos requieren header `X-API-Key: <WA_GATEWAY_KEY>` (o `?key=` para el iframe del
QR). `/health` queda abierto.

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| GET  | `/health` | Estado del servicio + sesiones activas (abierto). |
| GET  | `/tenants/:slug/status` | `{ slug, state, isReady, hasPendingQR, numero, started }`. |
| POST | `/tenants/:slug/start` | Arranca/asegura la sesion (idempotente). |
| POST | `/tenants/:slug/stop` | Detiene la sesion (conserva credenciales). |
| POST | `/tenants/:slug/logout` | Logout REAL (WhatsApp invalida el dispositivo). |
| GET  | `/tenants/:slug/qr` | Pagina HTML con el QR (o "Conectado"). Embebible en iframe con `?key=`. |
| POST | `/send` | Envia un mensaje (ver abajo). |

### POST /send

```json
{ "tenant": "mi-agencia", "telefono": "5491112345678",
  "contenido": "Hola", "audio_url": null, "video_url": null, "ptt": true }
```

`tenant` es el slug del workspace. Acepta `app` como alias por compatibilidad.
`telefono` puede ser un numero o un JID. Respuesta: `{ ok, meta_message_id }`.

---

## Contrato del webhook de entrantes (de-facto — ES el contrato)

Cada mensaje entrante (que Baileys pudo descifrar) se postea a `WEBHOOK_URL`
(default `{SUITE_API_URL}/api/whatsapp/webhook/incoming`) con header
`X-API-Key: <WA_GATEWAY_KEY>` y este body:

```json
{
  "tenant": "mi-agencia",
  "telefono": "5491112345678@s.whatsapp.net",
  "phone_publico": "5491100000000",
  "nombre_contacto": "Juan Perez",
  "contenido": "Hola, me interesa el 2 ambientes",
  "tipo": "text",
  "media_url": null,
  "meta_message_id": "3EB0XXXX",
  "timestamp": 1720000000
}
```

| Campo | Significado |
|-------|-------------|
| `tenant` | Slug del workspace de la suite. |
| `telefono` | JID del contacto (para @lid usa `senderPn` si esta disponible). |
| `phone_publico` | Numero publico del tenant (la agencia) que recibio el mensaje. |
| `nombre_contacto` | `pushName` de WhatsApp o `null`. |
| `contenido` | Texto / caption. `""` si es solo media. |
| `tipo` | `text` \| `audio` \| `image` \| `video` \| `document`. |
| `media_url` | URL de Cloudinary si habia media, o `null`. La suite **NO** recibe base64. |
| `meta_message_id` | `key.id` de WhatsApp (para dedupe). |
| `timestamp` | Epoch (segundos) del mensaje. |

El handler de este webhook lo crea **F2-03** (`/api/whatsapp/webhook/incoming` +
config del bot por workspace). Hasta entonces, el POST respondera 404 — esperado.

---

## Persistencia de auth-state

No se guarda en disco. Cada key de Baileys se lee/escribe contra la suite,
prefijada con `{workspace_slug}-`:

```
GET    {SUITE_API_URL}/api/wa-auth/{slug}-{key}     -> { key, value } | 404
PUT    {SUITE_API_URL}/api/wa-auth/{slug}-{key}     body { value: "<json>" }
DELETE {SUITE_API_URL}/api/wa-auth/{slug}-{key}
```

`value` es el auth-state serializado con `BufferJSON` (JSON string). El cache en
memoria hace reads sync (anti-PreKeyError) y fetch-through en cache frio tras un
restart. Ver `src/remoteAuthState.js`.

---

## Variables de entorno

| Var | Requerida | Descripcion |
|-----|-----------|-------------|
| `SUITE_API_URL` | si | Origen de la suite **SIN** `/api` (ej `https://tasar-api.run.app`). |
| `WA_GATEWAY_KEY` | si | Secreto compartido gateway<->suite (X-API-Key). |
| `WEBHOOK_URL` | no | Override del webhook de entrantes. Default `{SUITE_API_URL}/api/whatsapp/webhook/incoming`. |
| `CLOUDINARY_CLOUD_NAME` | no* | Cloudinary — sin las 3, la media entrante va con `media_url=null`. |
| `CLOUDINARY_API_KEY` | no* | " |
| `CLOUDINARY_API_SECRET` | no* | " |
| `PORT` | no | Default 8080 (Cloud Run lo inyecta). |
| `LOG_LEVEL` | no | pino level, default `info`. |
| `WA_DECRYPT_ERROR_THRESHOLD` | no | Errores de descifrado antes de auto-reconnect (default 3). |
| `WA_DECRYPT_ERROR_WINDOW_MS` | no | Ventana rolling del contador (default 300000). |
| `WA_SENT_CACHE_SIZE` | no | Tamano del cache de mensajes enviados para retry (default 2000). |

## Local

```
npm install
SUITE_API_URL=http://localhost:8600 WA_GATEWAY_KEY=dev PORT=8080 npm start
```

## Deploy

Docker (Node 20) via `Dockerfile`. El deploy lo dispara **Infra** en la etapa E1
(NO deployar desde este WO).
