import { useEffect, useState } from 'react';
import { Download, FileText, Filter, Plus, Share2 } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

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

  useEffect(() => {
    api.get<Report[]>('/reports').then(r => setReports(r.data));
  }, []);

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
          <button className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Filter className="h-4 w-4" /> Filtrar
          </button>
          <button className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Plus className="h-4 w-4" /> Reporte custom
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {reports.map((r, i) => (
          <ReportCard key={r.id} report={r} isNew={i === 0} theme={theme} />
        ))}
      </div>
    </div>
  );
}


function ReportCard({ report, isNew, theme }: { report: Report; isNew: boolean; theme: any }) {
  return (
    <div className="rounded-xl overflow-hidden flex flex-col transition-all hover:scale-[1.01] hover:shadow-xl"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      {/* Hero negro */}
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
        {/* Mini heatmap deco */}
        <div className="grid grid-cols-6 gap-1 max-w-[120px] opacity-40">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="aspect-square rounded-sm" style={{ background: '#22c55e', opacity: Math.random() * 0.6 + 0.2 }} />
          ))}
        </div>
      </div>

      {/* Stats */}
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

      {/* Botones */}
      <div className="px-5 pb-4 flex gap-2">
        <button className="flex-1 px-3 py-2 rounded-lg text-xs font-bold transition-all active:scale-95"
          style={{ background: theme.success, color: '#fff' }}>
          Abrir PDF
        </button>
        <button className="px-3 py-2 rounded-lg text-xs transition-all active:scale-95"
          style={{ background: theme.backgroundSecondary, color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
          <Share2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
