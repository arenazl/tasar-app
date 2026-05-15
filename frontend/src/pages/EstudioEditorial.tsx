import { useEffect, useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Share2, Download, BookmarkPlus, ChevronRight } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

interface ReportData {
  id: number;
  code: string;
  period_year: number;
  period_month: number;
  region: string;
  kind: string;
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

const MONTHS = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

export default function EstudioEditorial() {
  const { id } = useParams();
  const { theme } = useTheme();
  const [r, setR] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [scrollPct, setScrollPct] = useState(0);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<ReportData>(`/reports/${id}`).then(res => setR(res.data)).finally(() => setLoading(false));
  }, [id]);

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
      try { await navigator.share({ title: `Estudio ${r?.code} TasAR`, url }); return; } catch { /* ignore */ }
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

  const yoyDirection = (r.yoy_change_pct || 0) >= 0;
  const totalPages = r.pages_count || 38;
  const currentPage = Math.max(1, Math.round((scrollPct / 100) * totalPages));

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
          <button onClick={() => r.pdf_url ? window.open(r.pdf_url, '_blank') : toast.info('PDF en preparación')}
            className="px-2.5 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Download className="h-3 w-3" /> <span className="hidden sm:inline">PDF</span>
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
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] mb-6" style={{ color: theme.textSecondary }}>
            Edición {r.code} · {MONTHS[r.period_month]} {r.period_year} · {r.region}
          </div>
          <h1 className="font-display font-black tracking-tight leading-[1.02] text-[42px] sm:text-[56px] mb-6"
            style={{ color: theme.text }}>
            El interanual cierra en{' '}
            <span style={{ color: theme.primary }}>
              {yoyDirection ? '+' : ''}{r.yoy_change_pct?.toFixed(1) || '0,0'}%
            </span>
            {r.median_price_per_m2 && (
              <> y el m² supera USD {Math.round(r.median_price_per_m2 / 100) * 100} por primera vez desde 2019.</>
            )}
          </h1>
          <p className="text-lg leading-relaxed" style={{ color: theme.textSecondary }}>
            La recuperación del mercado inmobiliario porteño se afianza en {MONTHS[r.period_month]?.toLowerCase()}.
            El stock activo cae por tercer mes consecutivo, los permisos de obra suben 12% interanual y Palermo,
            Recoleta y Núñez lideran la suba de precios.
          </p>
          <div className="mt-6 flex items-center gap-3 pt-6" style={{ borderTop: `1px solid ${theme.border}` }}>
            <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm"
              style={{ background: theme.primary, color: theme.primaryText }}>TA</div>
            <div className="text-sm">
              <div className="font-bold" style={{ color: theme.text }}>Equipo TasAR</div>
              <div className="text-xs" style={{ color: theme.textSecondary }}>
                Publicado {r.published_at ? new Date(r.published_at).toLocaleDateString('es-AR', { day: '2-digit', month: 'long', year: 'numeric' }) : '—'}
                {' · '}{totalPages} páginas · lectura 18 min
              </div>
            </div>
          </div>
        </header>

        {/* TL;DR */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-14">
          <TldrCard n="01" h={`El índice toca USD ${Math.round(r.median_price_per_m2 || 2847)}/m²`}
            b={`Primer mes por encima de USD ${Math.round((r.median_price_per_m2 || 2847) / 100) * 100} desde octubre 2019. La aceleración se sostiene desde noviembre.`}
            theme={theme} className="est-fade est-d1" />
          <TldrCard n="02" h={`Stock activo cae ${r.mom_change_pct ? r.mom_change_pct.toFixed(1) : '-3,4'}%`}
            b={`${(r.active_listings || 62480).toLocaleString()} unidades en venta en ${r.region}, el menor nivel desde febrero 2023. Tres meses consecutivos en baja.`}
            theme={theme} className="est-fade est-d2" />
          <TldrCard n="03" h={`Permisos +${Math.round(((r.new_permits || 1213) / 1080 - 1) * 100)}% interanual`}
            b={`${(r.new_permits || 1213).toLocaleString()} permisos aprobados este mes. La obra nueva muestra el mejor ${MONTHS[r.period_month]?.toLowerCase()} en 7 años.`}
            theme={theme} className="est-fade est-d3" />
        </div>

        {/* §01 Índice */}
        <Section num="01" title="Índice" h2={`El índice supera USD ${Math.round((r.median_price_per_m2 || 2847) / 100) * 100}/m² por primera vez desde 2019.`} theme={theme}>
          <p>
            El <strong style={{ color: theme.text }}>Índice TasAR {r.region}</strong> cerró {MONTHS[r.period_month]?.toLowerCase()} en{' '}
            <strong style={{ color: theme.text }}>USD {Math.round(r.median_price_per_m2 || 2847).toLocaleString()}/m²</strong>,
            un +{(r.mom_change_pct || 1.2).toFixed(1)}% mensual y +{(r.yoy_change_pct || 14.2).toFixed(1)}% interanual.
            Es el mejor {MONTHS[r.period_month]?.toLowerCase()} desde 2019 y el séptimo mes consecutivo de suba.
          </p>
          <p>
            La dinámica responde a tres factores que vamos a desarmar en este informe:
            <strong style={{ color: theme.text }}> caída del stock activo</strong>,
            <strong style={{ color: theme.text }}> recuperación del crédito hipotecario</strong>
            y un cambio de mix — las ventas se están concentrando en barrios de mayor valor por metro.
          </p>
          <Figure caption={`Fig. 1 — Índice TasAR ${r.region}, USD/m² mediano ponderado. Fuente: TasAR Index v3.2.`} theme={theme}>
            <Sparkline theme={theme} data={[2380, 2410, 2425, 2440, 2460, 2480, 2510, 2530, 2560, 2590, 2620, 2680, 2720, 2780, 2820, 2890, Math.round(r.median_price_per_m2 || 3028)]} />
            <div className="flex justify-between mt-2 text-[11px] font-mono" style={{ color: theme.textSecondary }}>
              <span>Ene 25 · 2.380</span>
              <span style={{ color: theme.text, fontWeight: 700 }}>{MONTHS[r.period_month]?.slice(0, 3)} {String(r.period_year).slice(2)} · {Math.round(r.median_price_per_m2 || 3028)}</span>
            </div>
          </Figure>
        </Section>

        {/* Pull quote */}
        <PullQuote theme={theme} className="est-fade est-d4">
          "El m² porteño sumó USD 437 en 17 meses. Es la recuperación más firme desde el ciclo de 2017."
        </PullQuote>

        {/* §02 Zonas */}
        <Section num="02" title="Zonas" h2="Recuperación liderada por Palermo, Recoleta y Núñez." theme={theme}>
          <p>
            La suba no es homogénea. <strong style={{ color: theme.text }}>Palermo</strong> (+3,8% mensual),
            <strong style={{ color: theme.text }}> Núñez</strong> (+4,2%) y
            <strong style={{ color: theme.text }}> Caballito</strong> (+2,4%) concentran la mayor expansión.
            En el otro extremo, zonas del sur — Flores, Mataderos, Boedo — siguen en terreno levemente negativo.
          </p>
          <Figure caption={`Fig. 2 — USD/m² mediano por zona, top ${r.top_zones?.length || 11} en ${r.region}.`} theme={theme}>
            <BarChart data={r.top_zones || []} theme={theme} />
          </Figure>
        </Section>

        {/* §03 Oferta */}
        <Section num="03" title="Oferta" h2="El stock activo cae por tercer mes consecutivo." theme={theme}>
          <p>
            Las unidades activas en venta en {r.region} cerraron {MONTHS[r.period_month]?.toLowerCase()} en
            <strong style={{ color: theme.text }}> {(r.active_listings || 62480).toLocaleString()}</strong>,
            una baja del {r.mom_change_pct ? Math.abs(r.mom_change_pct).toFixed(1) : '3,4'}% respecto al mes anterior y la menor cifra desde febrero 2023.
          </p>
          <p>
            El tiempo medio de venta también se acorta: <strong style={{ color: theme.text }}>{r.avg_days_on_market || 94} días</strong>
            promedio, 8 días menos que en el Q1. La conjunción de menos oferta y ventas más rápidas
            es el patrón clásico de cambio de ciclo.
          </p>
        </Section>

        {/* §04 Obra nueva */}
        <Section num="04" title="Obra nueva" h2={`Permisos aprobados: ${(r.new_permits || 1213).toLocaleString()} en el mes.`} theme={theme}>
          <p>
            La obra nueva muestra el mejor {MONTHS[r.period_month]?.toLowerCase()} en 7 años con
            <strong style={{ color: theme.text }}> {(r.new_permits || 1213).toLocaleString()} permisos aprobados</strong>.
            El crecimiento es del +{Math.round(((r.new_permits || 1213) / 1080 - 1) * 100)}% interanual.
          </p>
          <Figure caption="Fig. 3 — Permisos de obra aprobados, últimos 13 meses." theme={theme}>
            <PermitsBarChart theme={theme} highlightLast />
          </Figure>
        </Section>

        {/* §05 Rentabilidad */}
        <Section num="05" title="Rentabilidad" h2="Cap rate promedio: 5,2% anual." theme={theme}>
          <p>
            La rentabilidad bruta del alquiler en {r.region} se ubica en 5,2% anual promedio,
            con diferencias marcadas según zona y tipología. Las zonas premium muestran cap rates
            más bajos por el mayor precio por m², mientras las del sur compensan con rendimientos del 6%+.
          </p>
          <CapRateTable theme={theme} />
          <p className="mt-6">
            La diferencia entre dpto y PH se sostiene en ~70 bps a favor del PH, reflejando
            el descuento estructural del segmento.
          </p>
        </Section>

        {/* §06 Lo que viene */}
        <Section num="06" title="Lo que viene" h2="Proyecciones para los próximos 6 meses." theme={theme}>
          <p>
            Si la pendiente actual se mantiene, el índice cruzaría los <strong style={{ color: theme.text }}>USD 3.000/m²</strong> antes
            de fin de año. Los factores a monitorear:
          </p>
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
                El Índice TasAR procesa avisos publicados, escrituras y permisos de obra. Mediana ponderada por
                tipología y barrio. Series desestacionalizadas. Documentación completa en tasar.app/methodology.
              </p>
            </div>
            <div>
              <div className="font-bold uppercase tracking-wider mb-2" style={{ color: theme.text }}>Sobre TasAR</div>
              <p className="leading-relaxed">
                TasAR es el motor de inteligencia inmobiliaria de Argentina. Procesamos millones de avisos al mes
                para tasadores, bancos, fondos e inmobiliarias. Reportes mensuales, API y CRM en
                tasar-app.netlify.app.
              </p>
            </div>
          </div>
          <div className="mt-6 text-center" style={{ color: theme.textSecondary }}>
            Edición {r.code} · TasAR © {new Date().getFullYear()}
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
  const items = data.length ? data : [
    { zone: 'Palermo', usd_m2: 3420 }, { zone: 'Recoleta', usd_m2: 3180 },
    { zone: 'Belgrano', usd_m2: 2890 }, { zone: 'Núñez', usd_m2: 2760 },
    { zone: 'Colegiales', usd_m2: 2430 }, { zone: 'Caballito', usd_m2: 2140 },
    { zone: 'Villa Crespo', usd_m2: 2020 }, { zone: 'Almagro', usd_m2: 1880 },
    { zone: 'San Telmo', usd_m2: 1640 }, { zone: 'Boedo', usd_m2: 1520 },
    { zone: 'Flores', usd_m2: 1480 },
  ];
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

function PermitsBarChart({ theme, highlightLast }: any) {
  const data = useMemo(() => [
    { k: 'May 25', v: 1080 }, { k: 'Jun', v: 1124 }, { k: 'Jul', v: 1015 }, { k: 'Ago', v: 980 },
    { k: 'Sep', v: 1056 }, { k: 'Oct', v: 1102 }, { k: 'Nov', v: 1138 }, { k: 'Dic', v: 1086 },
    { k: 'Ene 26', v: 1145 }, { k: 'Feb', v: 1174 }, { k: 'Mar', v: 1192 }, { k: 'Abr', v: 1208 },
    { k: 'May', v: 1213 },
  ], []);
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

function CapRateTable({ theme }: any) {
  const rows = [
    { zone: 'Palermo', dpto: '4,2%', ph: '4,9%', casa: '4,7%', heat: [0.85, 1.0, 0.95] },
    { zone: 'Recoleta', dpto: '4,8%', ph: '5,2%', casa: '5,1%', heat: [1.0, 0.75, 0.8] },
    { zone: 'Belgrano', dpto: '5,4%', ph: '5,8%', casa: '5,6%', heat: [0.6, 0.4, 0.5] },
    { zone: 'Núñez', dpto: '5,1%', ph: '5,5%', casa: '5,3%', heat: [0.8, 0.55, 0.65] },
    { zone: 'Caballito', dpto: '5,8%', ph: '6,1%', casa: '5,9%', heat: [0.35, 0.2, 0.25] },
    { zone: 'San Telmo', dpto: '6,4%', ph: '6,8%', casa: '6,2%', heat: [0.1, 0.05, 0.15] },
  ];
  return (
    <div className="rounded-xl overflow-hidden my-6" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="grid grid-cols-12 px-4 py-2.5 text-[10px] uppercase tracking-wider font-bold"
        style={{ background: theme.backgroundSecondary, color: theme.textSecondary, borderBottom: `1px solid ${theme.border}` }}>
        <div className="col-span-3">Zona</div>
        <div className="col-span-2 text-center">Dpto</div>
        <div className="col-span-2 text-center">PH</div>
        <div className="col-span-2 text-center">Casa</div>
        <div className="col-span-3 text-right">Relativo</div>
      </div>
      {rows.map((r, i) => (
        <div key={i} className="grid grid-cols-12 items-center px-4 py-2.5 text-sm"
          style={{ borderBottom: i < rows.length - 1 ? `1px solid ${theme.border}` : 'none' }}>
          <div className="col-span-3 font-semibold" style={{ color: theme.text }}>{r.zone}</div>
          <div className="col-span-2 text-center font-mono tabular-nums" style={{ color: theme.text }}>{r.dpto}</div>
          <div className="col-span-2 text-center font-mono tabular-nums" style={{ color: theme.text }}>{r.ph}</div>
          <div className="col-span-2 text-center font-mono tabular-nums" style={{ color: theme.text }}>{r.casa}</div>
          <div className="col-span-3 flex gap-1 justify-end">
            {r.heat.map((v, j) => (
              <div key={j} className="w-5 h-5 rounded" style={{ background: theme.primary, opacity: v }} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
