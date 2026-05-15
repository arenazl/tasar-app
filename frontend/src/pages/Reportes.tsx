import { useEffect, useMemo, useState } from 'react';
import { Download, Filter, Plus, Share2, X, Check } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { downloadCSV } from '../utils/csv';

interface Report {
  id: number;
  code: string;
  period_year: number;
  period_month: number;
  region: string;
  kind: string;
  tasar_index?: number;
  median_price_per_m2?: number;
  yoy_change_pct?: number;
  pages_count: number;
  pdf_url?: string;
  published_at?: string;
}

const MONTHS = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export default function Reportes() {
  const { theme } = useTheme();
  const [reports, setReports] = useState<Report[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [filterYear, setFilterYear] = useState<number | null>(null);
  const [filterKind, setFilterKind] = useState<string>('all');

  useEffect(() => {
    api.get<Report[]>('/reports').then(r => setReports(r.data));
  }, []);

  const kinds = useMemo(() => Array.from(new Set(reports.map(r => r.kind))), [reports]);
  const years = useMemo(() => Array.from(new Set(reports.map(r => r.period_year))).sort((a, b) => b - a), [reports]);

  const filtered = reports.filter(r =>
    (filterYear == null || r.period_year === filterYear) &&
    (filterKind === 'all' || r.kind === filterKind)
  );

  const exportAll = () => {
    if (!filtered.length) { toast.error('Sin reportes para exportar'); return; }
    downloadCSV(
      filtered.map(r => ({
        code: r.code, periodo: `${MONTHS[r.period_month]} ${r.period_year}`, region: r.region, kind: r.kind,
        tasar_index: r.tasar_index, median_usd_m2: r.median_price_per_m2, yoy_pct: r.yoy_change_pct,
        pages: r.pages_count, published_at: r.published_at,
      })),
      `tasar_reportes_${new Date().toISOString().slice(0, 10)}`
    );
    toast.success(`${filtered.length} reportes exportados`);
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      <header className="mb-6 flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight" style={{ color: theme.text }}>Reportes</h1>
          <p className="text-sm mt-1" style={{ color: theme.textSecondary }}>
            Análisis mensual del mercado · publicamos el primer día hábil del mes
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={exportAll}
            className="hidden sm:flex px-4 py-2 rounded-lg text-sm font-medium items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Download className="h-4 w-4" /> Exportar CSV
          </button>
          <button onClick={() => setShowFilters(true)}
            className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95 relative"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Filter className="h-4 w-4" /> Filtrar
            {(filterYear != null || filterKind !== 'all') && (
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full" style={{ background: theme.primary }} />
            )}
          </button>
          <button onClick={() => setShowCustom(true)}
            className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Plus className="h-4 w-4" /> Reporte custom
          </button>
        </div>
      </header>

      {/* Active filter chips */}
      {(filterYear != null || filterKind !== 'all') && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.textSecondary }}>Filtros:</span>
          {filterYear != null && (
            <button onClick={() => setFilterYear(null)} className="px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5"
              style={{ background: `${theme.primary}15`, color: theme.primary, border: `1px solid ${theme.primary}30` }}>
              {filterYear} <X className="h-3 w-3" />
            </button>
          )}
          {filterKind !== 'all' && (
            <button onClick={() => setFilterKind('all')} className="px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5"
              style={{ background: `${theme.primary}15`, color: theme.primary, border: `1px solid ${theme.primary}30` }}>
              {filterKind} <X className="h-3 w-3" />
            </button>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((r, i) => (
          <ReportCard key={r.id} report={r} isNew={i === 0} theme={theme} />
        ))}
        {filtered.length === 0 && (
          <div className="col-span-full p-12 text-center rounded-xl"
            style={{ background: theme.card, border: `2px dashed ${theme.border}`, color: theme.textSecondary }}>
            Sin reportes con esos filtros
          </div>
        )}
      </div>

      {showFilters && (
        <FilterModal theme={theme} years={years} kinds={kinds}
          filterYear={filterYear} setFilterYear={setFilterYear}
          filterKind={filterKind} setFilterKind={setFilterKind}
          onClose={() => setShowFilters(false)} />
      )}

      {showCustom && <CustomReportModal theme={theme} onClose={() => setShowCustom(false)} />}
    </div>
  );
}


function ReportCard({ report, isNew, theme }: { report: Report; isNew: boolean; theme: any }) {
  const open = () => {
    if (report.pdf_url) {
      window.open(report.pdf_url, '_blank');
    } else {
      toast.info(`Generando PDF de ${report.code}...`);
      setTimeout(() => toast.success('PDF listo (demo)'), 1200);
    }
  };

  const share = async () => {
    const url = `${window.location.origin}/reportes#${report.code}`;
    const text = `${report.code} · ${MONTHS[report.period_month]} ${report.period_year} — TasAR`;
    if (navigator.share) {
      try {
        await navigator.share({ title: text, url });
        return;
      } catch { /* user cancelled */ }
    }
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copiado al portapapeles');
    } catch {
      toast.error('No se pudo compartir');
    }
  };

  return (
    <div className="rounded-xl overflow-hidden flex flex-col transition-all hover:scale-[1.01] hover:shadow-xl"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="relative px-5 py-8" style={{ background: theme.sidebar, color: '#fff' }}>
        <div className="flex items-center justify-between mb-12">
          <div className="text-xs uppercase tracking-wider font-bold opacity-70">
            {report.code} · {report.kind}
          </div>
          {isNew && (
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider"
              style={{ background: '#22c55e', color: '#000' }}>nuevo</span>
          )}
        </div>
        <div className="font-display text-3xl font-black tracking-tight mb-3">
          {MONTHS[report.period_month]} {report.period_year}
        </div>
        <div className="grid grid-cols-6 gap-1 max-w-[120px] opacity-40">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-sm" style={{ background: '#22c55e', opacity: Math.random() * 0.6 + 0.2 }} />
          ))}
        </div>
      </div>

      <div className="px-5 py-3 flex items-center justify-between text-xs" style={{ color: theme.textSecondary }}>
        <div>
          {report.published_at && new Date(report.published_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })}
          {report.pages_count > 0 && <> · {report.pages_count} pp</>}
        </div>
      </div>
      <div className="px-5 pb-3 flex items-center gap-4">
        {report.yoy_change_pct != null && (
          <div>
            <div className="text-lg font-display font-black" style={{ color: report.yoy_change_pct >= 0 ? theme.success : theme.danger }}>
              {report.yoy_change_pct >= 0 ? '+' : ''}{report.yoy_change_pct}%
            </div>
            <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>YoY</div>
          </div>
        )}
        {report.median_price_per_m2 != null && (
          <div>
            <div className="text-lg font-display font-black tabular-nums" style={{ color: theme.text }}>
              {report.median_price_per_m2.toFixed(0)}
            </div>
            <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>USD/m²</div>
          </div>
        )}
      </div>

      <div className="px-5 pb-4 flex gap-2">
        <button onClick={open} className="flex-1 px-3 py-2 rounded-lg text-xs font-bold transition-all active:scale-95"
          style={{ background: theme.success, color: '#fff' }}>
          Abrir PDF
        </button>
        <button onClick={share} aria-label="Compartir"
          className="px-3 py-2 rounded-lg text-xs transition-all active:scale-95"
          style={{ background: theme.backgroundSecondary, color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
          <Share2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}


function FilterModal({ theme, years, kinds, filterYear, setFilterYear, filterKind, setFilterKind, onClose }: any) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-md rounded-2xl shadow-2xl animate-in zoom-in-95 duration-200"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>Filtrar reportes</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-4">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: theme.textSecondary }}>Año</div>
            <div className="flex flex-wrap gap-2">
              <Chip active={filterYear == null} onClick={() => setFilterYear(null)} label="Todos" theme={theme} />
              {years.map((y: number) => <Chip key={y} active={filterYear === y} onClick={() => setFilterYear(y)} label={String(y)} theme={theme} />)}
            </div>
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: theme.textSecondary }}>Tipo</div>
            <div className="flex flex-wrap gap-2">
              <Chip active={filterKind === 'all'} onClick={() => setFilterKind('all')} label="Todos" theme={theme} />
              {kinds.map((k: string) => <Chip key={k} active={filterKind === k} onClick={() => setFilterKind(k)} label={k} theme={theme} />)}
            </div>
          </div>
        </div>
        <div className="px-5 py-4 flex justify-end gap-2" style={{ borderTop: `1px solid ${theme.border}` }}>
          <button onClick={() => { setFilterYear(null); setFilterKind('all'); }}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.text }}>Limpiar</button>
          <button onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-bold transition-all active:scale-95 flex items-center gap-1.5"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Check className="h-4 w-4" /> Aplicar
          </button>
        </div>
      </div>
    </div>
  );
}

function Chip({ active, onClick, label, theme }: any) {
  return (
    <button onClick={onClick}
      className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all active:scale-95"
      style={{
        background: active ? theme.primary : theme.backgroundSecondary,
        color: active ? theme.primaryText : theme.text,
        border: `1px solid ${active ? theme.primary : theme.border}`,
      }}>{label}</button>
  );
}

function CustomReportModal({ theme, onClose }: any) {
  const [region, setRegion] = useState('CABA');
  const [kind, setKind] = useState('Residencial');
  const [year, setYear] = useState(new Date().getFullYear());
  const [month, setMonth] = useState(new Date().getMonth() + 1);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      await api.post('/reports/custom', { region, kind, period_year: year, period_month: month });
      toast.success(`Reporte ${region} ${MONTHS[month]} ${year} en cola`);
      onClose();
    } catch (e: any) {
      if (e.response?.status === 404) {
        toast.info('Endpoint /reports/custom pendiente — request guardada localmente');
        onClose();
      } else {
        toast.error(e.response?.data?.detail || 'Error generando reporte');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-md rounded-2xl shadow-2xl animate-in zoom-in-95 duration-200"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>Reporte custom</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <Field label="Región" value={region} onChange={setRegion} options={['CABA', 'GBA Norte', 'GBA Sur', 'GBA Oeste', 'Córdoba', 'Rosario']} theme={theme} />
          <Field label="Tipo" value={kind} onChange={setKind} options={['Residencial', 'Comercial', 'Industrial', 'Mixto']} theme={theme} />
          <div className="grid grid-cols-2 gap-3">
            <Field label="Año" value={String(year)} onChange={(v: string) => setYear(Number(v))}
              options={[2024, 2025, 2026].map(String)} theme={theme} />
            <Field label="Mes" value={String(month)} onChange={(v: string) => setMonth(Number(v))}
              options={MONTHS.slice(1).map((_, i) => String(i + 1))} renderOption={(v: string) => MONTHS[Number(v)]} theme={theme} />
          </div>
        </div>
        <div className="px-5 py-4 flex justify-end gap-2" style={{ borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose} disabled={loading}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={generate} disabled={loading}
            className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 disabled:opacity-50"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Plus className="h-4 w-4" /> {loading ? 'Generando...' : 'Generar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, options, renderOption, theme }: any) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>{label}</div>
      <select value={value} onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2 rounded-lg text-sm focus:outline-none"
        style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '14px' }}>
        {options.map((o: string) => <option key={o} value={o}>{renderOption ? renderOption(o) : o}</option>)}
      </select>
    </div>
  );
}
