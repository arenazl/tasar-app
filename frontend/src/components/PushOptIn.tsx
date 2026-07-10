import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Bell, X } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

// Convierte base64url -> Uint8Array (formato que pide PushManager.subscribe).
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from(rawData, (c) => c.charCodeAt(0));
}

const DISMISS_KEY = 'tasar_push_dismissed_until';
const DISMISS_DAYS_MS = 7 * 86400000;

/**
 * Banner de opt-in para Web Push (WO F3-03). Se muestra a vendedores/
 * supervisores (los que reciben leads/derivaciones/visitas del bot) — el rol
 * admin no gestiona conversaciones y no lo necesita. Registra la suscripción
 * contra POST /api/push/subscribe; el SW ya se registró en main.tsx.
 */
export function PushOptIn() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user || user.role === 'admin') return;
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
    if (Notification.permission === 'denied') return;

    if (Notification.permission === 'granted') {
      verifyAndSubscribe();
      return;
    }

    const dismissedUntil = parseInt(localStorage.getItem(DISMISS_KEY) || '0', 10);
    if (dismissedUntil > Date.now()) return;

    setShow(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const verifyAndSubscribe = async () => {
    try {
      const reg = await navigator.serviceWorker.ready;
      const existing = await reg.pushManager.getSubscription();
      if (existing) {
        const json = existing.toJSON() as any;
        await api.post('/push/subscribe', {
          endpoint: json.endpoint,
          keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
        });
      } else {
        await activarPush();
      }
    } catch (e) {
      console.warn('[push] verifyAndSubscribe:', e);
    }
  };

  const activarPush = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        toast.info('Permiso de notificaciones rechazado');
        setShow(false);
        localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DAYS_MS));
        return;
      }

      const reg = await navigator.serviceWorker.ready;
      const vapidR = await api.get('/push/vapid-public-key');
      const vapidKey = vapidR.data.public_key;
      if (!vapidKey) {
        toast.error('El servidor no tiene VAPID configurada');
        return;
      }

      const sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidKey) as BufferSource,
      });

      const json = sub.toJSON() as any;
      await api.post('/push/subscribe', {
        endpoint: json.endpoint,
        keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
      });

      toast.success('Notificaciones activadas');
      setShow(false);
    } catch (e: any) {
      console.error('[push] activar error:', e);
      toast.error('No se pudieron activar las notificaciones');
    } finally {
      setBusy(false);
    }
  };

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now() + DISMISS_DAYS_MS));
    setShow(false);
  };

  if (!show || !user) return null;

  return (
    <div
      className="fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-96 z-50 rounded-xl shadow-2xl p-4 animate-in fade-in slide-in-from-bottom-2 duration-300"
      style={{ background: theme.card, border: `1px solid ${theme.primary}40` }}
    >
      <div className="flex items-start gap-3">
        <div
          className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
          style={{ backgroundColor: `${theme.primary}20` }}
        >
          <Bell className="h-5 w-5" style={{ color: theme.primary }} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-bold text-sm mb-0.5" style={{ color: theme.text }}>
            Activá las notificaciones
          </h3>
          <p className="text-xs mb-3" style={{ color: theme.textSecondary }}>
            Te avisamos al instante cuando te asignan un lead, te derivan una conversación o se agenda una visita — aunque tengas la app cerrada.
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={activarPush}
              disabled={busy}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
              style={{ background: theme.primary, color: theme.primaryText }}
            >
              {busy ? 'Activando...' : 'Activar'}
            </button>
            <button
              onClick={dismiss}
              className="px-3 py-1.5 rounded-lg text-xs"
              style={{ border: `1px solid ${theme.border}`, color: theme.textSecondary }}
            >
              Después
            </button>
          </div>
        </div>
        <button
          onClick={dismiss}
          className="p-1 rounded-md flex-shrink-0"
          style={{ color: theme.textSecondary }}
          aria-label="Cerrar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

export function PushTestButton() {
  const { theme } = useTheme();
  const test = async () => {
    const t = toast.loading('Enviando push de prueba...');
    try {
      await api.post('/push/test');
      toast.dismiss(t);
      toast.success('Push enviado, esperá la notificación');
    } catch {
      toast.dismiss(t);
      toast.error('Error al enviar el push (¿tenés notificaciones activadas?)');
    }
  };
  return (
    <button
      onClick={test}
      className="mt-2 w-full px-3 py-2 rounded-lg text-xs font-bold transition-all active:scale-95"
      style={{ background: `${theme.primary}15`, color: theme.primary, border: `1px solid ${theme.primary}30` }}
    >
      Enviar push de prueba
    </button>
  );
}
