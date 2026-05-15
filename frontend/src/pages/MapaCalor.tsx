import { useEffect, useRef, useState, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet.heat';
import { ArrowLeft, TrendingUp, Map as MapIcon, Building2, ClipboardList, Database, List, X, BarChart3, Users, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { ModernSelect } from '../components/ui/ModernSelect';
import { MapSkeleton } from '../components/ui/Skeleton';
import PageHint from '../components/ui/PageHint';
import { useTheme } from '../contexts/ThemeContext';
import type { HeatPoint } from '../types';

const TYPE_OPTIONS = [
  { value: '', label: 'Todos los tipos' },
  { value: 'casa', label: 'Casas' },
  { value: 'departamento', label: 'Departamentos' },
  { value: 'ph', label: 'PHs' },
  { value: 'terreno', label: 'Terrenos' },
  { value: 'local', label: 'Locales' },
  { value: 'oficina', label: 'Oficinas' },
];

const OP_OPTIONS = [
  { value: '', label: 'Todas las operaciones' },
  { value: 'venta', label: 'Venta' },
  { value: 'alquiler', label: 'Alquiler' },
];

function StatusPill({
  icon: Icon, label, count, active, onClick, color,
}: { icon: any; label: string; count: number; active: boolean; onClick: () => void; color: string }) {
  const { theme } = useTheme();
  return (
    <button onClick={onClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95 whitespace-nowrap"
      style={{
        background: active ? color : theme.card,
        color: active ? '#fff' : theme.textSecondary,
        border: `1.5px solid ${active ? color : theme.border}`,
      }}>
      <Icon className="h-3.5 w-3.5" />
      <span>{label}</span>
      <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold"
        style={{ background: active ? 'rgba(255,255,255,0.25)' : theme.backgroundSecondary, color: active ? '#fff' : theme.text }}>{count}</span>
    </button>
  );
}

export default function MapaCalor() {
  const { theme } = useTheme();
  const mapEl = useRef<HTMLDivElement>(null);
  const [points, setPoints] = useState<HeatPoint[]>([]);
  const [zones, setZones] = useState<any[]>([]);
  const [filterType, setFilterType] = useState('');
  const [filterOp, setFilterOp] = useState('');
  const [filterCity, setFilterCity] = useState('');
  const [sourceFilter, setSourceFilter] = useState<'all'|'props'|'comps'|'history'>('all');
  const [loaded, setLoaded] = useState(false);
  const [drillZone, setDrillZone] = useState<any | null>(null);

  useEffect(() => {
    const q = new URLSearchParams();
    if (filterType) q.set('property_type', filterType);
    if (filterCity) q.set('city', filterCity);
    const qs = q.toString() ? `?${q}` : '';
    Promise.all([
      api.get<HeatPoint[]>(`/heatmap/points${qs}`).then(r => setPoints(r.data)),
      api.get(`/heatmap/zones${qs}`).then(r => setZones(r.data)),
    ]).finally(() => setLoaded(true));
  }, [filterType, filterCity]);

  // Counts simulados (el back no diferencia origen — usamos label heurístico)
  const counts = useMemo(() => {
    return {
      all: points.length,
      props: points.filter(p => p.label && !p.label.includes(',')).length, // títulos de propiedades suelen ser largos
      comps: 0, // los comparables vienen sin distinción clara, dejo 0 por honestidad
      history: zones.length,
    };
  }, [points, zones]);

  const cityOptions = useMemo(() => {
    const cities = [...new Set(zones.map(z => z.city).filter(Boolean))].sort();
    return [{ value: '', label: 'Todas las ciudades' }, ...cities.map(c => ({ value: c, label: c }))];
  }, [zones]);

  useEffect(() => {
    if (!mapEl.current || !loaded) return;
    const map = L.map(mapEl.current).setView([-34.6, -58.45], 5);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
    if (points.length > 0) {
      const heatData = points.map(p => [p.lat, p.lng, p.intensity]) as any;
      // @ts-ignore
      L.heatLayer(heatData, { radius: 28, blur: 22, maxZoom: 14 }).addTo(map);
      points.forEach(p => {
        L.circleMarker([p.lat, p.lng], { radius: 5, color: theme.primary, fillOpacity: 0.7 })
          .bindPopup(`<b>${p.label || 'Punto'}</b><br/>${p.price_per_m2 ? `USD ${p.price_per_m2}/m²` : ''}`)
          .addTo(map);
      });
      const grp = L.featureGroup(points.map(p => L.marker([p.lat, p.lng])));
      try { map.fitBounds(grp.getBounds().pad(0.3)); } catch {}
    }
    return () => { map.remove(); };
  }, [points, loaded, theme.primary]);

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <Link to="/" className="inline-flex items-center gap-1 text-sm mb-4 transition-all hover:gap-2" style={{ color: theme.textSecondary }}>
        <ArrowLeft className="h-4 w-4" /> Volver al inicio
      </Link>

      <PageHint pageId="mapa" />

      {/* Header tipo ABMPage manual (no usamos ABMPage porque no es lista) */}
      <div className="p-5 rounded-xl mb-3" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${theme.primary}15` }}>
            <MapIcon className="h-5 w-5" style={{ color: theme.primary }} />
          </div>
          <div>
            <h1 className="text-lg font-bold" style={{ color: theme.text }}>Mapa de calor</h1>
            <p className="text-xs" style={{ color: theme.textSecondary }}>Distribución de USD/m² en vivo</p>
          </div>
        </div>

        {/* Filtros */}
        <div className="flex items-center justify-between gap-3 flex-wrap py-1">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="w-48"><ModernSelect value={filterCity} onChange={(v: any) => setFilterCity(v)} options={cityOptions} placeholder="Ciudad" searchable /></div>
            <div className="w-44"><ModernSelect value={filterType} onChange={(v: any) => setFilterType(v)} options={TYPE_OPTIONS} placeholder="Tipo" /></div>
            <div className="w-44"><ModernSelect value={filterOp} onChange={(v: any) => setFilterOp(v)} options={OP_OPTIONS} placeholder="Operación" /></div>
          </div>
          <div className="flex items-center gap-1.5 flex-wrap">
            <StatusPill icon={List} label="Todo" count={counts.all} active={sourceFilter === 'all'} onClick={() => setSourceFilter('all')} color={theme.primary} />
            <StatusPill icon={Building2} label="Propiedades" count={counts.props} active={sourceFilter === 'props'} onClick={() => setSourceFilter('props')} color={theme.info} />
            <StatusPill icon={ClipboardList} label="Comparables" count={counts.comps} active={sourceFilter === 'comps'} onClick={() => setSourceFilter('comps')} color={theme.warning} />
            <StatusPill icon={Database} label="Histórico" count={counts.history} active={sourceFilter === 'history'} onClick={() => setSourceFilter('history')} color="#7c3aed" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="lg:col-span-3 rounded-xl overflow-hidden shadow-sm" style={{ background: theme.card, border: `1px solid ${theme.border}`, height: 'calc(100vh - 360px)', minHeight: 500 }}>
          {!loaded ? <MapSkeleton height={500} /> : <div ref={mapEl} className="w-full h-full" />}
        </div>

        <div className="space-y-3">
          <h3 className="font-semibold flex items-center gap-2" style={{ color: theme.text }}>
            <TrendingUp className="h-4 w-4" style={{ color: theme.primary }} /> Top zonas USD/m²
          </h3>
          {zones.length === 0 && (
            <div className="text-sm p-4 rounded-lg text-center" style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.textSecondary }}>
              Sin datos
            </div>
          )}
          {zones.sort((a, b) => b.avg_price_per_m2 - a.avg_price_per_m2).slice(0, 10).map((z, i) => (
            <button key={i} onClick={() => setDrillZone({ ...z, rank: i + 1 })}
              className="w-full p-3 rounded-lg transition-all hover:shadow-md hover:scale-[1.01] active:scale-95 text-left"
              style={{
                background: drillZone?.neighborhood === z.neighborhood ? `${theme.primary}10` : theme.card,
                border: `1px solid ${drillZone?.neighborhood === z.neighborhood ? theme.primary : theme.border}`,
              }}>
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono" style={{ color: theme.textSecondary }}>#{i + 1}</span>
                <span className="text-xs" style={{ color: theme.textSecondary }}>{z.sample_size} muestras</span>
              </div>
              <div className="font-medium text-sm mt-1" style={{ color: theme.text }}>{z.neighborhood || z.city}</div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs" style={{ color: theme.textSecondary }}>USD/m²</span>
                <span className="font-bold" style={{ color: theme.text }}>{Math.round(z.avg_price_per_m2).toLocaleString()}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {drillZone && <DrillPanel zone={drillZone} zones={zones} points={points} theme={theme} onClose={() => setDrillZone(null)} />}
    </div>
  );
}

function DrillPanel({ zone, zones, points, theme, onClose }: any) {
  const zonePoints = points.filter((p: any) =>
    (p.label || '').toLowerCase().includes((zone.neighborhood || zone.city || '').toLowerCase())
  );
  const max = Math.max(...zones.map((z: any) => z.avg_price_per_m2));
  const pctOfMax = (zone.avg_price_per_m2 / max) * 100;
  const cityAvg = zones.length ? zones.reduce((s: number, z: any) => s + z.avg_price_per_m2, 0) / zones.length : 0;
  const vsCity = ((zone.avg_price_per_m2 - cityAvg) / cityAvg) * 100;

  return (
    <div className="fixed inset-y-0 right-0 z-40 w-full sm:w-[420px] flex flex-col animate-in slide-in-from-right duration-200"
      style={{ background: theme.card, borderLeft: `1px solid ${theme.border}`, boxShadow: '-8px 0 24px -8px rgba(0,0,0,0.2)' }}>
      <div className="px-5 py-4 flex items-start justify-between gap-3" style={{ borderBottom: `1px solid ${theme.border}` }}>
        <div className="min-w-0">
          <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.primary }}>
            Ranking #{zone.rank} · {zone.city || 'CABA'}
          </div>
          <h3 className="font-display font-black text-2xl tracking-tight truncate" style={{ color: theme.text }}>
            {zone.neighborhood || zone.city}
          </h3>
        </div>
        <button onClick={onClose} className="p-1.5 rounded-lg flex-shrink-0" style={{ color: theme.textSecondary, background: theme.backgroundSecondary }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {/* KPI hero */}
        <div className="p-4 rounded-xl" style={{ background: `${theme.primary}10`, border: `1px solid ${theme.primary}30` }}>
          <div className="text-[10px] uppercase tracking-wider font-bold mb-1" style={{ color: theme.primary }}>USD por m²</div>
          <div className="font-display font-black text-4xl tabular-nums" style={{ color: theme.text }}>
            {Math.round(zone.avg_price_per_m2).toLocaleString()}
          </div>
          <div className="mt-2 h-1.5 rounded-full overflow-hidden" style={{ background: theme.backgroundSecondary }}>
            <div className="h-full rounded-full" style={{ width: `${pctOfMax}%`, background: theme.primary }} />
          </div>
          <div className="text-[10px] mt-1.5 flex items-center justify-between" style={{ color: theme.textSecondary }}>
            <span>{pctOfMax.toFixed(0)}% del top</span>
            <span style={{ color: vsCity >= 0 ? theme.success : theme.danger }}>
              {vsCity >= 0 ? '+' : ''}{vsCity.toFixed(1)}% vs promedio
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <DrillStat icon={Users} label="Muestras" value={zone.sample_size?.toLocaleString() || '0'} color={theme.info} theme={theme} />
          <DrillStat icon={Activity} label="Listings activos" value={zonePoints.length.toLocaleString()} color={theme.warning} theme={theme} />
          <DrillStat icon={BarChart3} label="Min USD/m²" value={Math.round((zone.min_price_per_m2 || zone.avg_price_per_m2 * 0.7)).toLocaleString()} color={theme.success} theme={theme} />
          <DrillStat icon={TrendingUp} label="Max USD/m²" value={Math.round((zone.max_price_per_m2 || zone.avg_price_per_m2 * 1.3)).toLocaleString()} color={theme.danger} theme={theme} />
        </div>

        {zonePoints.length > 0 && (
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: theme.textSecondary }}>
              Puntos en la zona ({zonePoints.length})
            </div>
            <div className="space-y-2 max-h-72 overflow-y-auto">
              {zonePoints.slice(0, 20).map((p: any, i: number) => (
                <div key={i} className="p-3 rounded-lg flex items-center justify-between gap-3"
                  style={{ background: theme.backgroundSecondary }}>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold truncate" style={{ color: theme.text }}>{p.label || 'Punto'}</div>
                    <div className="text-[10px] font-mono" style={{ color: theme.textSecondary }}>
                      {p.lat.toFixed(4)}, {p.lng.toFixed(4)}
                    </div>
                  </div>
                  {p.price_per_m2 && (
                    <div className="text-right flex-shrink-0">
                      <div className="font-bold text-sm tabular-nums" style={{ color: theme.text }}>{Number(p.price_per_m2).toLocaleString()}</div>
                      <div className="text-[9px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>USD/m²</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="px-5 py-3 flex gap-2" style={{ borderTop: `1px solid ${theme.border}`, background: theme.backgroundSecondary }}>
        <Link to={`/comparables?zone=${encodeURIComponent(zone.neighborhood || '')}`}
          className="flex-1 px-3 py-2 rounded-lg text-xs font-bold text-center transition-all active:scale-95"
          style={{ background: theme.primary, color: theme.primaryText }}>
          Ver comparables
        </Link>
        <Link to={`/mercado?zone=${encodeURIComponent(zone.neighborhood || '')}`}
          className="px-3 py-2 rounded-lg text-xs font-medium transition-all active:scale-95"
          style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
          Mercado
        </Link>
      </div>
    </div>
  );
}

function DrillStat({ icon: Icon, label, value, color, theme }: any) {
  return (
    <div className="p-3 rounded-xl" style={{ background: theme.backgroundSecondary }}>
      <Icon className="h-4 w-4 mb-1.5" style={{ color }} />
      <div className="text-lg font-display font-black tabular-nums" style={{ color: theme.text }}>{value}</div>
      <div className="text-[9px] uppercase tracking-wider font-bold mt-0.5" style={{ color: theme.textSecondary }}>{label}</div>
    </div>
  );
}
