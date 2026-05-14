import { useEffect, useState } from 'react';
import { Settings, Palette, Bell, Lock, Check, Type, Sparkles, Zap, Brain, Gem } from 'lucide-react';
import { toast } from 'sonner';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../services/api';

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

export default function Configuracion() {
  const { mode, toggle, presetId, setPreset, presets, theme, fontId, setFont, fonts } = useTheme();
  const [aiProvider, setAiProvider] = useState<string>('claude');
  const [claudeModel, setClaudeModel] = useState<string>('haiku');
  const [geminiModel, setGeminiModel] = useState<string>('gemini-2.5-flash');
  const [aiBusy, setAiBusy] = useState(false);

  useEffect(() => {
    api.get('/settings/ai_provider').then(r => { if (r.data?.value) setAiProvider(r.data.value); }).catch(() => {});
    api.get('/settings/claude_model').then(r => { if (r.data?.value) setClaudeModel(r.data.value); }).catch(() => {});
    api.get('/settings/gemini_model').then(r => { if (r.data?.value) setGeminiModel(r.data.value); }).catch(() => {});
  }, []);

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

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto animate-fade-in">
      <header className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Settings className="h-7 w-7" style={{ color: theme.primary }} /> Configuración
        </h1>
        <p className="mt-1" style={{ color: theme.textSecondary }}>Preferencias del workspace</p>
      </header>

      <div className="space-y-3">
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
                    TasAR · Mapa de valor por zona
                  </div>
                  <div className="text-xs leading-snug mt-1" style={{ color: theme.textSecondary, fontFamily: f.family }}>
                    Análisis comparativo de mercado · USD 2.890/m²
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        <Item icon={Bell} title="Notificaciones" desc="Avisos por email cuando se firme una tasación o un colaborador comente">
          <span className="text-sm" style={{ color: theme.textSecondary }}>Próximamente</span>
        </Item>
        <Item icon={Lock} title="Cambiar contraseña" desc="Actualizá tu password">
          <span className="text-sm" style={{ color: theme.textSecondary }}>Próximamente</span>
        </Item>
      </div>
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
