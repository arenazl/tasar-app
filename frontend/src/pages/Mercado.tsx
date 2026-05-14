import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Building2, Calendar, FileText, ArrowUp, ArrowDown } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

interface ZoneStat {
  zone: string;
  usd_m2: number;
  change_pct?: number;
  listings_count: number;
}

interface MarketDashboard {
  tasar_index: number;
  median_price_per_m2: number;
  yoy_change_pct?: number;
  mom_change_pct?: number;
  active_listings: number;
  avg_days_on_market: number;
  new_permits: number;
  top_zones: ZoneStat[];
}

export default function Mercado() {
  const { theme } = useTheme();
  const [data, setData] = useState<MarketDashboard | null>(null);
  const [period, setPeriod] = useState<'7d' | '30d' | '90d' | '12m' | '5a'>('90d');

  useEffect(() => {
    api.get<MarketDashboard>('/market/dashboard').then(r => setData(r.data));
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <header className="mb-6 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-4xl font-display font-black tracking-tight" style={{ color: theme.text }}>
            Mercado · CABA
          </h1>
          <p className="mt-1 text-sm" style={{ color: theme.textSecondary }}>
            Mayo 2026 · datos actualizados hace 24 horas · {data?.active_listings.toLocaleString() || '...'} avisos activos
          </p>
        </div>
        <div className="flex gap-1 p-1 rounded-lg" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          {(['7d', '30d', '90d', '12m', '5a'] as const).map(p => (
            <button key={p} onClick={() => setPeriod(p)}
              className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
              style={{
                background: period === p ? theme.text : 'transparent',
                color: period === p ? theme.background : theme.textSecondary,
              }}>
              {p}
            </button>
          ))}
        </div>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Kpi label="Índice TasAR · CABA" value={data ? data.tasar_index.toFixed(0) : '...'} suffix={data?.yoy_change_pct != null ? `+${data.yoy_change_pct}% YoY` : ''}
          icon={BarChart3} color={theme.primary} theme={theme} />
        <Kpi label="Oferta activa" value={data?.active_listings.toLocaleString() || '...'} suffix={data?.mom_change_pct != null ? `${data.mom_change_pct > 0 ? '+' : ''}${data.mom_change_pct}% vs mes ant.` : ''}
          icon={Building2} color={theme.info} theme={theme} />
        <Kpi label="Tiempo medio de venta" value={`${data?.avg_days_on_market || '...'} días`} suffix=""
          icon={Calendar} color={theme.warning} theme={theme} />
        <Kpi label="Permisos nuevos" value={data?.new_permits.toLocaleString() || '...'} suffix="último mes"
          icon={FileText} color={theme.success} theme={theme} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Mapa de calor placeholder */}
        <div className="lg:col-span-2 p-5 rounded-xl"
          style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold" style={{ color: theme.text }}>Mapa de calor · USD/m²</h3>
            <div className="flex items-center gap-2 text-xs" style={{ color: theme.textSecondary }}>
              <span>menor</span>
              <div className="flex gap-0.5">
                {[0.2, 0.4, 0.6, 0.8, 1].map(o => (
                  <div key={o} className="w-4 h-4 rounded" style={{ background: theme.primary, opacity: o }} />
                ))}
              </div>
              <span>mayor</span>
            </div>
          </div>
          <div className="text-xs mb-3" style={{ color: theme.textSecondary }}>
            Capital Federal · valor mediano por celda de 200m
          </div>
          {/* Grid de calor simulada (CABA shape) */}
          <div className="grid grid-cols-16 gap-1 max-w-3xl mx-auto">
            {Array.from({ length: 12 * 16 }).map((_, i) => {
              const row = Math.floor(i / 16);
              const col = i % 16;
              const centerR = 6, centerC = 8;
              const dist = Math.sqrt((row - centerR) ** 2 + (col - centerC) ** 2);
              if (dist > 7) return <div key={i} />;
              const intensity = Math.max(0.15, 1 - dist / 7) + Math.random() * 0.15;
              return (
                <div key={i} className="aspect-square rounded"
                  style={{ background: theme.primary, opacity: Math.min(1, intensity) }} />
              );
            })}
          </div>
        </div>

        {/* Ranking por zona */}
        <div className="p-5 rounded-xl"
          style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="mb-3">
            <h3 className="font-bold" style={{ color: theme.text }}>Ranking por zona</h3>
            <div className="text-xs" style={{ color: theme.textSecondary }}>USD/m² · top {data?.top_zones.length || 0}</div>
          </div>
          <div className="space-y-1.5">
            {!data && [1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="h-8 rounded animate-pulse" style={{ background: theme.backgroundSecondary }} />
            ))}
            {data?.top_zones.map((z, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5 px-2 rounded hover:scale-[1.01] transition-all"
                style={{ background: i % 2 === 0 ? theme.backgroundSecondary : 'transparent' }}>
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-xs font-mono w-7" style={{ color: theme.textSecondary }}>
                    #{String(i + 1).padStart(2, '0')}
                  </span>
                  <span style={{ color: theme.text }}>{z.zone}</span>
                </div>
                <div className="flex items-center gap-2">
                  {z.change_pct != null && (
                    <span className="text-[10px] flex items-center gap-0.5"
                      style={{ color: z.change_pct >= 0 ? theme.success : theme.danger }}>
                      {z.change_pct >= 0 ? <ArrowUp className="h-2.5 w-2.5" /> : <ArrowDown className="h-2.5 w-2.5" />}
                      {Math.abs(z.change_pct).toFixed(1)}%
                    </span>
                  )}
                  <span className="font-bold tabular-nums" style={{ color: theme.text }}>
                    {z.usd_m2.toLocaleString()}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function Kpi({ label, value, suffix, icon: Icon, color, theme }: any) {
  return (
    <div className="p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>{label}</div>
        <Icon className="h-4 w-4" style={{ color }} />
      </div>
      <div className="text-3xl font-display font-black tabular-nums" style={{ color: theme.text }}>{value}</div>
      {suffix && (
        <div className="text-xs mt-1" style={{ color: suffix.startsWith('+') ? theme.success : suffix.startsWith('-') ? theme.danger : theme.textSecondary }}>
          {suffix}
        </div>
      )}
    </div>
  );
}
