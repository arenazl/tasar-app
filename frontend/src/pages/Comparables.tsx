import { useEffect, useState } from 'react';
import { Search, Download, Database, MapPin } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { downloadCSV } from '../utils/csv';

interface ComparableResult {
  id: number;
  title: string;
  address?: string;
  neighborhood?: string;
  city?: string;
  total_area_m2?: number;
  rooms?: number;
  price: number;
  currency: string;
  price_per_m2?: number;
  days_on_market: number;
  condition?: string;
  match_score?: number;
  distance_m?: number;
}

const PILL_OPTIONS = {
  zone: ['Recoleta', 'Palermo', 'Belgrano', 'Núñez', 'Caballito'],
  radius: ['400', '800', '1200', '2000'],
  type: ['departamento', 'casa', 'ph'],
  rooms: ['1', '2', '3', '4', '5'],
  condition: ['a_estrenar', 'excelente', 'muy_bueno', 'bueno'],
  days: ['7', '30', '90', '180'],
};

export default function Comparables() {
  const { theme } = useTheme();
  const [zone, setZone] = useState('Recoleta');
  const [radius, setRadius] = useState('800');
  const [type, setType] = useState('departamento');
  const [rooms, setRooms] = useState('3');
  const [condition, setCondition] = useState('bueno');
  const [days, setDays] = useState('90');
  const [results, setResults] = useState<ComparableResult[]>([]);
  const [stats, setStats] = useState<{ total: number; min: number | null; max: number | null; median: number | null }>(
    { total: 0, min: null, max: null, median: null }
  );
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    try {
      const params: any = {
        neighborhood: zone, property_type: type, rooms: Number(rooms),
        condition, last_days: Number(days), limit: 50,
      };
      const r = await api.get('/market/comparables', { params });
      setResults(r.data.results);
      setStats({ total: r.data.total, min: r.data.min_ppm2, max: r.data.max_ppm2, median: r.data.median_ppm2 });
    } catch {}
    finally { setLoading(false); }
  };

  useEffect(() => { search(); }, []); // eslint-disable-line

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      <header className="mb-4">
        <div className="flex items-start justify-between mb-1 gap-3 flex-wrap">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2 sm:gap-3" style={{ color: theme.text }}>
              Comparables
              <span className="px-2 py-0.5 rounded-md text-[10px] sm:text-xs font-bold uppercase tracking-wider"
                style={{ background: '#22c55e20', color: '#22c55e' }}>live</span>
            </h1>
            <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
              <b>{stats.total}</b> resultados en vivo
            </p>
          </div>
          <button
            onClick={() => {
              if (!results.length) { toast.error('Sin resultados para exportar'); return; }
              downloadCSV(
                results.map(r => ({
                  id: r.id, title: r.title, address: r.address, neighborhood: r.neighborhood, city: r.city,
                  total_area_m2: r.total_area_m2, rooms: r.rooms, price: r.price, currency: r.currency,
                  price_per_m2: r.price_per_m2, days_on_market: r.days_on_market, condition: r.condition,
                  match_score: r.match_score, distance_m: r.distance_m,
                })),
                `comparables_${zone}_${type}_${rooms}amb_${new Date().toISOString().slice(0,10)}`
              );
              toast.success(`${results.length} comparables exportados`);
            }}
            disabled={!results.length}
            className="hidden sm:flex px-4 py-2 rounded-lg text-sm font-medium items-center gap-2 transition-all active:scale-95 disabled:opacity-50"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Download className="h-4 w-4" /> Exportar CSV
          </button>
        </div>

        {/* Filtros pills */}
        <div className="flex items-center gap-2 mt-4 flex-wrap">
          <FilterPill label="Zona" value={zone} options={PILL_OPTIONS.zone} onChange={setZone} theme={theme} />
          <FilterPill label="Radio" value={`${radius}m`} options={PILL_OPTIONS.radius.map(r => `${r}m`)}
            onChange={(v: string) => setRadius(v.replace('m', ''))} theme={theme} />
          <FilterPill label="Tipo" value={type} options={PILL_OPTIONS.type} onChange={setType} theme={theme} />
          <FilterPill label="Amb" value={`${rooms} amb`} options={PILL_OPTIONS.rooms.map(r => `${r} amb`)}
            onChange={(v: string) => setRooms(v.split(' ')[0])} theme={theme} />
          <FilterPill label="Estado" value={condition} options={PILL_OPTIONS.condition} onChange={setCondition} theme={theme} />
          <FilterPill label="Últimos" value={`${days}d`} options={PILL_OPTIONS.days.map(d => `${d}d`)}
            onChange={(v: string) => setDays(v.replace('d', ''))} theme={theme} />
          <button onClick={search} className="ml-auto px-4 py-1.5 rounded-full text-xs font-bold transition-all active:scale-95"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Search className="h-3.5 w-3.5 inline -mt-0.5" /> Buscar
          </button>
        </div>

        {stats.min && stats.max && (
          <div className="mt-3 flex items-center gap-2 text-sm" style={{ color: theme.textSecondary }}>
            <span><b>{stats.total} resultados</b></span>
            <span>·</span>
            <span>USD/m² <b style={{ color: theme.text }}>{Math.round(stats.min).toLocaleString()} – {Math.round(stats.max).toLocaleString()}</b></span>
            {stats.median && <><span>·</span><span>mediana <b style={{ color: theme.text }}>{Math.round(stats.median).toLocaleString()}</b></span></>}
          </div>
        )}
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Mapa placeholder */}
        <div className="lg:col-span-2 p-3 sm:p-5 rounded-xl"
          style={{ background: theme.card, border: `1px solid ${theme.border}`, minHeight: 280 }}>
          <div className="text-xs uppercase tracking-wider font-bold mb-3" style={{ color: theme.textSecondary }}>
            Distribución geográfica · zona {zone}
          </div>
          <div className="grid grid-cols-16 gap-1">
            {Array.from({ length: 12 * 16 }).map((_, i) => {
              const r = Math.floor(i / 16), c = i % 16;
              const d = Math.sqrt((r - 6) ** 2 + (c - 8) ** 2);
              if (d > 7) return <div key={i} />;
              return <div key={i} className="aspect-square rounded"
                style={{ background: theme.primary, opacity: Math.max(0.2, 1 - d / 7) }} />;
            })}
          </div>
          <div className="mt-3 text-center text-xs" style={{ color: theme.textSecondary }}>
            <MapPin className="h-3 w-3 inline mr-1" />
            Mostrando {Math.min(results.length, 12)} de {stats.total} comparables en el radio.
          </div>
        </div>

        {/* Lista resultados */}
        <div className="space-y-2 max-h-[80vh] overflow-y-auto">
          <h3 className="font-bold text-sm sticky top-0 py-2 -mt-2"
            style={{ color: theme.text, background: theme.background }}>
            Resultados <span className="text-xs font-normal" style={{ color: theme.textSecondary }}>
              ordenado por match
            </span>
          </h3>
          {loading && <div className="text-center text-xs py-4" style={{ color: theme.textSecondary }}>Cargando…</div>}
          {!loading && results.length === 0 && (
            <div className="text-center text-xs py-8" style={{ color: theme.textSecondary }}>Sin resultados</div>
          )}
          {results.map(r => {
            const match = r.match_score ? Math.round(r.match_score * 100) : null;
            return (
              <div key={r.id} className="p-3 rounded-lg transition-all hover:shadow-md"
                style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <div className="font-semibold text-sm truncate" style={{ color: theme.text }}>
                      {r.address || r.title.replace(/^\[DEMO\]\s*/, '')}
                    </div>
                    <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>
                      USD <b style={{ color: theme.text }}>{r.price.toLocaleString()}</b>
                      {r.price_per_m2 && <> · <b>{Math.round(r.price_per_m2)}</b> USD/m²</>}
                    </div>
                    <div className="text-[10px] mt-0.5" style={{ color: theme.textSecondary }}>
                      {r.total_area_m2}m² · {r.rooms} amb
                      {r.distance_m != null && <> · {r.distance_m}m</>}
                    </div>
                  </div>
                  {match != null && (
                    <div className="text-xs font-bold flex-shrink-0"
                      style={{ color: match >= 80 ? theme.success : match >= 60 ? theme.warning : theme.danger }}>
                      {match}%
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function FilterPill({ label, value, options, onChange, theme }: any) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button onClick={() => setOpen(o => !o)}
        className="px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-95"
        style={{
          background: open ? theme.text : theme.card,
          color: open ? theme.background : theme.text,
          border: `1px solid ${theme.border}`,
        }}>
        <span className="opacity-70">{label}</span>
        <b>{value}</b>
      </button>
      {open && (
        <div className="absolute top-full mt-1 left-0 z-30 rounded-lg shadow-xl py-1 min-w-[140px]"
          style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          {options.map((opt: string) => (
            <button key={opt} onClick={() => { onChange(opt); setOpen(false); }}
              className="w-full text-left px-3 py-1.5 text-xs transition-all hover:scale-[1.01]"
              style={{ color: theme.text, background: opt === value ? `${theme.primary}15` : 'transparent' }}>
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
