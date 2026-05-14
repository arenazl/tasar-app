import { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Building2, ClipboardList, FileCheck2, TrendingUp, Sparkles } from 'lucide-react';
import { DashboardStatSkeleton, ChartSkeleton, ListItemSkeleton } from '../components/ui/Skeleton';
import PageHint from '../components/ui/PageHint';
import { useTheme } from '../contexts/ThemeContext';
import type { DashboardData } from '../types';

const ICONS: Record<string, any> = {
  'Propiedades': Building2,
  'Estudios ACM': ClipboardList,
  'Tasaciones': FileCheck2,
  'Valor promedio': TrendingUp,
};

export default function Dashboard() {
  const { theme } = useTheme();
  const [data, setData] = useState<DashboardData | null>(null);
  const [aiTip, setAiTip] = useState<string>('Cargando recomendación...');
  const [aiBusy, setAiBusy] = useState(true);

  useEffect(() => {
    api.get<DashboardData>('/dashboard').then(r => setData(r.data));
    // Claude tarda 30-60s con haiku, hasta 120s con sonnet — timeout 180s
    api.post('/ai/chat', {
      message: 'Dame un tip corto (1 oración) sobre cómo mejorar tasaciones esta semana.',
      system: 'Sos un coach de tasadores inmobiliarios. Tu output es UNA oración corta accionable, sin saludos ni emojis.',
    }, { timeout: 180000 })
      .then(r => {
        const txt = r.data?.response || '';
        // Filtrar mensajes de fallback ("[Tasador AI ...]")
        const isFallback = txt.startsWith('[') && txt.endsWith(']');
        setAiTip(isFallback || !txt
          ? 'Cargá propiedades y creá estudios ACM para que el AI Coach te dé recomendaciones contextuales.'
          : txt);
      })
      .catch(() => setAiTip('Cargá propiedades para empezar a tasar.'))
      .finally(() => setAiBusy(false));
  }, []);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      <header className="mb-6">
        <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Dashboard</h1>
        <p className="mt-1" style={{ color: theme.textSecondary }}>Visión general de tu actividad</p>
      </header>

      {/* AI Coach — gradient dinámico según tema activo */}
      <div className="mb-6 p-6 rounded-2xl shadow-xl flex items-start gap-4 relative overflow-hidden"
        style={{
          background: `linear-gradient(135deg, ${theme.gradientFrom}, ${theme.gradientVia}, ${theme.gradientTo})`,
          color: theme.primaryText,
        }}>
        {/* Sparkle decorativo de fondo */}
        <div className="absolute top-0 right-0 w-64 h-64 rounded-full opacity-20 blur-3xl"
          style={{ background: theme.gradientTo, transform: 'translate(30%, -30%)' }} />
        <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-white/20 backdrop-blur flex items-center justify-center relative">
          <Sparkles className={`h-6 w-6 ${aiBusy ? 'animate-pulse' : ''}`} />
        </div>
        <div className="flex-1 relative">
          <div className="text-sm font-semibold opacity-90 mb-1 uppercase tracking-wider">AI Coach</div>
          <div className="text-lg leading-relaxed">{aiTip}</div>
        </div>
      </div>

      <PageHint pageId="propiedades" />

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {!data && [1, 2, 3, 4].map(i => <DashboardStatSkeleton key={i} />)}
        {data?.kpis.map(kpi => {
          const Icon = ICONS[kpi.label] || Building2;
          return (
            <div key={kpi.label} className="p-6 rounded-xl transition-all hover:shadow-lg hover:-translate-y-0.5"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div className="flex items-center justify-between mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
                  <Icon className="h-5 w-5" style={{ color: theme.primary }} />
                </div>
                {kpi.delta_pct !== undefined && (
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{ background: `${kpi.delta_pct >= 0 ? theme.success : theme.danger}20`, color: kpi.delta_pct >= 0 ? theme.success : theme.danger }}>
                    {kpi.delta_pct >= 0 ? '+' : ''}{kpi.delta_pct}%
                  </span>
                )}
              </div>
              <div className="text-2xl font-bold" style={{ color: theme.text }}>
                {kpi.unit === 'USD' ? `USD ${Number(kpi.value).toLocaleString()}` : kpi.value}
              </div>
              <div className="text-sm mt-1" style={{ color: theme.textSecondary }}>{kpi.label}</div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Por tipo */}
        <div className="p-6 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <h3 className="font-semibold mb-4" style={{ color: theme.text }}>Propiedades por tipo</h3>
          {!data && <ChartSkeleton height={200} />}
          {data && data.properties_by_type.length === 0 && (
            <div className="text-sm py-8 text-center" style={{ color: theme.textSecondary }}>Sin datos</div>
          )}
          {data && data.properties_by_type.length > 0 && (
            <div className="space-y-3">
              {data.properties_by_type.map(t => {
                const max = Math.max(...data.properties_by_type.map(x => x.count));
                const pct = (t.count / max) * 100;
                return (
                  <div key={t.type}>
                    <div className="flex items-center justify-between text-sm mb-1">
                      <span className="capitalize" style={{ color: theme.text }}>{t.type}</span>
                      <span className="font-medium" style={{ color: theme.text }}>{t.count}</span>
                    </div>
                    <div className="h-2 rounded-full overflow-hidden" style={{ background: theme.backgroundSecondary }}>
                      <div className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${theme.primary}, ${theme.info})` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recientes */}
        <div className="p-6 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <h3 className="font-semibold mb-4" style={{ color: theme.text }}>Tasaciones recientes</h3>
          {!data && <ListItemSkeleton count={3} />}
          {data && data.recent_appraisals.length === 0 && (
            <div className="text-sm py-8 text-center" style={{ color: theme.textSecondary }}>Sin tasaciones aún</div>
          )}
          {data && data.recent_appraisals.length > 0 && (
            <div className="space-y-2">
              {data.recent_appraisals.map((a: any) => (
                <div key={a.id} className="flex items-center justify-between p-3 rounded-lg transition-all hover:shadow-sm"
                  style={{ background: theme.backgroundSecondary }}>
                  <div>
                    <div className="font-medium capitalize" style={{ color: theme.text }}>{a.purpose}</div>
                    <div className="text-xs" style={{ color: theme.textSecondary }}>{new Date(a.created_at).toLocaleDateString()}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold" style={{ color: theme.text }}>{a.currency} {Number(a.final_value).toLocaleString()}</div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium capitalize"
                      style={{ background: `${a.status === 'signed' ? theme.success : theme.warning}20`, color: a.status === 'signed' ? theme.success : theme.warning }}>
                      {a.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
