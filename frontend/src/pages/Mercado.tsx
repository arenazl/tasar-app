import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet.heat';
import { Link } from 'react-router-dom';
import { BarChart3, Building2, Calendar, FileText, ArrowUp, ArrowDown, Map as MapIcon } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { BRAND } from '../config/brand';
import type { HeatPoint } from '../types';

interface ZoneStat {
  zone: string;
  usd_m2: number;
  change_pct?: number;
  listings_count: number;
}

interface MarketDashboard {
  tasar_index: number;
  median_price_per_m2: number;
  yoy_change_pct?: number | null;
  mom_change_pct?: number | null;
  active_listings: number;
  avg_days_on_market: number;
  new_permits: number | null;
  top_zones: ZoneStat[];
  // Reales (WO F4-02) — reemplazan el "Mayo 2026 · hace 24 horas" hardcodeado.
  report_period_label: string | null;
  listings_updated_at: string | null;
}

/** Formatea un timestamp real como "hace X min/h/d" — sin inventar una cifra fija. */
function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'hace instantes';
  if (diffMin < 60) return `hace ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `hace ${diffH} h`;
  const diffD = Math.floor(diffH / 24);
  return `hace ${diffD} d`;
}

export default function Mercado() {
  const { theme } = useTheme();
  const mapEl = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<MarketDashboard | null>(null);
  const [period, setPeriod] = useState<'7d' | '30d' | '90d' | '12m' | '5a'>('90d');
  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);

  useEffect(() => {
    setData(null);
    api.get<MarketDashboard>('/market/dashboard', { params: { period } })
      .then(r => setData(r.data))
      .catch(() => api.get<MarketDashboard>('/market/dashboard').then(r => setData(r.data)));
  }, [period]);

  // Heatmap real (WO F4-02): antes esto era una grilla 16x12 dibujada por
  // fórmula ("Grid de calor simulada", sin dato real detrás). Ahora reusa
  // /heatmap/points — el mismo endpoint del mapa completo en /mapa — que
  // además ahora suma market_listings (con coords reales) como fuente.
  useEffect(() => {
    api.get<HeatPoint[]>('/heatmap/points', { params: { city: 'Capital Federal' } })
      .then(r => setPoints(r.data))
      .catch(() => setPoints([]))
      .finally(() => setMapLoaded(true));
  }, []);

  useEffect(() => {
    if (!mapEl.current || !mapLoaded || points.length === 0) return;
    const map = L.map(mapEl.current, { zoomControl: false, attributionControl: false }).setView([-34.6, -58.44], 12);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    const heatData = points.map(p => [p.lat, p.lng, p.intensity]) as any;
    // @ts-expect-error -- leaflet.heat no trae tipos, heatLayer no existe en @types/leaflet
    L.heatLayer(heatData, { radius: 24, blur: 20, maxZoom: 14 }).addTo(map);
    try {
      const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng] as [number, number]));
      map.fitBounds(bounds.pad(0.2));
    } catch { /* best-effort, ignorar */ }
    return () => { map.remove(); };
  }, [points, mapLoaded]);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      {/* Header */}
      <header className="mb-6 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-display font-black tracking-tight" style={{ color: theme.text }}>
            Mercado · CABA
          </h1>
          <p className="mt-1 text-sm" style={{ color: theme.textSecondary }}>
            {data?.report_period_label ? `Reporte ${data.report_period_label}` : 'Sin reporte mensual publicado'}
            {' · '}
            {data?.listings_updated_at ? `listings actualizados ${timeAgo(data.listings_updated_at)}` : 'sin listings con fecha'}
            {' · '}{data ? data.active_listings.toLocaleString() : '...'} avisos activos en el período
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
        <Kpi label={`Índice ${BRAND.name} · CABA`} value={data ? data.tasar_index.toFixed(0) : '...'} suffix={data?.yoy_change_pct != null ? `+${data.yoy_change_pct}% YoY` : ''}
          icon={BarChart3} color={theme.primary} theme={theme} />
        <Kpi label="Oferta activa" value={data ? data.active_listings.toLocaleString() : '...'} suffix="listings reales del período"
          icon={Building2} color={theme.info} theme={theme} />
        <Kpi label="Tiempo medio de venta" value={data ? `${data.avg_days_on_market} días` : '...'} suffix="listings reales del período"
          icon={Calendar} color={theme.warning} theme={theme} />
        <Kpi label="Permisos nuevos" value={data?.new_permits != null ? data.new_permits.toLocaleString() : 'Sin dato'} suffix={data?.new_permits != null ? 'último mes (reporte)' : ''}
          icon={FileText} color={theme.success} theme={theme} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Mapa de calor real */}
        <div className="lg:col-span-2 p-5 rounded-xl"
          style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-bold" style={{ color: theme.text }}>Mapa de calor · USD/m²</h3>
            <Link to="/mapa" className="inline-flex items-center gap-1 text-xs font-semibold" style={{ color: theme.primary }}>
              <MapIcon className="h-3.5 w-3.5" /> Ver mapa completo
            </Link>
          </div>
          <div className="text-xs mb-3" style={{ color: theme.textSecondary }}>
            {points.length > 0 ? `${points.length.toLocaleString()} puntos reales con coordenadas` : 'Sin listings geocodificados para mostrar'}
          </div>
          <div className="rounded-lg overflow-hidden" style={{ height: 280, background: theme.backgroundSecondary }}>
            {!mapLoaded ? (
              <div className="w-full h-full animate-pulse" />
            ) : points.length > 0 ? (
              <div ref={mapEl} className="w-full h-full" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-xs text-center px-4" style={{ color: theme.textSecondary }}>
                No hay listings con coordenadas cargadas todavía
              </div>
            )}
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
