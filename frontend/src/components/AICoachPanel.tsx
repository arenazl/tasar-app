import { useEffect, useState, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import {
  Sparkles, RefreshCw, X, ChevronRight, AlertTriangle, CheckCircle2, Info, Bot,
} from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

interface CoachTip {
  title: string;
  body: string;
  severity: 'info' | 'warning' | 'success';
  action_label?: string;
  action_url?: string;
}

interface CoachResponse {
  route: string;
  tips: CoachTip[];
  generated_by_ai: boolean;
}

const LS_OPEN = 'tasar_coach_open';

/** Mapeo de pathname → route key del backend */
function routeFromPath(pathname: string): string {
  const seg = pathname.split('/').filter(Boolean)[0] || '';
  if (!seg || seg === '') return 'dashboard';
  if (seg === 'propiedades') return 'propiedades';
  if (seg === 'tasaciones') return 'tasaciones';
  if (seg === 'estudios') return 'tasaciones';
  if (seg === 'bandeja') return 'bandeja';
  if (seg === 'mercado') return 'mercado';
  if (seg === 'comparables') return 'comparables';
  if (seg === 'reportes') return 'reportes';
  if (seg === 'pipeline') return 'pipeline';
  if (seg === 'clientes') return 'clientes';
  if (seg === 'mapa') return 'mercado';
  if (seg === 'configuracion') return 'config';
  if (seg === 'tasador-ai') return 'tasaciones';
  return 'dashboard';
}

export default function AICoachPanel() {
  const { theme } = useTheme();
  const location = useLocation();
  const [open, setOpen] = useState(() => localStorage.getItem(LS_OPEN) !== 'false');
  const [loading, setLoading] = useState(false);
  const [tips, setTips] = useState<CoachTip[]>([]);
  const [generatedByAI, setGeneratedByAI] = useState(true);
  const [lastRoute, setLastRoute] = useState<string>('');

  const route = routeFromPath(location.pathname);

  useEffect(() => {
    localStorage.setItem(LS_OPEN, open ? 'true' : 'false');
  }, [open]);

  const fetchTips = useCallback(async () => {
    if (!open) return;
    setLoading(true);
    try {
      const r = await api.post<CoachResponse>('/ai/coach', { route }, { timeout: 180000 });
      setTips(r.data.tips || []);
      setGeneratedByAI(r.data.generated_by_ai);
      setLastRoute(route);
    } catch {
      setTips([{ title: 'AI Coach', body: 'Cargá data para obtener recomendaciones.', severity: 'info' }]);
      setGeneratedByAI(false);
    } finally {
      setLoading(false);
    }
  }, [open, route]);

  // Trigger al cambiar de ruta o al abrir
  useEffect(() => {
    if (open && route !== lastRoute) {
      fetchTips();
    }
  }, [open, route, lastRoute, fetchTips]);

  // En desktop el panel es always-open (sidebar fija). En mobile sigue siendo
  // FAB + bottom-sheet on demand.
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="lg:hidden fixed right-4 bottom-[88px] z-40 w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-all active:scale-95 hover:scale-110"
        style={{ background: theme.primary, color: theme.primaryText }}
        title="Abrir AI Coach"
      >
        <Sparkles className="h-5 w-5" />
      </button>
    );
  }

  return (
    <>
      {/* Backdrop solo mobile */}
      <div className="lg:hidden fixed inset-0 bg-black/40 z-30 animate-in fade-in duration-200"
        onClick={() => setOpen(false)} />
      <aside
        className="fixed z-40 flex flex-col shadow-xl animate-in slide-in-from-bottom lg:slide-in-from-right duration-200
                   inset-x-0 bottom-0 max-h-[80vh] rounded-t-2xl
                   lg:inset-x-auto lg:bottom-0 lg:top-16 lg:right-0 lg:w-80 lg:max-h-none lg:rounded-none"
        style={{ background: theme.card, borderTop: `1px solid ${theme.border}`, borderLeft: `1px solid ${theme.border}` }}
      >
        {/* drag handle solo mobile */}
        <div className="lg:hidden flex justify-center py-2 flex-shrink-0">
          <span className="w-10 h-1 rounded-full" style={{ background: theme.border }} />
        </div>
      {/* Header */}
      <div
        className="flex-shrink-0 px-4 py-3 flex items-center justify-between gap-2"
        style={{ borderBottom: `1px solid ${theme.border}`, background: `linear-gradient(135deg, ${theme.primary}08, transparent)` }}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: `${theme.primary}20` }}>
            <Bot className="h-4 w-4" style={{ color: theme.primary }} />
          </div>
          <div className="min-w-0">
            <div className="font-bold text-sm flex items-center gap-1" style={{ color: theme.text }}>
              AI Coach
              <Sparkles className="h-3 w-3" style={{ color: theme.primary }} />
            </div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: theme.textSecondary }}>
              {generatedByAI ? 'Contexto: ' : 'Sin IA · '}{route}
            </div>
          </div>
        </div>
        <div className="flex gap-1">
          <button onClick={fetchTips} disabled={loading}
            className="p-1.5 rounded-lg transition-all active:scale-95 disabled:opacity-50"
            style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}
            title="Refrescar">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={() => setOpen(false)}
            className="lg:hidden p-1.5 rounded-lg transition-all active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}
            title="Cerrar">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Tips */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        {loading && tips.length === 0 && (
          <div className="py-12 flex flex-col items-center gap-3">
            <div className="relative h-12 w-12 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full blur-xl opacity-50 animate-pulse"
                style={{ background: theme.primary }} />
              <div className="absolute inset-0 animate-spin rounded-full border-2 border-t-transparent"
                style={{ borderColor: `${theme.primary}22`, borderTopColor: theme.primary, animationDuration: '1.2s' }} />
              <Sparkles className="h-5 w-5 relative animate-pulse" style={{ color: theme.primary }} />
            </div>
            <div className="text-[10px] uppercase tracking-wider font-medium" style={{ color: theme.textSecondary }}>
              Claude analizando…
            </div>
          </div>
        )}

        {!loading && tips.length === 0 && (
          <div className="text-center text-xs py-8" style={{ color: theme.textSecondary }}>
            Sin recomendaciones por ahora.
          </div>
        )}

        {tips.map((t, i) => (
          <TipCard key={i} tip={t} />
        ))}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 px-4 py-2.5 text-[10px] flex items-center justify-between"
        style={{ background: theme.backgroundSecondary, borderTop: `1px solid ${theme.border}`, color: theme.textSecondary }}>
        <span className="uppercase tracking-wider">Powered by Claude</span>
        <span>contexto: <b style={{ color: theme.text }}>{route}</b></span>
      </div>
      </aside>
    </>
  );
}


function TipCard({ tip }: { tip: CoachTip }) {
  const { theme } = useTheme();
  const colorMap = {
    info: theme.info,
    warning: theme.warning,
    success: theme.success,
  };
  const IconMap = {
    info: Info,
    warning: AlertTriangle,
    success: CheckCircle2,
  };
  const c = colorMap[tip.severity] || theme.info;
  const Icon = IconMap[tip.severity] || Info;
  return (
    <div className="p-3 rounded-xl animate-fade-in"
      style={{ background: `${c}08`, border: `1px solid ${c}30` }}>
      <div className="flex items-start gap-2 mb-1">
        <Icon className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: c }} />
        <div className="font-bold text-xs leading-snug" style={{ color: theme.text }}>
          {tip.title}
        </div>
      </div>
      <div className="text-xs leading-relaxed pl-6" style={{ color: theme.textSecondary }}>
        {tip.body}
      </div>
      {tip.action_label && tip.action_url && (
        <a href={tip.action_url}
          className="inline-flex items-center gap-1 mt-2 ml-6 text-[10px] font-bold uppercase tracking-wider transition-all hover:gap-2"
          style={{ color: c }}>
          {tip.action_label} <ChevronRight className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}
