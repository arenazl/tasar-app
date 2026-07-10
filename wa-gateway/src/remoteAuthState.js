/**
 * remoteAuthState — persiste el authState de Baileys contra la suite TasAR.
 *
 * Portado de SalesBot/baileys/src/remoteAuthState.js (WO F0-05). Diferencias
 * clave con el original:
 *
 *   1. Store single-key en vez de bulk. La suite expone un key-value plano
 *      (espejo de AgentFlow baileys_auth):
 *        GET    {SUITE_API}/api/wa-auth/{key}   -> { key, value } | 404
 *        PUT    {SUITE_API}/api/wa-auth/{key}   body { value: "<json>" }
 *        DELETE {SUITE_API}/api/wa-auth/{key}
 *      No hay endpoint /bulk-sessions, asi que reemplazamos el bulk-load inicial
 *      por fetch-through: `keys.get` lee del cache y, si falla (cache frio tras
 *      un restart), hace un GET puntual y popula el cache. Esto conserva la
 *      propiedad anti-PreKeyError (reads sync desde cache dentro de la sesion)
 *      sin depender de un endpoint bulk.
 *
 *   2. Keys prefijadas con `{workspace_slug}-` para namespacing por tenant en
 *      la tabla comun `wa_sessions`.
 *
 *   3. value se guarda como JSON string (columna Text), sin base64.
 */
const axios = require('axios')
const { initAuthCreds, BufferJSON, proto } = require('@whiskeysockets/baileys')

function buildClient({ apiUrl, apiKey }) {
  return axios.create({
    baseURL: apiUrl.replace(/\/$/, ''),
    headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
    timeout: 30000,
  })
}

function keyToPath(category, id) {
  const safeCat = String(category).replace(/[^a-z0-9-]/gi, '_')
  const safeId = String(id).replace(/[^a-z0-9._-]/gi, '_')
  return `${safeCat}__${safeId}`
}

async function makeRemoteAuthState({ apiUrl, apiKey, slug, logger }) {
  const client = buildClient({ apiUrl, apiKey })

  // Prefijo de tenant para namespacing en la tabla comun wa_sessions.
  const prefix = `${slug}-`
  const remoteKey = (localKey) => `${prefix}${localKey}`
  const encode = (k) => encodeURIComponent(remoteKey(k))

  // ─── Cache en memoria ────────────────────────────────────────────────
  // localKey (string) → parsed object. Reads sync desde aca.
  const cache = new Map()

  // ─── Cola de escrituras background ─────────────────────────────────
  const writeQueue = new Map()  // localKey → latest value pending
  const deleteQueue = new Set() // localKeys pendientes de borrar
  let flushTimer = null
  let flushing = false

  async function putRemote(localKey, value) {
    await client.put(`/api/wa-auth/${encode(localKey)}`, {
      value: JSON.stringify(value, BufferJSON.replacer),
    })
  }

  async function deleteRemote(localKey) {
    await client.delete(`/api/wa-auth/${encode(localKey)}`)
  }

  async function getRemote(localKey) {
    try {
      const r = await client.get(`/api/wa-auth/${encode(localKey)}`)
      if (r.data && typeof r.data.value === 'string') {
        return JSON.parse(r.data.value, BufferJSON.reviver)
      }
      return null
    } catch (e) {
      if (e?.response?.status === 404) return null
      logger?.warn({ slug, localKey, err: e.message }, '[authState] getRemote fallo')
      return null
    }
  }

  async function flushOnce() {
    if (flushing) return
    if (writeQueue.size === 0 && deleteQueue.size === 0) return
    flushing = true
    const writes = Array.from(writeQueue.entries())
    const deletes = Array.from(deleteQueue)
    writeQueue.clear()
    deleteQueue.clear()
    try {
      // Single-key: un PUT/DELETE por clave. La coalescencia por Map ya dedupea
      // escrituras rapidas a la misma clave antes de este flush.
      await Promise.all([
        ...writes.map(([k, v]) =>
          putRemote(k, v).catch((e) =>
            logger?.error({ slug, key: k, err: e.message }, '[authState] write fail')
          )
        ),
        ...deletes.map((k) =>
          deleteRemote(k).catch((e) =>
            logger?.warn({ slug, key: k, err: e.message }, '[authState] delete fail')
          )
        ),
      ])
    } finally {
      flushing = false
      // Si quedo algo nuevo encolado mientras flusheaba, re-disparar.
      if (writeQueue.size > 0 || deleteQueue.size > 0) scheduleFlush()
    }
  }

  function scheduleFlush() {
    if (flushTimer) return
    flushTimer = setTimeout(() => {
      flushTimer = null
      flushOnce().catch((e) => logger?.error({ slug, err: e.message }, '[authState] flush error'))
    }, 80)  // agrupamos escrituras de los proximos 80ms
  }

  function readSync(localKey) {
    return cache.get(localKey) || null
  }

  function writeMemAndQueue(localKey, value) {
    cache.set(localKey, value)
    writeQueue.set(localKey, value)
    deleteQueue.delete(localKey)
    scheduleFlush()
  }

  function deleteMemAndQueue(localKey) {
    cache.delete(localKey)
    writeQueue.delete(localKey)
    deleteQueue.add(localKey)
    scheduleFlush()
  }

  // ─── Creds ──────────────────────────────────────────────────────────
  // Cache frio: intentamos leer creds del backend antes de generar nuevas.
  let creds = await getRemote('creds')
  if (creds) {
    cache.set('creds', creds)
  } else {
    creds = initAuthCreds()
    writeMemAndQueue('creds', creds)
    await flushOnce()  // grabar creds inicial de una
  }

  // ─── Public API ────────────────────────────────────────────────────
  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
          const out = {}
          // 1) Resolver los que ya estan en cache; juntar los misses.
          const misses = []
          for (const id of ids) {
            const localKey = keyToPath(type, id)
            const cached = readSync(localKey)
            if (cached !== null) {
              out[id] = type === 'app-state-sync-key'
                ? proto.Message.AppStateSyncKeyData.fromObject(cached)
                : cached
            } else {
              misses.push({ id, localKey })
            }
          }
          // 2) Fetch-through de los misses (cache frio tras restart).
          if (misses.length > 0) {
            const fetched = await Promise.all(
              misses.map(({ localKey }) => getRemote(localKey))
            )
            misses.forEach(({ id, localKey }, i) => {
              const value = fetched[i]
              if (value !== null) {
                cache.set(localKey, value)
                out[id] = type === 'app-state-sync-key'
                  ? proto.Message.AppStateSyncKeyData.fromObject(value)
                  : value
              }
            })
          }
          return out
        },
        set: async (data) => {
          for (const category of Object.keys(data)) {
            for (const id of Object.keys(data[category])) {
              const value = data[category][id]
              const localKey = keyToPath(category, id)
              if (value) writeMemAndQueue(localKey, value)
              else deleteMemAndQueue(localKey)
            }
          }
          // No await — los writes son async background.
        },
      },
    },
    saveCreds: async () => {
      writeMemAndQueue('creds', creds)
    },
    // helper expuesto para forzar persistencia (util en shutdown)
    flush: flushOnce,
  }
}

module.exports = { makeRemoteAuthState }
