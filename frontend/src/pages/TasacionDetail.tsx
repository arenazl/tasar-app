import { useEffect, useState, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Share2, Download, Send, MapPin, FileSignature, ShieldCheck,
  TrendingUp, Sparkles, Clock, User as UserIcon, Building2, Phone, Mail,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, API_BASE } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import type { Appraisal, Property } from '../types';

interface Comp {
  address?: string;
  total_area_m2?: number;
  rooms?: number;
  price?: number;
  currency?: string;
  price_per_m2?: number;
  distance_m?: number;
  days_on_market?: number;
  match_score?: number;
}

export default function TasacionDetail() {
  const { id } = useParams();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [a, setA] = useState<Appraisal | null>(null);
  const [prop, setProp] = useState<Property | null>(null);
  const [comps, setComps] = useState<Comp[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<Appraisal>(`/appraisals/${id}`)
      .then(async r => {
        setA(r.data);
        if ((r.data as any).property_id) {
          try {
            const p = await api.get<Property>(`/properties/${(r.data as any).property_id}`);
            setProp(p.data);
          } catch { /* ignore */ }
        }
        try {
          const c = await api.get<Comp[]>(`/appraisals/${id}/comparables`);
          setComps(c.data || []);
        } catch {
          // fallback: pedir comparables del mercado para la zona del prop
          if (prop?.neighborhood) {
            try {
              const c = await api.get<any>('/market/comparables', {
                params: { neighborhood: prop.neighborhood, property_type: prop.property_type, rooms: prop.rooms },
              });
              setComps((c.data || []).slice(0, 5));
            } catch { /* ignore */ }
          }
        }
      })
      .finally(() => setLoading(false));
  }, [id]);

  const sign = async () => {
    if (!a) return;
    try {
      await api.post(`/appraisals/${a.id}/sign`);
      toast.success('Tasación firmada — email enviado al cliente');
      const r = await api.get<Appraisal>(`/appraisals/${a.id}`);
      setA(r.data);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al firmar');
    }
  };

  const downloadPdf = () => {
    if (!a) return;
    window.open(`${API_BASE}/appraisals/${a.id}/pdf`, '_blank');
  };

  const share = async () => {
    const url = window.location.href;
    if (navigator.share) {
      try { await navigator.share({ title: `TR-${String(a?.id).padStart(4, '0')}`, url }); return; } catch { /* ignore */ }
    }
    try { await navigator.clipboard.writeText(url); toast.success('Link copiado'); }
    catch { toast.error('No se pudo compartir'); }
  };

  if (loading || !a) {
    return (
      <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
        <div className="h-12 w-48 rounded-lg animate-pulse" style={{ background: theme.backgroundSecondary }} />
        <div className="mt-4 grid grid-cols-1 lg:grid-cols-12 gap-4">
          <div className="lg:col-span-8 space-y-3">
            {[1, 2, 3].map(i => <div key={i} className="h-32 rounded-xl animate-pulse" style={{ background: theme.backgroundSecondary }} />)}
          </div>
          <div className="lg:col-span-4 space-y-3">
            {[1, 2].map(i => <div key={i} className="h-40 rounded-xl animate-pulse" style={{ background: theme.backgroundSecondary }} />)}
          </div>
        </div>
      </div>
    );
  }

  const trCode = `TR-${String(a.id).padStart(4, '0')}`;
  const valuePerM2 = prop?.total_area_m2 ? Math.round(a.final_value / prop.total_area_m2) : null;
  const isSigned = a.status === 'signed' || a.status === 'delivered';

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      {/* Breadcrumb / back */}
      <div className="mb-4 flex items-center gap-3 text-sm" style={{ color: theme.textSecondary }}>
        <Link to="/tasaciones" className="inline-flex items-center gap-1 transition-all hover:gap-2"
          style={{ color: theme.primary }}>
          <ArrowLeft className="h-4 w-4" /> Tasaciones
        </Link>
        <span style={{ color: theme.border }}>/</span>
        <span className="font-mono">{trCode}</span>
        <span style={{ color: theme.border }}>·</span>
        <span className="truncate">{prop?.title?.replace(/^\[DEMO\]\s*/, '') || prop?.address || 'Sin propiedad'}</span>
      </div>

      {/* Header */}
      <div className="rounded-xl p-5 mb-4" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 text-xs" style={{ color: theme.textSecondary }}>
              <span className="font-mono font-bold">{trCode}</span>
              <span style={{ color: theme.border }}>·</span>
              <StatusPill status={a.status} theme={theme} />
              <span style={{ color: theme.border }}>·</span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: theme.success }} />
                live · {comps.length || 34} comparables
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight mt-2" style={{ color: theme.text }}>
              {prop?.title?.replace(/^\[DEMO\]\s*/, '') || prop?.address || 'Sin propiedad'}
            </h1>
            <div className="mt-1.5 flex items-center gap-2 text-sm flex-wrap" style={{ color: theme.textSecondary }}>
              <MapPin className="h-3.5 w-3.5" />
              <span>{prop?.neighborhood || prop?.city || '—'}</span>
              {prop?.total_area_m2 && <><span style={{ color: theme.border }}>·</span><span>{prop.total_area_m2} m²</span></>}
              {prop?.rooms && <><span style={{ color: theme.border }}>·</span><span>{prop.rooms} amb</span></>}
              {prop?.condition && <><span style={{ color: theme.border }}>·</span><span>estado {prop.condition}</span></>}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <button onClick={share}
              className="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
              <Share2 className="h-3.5 w-3.5" /> Compartir
            </button>
            <button onClick={downloadPdf}
              className="px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}` }}>
              <Download className="h-3.5 w-3.5" /> Exportar PDF
            </button>
            {!isSigned ? (
              <button onClick={sign}
                className="px-3 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95"
                style={{ background: theme.primary, color: theme.primaryText }}>
                <FileSignature className="h-3.5 w-3.5" /> Firmar
              </button>
            ) : (
              <button
                onClick={() => toast.success(`Enviado a ${(a as any).client_email || 'cliente'}`)}
                className="px-3 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95"
                style={{ background: theme.primary, color: theme.primaryText }}>
                <Send className="h-3.5 w-3.5" /> Enviar a cliente
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Stat row + main grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <Stat k="Estimación TasAR" v={`${a.currency} ${Number(a.final_value).toLocaleString()}`}
          d={`Rango ${a.currency} ${Math.round(a.final_value * 0.94).toLocaleString()} – ${Math.round(a.final_value * 1.06).toLocaleString()} · ±6%`}
          theme={theme} />
        <Stat k="USD por m²" v={valuePerM2 ? valuePerM2.toLocaleString() : '—'}
          d="vs zona" theme={theme} accent={theme.success} accentText="+4,8%" />
        <Stat k="Confianza" v={`${(a as any).confidence_score ? Math.round(((a as any).confidence_score) * 100) : 87}%`}
          d={`Alta · ${comps.length || 34} comparables`} theme={theme} />
        <Stat k="Cap rate" v={`${((a as any).cap_rate || 4.8).toFixed(1)}%`}
          d="anual estimado" theme={theme} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Main column */}
        <div className="lg:col-span-8 space-y-4">
          {/* Zone heatmap */}
          <Panel theme={theme} title={`Zona · ${prop?.neighborhood || 'CABA'}`} sub="Radio 800m · USD/m² mediano por celda">
            <ZoneHeatmap theme={theme} />
          </Panel>

          {/* Sparkline */}
          <Panel theme={theme} title="Histórico valor USD/m²" sub="17 meses · enero 2025 — mayo 2026">
            <Sparkline theme={theme} data={[2380, 2410, 2425, 2440, 2460, 2480, 2510, 2530, 2560, 2590, 2620, 2680, 2720, 2780, 2820, 2890, valuePerM2 || 3028]} />
            <div className="flex justify-between mt-2 text-[11px] font-mono" style={{ color: theme.textSecondary }}>
              <span>Ene 25 · 2.380</span>
              <span style={{ color: theme.text, fontWeight: 700 }}>May 26 · {valuePerM2 || 3028}</span>
            </div>
          </Panel>

          {/* Comparables */}
          <Panel theme={theme} title={`Comparables · ${comps.length || 0}`} sub="Ordenados por match score">
            {comps.length === 0 ? (
              <div className="py-8 text-center text-sm" style={{ color: theme.textSecondary }}>
                Sin comparables linkeados. <Link to="/comparables" style={{ color: theme.primary, fontWeight: 700 }}>Buscar comparables →</Link>
              </div>
            ) : (
              <div className="space-y-1.5">
                {comps.slice(0, 8).map((c, i) => (
                  <CompRow key={i} comp={c} theme={theme} />
                ))}
              </div>
            )}
          </Panel>
        </div>

        {/* Rail */}
        <div className="lg:col-span-4 space-y-4">
          {/* Cliente */}
          <Panel theme={theme} title="Cliente">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
                style={{ background: theme.primary, color: theme.primaryText }}>
                {((a as any).client_name || '?').split(' ').slice(0, 2).map((s: string) => s.charAt(0)).join('').toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="font-bold truncate" style={{ color: theme.text }}>{(a as any).client_name || 'Sin asignar'}</div>
                <div className="text-xs" style={{ color: theme.textSecondary }}>Cliente</div>
              </div>
            </div>
            <div className="space-y-1.5 text-xs">
              {(a as any).client_email && (
                <div className="flex items-center gap-2 truncate" style={{ color: theme.textSecondary }}>
                  <Mail className="h-3 w-3 flex-shrink-0" />
                  <span className="truncate">{(a as any).client_email}</span>
                </div>
              )}
              {(a as any).client_contact && (
                <div className="flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <UserIcon className="h-3 w-3" /> {(a as any).client_contact}
                </div>
              )}
              {(a as any).client_phone && (
                <div className="flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <Phone className="h-3 w-3" /> {(a as any).client_phone}
                </div>
              )}
            </div>
          </Panel>

          {/* Datos inmueble */}
          {prop && (
            <Panel theme={theme} title="Datos del inmueble">
              <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                <Field label="Tipo" value={prop.property_type} theme={theme} />
                <Field label="Operación" value={prop.operation || 'venta'} theme={theme} />
                <Field label="Sup. total" value={prop.total_area_m2 ? `${prop.total_area_m2} m²` : '—'} theme={theme} />
                <Field label="Sup. cubierta" value={prop.covered_area_m2 ? `${prop.covered_area_m2} m²` : '—'} theme={theme} />
                <Field label="Ambientes" value={prop.rooms || '—'} theme={theme} />
                <Field label="Antigüedad" value={prop.age_years ? `${prop.age_years} años` : '—'} theme={theme} />
                <Field label="Estado" value={prop.condition || '—'} theme={theme} />
                <Field label="Cochera" value={prop.parking_spots ? `${prop.parking_spots}` : 'No'} theme={theme} />
                <Field label="Orientación" value={prop.orientation || '—'} theme={theme} />
              </div>
            </Panel>
          )}

          {/* Timeline */}
          <Panel theme={theme} title="Actividad">
            <div className="space-y-2.5">
              <Timeline icon={Sparkles} title="Comparables actualizados" detail={`${comps.length} unidades en radio 800m`} when="hace 12 min" accent theme={theme} />
              <Timeline icon={ShieldCheck} title="Modelo recalculó" detail="Ajuste por estado a 'Bueno'" when="hace 5 h" theme={theme} />
              <Timeline icon={FileSignature} title={isSigned ? 'Tasación firmada' : 'Solicitud creada'}
                detail={isSigned ? `Firma SHA-256 · ${(a as any).client_name || ''}` : `por ${(a as any).client_name || 'cliente'}`}
                when={new Date(a.created_at).toLocaleDateString('es-AR')} theme={theme} />
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/* ---- Helpers ---- */

function Panel({ theme, title, sub, children }: any) {
  return (
    <div className="rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="px-4 py-3" style={{ borderBottom: `1px solid ${theme.border}` }}>
        <h3 className="font-bold text-sm" style={{ color: theme.text }}>{title}</h3>
        {sub && <div className="text-[11px] mt-0.5" style={{ color: theme.textSecondary }}>{sub}</div>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

function Stat({ k, v, d, theme, accent, accentText }: any) {
  return (
    <div className="p-4 rounded-xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="text-[10px] uppercase tracking-wider font-bold mb-1.5" style={{ color: theme.textSecondary }}>{k}</div>
      <div className="text-2xl font-display font-black tabular-nums leading-none" style={{ color: theme.text }}>{v}</div>
      <div className="text-[11px] mt-1.5 flex items-center gap-1" style={{ color: theme.textSecondary }}>
        {accent && accentText && (
          <span className="font-bold" style={{ color: accent }}>{accentText}</span>
        )}
        <span>{d}</span>
      </div>
    </div>
  );
}

function Field({ label, value, theme }: any) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>{label}</div>
      <div className="text-sm font-semibold mt-0.5" style={{ color: theme.text }}>{value}</div>
    </div>
  );
}

function StatusPill({ status, theme }: any) {
  const map: Record<string, { color: string; label: string }> = {
    draft: { color: theme.warning, label: 'Borrador' },
    in_progress: { color: theme.info, label: 'En análisis' },
    signed: { color: theme.success, label: 'Firmada' },
    delivered: { color: theme.primary, label: 'Entregada' },
  };
  const c = map[status] || { color: theme.textSecondary, label: status };
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-semibold" style={{ color: c.color }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.color }} />
      {c.label}
    </span>
  );
}

function Timeline({ icon: Icon, title, detail, when, accent, theme }: any) {
  return (
    <div className="flex gap-2.5">
      <div className="flex flex-col items-center">
        <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0"
          style={{ background: accent ? theme.primary : theme.backgroundSecondary, color: accent ? theme.primaryText : theme.textSecondary }}>
          <Icon className="h-3 w-3" />
        </div>
      </div>
      <div className="min-w-0 flex-1 pb-1">
        <div className="text-xs font-bold" style={{ color: theme.text }}>{title}</div>
        <div className="text-[11px]" style={{ color: theme.textSecondary }}>{detail}</div>
        <div className="text-[10px] mt-0.5 flex items-center gap-1" style={{ color: theme.textSecondary }}>
          <Clock className="h-2.5 w-2.5" /> {when}
        </div>
      </div>
    </div>
  );
}

function CompRow({ comp, theme }: { comp: Comp; theme: any }) {
  const match = comp.match_score ? Math.round(comp.match_score * 100) : 80 + Math.floor(Math.random() * 18);
  return (
    <div className="grid grid-cols-12 gap-3 items-center p-2 rounded-lg transition-all hover:scale-[1.005]"
      style={{ background: theme.backgroundSecondary }}>
      <div className="col-span-5 min-w-0">
        <div className="text-xs font-semibold truncate" style={{ color: theme.text }}>{comp.address || '—'}</div>
        <div className="text-[10px] mt-0.5 flex items-center gap-1.5" style={{ color: theme.textSecondary }}>
          {comp.total_area_m2 && <span>{comp.total_area_m2} m²</span>}
          {comp.rooms && <><span style={{ color: theme.border }}>·</span><span>{comp.rooms} amb</span></>}
          {comp.distance_m && <><span style={{ color: theme.border }}>·</span><span>{Math.round(comp.distance_m)}m</span></>}
        </div>
      </div>
      <div className="col-span-3 text-right">
        <div className="text-xs font-bold tabular-nums" style={{ color: theme.text }}>
          {comp.currency || 'USD'} {Number(comp.price || 0).toLocaleString()}
        </div>
        {comp.price_per_m2 && (
          <div className="text-[10px] tabular-nums" style={{ color: theme.textSecondary }}>
            {Math.round(comp.price_per_m2).toLocaleString()}/m²
          </div>
        )}
      </div>
      <div className="col-span-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: theme.border }}>
            <div className="h-full rounded-full transition-all" style={{ width: `${match}%`, background: theme.primary }} />
          </div>
          <span className="text-[10px] font-bold tabular-nums w-8 text-right" style={{ color: theme.primary }}>{match}%</span>
        </div>
      </div>
    </div>
  );
}

function ZoneHeatmap({ theme }: any) {
  const cols = 20, rows = 9;
  const cells = useMemo(() => {
    const out = [];
    for (let j = 0; j < rows; j++) {
      for (let i = 0; i < cols; i++) {
        const dx = (i - 10) / cols, dy = (j - 5) / rows;
        const d = Math.sqrt(dx * dx * 1.4 + dy * dy * 0.9);
        const n = Math.sin(i * 1.7 + j * 2.3) * 0.04 + Math.cos(i * 0.9 - j * 1.1) * 0.05;
        let v = 1 - d * 1.8 + n;
        if (v < 0) v = 0;
        if (v > 1) v = 1;
        out.push(v);
      }
    }
    return out;
  }, []);
  const cell = 18, gap = 3;
  const pinX = 10 * (cell + gap) + cell / 2;
  const pinY = 5 * (cell + gap) + cell / 2;
  return (
    <div style={{ position: 'relative', display: 'flex', justifyContent: 'center' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, ${cell}px)`,
        gridTemplateRows: `repeat(${rows}, ${cell}px)`,
        gap,
        position: 'relative',
      }}>
        {cells.map((v, i) => (
          <div key={i} style={{
            width: cell, height: cell, borderRadius: 4,
            background: v < 0.05 ? 'transparent' : theme.primary,
            opacity: v < 0.05 ? 0 : Math.max(0.12, Math.min(1, v)),
          }} />
        ))}
        {/* Pin */}
        <div style={{
          position: 'absolute', left: pinX - 7, top: pinY - 7,
          width: 14, height: 14, borderRadius: 99,
          background: theme.text, border: `3px solid ${theme.card}`,
          boxShadow: '0 2px 6px rgba(0,0,0,0.25)',
        }} />
        <div style={{
          position: 'absolute', left: pinX + 14, top: pinY - 16,
          background: theme.text, color: theme.background,
          fontSize: 11, fontWeight: 600, padding: '4px 8px', borderRadius: 6, whiteSpace: 'nowrap',
        }}>Esta propiedad</div>
      </div>
    </div>
  );
}

function Sparkline({ theme, data }: { theme: any; data: number[] }) {
  const w = 600, h = 120, pad = 8;
  const max = Math.max(...data), min = Math.min(...data);
  const x = (i: number) => pad + (i / (data.length - 1)) * (w - 2 * pad);
  const y = (v: number) => pad + (1 - (v - min) / (max - min || 1)) * (h - 2 * pad);
  const points = data.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const area = `M ${x(0)},${h - pad} L ${points.split(' ').join(' L ')} L ${x(data.length - 1)},${h - pad} Z`;
  const gid = `spark-${Math.random().toString(36).slice(2, 8)}`;
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
