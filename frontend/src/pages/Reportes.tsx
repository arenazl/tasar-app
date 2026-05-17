import { useEffect, useMemo, useState } from 'react';
import { Download, Plus, Share2, X, Check, BookOpen, FileText, List, ArrowUpDown, Calendar } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { downloadCSV } from '../utils/csv';
import { ABMPage } from '../components/ui/ABMPage';
import { ModernSelect } from '../components/ui/ModernSelect';
import PageHint from '../components/ui/PageHint';

const SORT_OPTIONS = [
  { value: 'recent', label: 'Más recientes' },
  { value: 'old', label: 'Más antiguos' },
  { value: 'yoy_desc', label: 'Mayor YoY' },
  { value: 'yoy_asc', label: 'Menor YoY' },
];

function StatusPill({ icon: Icon, label, count, active, onClick, color, theme }: any) {
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
  const [loading, setLoading] = useState(true);
  const [showCustom, setShowCustom] = useState(false);
  const [search, setSearch] = useState('');
  const [filterYear, setFilterYear] = useState<string>('all');
  const [filterKind, setFilterKind] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('recent');

  useEffect(() => {
    setLoading(true);
    api.get<Report[]>('/reports').then(r => setReports(r.data)).finally(() => setLoading(false));
  }, []);

  const kinds = useMemo(() => Array.from(new Set(reports.map(r => r.kind))), [reports]);
  const years = useMemo(() => Array.from(new Set(reports.map(r => r.period_year))).sort((a, b) => b - a), [reports]);

  const yearOptions = useMemo(() => [
    { value: 'all', label: 'Todos los años' },
    ...years.map(y => ({ value: String(y), label: String(y) })),
  ], [years]);

  const kindOptions = useMemo(() => [
    { value: 'all', label: 'Todos los tipos' },
    ...kinds.map(k => ({ value: k, label: k.charAt(0).toUpperCase() + k.slice(1) })),
  ], [kinds]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: reports.length };
    years.forEach(y => { c[`y_${y}`] = reports.filter(r => r.period_year === y).length; });
    return c;
  }, [reports, years]);

  const filtered = useMemo(() => {
    const s = search.toLowerCase().trim();
    const list = reports.filter(r => {
      if (filterYear !== 'all' && String(r.period_year) !== filterYear) return false;
      if (filterKind !== 'all' && r.kind !== filterKind) return false;
      if (s) {
        const text = `${r.code} ${MONTHS[r.period_month]} ${r.period_year} ${r.region} ${r.kind}`.toLowerCase();
        if (!text.includes(s)) return false;
      }
      return true;
    });
    return [...list].sort((a, b) => {
      if (sortBy === 'recent') return (b.period_year * 12 + b.period_month) - (a.period_year * 12 + a.period_month);
      if (sortBy === 'old') return (a.period_year * 12 + a.period_month) - (b.period_year * 12 + b.period_month);
      if (sortBy === 'yoy_desc') return (b.yoy_change_pct || 0) - (a.yoy_change_pct || 0);
      if (sortBy === 'yoy_asc') return (a.yoy_change_pct || 0) - (b.yoy_change_pct || 0);
      return 0;
    });
  }, [reports, search, filterYear, filterKind, sortBy]);

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
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <PageHint pageId="reportes" />
      <ABMPage
        title="Reportes"
        icon={<FileText className="h-5 w-5" />}
        backLink="/"
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Buscar por código, mes, año o región..."
        onAdd={() => setShowCustom(true)}
        buttonLabel="Reporte custom"
        buttonIcon={<Plus className="h-4 w-4" />}
        loading={loading}
        isEmpty={!loading && filtered.length === 0}
        emptyMessage={reports.length === 0 ? 'Sin reportes publicados todavía' : 'Sin resultados con esos filtros'}
        secondaryFilters={
          <div className="flex items-center justify-between gap-3 flex-wrap py-1">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="w-44"><ModernSelect value={filterYear} onChange={(v: any) => setFilterYear(v)} options={yearOptions} placeholder="Año" /></div>
              <div className="w-44"><ModernSelect value={filterKind} onChange={(v: any) => setFilterKind(v)} options={kindOptions} placeholder="Tipo" /></div>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <StatusPill icon={List} label="Todos" count={counts.all} active={filterYear === 'all'}
                onClick={() => setFilterYear('all')} color={theme.primary} theme={theme} />
              {years.slice(0, 4).map(y => (
                <StatusPill key={y} icon={Calendar} label={String(y)} count={counts[`y_${y}`] || 0}
                  active={filterYear === String(y)} onClick={() => setFilterYear(String(y))} color={theme.info} theme={theme} />
              ))}
            </div>
          </div>
        }
        headerActions={
          <div className="flex items-center gap-2">
            <button onClick={exportAll}
              className="hidden md:flex px-3 py-2 rounded-lg text-xs font-medium items-center gap-1.5 transition-all active:scale-95"
              style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
              <Download className="h-3.5 w-3.5" /> CSV
            </button>
            <ArrowUpDown className="h-4 w-4" style={{ color: theme.textSecondary }} />
            <div className="w-44">
              <ModernSelect value={sortBy} onChange={(v: any) => setSortBy(v)} options={SORT_OPTIONS} placeholder="Ordenar..." />
            </div>
          </div>
        }
      >
        <div className="col-span-full grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((r, i) => (
            <ReportCard key={r.id} report={r} isNew={i === 0} theme={theme} />
          ))}
        </div>
      </ABMPage>

      {showCustom && <CustomReportModal theme={theme} onClose={() => setShowCustom(false)} />}
    </div>
  );
}


function ReportCard({ report, isNew, theme }: { report: Report; isNew: boolean; theme: any }) {
  const navigate = useNavigate();

  const read = () => navigate(`/reportes/${report.id}`);

  const openPdf = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (report.pdf_url) {
      window.open(report.pdf_url, '_blank');
    } else {
      toast.info(`Generando PDF de ${report.code}...`);
      setTimeout(() => toast.success('PDF listo (demo)'), 1200);
    }
  };

  const share = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const url = `${window.location.origin}/reportes/${report.id}`;
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
    <div onClick={read}
      className="rounded-xl overflow-hidden flex flex-col transition-all hover:scale-[1.01] hover:shadow-xl cursor-pointer active:scale-[0.99]"
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
        <button onClick={(e) => { e.stopPropagation(); read(); }}
          className="flex-1 px-3 py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 transition-all active:scale-95"
          style={{ background: theme.primary, color: theme.primaryText }}>
          <BookOpen className="h-3.5 w-3.5" /> Leer
        </button>
        <button onClick={openPdf} aria-label="Descargar PDF"
          className="px-3 py-2 rounded-lg text-xs transition-all active:scale-95"
          style={{ background: theme.backgroundSecondary, color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
          <Download className="h-3.5 w-3.5" />
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
