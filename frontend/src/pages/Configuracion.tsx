import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Settings, Palette, Bell, Lock, Check, Type, Sparkles, Zap, Brain, Gem, X, Loader2,
  FlaskConical, Trash2, AlertTriangle,
  UserCog, Layers, ListChecks, GraduationCap, Bot, LayoutDashboard, ChevronRight, type LucideIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../services/api';
import { PushTestButton } from '../components/PushOptIn';
import PageHint from '../components/ui/PageHint';
import { BRAND } from '../config/brand';

const CLAUDE_MODELS = [
  { value: 'haiku', label: 'Haiku', desc: 'Rápido y económico', icon: Zap, color: '#16a34a' },
  { value: 'sonnet', label: 'Sonnet', desc: 'Balance — calidad y velocidad', icon: Brain, color: '#2563eb' },
  { value: 'opus', label: 'Opus', desc: 'Máxima profundidad de análisis', icon: Gem, color: '#7c3aed' },
];

const GEMINI_MODELS = [
  { value: 'gemini-2.5-flash', label: 'Flash 2.5', desc: 'Rápido', icon: Zap, color: '#16a34a' },
  { value: 'gemini-2.5-pro', label: 'Pro 2.5', desc: 'Profundo', icon: Gem, color: '#7c3aed' },
];

const AI_PROVIDERS = [
  { value: 'claude', label: 'Claude (Anthropic)', desc: 'Calidad alta · headless local', icon: Brain, color: '#d97706' },
  { value: 'gemini', label: 'Gemini (Google)', desc: 'Rápido · API cloud', icon: Sparkles, color: '#2563eb' },
];

// Accesos de gestión reubicados desde el top-level de la nav (WO F6-04, poda
// agresiva). Cada uno linkea a su ruta viva. Agrupados por área.
const MANAGE_GROUPS: { title: string; links: { to: string; icon: LucideIcon; label: string; desc: string }[] }[] = [
  {
    title: 'Equipo',
    links: [
      { to: '/equipo', icon: UserCog, label: 'Gestión de equipo', desc: 'Usuarios, roles e invitaciones' },
    ],
  },
  {
    title: 'DMO',
    links: [
      { to: '/dmo-templates', icon: Layers, label: 'Templates DMO', desc: 'Plantillas de actividad diaria' },
      { to: '/dmo-asignaciones', icon: ListChecks, label: 'Asignaciones', desc: 'DMO por vendedor' },
      { to: '/coaches', icon: GraduationCap, label: 'Coaches', desc: 'Acompañamiento del equipo' },
    ],
  },
  {
    title: 'Bot',
    links: [
      { to: '/datos-ia', icon: Bot, label: 'Datos IA · Bot', desc: 'Conocimiento que usa el asistente' },
    ],
  },
  {
    title: 'Métricas',
    links: [
      { to: '/metricas', icon: LayoutDashboard, label: 'Tablero de KPIs', desc: 'Indicadores del workspace' },
    ],
  },
];

export default function Configuracion() {
  const { mode, toggle, presetId, setPreset, presets, theme, fontId, setFont, fonts } = useTheme();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  // Gestión del workspace (WO F6-04): Configuración concentra los accesos que
  // salieron del top-level de la nav. Supervisor+admin.
  const isManager = user?.role === 'admin' || user?.role === 'supervisor';
  const [aiProvider, setAiProvider] = useState<string>('claude');
  const [claudeModel, setClaudeModel] = useState<string>('haiku');
  const [geminiModel, setGeminiModel] = useState<string>('gemini-2.5-flash');
  const [aiBusy, setAiBusy] = useState(false);

  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifyAppraisal, setNotifyAppraisal] = useState(true);
  const [notifyComment, setNotifyComment] = useState(false);
  const [showPwdModal, setShowPwdModal] = useState(false);

  // Datos de ejemplo del workspace (WO F5-03) — generar/borrar, solo admin.
  const [demoBusy, setDemoBusy] = useState(false);
  const [purgePreview, setPurgePreview] = useState<Record<string, number> | null>(null);
  const [purgeBusy, setPurgeBusy] = useState(false);

  useEffect(() => {
    api.get('/settings/ai_provider').then(r => { if (r.data?.value) setAiProvider(r.data.value); }).catch(() => {});
    api.get('/settings/claude_model').then(r => { if (r.data?.value) setClaudeModel(r.data.value); }).catch(() => {});
    api.get('/settings/gemini_model').then(r => { if (r.data?.value) setGeminiModel(r.data.value); }).catch(() => {});
    api.get('/settings/notify_email').then(r => { if (r.data?.value != null) setNotifyEmail(r.data.value === 'true'); }).catch(() => {});
    api.get('/settings/notify_appraisal').then(r => { if (r.data?.value != null) setNotifyAppraisal(r.data.value === 'true'); }).catch(() => {});
    api.get('/settings/notify_comment').then(r => { if (r.data?.value != null) setNotifyComment(r.data.value === 'true'); }).catch(() => {});
  }, []);

  const toggleNotify = (key: string, current: boolean, setter: (v: boolean) => void, label: string) => {
    const next = !current;
    setter(next);
    saveSetting(key, String(next), label);
  };

  const saveSetting = async (key: string, val: string, label: string) => {
    setAiBusy(true);
    try {
      await api.put(`/settings/${key}`, { value: val });
      toast.success(`${label} actualizado`);
    } catch {
      toast.error(`No se pudo guardar ${label}`);
    } finally {
      setAiBusy(false);
    }
  };

  const saveProvider = (v: string) => { setAiProvider(v); saveSetting('ai_provider', v, 'Proveedor IA'); };
  const saveClaudeModel = (v: string) => { setClaudeModel(v); saveSetting('claude_model', v, 'Modelo Claude'); };
  const saveGeminiModel = (v: string) => { setGeminiModel(v); saveSetting('gemini_model', v, 'Modelo Gemini'); };

  const activeModels = aiProvider === 'gemini' ? GEMINI_MODELS : CLAUDE_MODELS;
  const activeModel = aiProvider === 'gemini' ? geminiModel : claudeModel;
  const saveModel = aiProvider === 'gemini' ? saveGeminiModel : saveClaudeModel;

  const generateDemoData = async () => {
    setDemoBusy(true);
    try {
      const r = await api.post('/demo/generate', { n_properties: 12 });
      toast.success(`Demo cargada: ${r.data.properties_created} propiedades, ${r.data.vendors_created} vendedores, ${r.data.conversations_created} conversaciones`);
      setPurgePreview(null);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo cargar la demo');
    } finally {
      setDemoBusy(false);
    }
  };

  const previewPurge = async () => {
    setPurgeBusy(true);
    try {
      const r = await api.post('/demo/purge', { confirm: false });
      const { dry_run, ...counts } = r.data;
      void dry_run;
      setPurgePreview(counts);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo calcular qué se borraría');
    } finally {
      setPurgeBusy(false);
    }
  };

  const confirmPurge = async () => {
    setPurgeBusy(true);
    try {
      const r = await api.post('/demo/purge', { confirm: true });
      toast.success(`Demo borrada: ${r.data.properties_deleted} propiedades, ${r.data.vendors_deleted} vendedores, ${r.data.conversations_deleted} conversaciones`);
      if (r.data.properties_kept_in_use > 0) {
        toast.info(`${r.data.properties_kept_in_use} propiedad(es) demo se conservaron porque ya tienen una tasación/visita/operación real cargada`);
      }
      setPurgePreview(null);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo borrar la demo');
    } finally {
      setPurgeBusy(false);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto animate-fade-in">
      <PageHint pageId="configuracion" />
      <header className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Settings className="h-7 w-7" style={{ color: theme.primary }} /> Configuración
        </h1>
        <p className="mt-1" style={{ color: theme.textSecondary }}>Preferencias del workspace</p>
      </header>

      <div className="space-y-3">
        {/* GESTIÓN DEL WORKSPACE (WO F6-04) — solo supervisor/admin.
            Concentra los accesos que salieron del top-level de la nav. */}
        {isManager && (
          <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
                <UserCog className="h-5 w-5" style={{ color: theme.primary }} />
              </div>
              <div className="flex-1">
                <div className="font-semibold" style={{ color: theme.text }}>Gestión del workspace</div>
                <div className="text-sm" style={{ color: theme.textSecondary }}>Equipo, DMO, bot y métricas</div>
              </div>
            </div>
            <div className="space-y-4">
              {MANAGE_GROUPS.map(group => (
                <div key={group.title}>
                  <div className="text-[10px] uppercase tracking-wider font-bold mb-2" style={{ color: theme.textSecondary }}>
                    {group.title}
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {group.links.map(({ to, icon: Icon, label, desc }) => (
                      <Link key={to} to={to}
                        className="flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.01] active:scale-95"
                        style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}` }}>
                        <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{ background: `${theme.primary}15`, color: theme.primary }}>
                          <Icon className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold truncate" style={{ color: theme.text }}>{label}</div>
                          <div className="text-xs truncate" style={{ color: theme.textSecondary }}>{desc}</div>
                        </div>
                        <ChevronRight className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
                      </Link>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TEMA */}
        <Item icon={Palette} title="Tema visual" desc="Elegí paleta + modo light/dark">
          <button onClick={toggle}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-95 capitalize"
            style={{ background: theme.primary, color: theme.primaryText }}>
            Modo {mode === 'light' ? 'light' : 'dark'} — cambiar
          </button>
        </Item>

        {/* PALETAS */}
        <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
              <Palette className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <div>
              <div className="font-semibold" style={{ color: theme.text }}>Paletas disponibles</div>
              <div className="text-sm" style={{ color: theme.textSecondary }}>{presets.length} temas comerciales</div>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {presets.map(p => {
              const isActive = p.id === presetId;
              const variant = mode === 'dark' ? p.dark : p.light;
              return (
                <button key={p.id} onClick={() => setPreset(p.id)}
                  className="p-3 rounded-lg text-left transition-all hover:scale-[1.02] active:scale-95"
                  style={{
                    background: isActive ? `${p.accent}10` : theme.backgroundSecondary,
                    border: `2px solid ${isActive ? p.accent : 'transparent'}`,
                  }}>
                  <div className="flex items-center gap-1 mb-2">
                    <div className="w-6 h-6 rounded-md shadow" style={{ background: p.accent }} />
                    <div className="w-4 h-6 rounded-md shadow" style={{ background: variant.sidebar }} />
                    <div className="w-3 h-6 rounded-md shadow" style={{ background: variant.card, border: `1px solid ${variant.border}` }} />
                    {isActive && (
                      <div className="ml-auto w-5 h-5 rounded-full flex items-center justify-center" style={{ background: p.accent }}>
                        <Check className="h-3 w-3 text-white" strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <div className="text-sm font-semibold" style={{ color: theme.text }}>{p.label}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{p.description}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* PROVEEDOR IA */}
        <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
              <Sparkles className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <div className="flex-1">
              <div className="font-semibold flex items-center gap-2" style={{ color: theme.text }}>
                Proveedor de IA
                {aiBusy && <span className="text-xs animate-pulse" style={{ color: theme.textSecondary }}>guardando…</span>}
              </div>
              <div className="text-sm" style={{ color: theme.textSecondary }}>
                Motor que potencia el chat, análisis y sugerencias de comparables
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            {AI_PROVIDERS.map(p => {
              const Icon = p.icon;
              const isActive = p.value === aiProvider;
              return (
                <button key={p.value} onClick={() => saveProvider(p.value)} disabled={aiBusy}
                  className="p-4 rounded-lg text-left transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50"
                  style={{
                    background: isActive ? `${p.color}10` : theme.backgroundSecondary,
                    border: `2px solid ${isActive ? p.color : 'transparent'}`,
                  }}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                      style={{ background: `${p.color}20` }}>
                      <Icon className="h-5 w-5" style={{ color: p.color }} />
                    </div>
                    {isActive && (
                      <div className="w-5 h-5 rounded-full flex items-center justify-center" style={{ background: p.color }}>
                        <Check className="h-3 w-3 text-white" strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <div className="font-semibold mt-2" style={{ color: theme.text }}>{p.label}</div>
                  <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{p.desc}</div>
                </button>
              );
            })}
          </div>

          <div className="text-xs uppercase tracking-wider font-bold mb-2 mt-4" style={{ color: theme.textSecondary }}>
            Modelo · {aiProvider === 'gemini' ? 'Gemini' : 'Claude'}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {activeModels.map(m => {
              const Icon = m.icon;
              const isActive = m.value === activeModel;
              return (
                <button key={m.value} onClick={() => saveModel(m.value)} disabled={aiBusy}
                  className="p-3 rounded-lg text-left transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50"
                  style={{
                    background: isActive ? `${m.color}10` : theme.backgroundSecondary,
                    border: `2px solid ${isActive ? m.color : 'transparent'}`,
                  }}>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <Icon className="h-4 w-4" style={{ color: m.color }} />
                    {isActive && (
                      <div className="w-4 h-4 rounded-full flex items-center justify-center" style={{ background: m.color }}>
                        <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <div className="font-semibold text-sm" style={{ color: theme.text }}>{m.label}</div>
                  <div className="text-[10px] mt-0.5" style={{ color: theme.textSecondary }}>{m.desc}</div>
                </button>
              );
            })}
          </div>
        </div>

        {/* TIPOGRAFÍAS */}
        <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
              <Type className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <div>
              <div className="font-semibold" style={{ color: theme.text }}>Tipografía</div>
              <div className="text-sm" style={{ color: theme.textSecondary }}>{fonts.length} fuentes disponibles · se aplica a toda la app</div>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {fonts.map(f => {
              const isActive = f.id === fontId;
              return (
                <button key={f.id} onClick={() => setFont(f.id)}
                  className="p-4 rounded-lg text-left transition-all hover:scale-[1.01] active:scale-95"
                  style={{
                    background: isActive ? `${theme.primary}10` : theme.backgroundSecondary,
                    border: `2px solid ${isActive ? theme.primary : 'transparent'}`,
                  }}>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="font-black text-2xl leading-none tracking-tight"
                      style={{ color: theme.text, fontFamily: f.family }}>
                      {f.label}
                    </div>
                    {isActive && (
                      <div className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center" style={{ background: theme.primary }}>
                        <Check className="h-3 w-3 text-white" strokeWidth={3} />
                      </div>
                    )}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider font-semibold mb-2" style={{ color: theme.textSecondary }}>
                    {f.description}
                  </div>
                  <div className="text-sm leading-snug" style={{ color: theme.text, fontFamily: f.family }}>
                    {BRAND.name} · {BRAND.taglineLong}
                  </div>
                  <div className="text-xs leading-snug mt-1" style={{ color: theme.textSecondary, fontFamily: f.family }}>
                    Análisis comparativo de mercado · USD 2.890/m²
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* NOTIFICACIONES */}
        <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
              <Bell className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <div className="flex-1">
              <div className="font-semibold" style={{ color: theme.text }}>Notificaciones</div>
              <div className="text-sm" style={{ color: theme.textSecondary }}>Cuándo querés recibir emails</div>
            </div>
          </div>
          <div className="space-y-2">
            <Toggle theme={theme} label="Email general" desc="Resumen semanal del workspace" checked={notifyEmail}
              onChange={() => toggleNotify('notify_email', notifyEmail, setNotifyEmail, 'Email')} />
            <Toggle theme={theme} label="Tasaciones firmadas" desc="Cuando se firma una tasación" checked={notifyAppraisal}
              onChange={() => toggleNotify('notify_appraisal', notifyAppraisal, setNotifyAppraisal, 'Tasaciones')} />
            <Toggle theme={theme} label="Comentarios del equipo" desc="Cuando un colaborador comenta un estudio" checked={notifyComment}
              onChange={() => toggleNotify('notify_comment', notifyComment, setNotifyComment, 'Comentarios')} />
          </div>
          <button
            onClick={async () => {
              const t = toast.loading('Enviando email de prueba...');
              try {
                const r = await api.post('/settings/test-email');
                toast.dismiss(t);
                if (r.data?.ok) toast.success(`Email enviado a ${r.data.to}`);
                else toast.error('No se pudo enviar (SMTP no configurado)');
              } catch (e: any) {
                toast.dismiss(t);
                toast.error(e.response?.data?.detail || 'Error enviando email');
              }
            }}
            className="mt-3 w-full px-3 py-2 rounded-lg text-xs font-bold transition-all active:scale-95"
            style={{ background: `${theme.primary}15`, color: theme.primary, border: `1px solid ${theme.primary}30` }}>
            Enviar email de prueba
          </button>

          <div className="text-xs mt-4 mb-1" style={{ color: theme.textSecondary }}>
            Push del navegador — te avisa aunque tengas la app cerrada. Activalo desde el banner que aparece al ingresar.
          </div>
          <PushTestButton />
        </div>

        {/* DATOS DE EJEMPLO (WO F5-03) — solo admin */}
        {isAdmin && (
          <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
                <FlaskConical className="h-5 w-5" style={{ color: theme.primary }} />
              </div>
              <div className="flex-1">
                <div className="font-semibold" style={{ color: theme.text }}>Datos de ejemplo</div>
                <div className="text-sm" style={{ color: theme.textSecondary }}>
                  12 propiedades + 3 vendedores + DMO + 5 conversaciones, todo marcado [DEMO]
                </div>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-2.5">
              <button onClick={generateDemoData} disabled={demoBusy}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 active:scale-[0.98] disabled:opacity-50"
                style={{ background: theme.primary, color: theme.primaryText }}>
                {demoBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FlaskConical className="h-4 w-4" />}
                Cargar datos de ejemplo
              </button>
              <button onClick={previewPurge} disabled={purgeBusy}
                className="flex-1 px-4 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 active:scale-[0.98] disabled:opacity-50"
                style={{ background: `${theme.danger}12`, color: theme.danger, border: `1px solid ${theme.danger}30` }}>
                {purgeBusy && !purgePreview ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                Borrar datos de ejemplo
              </button>
            </div>

            {purgePreview && (
              <div className="mt-3 p-3.5 rounded-lg space-y-2" style={{ background: `${theme.danger}08`, border: `1px solid ${theme.danger}30` }}>
                <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: theme.danger }}>
                  <AlertTriangle className="h-3.5 w-3.5" /> Se van a borrar (nada real se toca):
                </div>
                <ul className="text-xs space-y-0.5" style={{ color: theme.textSecondary }}>
                  <li>{purgePreview.properties_to_delete} propiedades demo{purgePreview.properties_kept_in_use ? ` (${purgePreview.properties_kept_in_use} se conservan por tener datos reales asociados)` : ''}</li>
                  <li>{purgePreview.vendors_to_delete} vendedores demo</li>
                  <li>{purgePreview.conversations_to_delete} conversaciones demo ({purgePreview.messages_to_delete} mensajes)</li>
                  <li>{purgePreview.dmo_assignments_to_delete} asignaciones DMO demo</li>
                </ul>
                <div className="flex gap-2 pt-1">
                  <button onClick={confirmPurge} disabled={purgeBusy}
                    className="px-3 py-1.5 rounded-md text-xs font-bold disabled:opacity-50"
                    style={{ background: theme.danger, color: '#fff' }}>
                    {purgeBusy ? 'Borrando…' : 'Confirmar borrado'}
                  </button>
                  <button onClick={() => setPurgePreview(null)}
                    className="px-3 py-1.5 rounded-md text-xs font-bold"
                    style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* PASSWORD */}
        <Item icon={Lock} title="Cambiar contraseña" desc="Actualizá tu password">
          <button onClick={() => setShowPwdModal(true)}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
            style={{ background: theme.primary, color: theme.primaryText }}>
            Cambiar
          </button>
        </Item>
      </div>

      {showPwdModal && <PasswordModal theme={theme} onClose={() => setShowPwdModal(false)} />}
    </div>
  );
}

function Toggle({ theme, label, desc, checked, onChange }: any) {
  return (
    <button onClick={onChange}
      className="w-full flex items-center justify-between gap-4 p-3 rounded-lg transition-all active:scale-[0.99]"
      style={{ background: theme.backgroundSecondary }}>
      <div className="text-left min-w-0">
        <div className="text-sm font-semibold" style={{ color: theme.text }}>{label}</div>
        <div className="text-xs" style={{ color: theme.textSecondary }}>{desc}</div>
      </div>
      <div className="flex-shrink-0 w-11 h-6 rounded-full transition-all relative"
        style={{ background: checked ? theme.primary : theme.border }}>
        <div className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all"
          style={{ left: checked ? 'calc(100% - 22px)' : '2px' }} />
      </div>
    </button>
  );
}

function PasswordModal({ theme, onClose }: any) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (next.length < 6) { toast.error('Mínimo 6 caracteres'); return; }
    if (next !== confirm) { toast.error('Las contraseñas no coinciden'); return; }
    setLoading(true);
    try {
      await api.post('/auth/change-password', { current_password: current, new_password: next });
      toast.success('Contraseña actualizada');
      onClose();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al cambiar contraseña');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-sm rounded-2xl shadow-2xl animate-in zoom-in-95 duration-200"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>Cambiar contraseña</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <PwdField theme={theme} label="Contraseña actual" value={current} onChange={setCurrent} />
          <PwdField theme={theme} label="Nueva contraseña" value={next} onChange={setNext} />
          <PwdField theme={theme} label="Confirmar nueva" value={confirm} onChange={setConfirm} />
        </div>
        <div className="px-5 py-4 flex justify-end gap-2" style={{ borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose} disabled={loading}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={submit} disabled={loading || !current || !next}
            className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 disabled:opacity-50"
            style={{ background: theme.primary, color: theme.primaryText }}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

function PwdField({ theme, label, value, onChange }: any) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>{label}</div>
      <input type="password" value={value} onChange={e => onChange(e.target.value)} autoComplete="off"
        className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2"
        style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' }} />
    </div>
  );
}

function Item({ icon: Icon, title, desc, children }: any) {
  const { theme } = useTheme();
  return (
    <div className="p-5 rounded-xl flex items-center justify-between gap-4"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="flex items-center gap-4 flex-1 min-w-0">
        <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: `${theme.primary}15` }}>
          <Icon className="h-5 w-5" style={{ color: theme.primary }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold" style={{ color: theme.text }}>{title}</div>
          <div className="text-sm" style={{ color: theme.textSecondary }}>{desc}</div>
        </div>
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}
