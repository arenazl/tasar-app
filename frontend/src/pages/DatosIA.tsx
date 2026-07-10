import { useEffect, useState, useCallback } from 'react';
import {
  Bot, Building2, MessageSquare, Clock, HelpCircle, Plug, Check, Loader2,
  Plus, Trash2, Power, RefreshCw, QrCode, Smartphone, ShieldCheck, AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../services/api';

interface BotConfig {
  enabled: boolean;
  business_name: string | null;
  business_description: string | null;
  address: string | null;
  zones: string | null;
  phone: string | null;
  email: string | null;
  website: string | null;
  services: string | null;
  commissions_text: string | null;
  differentials: string | null;
  welcome_message: string | null;
  off_hours_message: string | null;
  derivation_message: string | null;
  business_hours: string | null;
  derivation_words: string | null;
  tone: string | null;
  channel_provider: string | null;
  meta_phone_number_id: string | null;
  meta_configured: boolean;
}

interface Faq {
  id: number;
  question: string;
  answer: string;
  priority: number;
  is_active: boolean;
}

interface WaStatus {
  slug: string;
  state: string;
  isReady: boolean;
  hasPendingQR: boolean;
  numero: string | null;
  started: boolean;
}

type TabId = 'negocio' | 'mensajes' | 'horario' | 'faqs' | 'conexion';

const TABS: { id: TabId; label: string; icon: typeof Bot }[] = [
  { id: 'negocio', label: 'Negocio', icon: Building2 },
  { id: 'mensajes', label: 'Mensajes', icon: MessageSquare },
  { id: 'horario', label: 'Horario / Derivación', icon: Clock },
  { id: 'faqs', label: 'FAQs', icon: HelpCircle },
  { id: 'conexion', label: 'Conexión', icon: Plug },
];

const TONES = ['profesional', 'cercano', 'formal'];

export default function DatosIA() {
  const { theme } = useTheme();
  const [tab, setTab] = useState<TabId>('negocio');
  const [cfg, setCfg] = useState<BotConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<BotConfig>('/bot-config');
      setCfg(r.data);
    } catch {
      toast.error('No se pudo cargar la configuración del bot');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const patch = (field: keyof BotConfig, value: string | boolean) => {
    setCfg((c) => (c ? { ...c, [field]: value } : c));
  };

  const save = async () => {
    if (!cfg) return;
    setSaving(true);
    try {
      const r = await api.put<BotConfig>('/bot-config', cfg);
      setCfg(r.data);
      toast.success('Configuración guardada');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar');
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async () => {
    if (!cfg) return;
    const next = !cfg.enabled;
    patch('enabled', next);
    try {
      await api.put('/bot-config', { enabled: next });
      toast.success(next ? 'Bot activado' : 'Bot desactivado');
    } catch (e: any) {
      patch('enabled', !next);
      toast.error(e.response?.data?.detail || 'No se pudo cambiar el estado');
    }
  };

  if (loading || !cfg) {
    return (
      <div className="flex items-center justify-center h-64" style={{ color: theme.textSecondary }}>
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto animate-fade-in">
      <header className="mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
            <Bot className="h-7 w-7" style={{ color: theme.primary }} /> Datos IA · Bot de WhatsApp
          </h1>
          <p className="mt-1" style={{ color: theme.textSecondary }}>
            Configurá cómo responde el asistente virtual de tu inmobiliaria
          </p>
        </div>
        <button
          onClick={toggleEnabled}
          className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all active:scale-95"
          style={{
            background: cfg.enabled ? `${theme.primary}15` : theme.backgroundSecondary,
            color: cfg.enabled ? theme.primary : theme.textSecondary,
            border: `1px solid ${cfg.enabled ? theme.primary : theme.border}`,
          }}
        >
          <Power className="h-4 w-4" />
          {cfg.enabled ? 'Bot activo' : 'Bot inactivo'}
        </button>
      </header>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 overflow-x-auto pb-1">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = t.id === tab;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className="px-3.5 py-2 rounded-lg text-sm font-semibold flex items-center gap-1.5 whitespace-nowrap transition-all"
              style={{
                background: active ? theme.primary : theme.backgroundSecondary,
                color: active ? theme.primaryText : theme.textSecondary,
              }}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>

      <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        {tab === 'negocio' && (
          <div className="space-y-4">
            <Field theme={theme} label="Nombre del negocio" value={cfg.business_name} onChange={(v) => patch('business_name', v)} />
            <Field theme={theme} label="Sobre nosotros" value={cfg.business_description} onChange={(v) => patch('business_description', v)} textarea />
            <Field theme={theme} label="Servicios que ofrecen" value={cfg.services} onChange={(v) => patch('services', v)} textarea />
            <Field theme={theme} label="Diferenciales (por qué elegirlos)" value={cfg.differentials} onChange={(v) => patch('differentials', v)} textarea />
            <Field theme={theme} label="Comisiones / honorarios" value={cfg.commissions_text} onChange={(v) => patch('commissions_text', v)} textarea />
            <Field theme={theme} label="Zonas / barrios donde operan" value={cfg.zones} onChange={(v) => patch('zones', v)} textarea />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field theme={theme} label="Dirección" value={cfg.address} onChange={(v) => patch('address', v)} />
              <Field theme={theme} label="Teléfono" value={cfg.phone} onChange={(v) => patch('phone', v)} />
              <Field theme={theme} label="Email" value={cfg.email} onChange={(v) => patch('email', v)} />
              <Field theme={theme} label="Web" value={cfg.website} onChange={(v) => patch('website', v)} />
            </div>
          </div>
        )}

        {tab === 'mensajes' && (
          <div className="space-y-4">
            <Field theme={theme} label="Mensaje de bienvenida" hint="Usá {negocio} para el nombre del negocio" value={cfg.welcome_message} onChange={(v) => patch('welcome_message', v)} textarea />
            <Field theme={theme} label="Mensaje fuera de horario" value={cfg.off_hours_message} onChange={(v) => patch('off_hours_message', v)} textarea />
            <Field theme={theme} label="Mensaje al derivar a un asesor" value={cfg.derivation_message} onChange={(v) => patch('derivation_message', v)} textarea />
          </div>
        )}

        {tab === 'horario' && (
          <div className="space-y-4">
            <Field theme={theme} label="Horario de atención" value={cfg.business_hours} onChange={(v) => patch('business_hours', v)} textarea />
            <Field theme={theme} label="Palabras que disparan derivación" hint="Separadas por coma" value={cfg.derivation_words} onChange={(v) => patch('derivation_words', v)} textarea />
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Tono</div>
              <div className="flex gap-2">
                {TONES.map((t) => (
                  <button key={t} onClick={() => patch('tone', t)}
                    className="px-3 py-2 rounded-lg text-sm font-medium capitalize transition-all active:scale-95"
                    style={{
                      background: cfg.tone === t ? `${theme.primary}15` : theme.backgroundSecondary,
                      color: cfg.tone === t ? theme.primary : theme.textSecondary,
                      border: `2px solid ${cfg.tone === t ? theme.primary : 'transparent'}`,
                    }}>
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === 'faqs' && <FaqsTab theme={theme} />}

        {tab === 'conexion' && <ConexionTab theme={theme} cfg={cfg} reload={load} />}

        {tab !== 'faqs' && tab !== 'conexion' && (
          <div className="mt-6 flex justify-end">
            <button onClick={save} disabled={saving}
              className="px-5 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 disabled:opacity-50 transition-all active:scale-95"
              style={{ background: theme.primary, color: theme.primaryText }}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Guardar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ theme, label, value, onChange, textarea, hint }: {
  theme: any; label: string; value: string | null; onChange: (v: string) => void; textarea?: boolean; hint?: string;
}) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>
        {label}{hint && <span className="normal-case font-normal ml-2 opacity-70">· {hint}</span>}
      </div>
      {textarea ? (
        <textarea value={value || ''} onChange={(e) => onChange(e.target.value)} rows={3}
          className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 resize-y"
          style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' }} />
      ) : (
        <input value={value || ''} onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2"
          style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' }} />
      )}
    </div>
  );
}

function FaqsTab({ theme }: { theme: any }) {
  const [faqs, setFaqs] = useState<Faq[]>([]);
  const [q, setQ] = useState('');
  const [a, setA] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get<Faq[]>('/bot-config/faqs');
      setFaqs(r.data);
    } catch { /* noop */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  const add = async () => {
    if (!q.trim() || !a.trim()) { toast.error('Completá pregunta y respuesta'); return; }
    setBusy(true);
    try {
      await api.post('/bot-config/faqs', { question: q, answer: a, priority: 0, is_active: true });
      setQ(''); setA('');
      await load();
      toast.success('FAQ agregada');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo agregar');
    } finally { setBusy(false); }
  };

  const remove = async (id: number) => {
    try {
      await api.delete(`/bot-config/faqs/${id}`);
      await load();
    } catch { toast.error('No se pudo borrar'); }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2 p-4 rounded-lg" style={{ background: theme.backgroundSecondary }}>
        <Field theme={theme} label="Pregunta" value={q} onChange={setQ} />
        <Field theme={theme} label="Respuesta" value={a} onChange={setA} textarea />
        <button onClick={add} disabled={busy}
          className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 disabled:opacity-50 active:scale-95"
          style={{ background: theme.primary, color: theme.primaryText }}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Agregar FAQ
        </button>
      </div>
      {faqs.length === 0 ? (
        <div className="text-sm text-center py-6" style={{ color: theme.textSecondary }}>
          Sin FAQs cargadas. Las FAQs tienen prioridad sobre el resto del conocimiento del bot.
        </div>
      ) : (
        <div className="space-y-2">
          {faqs.map((f) => (
            <div key={f.id} className="p-3 rounded-lg flex items-start justify-between gap-3" style={{ background: theme.backgroundSecondary }}>
              <div className="min-w-0">
                <div className="font-semibold text-sm" style={{ color: theme.text }}>{f.question}</div>
                <div className="text-sm mt-0.5" style={{ color: theme.textSecondary }}>{f.answer}</div>
              </div>
              <button onClick={() => remove(f.id)} className="p-1.5 rounded-lg flex-shrink-0" style={{ color: '#ef4444' }} title="Borrar">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ConexionTab({ theme, cfg, reload }: { theme: any; cfg: BotConfig; reload: () => Promise<void> }) {
  const [status, setStatus] = useState<WaStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [provider, setProvider] = useState<'baileys' | 'meta'>((cfg.channel_provider as 'baileys' | 'meta') || 'baileys');
  const [phoneNumberId, setPhoneNumberId] = useState(cfg.meta_phone_number_id || '');
  const [savingProvider, setSavingProvider] = useState(false);

  useEffect(() => {
    setProvider((cfg.channel_provider as 'baileys' | 'meta') || 'baileys');
    setPhoneNumberId(cfg.meta_phone_number_id || '');
  }, [cfg.channel_provider, cfg.meta_phone_number_id]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<WaStatus>('/wa/status');
      setStatus(r.data);
    } catch {
      setStatus(null);
    } finally { setLoading(false); }
  }, []);
  useEffect(() => { if (provider === 'baileys') refresh(); }, [refresh, provider]);

  const start = async () => {
    try { await api.post('/wa/start'); toast.success('Sesión iniciada'); refresh(); }
    catch (e: any) { toast.error(e.response?.data?.detail || 'No se pudo iniciar'); }
  };

  const openQr = async () => {
    try {
      const r = await api.get('/wa/qr.html', { responseType: 'text' });
      const blob = new Blob([r.data as string], { type: 'text/html' });
      window.open(URL.createObjectURL(blob), '_blank');
    } catch { toast.error('No se pudo abrir el QR'); }
  };

  const saveProvider = async () => {
    setSavingProvider(true);
    try {
      await api.put('/bot-config', {
        channel_provider: provider,
        meta_phone_number_id: phoneNumberId.trim() || null,
      });
      await reload();
      toast.success('Conexión actualizada');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar la conexión');
    } finally { setSavingProvider(false); }
  };

  const stateLabel: Record<string, string> = {
    open: 'Conectado', connecting: 'Conectando', close: 'Desconectado', none: 'Sin sesión',
  };
  const st = status?.state || 'none';
  const connected = st === 'open';

  return (
    <div className="space-y-5">
      {/* Selector de proveedor */}
      <div>
        <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>
          Proveedor de canal
        </div>
        <div className="flex gap-2">
          <button onClick={() => setProvider('baileys')}
            className="flex-1 px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95"
            style={{
              background: provider === 'baileys' ? `${theme.primary}15` : theme.backgroundSecondary,
              color: provider === 'baileys' ? theme.primary : theme.textSecondary,
              border: `2px solid ${provider === 'baileys' ? theme.primary : 'transparent'}`,
            }}>
            <Smartphone className="h-4 w-4" /> WhatsApp Web (Baileys)
          </button>
          <button onClick={() => setProvider('meta')}
            className="flex-1 px-3 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 transition-all active:scale-95"
            style={{
              background: provider === 'meta' ? `${theme.primary}15` : theme.backgroundSecondary,
              color: provider === 'meta' ? theme.primary : theme.textSecondary,
              border: `2px solid ${provider === 'meta' ? theme.primary : 'transparent'}`,
            }}>
            <ShieldCheck className="h-4 w-4" /> Meta Cloud API oficial
          </button>
        </div>
        <p className="text-xs mt-1.5" style={{ color: theme.textSecondary }}>
          Baileys es no oficial (riesgo de bloqueo del número). Meta Cloud API es el canal oficial de Meta — recomendado para producción.
        </p>
      </div>

      {provider === 'baileys' ? (
        <div className="space-y-4">
          <div className="p-4 rounded-lg" style={{ background: theme.backgroundSecondary }}>
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>Estado</div>
              <div className="font-semibold flex items-center gap-1.5"
                style={{ color: connected ? '#16a34a' : theme.textSecondary }}>
                <span className="w-2 h-2 rounded-full" style={{ background: connected ? '#16a34a' : theme.border }} />
                {stateLabel[st] || st}
              </div>
            </div>
            {status?.numero && (
              <div className="mt-3 text-sm" style={{ color: theme.textSecondary }}>
                Número conectado: <span style={{ color: theme.text }}>{status.numero}</span>
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={refresh} disabled={loading}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50 active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Actualizar estado
            </button>
            <button onClick={start}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
              <Power className="h-4 w-4" /> Iniciar sesión
            </button>
            {!connected && (
              <button onClick={openQr}
                className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 active:scale-95"
                style={{ background: theme.primary, color: theme.primaryText }}>
                <QrCode className="h-4 w-4" /> Escanear QR
              </button>
            )}
          </div>
          <p className="text-xs" style={{ color: theme.textSecondary }}>
            Escaneá el QR desde WhatsApp &gt; Dispositivos vinculados.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-3 rounded-lg flex items-start gap-2.5 text-sm"
            style={{
              background: cfg.meta_configured ? `${theme.primary}10` : '#f59e0b15',
              border: `1px solid ${cfg.meta_configured ? theme.border : '#f59e0b40'}`,
            }}>
            {cfg.meta_configured ? (
              <ShieldCheck className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: theme.primary }} />
            ) : (
              <AlertTriangle className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: '#f59e0b' }} />
            )}
            <div style={{ color: theme.text }}>
              {cfg.meta_configured
                ? 'El servidor tiene las credenciales de Meta (token, verify token y app secret) configuradas.'
                : 'El servidor todavía no tiene configuradas las credenciales de Meta (token de acceso, verify token y app secret). Pedile a Infraestructura que las cargue como variables de entorno — nunca se ingresan acá.'}
            </div>
          </div>

          <Field
            theme={theme}
            label="Phone Number ID de Meta"
            hint="El ID del número dentro de tu WhatsApp Business Account, no el número en sí"
            value={phoneNumberId}
            onChange={setPhoneNumberId}
          />

          <div className="flex justify-end">
            <button onClick={saveProvider} disabled={savingProvider}
              className="px-5 py-2.5 rounded-lg text-sm font-bold flex items-center gap-2 disabled:opacity-50 transition-all active:scale-95"
              style={{ background: theme.primary, color: theme.primaryText }}>
              {savingProvider ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Guardar conexión
            </button>
          </div>

          <p className="text-xs" style={{ color: theme.textSecondary }}>
            Webhook a configurar en Meta: <code>/api/meta/webhook</code>. El verify token y el token de acceso los define el servidor (env), no se cargan en esta pantalla.
          </p>
        </div>
      )}

      {provider === 'baileys' && (
        <div className="flex justify-end">
          <button onClick={saveProvider} disabled={savingProvider}
            className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 disabled:opacity-50 active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
            {savingProvider ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />} Confirmar proveedor
          </button>
        </div>
      )}
    </div>
  );
}
