/**
 * Auto-update de la PWA sin reinstalar (WO F4-04).
 *
 * Compara la versión embebida en el build (`__APP_VERSION__`, generada por el
 * plugin `emit-version-json` de `vite.config.ts`) contra `version.json` servido
 * `no-store`. Si difieren, recarga UNA sola vez (guard anti-loop por versión).
 *
 * Referencia: base-compartida/6-GUIA-PWA.md — Nivel 1.
 */

const RELOAD_GUARD_PREFIX = 'tasar-reloaded-';

async function fetchServerVersion(): Promise<string | null> {
  try {
    const r = await fetch(`/version.json?_=${Date.now()}`, { cache: 'no-store' });
    if (!r.ok) return null;
    const data = (await r.json()) as { version?: string };
    return data.version ?? null;
  } catch {
    return null; // offline / error: no hacemos nada
  }
}

export function setupVersionCheck(): void {
  const current = __APP_VERSION__;

  const check = async () => {
    if (document.visibilityState !== 'visible') return;
    const server = await fetchServerVersion();
    if (!server || server === current) return;

    // Guard anti-loop: recargamos UNA vez por versión detectada.
    const guard = RELOAD_GUARD_PREFIX + server;
    if (sessionStorage.getItem(guard)) return;
    sessionStorage.setItem(guard, '1');
    location.reload();
  };

  check(); // al arrancar
  document.addEventListener('visibilitychange', check); // al volver a foco (PWA desde multitarea)
  window.addEventListener('focus', check);
}
