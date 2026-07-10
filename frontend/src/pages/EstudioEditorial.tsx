import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Share2, Download, BookmarkPlus } from 'lucide-react';
import { toast } from 'sonner';
import { api, API_BASE } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { BRAND } from '../config/brand';

interface ReportData {
  id: number;
  code: string;
  period_year: number;
  period_month: number;
  region: string;
  kind: string;
  source: string; // 'seed' (demo) | 'custom' (agregación real sobre market_listings)
  tasar_index: number | null;
  median_price_per_m2: number | null;
  yoy_change_pct: number | null;
  mom_change_pct: number | null;
  active_listings: number | null;
  avg_days_on_market: number | null;
  new_permits: number | null;
  pages_count: number;
  pdf_url: string | null;
  published_at: string | null;
  top_zones: { zone: string; usd_m2: number; change_pct?: number }[];
}

interface ReportHistoryPoint {
  period_year: number;
  period_month: number;
  median_price_per_m2: number | null;
  new_permits: number | null;
}

const MONTHS = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export default function EstudioEditorial() {
  const { id } = useParams();
  const { theme } = useTheme();
  const [r, setR] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scrollPct, setScrollPct] = useState(0);
  const [history, setHistory] = useState<ReportHistoryPoint[]>([]);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<ReportData>(`/reports/${id}`).then(res => setR(res.data)).finally(() => setLoading(false));
  }, [id]);

  // Serie histórica REAL para el gráfico de índice y de permisos: otras
  // ediciones del mismo reporte (region), no un array hardcodeado (regla
  // dura 11 / hallazgo F4-02: sparkline y bar chart traían valores fijos).
  useEffect(() => {
    if (!r?.region) return;
    api.get<ReportHistoryPoint[]>('/reports', { params: { region: r.region } })
      .then(res => {
        const sorted = [...res.data].sort((a, b) => (a.period_year * 12 + a.period_month) - (b.period_year * 12 + b.period_month));
        setHistory(sorted);
      })
      .catch(() => setHistory([]));
  }, [r?.region]);

  const priceHistory = useMemo(
    () => history.filter(h => h.median_price_per_m2 != null),
    [history]
  );
  const priceSeries = useMemo(() => priceHistory.map(h => h.median_price_per_m2 as number), [priceHistory]);
  const permitsHistory = useMemo(
    () => history.filter(h => h.new_permits != null),
    [history]
  );
  const permitsSeries = useMemo(() => permitsHistory.map(h => h.new_permits as number), [permitsHistory]);

  const openPdf = async () => {
    if (!r) return;
    setPdfLoading(true);
    const token = localStorage.getItem('tasar_token');
    try {
      const res = await fetch(`${API_BASE}/reports/${r.id}/pdf`, { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('pdf fetch failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      toast.error('No se pudo abrir el PDF');
    } finally {
      setPdfLoading(false);
    }
  };

  useEffect(() => {
    const onScroll = () => {
      const el = document.scrollingElement || document.documentElement;
      const max = el.scrollHeight - el.clientHeight;
      const pct = max > 0 ? Math.min(100, Math.max(0, (el.scrollTop / max) * 100)) : 0;
      setScrollPct(pct);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const share = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try { await navigator.share({ title: `Estudio ${r?.code} ${BRAND.name}`, url }); return; } catch { /* ignore */ }
    }
    try { await navigator.clipboard.writeText(url); toast.success('Link copiado'); }
    catch { toast.error('No se pudo compartir'); }
  };

  if (loading || !r) {
    return (
      <div className="max-w-[880px] mx-auto p-8 space-y-6">
        <div className="h-12 rounded-lg animate-pulse" style={{ background: theme.backgroundSecondary }} />
        <div className="h-64 rounded-xl animate-pulse" style={{ background: theme.backgroundSecondary }} />
        <div className="grid grid-cols-3 gap-3">
          {[1, 2, 3].map(i => <div key={i} className="h-40 rounded-xl animate-pulse" style={{ background: theme.backgroundSecondary }} />)}
        </div>
      </div>
    );
  }

  const yoyDirection = (r.yoy_change_pct ?? 0) >= 0;
  const totalPages = r.pages_count || 2;
  const currentPage = Math.max(1, Math.round((scrollPct / 100) * totalPages));
  // Top zonas reales del reporte (r.top_zones), NO texto fijo (regla dura 11).
  const topZones = [...(r.top_zones || [])].sort((a, b) => b.usd_m2 - a.usd_m2).slice(0, 3);
  // Delta real de precio calculado sobre la serie historica de ediciones
  // de la misma region (>= 2 puntos reales) -- reemplaza el pull quote
  // hardcodeado ("USD 437 en 17 meses").
  const priceDelta = priceSeries.length >= 2 ? Math.round(priceSeries[priceSeries.length - 1] - priceSeries[0]) : null;
  const priceDeltaMonths = priceSeries.length >= 2 ? priceSeries.length - 1 : null;

  const fmtPct = (v: number | null | undefined) => v == null ? null : `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;
  const fmtUsd = (v: number | null | undefined) => v == null ? null : `USD ${Math.round(v).toLocaleString()}`;
  const monthLabel = MONTHS[r.period_month]?.toLowerCase() || '-';
  const momLabel = fmtPct(r.mom_change_pct);
  const yoyLabel = fmtPct(r.yoy_change_pct);
  const changeClause = momLabel && yoyLabel
    ? `${momLabel} mensual y ${yoyLabel} interanual`
    : momLabel ? `${momLabel} mensual` : yoyLabel ? `${yoyLabel} interanual` : null;

  return (
    <div className="animate-fade-in">
      <style>{`
        @keyframes estIn { 0% { opacity: 0; transform: translateY(16px); } 100% { opacity: 1; transform: translateY(0); } }
        .est-fade { animation: estIn 500ms cubic-bezier(0.22, 1, 0.36, 1) both; }
        .est-d1 { animation-delay: 60ms; }
        .est-d2 { animation-delay: 140ms; }
        .est-d3 { animation-delay: 220ms; }
        .est-d4 { animation-delay: 300ms; }
        .est-d5 { animation-delay: 380ms; }
      `}</style>

      {/* Sticky toolbar */}
      <div className="sticky top-0 z-30 px-6 py-3 flex items-center justify-between gap-4"
        style={{ background: theme.card + 'ee', backdropFilter: 'blur(12px)', borderBottom: `1px solid ${theme.border}` }}>
        <div className="flex items-center gap-4 min-w-0">
          <Link to="/reportes" className="inline-flex items-center gap-1.5 text-xs font-semibold transition-all hover:gap-2"
            style={{ color: theme.textSecondary }}>
            <ArrowLeft className="h-3.5 w-3.5" /> Volver a Reportes
          </Link>
          <div className="hidden sm:flex items-center gap-2 min-w-0">
            <span className="text-[11px] font-mono tabular-nums whitespace-nowrap" style={{ color: theme.textSecondary }}>
              Pág. {currentPage}/{totalPages}
            </span>
            <div className="w-32 h-1 rounded-full overflow-hidden" style={{ background: theme.border }}>
              <div className="h-full rounded-full transition-all duration-150" style={{ width: `${scrollPct}%`, background: theme.primary }} />
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={share}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Share2 className="h-3 w-3" /> <span className="hidden sm:inline">Compartir</span>
          </button>
          <button onClick={openPdf} disabled={pdfLoading}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all active:scale-95 disabled:opacity-50"
            style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Download className="h-3 w-3" /> <span className="hidden sm:inline">{pdfLoading ? 'Abriendo...' : 'PDF'}</span>
          </button>
          <button onClick={() => toast.success('Te avisaremos cuando salga la próxima edición')}
            className="px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <BookmarkPlus className="h-3 w-3" /> Suscribirse
          </button>
        </div>
      </div>

      {/* Documento centrado */}
      <article className="max-w-[760px] mx-auto px-5 sm:px-8 py-12">

        {/* Cover */}
        <header className="est-fade mb-12">
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] mb-6 flex items-center gap-2" style={{ color: theme.textSecondary }}>
            <span>Edición {r.code} · {MONTHS[r.period_month]} {r.period_year} · {r.region}</span>
            {r.source === 'seed' && (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}
                title="Datos de referencia (seed), no es una agregación en vivo sobre el mercado">
                [DEMO]
              </span>
            )}
          </div>
          <h1 className="font-display font-black tracking-tight leading-[1.02] text-[42px] sm:text-[56px] mb-6"
            style={{ color: theme.text }}>
            {r.yoy_change_pct != null ? (
              <>El interanual cierra en{' '}
                <span style={{ color: theme.primary }}>{yoyDirection ? '+' : ''}{r.yoy_change_pct.toFixed(1)}%</span>
              </>
            ) : (
              <>Índice de mercado · {r.region}</>
            )}
            {r.median_price_per_m2 != null && (
              <> {r.yoy_change_pct != null ? 'y el' : 'El'} m² se ubica en USD {Math.round(r.median_price_per_m2).toLocaleString()}.</>
            )}
          </h1>
          <p className="text-lg leading-relaxed" style={{ color: theme.textSecondary }}>
            {topZones.length > 0 ? (
              <>Zonas con mayor USD/m² en {r.region} este período: {topZones.map((z, i) => (
                <span key={z.zone}>
                  {i > 0 && (i === topZones.length - 1 ? ' y ' : ', ')}
                  <strong style={{ color: theme.text }}>{z.zone}</strong>
                  {z.change_pct != null && ` (${z.change_pct >= 0 ? '+' : ''}${z.change_pct.toFixed(1)}%)`}
                </span>
              ))}.</>
            ) : (
              <>Sin datos de zonas para este período todavía.</>
            )}
          </p>
          <div className="mt-6 flex items-center gap-3 pt-6" style={{ borderTop: `1px solid ${theme.border}` }}>
            <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm"
              style={{ background: theme.primary, color: theme.primaryText }}>TA</div>
            <div className="text-sm">
              <div className="font-bold" style={{ color: theme.text }}>Equipo {BRAND.name}</div>
              <div className="text-xs" style={{ color: theme.textSecondary }}>
                Publicado {r.published_at ? new Date(r.published_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' }) : '—'}
                {' · '}{totalPages} páginas
              </div>
            </div>
          </div>
        </header>

        {/* TL;DR */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-14">
          <TldrCard n="01"
            h={r.median_price_per_m2 != null ? `El índice se ubica en ${fmtUsd(r.median_price_per_m2)}/m²` : 'Índice sin dato'}
            b={momLabel ? `Variación mensual: ${momLabel}.` : 'Sin dato de variación mensual para este período.'}
            theme={theme} className="est-fade est-d1" />
          <TldrCard n="02"
            h={r.active_listings != null ? `${r.active_listings.toLocaleString()} avisos activos` : 'Oferta activa sin dato'}
            b={r.avg_days_on_market != null ? `Promedio de ${r.avg_days_on_market} días en mercado en ${r.region}.` : 'Sin dato de días promedio en mercado.'}
            theme={theme} className="est-fade est-d2" />
          <TldrCard n="03"
            h={r.new_permits != null ? `${r.new_permits.toLocaleString()} permisos de obra` : 'Permisos sin dato'}
            b={r.new_permits != null ? 'Permisos de obra nueva aprobados en el período.' : 'Sin dato de permisos de obra para este período.'}
            theme={theme} className="est-fade est-d3" />
        </div>

        {/* §01 Índice */}
        <Section num="01" title="Índice" h2={r.median_price_per_m2 != null ? `El índice cierra en ${fmtUsd(r.median_price_per_m2)}/m² en ${r.region}.` : `Índice ${r.region} sin dato para este período.`} theme={theme}>
          <p>
            El <strong style={{ color: theme.text }}>Índice {BRAND.name} {r.region}</strong> cerró {monthLabel} en{' '}
            <strong style={{ color: theme.text }}>{fmtUsd(r.median_price_per_m2) || 'sin dato disponible'}</strong>
            {changeClause && <>, {changeClause}</>}.
          </p>
          {priceSeries.length >= 2 ? (
            <Figure caption={`Fig. 1 — Índice ${BRAND.name} ${r.region}, USD/m² mediano por edición publicada. ${priceSeries.length} ediciones con dato.`} theme={theme}>
              <Sparkline theme={theme} data={priceSeries} />
              <div className="flex justify-between mt-2 text-[11px] font-mono" style={{ color: theme.textSecondary }}>
                <span>{MONTHS[priceHistory[0].period_month]?.slice(0, 3)} {String(priceHistory[0].period_year).slice(2)} · {Math.round(priceSeries[0]).toLocaleString()}</span>
                <span style={{ color: theme.text, fontWeight: 700 }}>
                  {MONTHS[priceHistory[priceHistory.length - 1].period_month]?.slice(0, 3)} {String(priceHistory[priceHistory.length - 1].period_year).slice(2)} · {Math.round(priceSeries[priceSeries.length - 1]).toLocaleString()}
                </span>
              </div>
            </Figure>
          ) : (
            <p className="text-sm italic" style={{ color: theme.textSecondary }}>
              Serie histórica insuficiente para graficar la evolución del índice ({priceSeries.length} edición con dato).
            </p>
          )}
        </Section>

        {/* Pull quote — solo si hay >= 2 ediciones reales para calcular el delta */}
        {priceDelta != null && (
          <PullQuote theme={theme} className="est-fade est-d4">
            "El m² de {r.region} {priceDelta >= 0 ? 'sumó' : 'perdió'} {fmtUsd(Math.abs(priceDelta))} en {priceDeltaMonths} {priceDeltaMonths === 1 ? 'edición' : 'ediciones'} publicadas."
          </PullQuote>
        )}

        {/* §02 Zonas */}
        <Section num="02" title="Zonas"
          h2={topZones.length > 0 ? `${topZones[0].zone} lidera el USD/m² en ${r.region}.` : `Sin datos de zonas para ${r.region}.`}
          theme={theme}>
          {topZones.length > 0 ? (
            <p>
              Las zonas con mayor USD/m² del período son {topZones.map((z, i) => (
                <span key={z.zone}>
                  {i > 0 && (i === topZones.length - 1 ? ' y ' : ', ')}
                  <strong style={{ color: theme.text }}>{z.zone}</strong>
                  {' '}({Math.round(z.usd_m2).toLocaleString()} USD/m²{z.change_pct != null ? `, ${fmtPct(z.change_pct)}` : ''})
                </span>
              ))}.
            </p>
          ) : (
            <p>Todavía no hay avisos activos con zona asignada para este período.</p>
          )}
          {(r.top_zones?.length || 0) > 0 && (
            <Figure caption={`Fig. 2 — USD/m² mediano por zona, top ${r.top_zones.length} en ${r.region}.`} theme={theme}>
              <BarChart data={r.top_zones} theme={theme} />
            </Figure>
          )}
        </Section>

        {/* §03 Oferta */}
        <Section num="03" title="Oferta"
          h2={r.active_listings != null ? `${r.active_listings.toLocaleString()} avisos activos en ${r.region}.` : `Oferta activa sin dato en ${r.region}.`}
          theme={theme}>
          <p>
            Las unidades activas en venta en {r.region} cerraron {monthLabel} en{' '}
            <strong style={{ color: theme.text }}>{r.active_listings != null ? r.active_listings.toLocaleString() : 'sin dato'}</strong>
            {momLabel && <>, {momLabel} respecto al período anterior</>}.
          </p>
          <p>
            Tiempo medio de venta:{' '}
            <strong style={{ color: theme.text }}>{r.avg_days_on_market != null ? `${r.avg_days_on_market} días` : 'sin dato'}</strong> promedio.
          </p>
        </Section>

        {/* §04 Obra nueva */}
        <Section num="04" title="Obra nueva"
          h2={r.new_permits != null ? `${r.new_permits.toLocaleString()} permisos aprobados en el período.` : 'Sin dato de permisos para este período.'}
          theme={theme}>
          <p>
            {r.new_permits != null
              ? <>Se aprobaron <strong style={{ color: theme.text }}>{r.new_permits.toLocaleString()} permisos</strong> de obra nueva en {r.region} durante el período.</>
              : 'No hay dato de permisos de obra nueva para este período.'}
          </p>
          {permitsSeries.length >= 2 ? (
            <Figure caption={`Fig. 3 — Permisos de obra aprobados, ${permitsSeries.length} ediciones con dato.`} theme={theme}>
              <PermitsBarChart theme={theme} history={permitsHistory} highlightLast />
            </Figure>
          ) : (
            <p className="text-sm italic" style={{ color: theme.textSecondary }}>
              Serie histórica insuficiente para graficar permisos ({permitsSeries.length} edición con dato).
            </p>
          )}
        </Section>

        {/* §05 Lo que viene */}
        <Section num="05" title="Lo que viene" h2="Factores a monitorear en los próximos meses." theme={theme}>
          <ul className="space-y-2 mt-3 mb-4 pl-5">
            <li style={{ color: theme.textSecondary }}>
              <strong style={{ color: theme.text }}>Crédito hipotecario UVA</strong> — los stocks de oferta podrían
              volver a subir si bajan las tasas.
            </li>
            <li style={{ color: theme.textSecondary }}>
              <strong style={{ color: theme.text }}>Tipo de cambio</strong> — la suba del paralelo presionaría a la baja
              los precios en USD.
            </li>
            <li style={{ color: theme.textSecondary }}>
              <strong style={{ color: theme.text }}>Obra nueva</strong> — el flujo de permisos sostenido implica más
              oferta efectiva en 18-24 meses.
            </li>
          </ul>
        </Section>

        {/* Footer */}
        <footer className="mt-16 pt-8 text-xs" style={{ borderTop: `1px solid ${theme.border}`, color: theme.textSecondary }}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div>
              <div className="font-bold uppercase tracking-wider mb-2" style={{ color: theme.text }}>Metodología</div>
              <p className="leading-relaxed">
                El Índice {BRAND.name} procesa avisos publicados, escrituras y permisos de obra. Mediana ponderada por
                tipología y barrio. Series desestacionalizadas. Documentación completa en tasar.app/methodology.
              </p>
            </div>
            <div>
              <div className="font-bold uppercase tracking-wider mb-2" style={{ color: theme.text }}>Sobre {BRAND.name}</div>
              <p className="leading-relaxed">
                {BRAND.name} es el motor de inteligencia inmobiliaria de Argentina. Procesamos millones de avisos al mes
                para tasadores, bancos, fondos e inmobiliarias. Reportes mensuales, API y CRM en
                tasar-app.netlify.app.
              </p>
            </div>
          </div>
          <div className="mt-6 text-center" style={{ color: theme.textSecondary }}>
            Edición {r.code} · {BRAND.name} © {new Date().getFullYear()}
          </div>
        </footer>
      </article>
    </div>
  );
}


/* ---- Components ---- */

function TldrCard({ n, h, b, theme, className }: any) {
  return (
    <div className={`p-5 rounded-xl ${className}`} style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="text-3xl font-display font-black mb-2" style={{ color: theme.primary }}>{n}</div>
      <div className="font-bold text-base leading-snug mb-2" style={{ color: theme.text }}>{h}</div>
      <div className="text-sm leading-relaxed" style={{ color: theme.textSecondary }}>{b}</div>
    </div>
  );
}

function Section({ num, title, h2, theme, children }: any) {
  return (
    <section className="mb-14 est-fade">
      <div className="text-[10px] font-bold uppercase tracking-[0.25em] mb-3" style={{ color: theme.primary }}>
        §{num} · {title}
      </div>
      <h2 className="font-display font-black tracking-tight text-3xl sm:text-4xl mb-5 leading-tight" style={{ color: theme.text }}>
        {h2}
      </h2>
      <div className="space-y-4 text-base leading-relaxed" style={{ color: theme.textSecondary }}>
        {children}
      </div>
    </section>
  );
}

function Figure({ caption, theme, children }: any) {
  return (
    <figure className="my-6 p-5 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      {children}
      <figcaption className="mt-4 text-[11px] italic" style={{ color: theme.textSecondary }}>
        {caption}
      </figcaption>
    </figure>
  );
}

function PullQuote({ theme, children, className }: any) {
  return (
    <blockquote className={`my-14 px-6 py-2 ${className}`}
      style={{ borderLeft: `4px solid ${theme.primary}` }}>
      <p className="font-display text-2xl sm:text-3xl font-bold leading-snug tracking-tight"
        style={{ color: theme.text }}>
        {children}
      </p>
    </blockquote>
  );
}

function Sparkline({ theme, data }: { theme: any; data: number[] }) {
  const w = 600, h = 140, pad = 8;
  const max = Math.max(...data), min = Math.min(...data);
  const x = (i: number) => pad + (i / (data.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - min) / (max - min || 1)) * (h - 2 * pad);
  const points = data.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const area = `M ${x(0)},${h - pad} L ${points.split(' ').join(' L ')} L ${x(data.length - 1)},${h - pad} Z`;
  const gid = `est-spark-${Math.random().toString(36).slice(2, 8)}`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} style={{ display: 'block' }}>
      <defs>
        <linearGradient id={gid} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={theme.primary} stopOpacity="0.22" />
          <stop offset="100%" stopColor={theme.primary} stopOpacity="0" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map(g => (
        <line key={g} x1={pad} x2={w - pad} y1={pad + g * (h - 2 * pad)} y2={pad + g * (h - 2 * pad)}
          stroke={theme.border} strokeWidth="1" strokeDasharray="3 4" />
      ))}
      <path d={area} fill={`url(#${gid})`} />
      <polyline points={points} fill="none" stroke={theme.primary} strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(data.length - 1)} cy={y(data[data.length - 1])} r="4.5" fill={theme.primary} />
      <circle cx={x(data.length - 1)} cy={y(data[data.length - 1])} r="10" fill={theme.primary} opacity="0.2" />
    </svg>
  );
}

function BarChart({ data, theme }: { data: any[]; theme: any }) {
  const items = data;
  const max = Math.max(...items.map(i => i.usd_m2));
  return (
    <div className="space-y-2">
      {items.slice(0, 11).map((it, i) => (
        <div key={i} className="grid grid-cols-12 items-center gap-3 text-xs">
          <div className="col-span-3 truncate font-semibold" style={{ color: theme.text }}>{it.zone}</div>
          <div className="col-span-7">
            <div className="h-4 rounded" style={{
              width: `${(it.usd_m2 / max) * 100}%`,
              background: `linear-gradient(90deg, ${theme.primary}, ${theme.primary}aa)`,
              minWidth: 4,
            }} />
          </div>
          <div className="col-span-2 text-right font-mono tabular-nums font-bold" style={{ color: theme.text }}>
            {Math.round(it.usd_m2).toLocaleString()}
          </div>
        </div>
      ))}
    </div>
  );
}

interface PermitsHistoryPoint {
  period_year: number;
  period_month: number;
  new_permits: number | null;
}

function PermitsBarChart({ theme, history, highlightLast }: { theme: any; history: PermitsHistoryPoint[]; highlightLast?: boolean }) {
  const MONTHS_SHORT = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  const data = history.map(h => ({ k: `${MONTHS_SHORT[h.period_month]} ${String(h.period_year).slice(2)}`, v: h.new_permits as number }));
  const max = Math.max(...data.map(d => d.v));
  return (
    <div className="flex items-end justify-between gap-1.5 h-44">
      {data.map((d, i) => {
        const h = (d.v / max) * 100;
        const isLast = highlightLast && i === data.length - 1;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-2">
            <div className="w-full rounded-t transition-all" style={{
              height: `${h}%`,
              background: isLast ? theme.primary : `${theme.primary}55`,
            }} />
            <div className="text-[9px] font-mono whitespace-nowrap" style={{ color: isLast ? theme.text : theme.textSecondary, fontWeight: isLast ? 700 : 400 }}>
              {d.k}
            </div>
          </div>
        );
      })}
    </div>
  );
}
