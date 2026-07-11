import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Zap, Download, Share2, ArrowRight, Loader2, RotateCcw, MapPin,
  TrendingUp, TrendingDown, Sparkles, Info, UserPlus, Building2,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, API_BASE } from '../services/api';
import { ModernSelect } from '../components/ui/ModernSelect';
import PageHint from '../components/ui/PageHint';
import { NextStepCard } from '../components/ui/NextStepCard';
import { useTheme } from '../contexts/ThemeContext';
import type { Property } from '../types';

const TYPE_OPTIONS = [
  { value: 'departamento', label: 'Departamento' },
  { value: 'casa', label: 'Casa' },
  { value: 'ph', label: 'PH' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'local', label: 'Local comercial' },
  { value: 'oficina', label: 'Oficina' },
];
const CONDITION_OPTIONS = [
  { value: 'a_estrenar', label: 'A estrenar' },
  { value: 'excelente', label: 'Excelente' },
  { value: 'muy_bueno', label: 'Muy bueno' },
  { value: 'bueno', label: 'Bueno' },
  { value: 'regular', label: 'Regular' },
  { value: 'a_reciclar', label: 'A reciclar' },
];

const SCOPE_LABEL: Record<string, string> = {
  zona: 'Zona (barrio/ciudad)',
  provincia: 'Provincia',
  nacional: 'Nacional',
  sin_datos: 'Sin datos suficientes',
};

interface Band { low: number | null; typical: number | null; high: number | null; }
interface ValuationOutput {
  pricePerM2USD: Band;
  totalPriceUSD: Band;
  confidence?: string;
  marketSummary?: string;
  factorsUp?: string[];
  factorsDown?: string[];
  commercialStrategy?: string;
}
interface AnchorComparable {
  title: string; location: string; surface_m2: number;
  total_price_usd: number; price_per_m2_usd: number | null;
}
interface ValuationResult {
  id: number;
  scope: string;
  ai_used: boolean;
  currency: string;
  input: Record<string, unknown>;
  output: ValuationOutput;
  anchor: { count: number; comparables: AnchorComparable[] } | null;
}

const CONFIDENCE_COLOR: Record<string, string> = {
  alta: '#16a34a', media: '#f59e0b', baja: '#dc2626',
};

export default function TasacionExpress() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [form, setForm] = useState<Record<string, string>>({
    property_type: 'departamento', province: '', city: '', neighborhood: '',
    total_area_m2: '', rooms: '', bedrooms: '', age_years: '', condition: 'bueno', features: '',
  });
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<ValuationResult | null>(null);
  // Contexto de encadenado (WO F6-03): ?cliente= viene de la ficha de cliente;
  // ?propiedad= viene del alta de propiedad ("tasar esta propiedad") y pre-llena
  // el formulario con los datos reales de esa propiedad.
  const [clientId, setClientId] = useState<number | null>(null);
  const [savingLead, setSavingLead] = useState(false);

  const set = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));

  // Pre-carga por query param.
  useEffect(() => {
    const cliente = searchParams.get('cliente');
    const propiedad = searchParams.get('propiedad');
    if (cliente) setClientId(Number(cliente));
    if (propiedad) {
      api.get<Property>(`/properties/${propiedad}`).then(r => {
        const p = r.data;
        setForm(f => ({
          ...f,
          property_type: p.property_type || f.property_type,
          province: p.province || '',
          city: p.city || '',
          neighborhood: p.neighborhood || '',
          total_area_m2: p.total_area_m2 != null ? String(p.total_area_m2) : '',
          rooms: p.rooms != null ? String(p.rooms) : '',
          bedrooms: p.bedrooms != null ? String(p.bedrooms) : '',
          age_years: p.age_years != null ? String(p.age_years) : '',
          condition: p.condition || f.condition,
        }));
        toast.info('Datos de la propiedad cargados — tasá con un clic');
      }).catch(() => {});
    }
    if (cliente || propiedad) {
      searchParams.delete('cliente');
      searchParams.delete('propiedad');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const submit = async () => {
    if (!form.total_area_m2 || Number(form.total_area_m2) <= 0) {
      return toast.error('Ingresá la superficie total (m2)');
    }
    setBusy(true);
    setResult(null);
    try {
      const payload = {
        property_type: form.property_type,
        province: form.province || null,
        city: form.city || null,
        neighborhood: form.neighborhood || null,
        total_area_m2: Number(form.total_area_m2),
        rooms: form.rooms ? Number(form.rooms) : null,
        bedrooms: form.bedrooms ? Number(form.bedrooms) : null,
        age_years: form.age_years ? Number(form.age_years) : null,
        condition: form.condition || null,
        features: form.features ? form.features.split(',').map(s => s.trim()).filter(Boolean) : [],
      };
      const r = await api.post<ValuationResult>('/valuations/express', payload);
      setResult(r.data);
      if (r.data.scope === 'sin_datos') {
        toast.warning('No hay comparables suficientes en el catálogo para esta propiedad');
      } else {
        toast.success('Valuación lista');
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al valuar');
    } finally {
      setBusy(false);
    }
  };

  const reset = () => { setResult(null); };

  const downloadPdf = () => {
    if (!result) return;
    const token = localStorage.getItem('tasar_token');
    fetch(`${API_BASE}/valuations/express/${result.id}/pdf`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; link.download = `tasacion-express-${result.id}.pdf`; link.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => toast.error('No se pudo descargar el PDF'));
  };

  const valuationSummary = (): string => {
    if (!result) return '';
    const t = result.output.totalPriceUSD;
    const loc = [form.neighborhood, form.city].filter(Boolean).join(', ') || 'la zona';
    const typical = t.typical != null ? `USD ${t.typical.toLocaleString()}` : 'a confirmar';
    const range = (t.low != null && t.high != null)
      ? ` (rango USD ${t.low.toLocaleString()} - ${t.high.toLocaleString()})` : '';
    return `Tasación express: ${form.property_type} en ${loc}, ${form.total_area_m2} m2. Valor estimado ${typical}${range}.`;
  };

  const share = () => {
    if (!result) return;
    window.open(`https://wa.me/?text=${encodeURIComponent(valuationSummary())}`, '_blank');
  };

  // Eslabón 1a del ciclo: guardar el resultado como cliente interesado. Si el
  // express se abrió desde una ficha (?cliente=), vamos directo a esa ficha; si
  // no, creamos un lead con nombre PROVISIONAL (nunca datos inventados de una
  // persona real: sin teléfono/DNI ficticios) + la valuación en las notas, y
  // abrimos su ficha para completarlo.
  const saveAsLead = async () => {
    if (clientId) {
      navigate(`/clientes/${clientId}`);
      return;
    }
    setSavingLead(true);
    try {
      const loc = [form.neighborhood, form.city].filter(Boolean).join(', ') || 'zona sin especificar';
      const provisionalName = `Interesado · ${form.property_type} en ${loc}`;
      const r = await api.post<{ id: number }>('/clients', {
        name: provisionalName,
        type: 'particular',
        notes: valuationSummary(),
      });
      toast.success('Lead creado — completá sus datos de contacto');
      navigate(`/clientes/${r.data.id}`);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo crear el cliente');
    } finally {
      setSavingLead(false);
    }
  };

  // Eslabón 1b: cargar la propiedad con los datos del formulario ya pre-cargados.
  const loadProperty = () => {
    const params = new URLSearchParams({ nueva: '1' });
    const loc = [form.neighborhood, form.city].filter(Boolean).join(', ');
    if (loc) params.set('title', `${form.property_type} en ${loc}`);
    const map: Record<string, string> = {
      property_type: form.property_type, province: form.province, city: form.city,
      neighborhood: form.neighborhood, total_area_m2: form.total_area_m2, rooms: form.rooms,
      bedrooms: form.bedrooms, age_years: form.age_years, condition: form.condition,
    };
    Object.entries(map).forEach(([k, v]) => { if (v) params.set(k, v); });
    navigate(`/propiedades?${params.toString()}`);
  };

  const out = result?.output;
  const scopeReal = result && result.scope !== 'zona' && result.scope !== 'sin_datos';

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in">
      <PageHint pageId="tasacion-express" />

      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-11 h-11 rounded-xl flex items-center justify-center"
          style={{ background: 'linear-gradient(135deg, #f59e0b, #ef4444)' }}>
          <Zap className="h-6 w-6 text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Tasación express</h1>
          <p className="text-sm" style={{ color: theme.textSecondary }}>
            Valor instantáneo anclado a comparables reales del mercado
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <div className="rounded-2xl p-5" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="space-y-4">
            <ModernSelect label="Tipo de propiedad" value={form.property_type}
              onChange={(v: any) => set('property_type', v)} options={TYPE_OPTIONS} />

            <div className="grid grid-cols-2 gap-3">
              <Field label="Provincia" value={form.province} onChange={(v) => set('province', v)} placeholder="Buenos Aires" />
              <Field label="Ciudad / Partido" value={form.city} onChange={(v) => set('city', v)} placeholder="CABA" />
            </div>
            <Field label="Barrio" value={form.neighborhood} onChange={(v) => set('neighborhood', v)} placeholder="Palermo" />

            <div className="grid grid-cols-3 gap-3">
              <Field label="Sup. total (m2)" type="number" value={form.total_area_m2} onChange={(v) => set('total_area_m2', v)} placeholder="80" />
              <Field label="Ambientes" type="number" value={form.rooms} onChange={(v) => set('rooms', v)} placeholder="3" />
              <Field label="Dormitorios" type="number" value={form.bedrooms} onChange={(v) => set('bedrooms', v)} placeholder="2" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Field label="Antigüedad (años)" type="number" value={form.age_years} onChange={(v) => set('age_years', v)} placeholder="10" />
              <ModernSelect label="Estado" value={form.condition}
                onChange={(v: any) => set('condition', v)} options={CONDITION_OPTIONS} />
            </div>

            <Field label="Características (separadas por coma)" value={form.features}
              onChange={(v) => set('features', v)} placeholder="cochera, pileta, balcón" />

            <button onClick={submit} disabled={busy}
              className="w-full py-3 rounded-xl font-semibold text-white flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #f59e0b, #ef4444)' }}>
              {busy ? <Loader2 className="h-5 w-5 animate-spin" /> : <Zap className="h-5 w-5" />}
              {busy ? 'Calculando...' : 'Tasar ahora'}
            </button>
          </div>
        </div>

        {/* Result */}
        <div className="rounded-2xl p-5 flex flex-col" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          {!result && !busy && (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-12">
              <Sparkles className="h-12 w-12 mb-3" style={{ color: theme.textSecondary }} />
              <p style={{ color: theme.textSecondary }}>
                Completá los datos y obtené el valor estimado en segundos.
              </p>
            </div>
          )}
          {busy && (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin" style={{ color: theme.primary }} />
            </div>
          )}
          {result && out && (
            <div className="animate-fade-in space-y-4">
              {/* Scope badge */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md font-semibold"
                  style={{ background: `${theme.info}18`, color: theme.info }}>
                  <MapPin className="h-3 w-3" /> {SCOPE_LABEL[result.scope] || result.scope}
                </span>
                {result.anchor && (
                  <span className="text-[11px] px-2 py-1 rounded-md font-medium"
                    style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                    {result.anchor.count} comparables
                  </span>
                )}
                <span className="text-[11px] px-2 py-1 rounded-md font-medium"
                  style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                  {result.ai_used ? 'IA anclada' : 'Estimación determinística'}
                </span>
              </div>

              {scopeReal && (
                <div className="flex items-start gap-2 text-xs p-2.5 rounded-lg"
                  style={{ background: `${theme.warning}15`, color: theme.text }}>
                  <Info className="h-4 w-4 flex-shrink-0 mt-0.5" style={{ color: theme.warning }} />
                  <span>
                    Sin datos del barrio: el valor se ancló a nivel <b>{SCOPE_LABEL[result.scope]?.toLowerCase()}</b>.
                    Es más orientativo.
                  </span>
                </div>
              )}

              {/* Valor */}
              <div className="rounded-xl p-4 text-white" style={{ background: 'linear-gradient(135deg, #f59e0b, #ef4444)' }}>
                <div className="text-xs opacity-90">Valor estimado (cierre)</div>
                <div className="text-3xl font-bold mt-1">
                  {out.totalPriceUSD.typical != null
                    ? `${result.currency} ${out.totalPriceUSD.typical.toLocaleString()}`
                    : 'Sin dato'}
                </div>
                {out.totalPriceUSD.low != null && out.totalPriceUSD.high != null && (
                  <div className="text-xs mt-1 opacity-90">
                    Rango: {result.currency} {out.totalPriceUSD.low.toLocaleString()} - {out.totalPriceUSD.high.toLocaleString()}
                  </div>
                )}
                {out.pricePerM2USD.typical != null && (
                  <div className="text-xs mt-2 opacity-90">
                    USD/m2: {out.pricePerM2USD.low ?? '-'} · <b>{out.pricePerM2USD.typical}</b> · {out.pricePerM2USD.high ?? '-'}
                  </div>
                )}
              </div>

              {out.confidence && (
                <div className="flex items-center gap-2 text-sm">
                  <span style={{ color: theme.textSecondary }}>Confianza:</span>
                  <span className="font-semibold capitalize"
                    style={{ color: CONFIDENCE_COLOR[out.confidence] || theme.text }}>{out.confidence}</span>
                </div>
              )}

              {out.marketSummary && (
                <p className="text-sm" style={{ color: theme.textSecondary }}>{out.marketSummary}</p>
              )}

              {/* Factores */}
              {((out.factorsUp?.length ?? 0) > 0 || (out.factorsDown?.length ?? 0) > 0) && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    {(out.factorsUp || []).map((f, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-xs mb-1" style={{ color: theme.text }}>
                        <TrendingUp className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" style={{ color: '#16a34a' }} /> {f}
                      </div>
                    ))}
                  </div>
                  <div>
                    {(out.factorsDown || []).map((f, i) => (
                      <div key={i} className="flex items-start gap-1.5 text-xs mb-1" style={{ color: theme.text }}>
                        <TrendingDown className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" style={{ color: '#dc2626' }} /> {f}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {out.commercialStrategy && (
                <div className="text-xs p-3 rounded-lg" style={{ background: theme.backgroundSecondary, color: theme.text }}>
                  <b>Estrategia:</b> {out.commercialStrategy}
                </div>
              )}

              {/* Acciones */}
              <div className="flex flex-wrap gap-2 pt-2">
                <button onClick={downloadPdf}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
                  style={{ background: `${theme.primary}15`, color: theme.primary }}>
                  <Download className="h-4 w-4" /> PDF
                </button>
                <button onClick={share}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
                  style={{ background: '#22c55e18', color: '#16a34a' }}>
                  <Share2 className="h-4 w-4" /> Compartir
                </button>
                <button onClick={() => navigate('/tasaciones')}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
                  style={{ background: `${theme.text}12`, color: theme.text }}>
                  Tasación completa <ArrowRight className="h-4 w-4" />
                </button>
                <button onClick={reset}
                  className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all active:scale-95"
                  style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                  <RotateCcw className="h-4 w-4" /> Otra
                </button>
              </div>

              {/* Eslabón 1 del ciclo: el resultado desemboca en lead + propiedad. */}
              <NextStepCard
                className="mt-2"
                message={clientId
                  ? 'Volvé a la ficha del cliente para seguir con la operación.'
                  : 'Convertí esta tasación en un lead y cargá la propiedad al catálogo.'}
                actions={[
                  {
                    label: clientId ? 'Ver ficha del cliente' : 'Guardar como cliente interesado',
                    icon: <UserPlus className="h-4 w-4" />,
                    onClick: saveAsLead,
                    disabled: savingLead,
                  },
                  {
                    label: 'Cargar la propiedad',
                    icon: <Building2 className="h-4 w-4" />,
                    variant: 'secondary',
                    onClick: loadProperty,
                  },
                ]}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}
function Field({ label, value, onChange, type = 'text', placeholder }: FieldProps) {
  const { theme } = useTheme();
  return (
    <div>
      <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all"
        style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: '16px' }} />
    </div>
  );
}
