/**
 * tasar-wa-gateway — gateway WhatsApp unico (Baileys) para la suite inmobiliaria.
 *
 * Portado de SalesBot/baileys/src/index.js (WO F0-05). Multi-tenant: cada tenant
 * = workspace de la suite TasAR.
 *
 * Boot:
 *   1. GET {SUITE_API_URL}/api/wa/tenants -> workspaces con canal Baileys activo.
 *   2. Por cada slug, arranca un socket Baileys que persiste su auth-state contra
 *      {SUITE_API_URL}/api/wa-auth/{workspace_slug}-{key} (remoteAuthState).
 *
 * Runtime:
 *   - Mensajes entrantes -> POST {WEBHOOK_URL} (default {SUITE_API_URL}/api/whatsapp/webhook/incoming)
 *     con el contrato de-facto (ver README). El media se sube a Cloudinary aca y
 *     se manda como media_url (la suite NO recibe base64).
 *   - Mensajes salientes -> POST /send  body { tenant, telefono, contenido?, audio_url?, video_url?, ptt? }
 *   - QR / estado        -> /tenants/:slug/status | /qr | /start | /stop
 */
const express = require('express')
const axios = require('axios')
const pino = require('pino')
const QRCode = require('qrcode')
const cloudinary = require('cloudinary').v2
const { Boom } = require('@hapi/boom')
const {
  default: makeWASocket,
  fetchLatestBaileysVersion,
  DisconnectReason,
  downloadMediaMessage,
} = require('@whiskeysockets/baileys')

const { makeRemoteAuthState } = require('./remoteAuthState')

const PORT = parseInt(process.env.PORT || '8080', 10)
// Origen de la suite (SIN /api). Ej: https://tasar-api-xxxxx.run.app
const SUITE_API_URL = (process.env.SUITE_API_URL || 'http://localhost:8600').replace(/\/$/, '')
// Secreto compartido gateway<->suite (X-API-Key). Protege wa-auth/tenants en la
// suite y los endpoints Express de este gateway.
const WA_GATEWAY_KEY = process.env.WA_GATEWAY_KEY || ''
// URL del webhook de entrantes. Default derivado del origen de la suite.
const WEBHOOK_URL = (process.env.WEBHOOK_URL || `${SUITE_API_URL}/api/whatsapp/webhook/incoming`)

// Auto-reconnect por errores de descifrado Signal (ventana rolling).
const DECRYPT_ERROR_THRESHOLD = parseInt(process.env.WA_DECRYPT_ERROR_THRESHOLD || '3', 10)
const DECRYPT_ERROR_WINDOW_MS = parseInt(process.env.WA_DECRYPT_ERROR_WINDOW_MS || '300000', 10)
// Cache de mensajes enviados (key.id -> message) para responder retry receipts.
const MAX_CACHE = parseInt(process.env.WA_SENT_CACHE_SIZE || '2000', 10)

const logger = pino({ level: process.env.LOG_LEVEL || 'info' })

// Cliente HTTP hacia la suite (bootstrap tenants + webhook entrantes).
const suiteClient = axios.create({
  baseURL: SUITE_API_URL,
  headers: { 'X-API-Key': WA_GATEWAY_KEY, 'Content-Type': 'application/json' },
  // El webhook puede tardar (la suite llama IA/TTS en F2-03). Axios no reintenta.
  timeout: 90000,
})

// ─── Cloudinary (upload de media entrante) ─────────────────────────────
const CLOUDINARY_ENABLED = !!(
  process.env.CLOUDINARY_CLOUD_NAME &&
  process.env.CLOUDINARY_API_KEY &&
  process.env.CLOUDINARY_API_SECRET
)
if (CLOUDINARY_ENABLED) {
  cloudinary.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET,
    secure: true,
  })
} else {
  logger.warn('[cloudinary] CLOUDINARY_* incompleto — media entrante ira con media_url=null')
}

// tipo Baileys -> resource_type Cloudinary
function cloudinaryResourceType(tipo) {
  if (tipo === 'image') return 'image'
  if (tipo === 'audio' || tipo === 'video') return 'video' // Cloudinary trata audio como 'video'
  return 'raw' // document / otros
}

function uploadToCloudinary(buffer, tipo) {
  return new Promise((resolve, reject) => {
    const stream = cloudinary.uploader.upload_stream(
      { resource_type: cloudinaryResourceType(tipo), folder: 'tasar-wa' },
      (err, result) => (err ? reject(err) : resolve(result))
    )
    stream.end(buffer)
  })
}

// slug -> { sock, state, qr?, numero?, sentMessagesCache }
const sessions = new Map()
// slug -> timestamps de errores de descifrado en ventana rolling.
const decryptErrors = new Map()

function recordDecryptError(slug) {
  const now = Date.now()
  const arr = decryptErrors.get(slug) || []
  const filtered = arr.filter((t) => now - t < DECRYPT_ERROR_WINDOW_MS)
  filtered.push(now)
  decryptErrors.set(slug, filtered)
  if (filtered.length >= DECRYPT_ERROR_THRESHOLD) {
    logger.warn({ slug, count: filtered.length, threshold: DECRYPT_ERROR_THRESHOLD },
      '[auto-reconnect] decrypt threshold alcanzado — forzando reconnect')
    decryptErrors.set(slug, [])
    const s = sessions.get(slug)
    if (s?.sock) {
      try { s.sock.end(new Error('auto-reconnect: decrypt threshold')) }
      catch (e) { logger.error({ slug, err: e.message }, '[auto-reconnect] error cerrando socket') }
    }
  }
}

const DECRYPT_ERROR_PATTERNS = [
  /failed to decrypt/i,
  /MessageCounterError/i,
  /Key used already or never filled/i,
  /SessionError/i,
  /Bad MAC/i,
]

function isDecryptError(obj) {
  try {
    const msg = obj?.msg || ''
    const errMsg = obj?.err?.message || obj?.error?.message || ''
    return DECRYPT_ERROR_PATTERNS.some((re) => re.test(`${msg} ${errMsg}`))
  } catch (_) {
    return false
  }
}

// Logger proxy: intercepta error/warn para detectar fallos de descifrado por slug.
function makeLoggerProxy(baseChild, slug) {
  const proxy = Object.create(baseChild)
  for (const level of ['error', 'warn']) {
    const orig = baseChild[level].bind(baseChild)
    proxy[level] = function (objOrMsg, ...rest) {
      try {
        if (objOrMsg && typeof objOrMsg === 'object' && isDecryptError(objOrMsg)) {
          recordDecryptError(slug)
        }
      } catch (_) { /* never break log */ }
      return orig(objOrMsg, ...rest)
    }
  }
  const origChild = baseChild.child.bind(baseChild)
  proxy.child = function (...args) {
    return makeLoggerProxy(origChild(...args), slug)
  }
  return proxy
}

function jidToPhone(jid) {
  if (!jid) return null
  return jid.split('@')[0].split(':')[0]
}

function buildOutgoingJid(telefono) {
  if (!telefono) return null
  if (telefono.includes('@')) return telefono
  const digits = String(telefono).replace(/[^\d]/g, '')
  if (!digits) return null
  return `${digits}@s.whatsapp.net`
}

function inferTipo(msg) {
  const m = msg.message || {}
  if (m.audioMessage) return 'audio'
  if (m.imageMessage) return 'image'
  if (m.videoMessage) return 'video'
  if (m.documentMessage) return 'document'
  return 'text'
}

function extractText(msg) {
  const m = msg.message || {}
  return (
    m.conversation
    || m.extendedTextMessage?.text
    || m.imageMessage?.caption
    || m.videoMessage?.caption
    || null
  )
}

async function reportIncoming(slug, payload) {
  try {
    await suiteClient.post(WEBHOOK_URL, payload)
  } catch (e) {
    logger.error({ slug, status: e?.response?.status, err: e.message },
      '[incoming] error posteando webhook a la suite')
  }
}

async function startSession(slug) {
  if (sessions.get(slug)?.state === 'open') {
    logger.info({ slug }, '[session] ya esta abierta')
    return sessions.get(slug)
  }

  logger.info({ slug }, '[session] arrancando…')
  const auth = await makeRemoteAuthState({
    apiUrl: SUITE_API_URL,
    apiKey: WA_GATEWAY_KEY,
    slug,
    logger,
  })
  const { version } = await fetchLatestBaileysVersion()

  const sentMessagesCache = new Map()  // key.id -> message (para retry receipts)

  const sock = makeWASocket({
    version,
    auth: auth.state,
    logger: makeLoggerProxy(logger.child({ slug }), slug),
    printQRInTerminal: false,
    syncFullHistory: false,
    markOnlineOnConnect: true,
    // getMessage: Baileys lo llama cuando el receptor pide retry de un mensaje
    // que no pudo descifrar; devolverlo re-cifra y reenvia (fixea "Esperando
    // este mensaje"). Portado de SalesBot (index.js ~238-247).
    getMessage: async (key) => {
      const cached = sentMessagesCache.get(key.id)
      if (cached) {
        logger.info({ slug, id: key.id }, '[getMessage] cache HIT — re-enviando para retry')
        return cached
      }
      logger.warn({ slug, id: key.id }, '[getMessage] cache MISS — placeholder')
      return { conversation: '' }
    },
  })

  const session = { sock, state: 'connecting', qr: null, numero: null, sentMessagesCache }
  sessions.set(slug, session)

  sock.ev.on('creds.update', auth.saveCreds)

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update
    if (qr) {
      try {
        session.qr = await QRCode.toDataURL(qr)
        logger.info({ slug }, '[session] QR generado')
      } catch (e) {
        logger.error({ slug, err: e.message }, '[session] error generando QR')
      }
    }
    if (connection === 'open') {
      session.state = 'open'
      session.qr = null
      session.numero = jidToPhone(sock.user?.id)
      decryptErrors.set(slug, [])
      logger.info({ slug, numero: session.numero }, '[session] conectado')
    } else if (connection === 'close') {
      session.state = 'close'
      const code = (lastDisconnect?.error instanceof Boom)
        ? lastDisconnect.error.output?.statusCode
        : undefined
      logger.warn({ slug, code }, '[session] desconectado')
      if (code !== DisconnectReason.loggedOut) {
        setTimeout(() => startSession(slug).catch((e) =>
          logger.error({ slug, err: e.message }, '[session] reconnect fail')), 5000)
      } else {
        sessions.delete(slug)
      }
    }
  })

  sock.ev.on('messages.upsert', async (m) => {
    if (m.type !== 'notify') return
    for (const msg of m.messages) {
      if (msg.key.fromMe) continue
      const rawJid = msg.key.remoteJid
      if (!rawJid || rawJid.endsWith('@g.us') || rawJid.endsWith('@broadcast')) continue

      const senderPn = msg.key.senderPn || msg.senderPn || null
      const usableJid = (rawJid.endsWith('@lid') && senderPn) ? senderPn : rawJid

      // GUARD: msg.message null = Signal no pudo descifrar. NO reportar; Baileys
      // ya mando retry receipt y este handler se re-dispara con el payload lleno.
      if (!msg.message) {
        logger.warn({ slug, id: msg.key.id, jid: usableJid },
          '[incoming] mensaje sin descifrar — esperando retry')
        continue
      }

      const tipo = inferTipo(msg)
      const contenido = extractText(msg) || ''

      // Media: descargar y subir a Cloudinary -> media_url (la suite NO recibe b64).
      let mediaUrl = null
      if (tipo === 'audio' || tipo === 'image' || tipo === 'video' || tipo === 'document') {
        try {
          const buf = await downloadMediaMessage(msg, 'buffer', {}, {
            logger,
            reuploadRequest: sock.updateMediaMessage,
          })
          if (buf && buf.length > 0 && CLOUDINARY_ENABLED) {
            const up = await uploadToCloudinary(buf, tipo)
            mediaUrl = up?.secure_url || null
            logger.info({ slug, tipo, size: buf.length, url: mediaUrl }, '[incoming] media subida a Cloudinary')
          } else if (buf && buf.length > 0) {
            logger.warn({ slug, tipo }, '[incoming] media descargada pero Cloudinary off — media_url=null')
          }
        } catch (e) {
          logger.error({ slug, tipo, err: e.message }, '[incoming] error con media')
        }
      }

      // ── CONTRATO WEBHOOK (de-facto, ver README) ──
      const payload = {
        tenant: slug,                                   // workspace slug
        telefono: usableJid,                            // JID del contacto
        phone_publico: session.numero,                  // numero publico del tenant (la agencia)
        nombre_contacto: msg.pushName || null,
        contenido,
        tipo,                                           // text|audio|image|video|document
        media_url: mediaUrl,
        meta_message_id: msg.key.id,
        timestamp: msg.messageTimestamp ? Number(msg.messageTimestamp) : null,
      }
      reportIncoming(slug, payload)
    }
  })

  return session
}

async function stopSession(slug, { logout = false } = {}) {
  const s = sessions.get(slug)
  if (!s || !s.sock) {
    sessions.delete(slug)
    return { modo: 'no_session' }
  }
  if (logout) {
    try {
      await s.sock.logout()
      logger.info({ slug }, '[logout] sock.logout() OK')
    } catch (e) {
      logger.warn({ slug, err: e.message }, '[logout] sock.logout() fallo — descartando igual')
    }
  }
  try { s.sock.end(new Error(logout ? 'explicit logout' : 'explicit stop')) } catch (_) {}
  sessions.delete(slug)
  return { modo: logout ? 'logout_ok' : 'stopped' }
}

async function bootSessions() {
  try {
    const r = await suiteClient.get('/api/wa/tenants')
    const apps = Array.isArray(r.data) ? r.data : (r.data?.items || [])
    logger.info({ count: apps.length }, '[boot] arrancando sesiones')
    for (const app of apps) {
      const slug = app.slug || app.workspace_slug
      if (!slug) continue
      startSession(slug).catch((e) => logger.error({ slug, err: e.message }, '[boot] fail'))
    }
  } catch (e) {
    logger.error({ status: e?.response?.status, err: e.message },
      '[boot] no pude leer /api/wa/tenants, sigo sin sesiones precreadas')
  }
}

// ---------- HTTP server ----------

const app = express()
app.use(express.json({ limit: '5mb' }))

// Auth X-API-Key (o ?key= para el iframe del QR). /health queda abierto.
app.use((req, res, next) => {
  if (req.path === '/health') return next()
  if (!WA_GATEWAY_KEY) return next()  // dev sin secreto
  const provided = req.headers['x-api-key'] || req.query.key
  if (provided !== WA_GATEWAY_KEY) {
    return res.status(401).json({ ok: false, error: 'invalid X-API-Key' })
  }
  next()
})

app.get('/health', (_req, res) => {
  const status = {}
  for (const [slug, s] of sessions) status[slug] = { state: s.state, numero: s.numero }
  res.json({ ok: true, service: 'tasar-wa-gateway', sessions: status })
})

app.get('/tenants/:slug/status', (req, res) => {
  const { slug } = req.params
  const s = sessions.get(slug)
  res.json({
    slug,
    state: s?.state || 'none',
    isReady: s?.state === 'open',
    hasPendingQR: !!s?.qr,
    numero: s?.numero || null,
    started: !!s,
  })
})

app.post('/tenants/:slug/start', async (req, res) => {
  try {
    const s = await startSession(req.params.slug)
    res.json({ ok: true, state: s.state })
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  }
})

app.post('/tenants/:slug/stop', async (req, res) => {
  try {
    const r = await stopSession(req.params.slug, { logout: false })
    res.json({ ok: true, ...r })
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  }
})

app.post('/tenants/:slug/logout', async (req, res) => {
  try {
    const r = await stopSession(req.params.slug, { logout: true })
    res.json({ ok: true, ...r })
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message })
  }
})

// QR como pagina HTML (la suite la embebe en un iframe). Acepta ?key= para el iframe.
app.get('/tenants/:slug/qr', async (req, res) => {
  const { slug } = req.params
  let session = sessions.get(slug)
  if (!session) {
    try { session = await startSession(slug) }
    catch (e) {
      return res.status(200).send(htmlWrap(`<h3>Error</h3><p>${e.message}</p>`, 'crimson'))
    }
  }
  if (session.state === 'open') {
    return res.send(htmlWrap(`<h3>Conectado</h3><p>Numero: ${session.numero || '-'}</p>`, '#16a34a'))
  }
  if (session.qr) {
    return res.send(htmlWrap(`<img src="${session.qr}" alt="QR" style="max-width:320px;width:100%" />
      <p>Escanea con WhatsApp &gt; Dispositivos vinculados</p>`))
  }
  return res.send(htmlWrap('<h3>Generando QR…</h3><p>Refresca en unos segundos.</p>', '#888'))
})

function htmlWrap(inner, color = '#111') {
  return `<html><body style="font-family:sans-serif;padding:2rem;text-align:center;color:${color}">${inner}</body></html>`
}

app.post('/send', async (req, res) => {
  const { tenant, app: appAlias, telefono, contenido, audio_url, video_url, ptt } = req.body || {}
  const slug = tenant || appAlias  // acepta 'tenant' (preferido) o 'app' (compat)
  if (!slug || !telefono) {
    return res.status(400).json({ ok: false, error: 'tenant + telefono requeridos' })
  }
  const session = sessions.get(slug)
  if (!session || session.state !== 'open') {
    return res.status(409).json({ ok: false, error: `sesion '${slug}' no conectada (state=${session?.state || 'none'})` })
  }
  const jid = buildOutgoingJid(telefono)
  if (!jid) return res.status(400).json({ ok: false, error: 'telefono invalido' })

  try {
    let result
    if (audio_url) {
      result = await session.sock.sendMessage(jid, {
        audio: { url: audio_url },
        ptt: ptt !== false,
        mimetype: 'audio/ogg; codecs=opus',
      })
      if (contenido) {
        const r2 = await session.sock.sendMessage(jid, { text: contenido })
        if (r2?.message && r2?.key?.id) session.sentMessagesCache.set(r2.key.id, r2.message)
      }
    } else if (video_url) {
      result = await session.sock.sendMessage(jid, {
        video: { url: video_url },
        mimetype: 'video/mp4',
        caption: contenido || '',
      })
    } else {
      result = await session.sock.sendMessage(jid, { text: contenido || '' })
    }
    if (result?.message && result?.key?.id) {
      session.sentMessagesCache.set(result.key.id, result.message)
      if (session.sentMessagesCache.size > MAX_CACHE) {
        const firstKey = session.sentMessagesCache.keys().next().value
        session.sentMessagesCache.delete(firstKey)
      }
    }
    res.json({ ok: true, meta_message_id: result?.key?.id || null })
  } catch (e) {
    logger.error({ slug, telefono, err: e.message }, '[send] fail')
    res.status(500).json({ ok: false, error: e.message })
  }
})

app.listen(PORT, () => {
  logger.info({ port: PORT, suite: SUITE_API_URL, webhook: WEBHOOK_URL }, '[tasar-wa-gateway] up')
  bootSessions()
})
