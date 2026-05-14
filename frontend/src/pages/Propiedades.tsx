import { useEffect, useMemo, useState } from 'react';
import {
  Plus, MapPin, Bed, Bath, Maximize2, Sparkles, Building2, Home as HomeIcon,
  FileText, DollarSign, ArrowUpDown, List, CircleDot, Star, Award, CheckCircle2,
  Inbox, Tag, Trees, Store, Briefcase, Castle,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { ABMPage, ABMCard, ABMCardActions, ABMTable, ABMTableAction } from '../components/ui/ABMPage';
import { WizardModal, type WizardStep } from '../components/ui/WizardModal';
import { ModernSelect } from '../components/ui/ModernSelect';
import PageHint from '../components/ui/PageHint';
import { ConfirmModal } from '../components/ui/ConfirmModal';
import { useTheme } from '../contexts/ThemeContext';
import type { Property } from '../types';

const TYPE_OPTIONS = [
  { value: '', label: 'Todos los tipos' },
  { value: 'casa', label: 'Casa' },
  { value: 'departamento', label: 'Departamento' },
  { value: 'ph', label: 'PH' },
  { value: 'terreno', label: 'Terreno' },
  { value: 'local', label: 'Local comercial' },
  { value: 'oficina', label: 'Oficina' },
];
const OPERATION_OPTIONS = [
  { value: '', label: 'Todas las operaciones' },
  { value: 'venta', label: 'Venta' },
  { value: 'alquiler', label: 'Alquiler' },
];
const CONDITION_OPTIONS = [
  { value: 'a_estrenar', label: 'A estrenar' },
  { value: 'excelente', label: 'Excelente' },
  { value: 'muy_bueno', label: 'Muy bueno' },
  { value: 'bueno', label: 'Bueno' },
  { value: 'regular', label: 'Regular' },
  { value: 'a_reciclar', label: 'A reciclar' },
];
const SORT_OPTIONS = [
  { value: 'recent', label: 'Más recientes' },
  { value: 'price_desc', label: 'Precio mayor a menor' },
  { value: 'price_asc', label: 'Precio menor a mayor' },
  { value: 'area_desc', label: 'Mayor superficie' },
  { value: 'title', label: 'Alfabético' },
];

const TYPE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  casa: { bg: '#fef3c7', text: '#92400e', label: 'Casa' },
  departamento: { bg: '#dbeafe', text: '#1e40af', label: 'Depto' },
  ph: { bg: '#fce7f3', text: '#9f1239', label: 'PH' },
  terreno: { bg: '#dcfce7', text: '#166534', label: 'Terreno' },
  local: { bg: '#ede9fe', text: '#5b21b6', label: 'Local' },
  oficina: { bg: '#e0f2fe', text: '#075985', label: 'Oficina' },
};

const TYPE_ICONS: Record<string, any> = {
  casa: HomeIcon,
  departamento: Building2,
  ph: Castle,
  terreno: Trees,
  local: Store,
  oficina: Briefcase,
};

const COND_COLORS: Record<string, string> = {
  a_estrenar: '#16a34a', excelente: '#22c55e', muy_bueno: '#3b82f6',
  bueno: '#0ea5e9', regular: '#f59e0b', a_reciclar: '#dc2626',
};

const emptyForm: any = {
  title: '', property_type: 'departamento', operation: 'venta',
  province: '', city: '', neighborhood: '', address: '',
  latitude: '', longitude: '',
  total_area_m2: '', covered_area_m2: '', rooms: '', bedrooms: '', bathrooms: '',
  parking_spots: '', age_years: '', condition: '', floor: '',
  asking_price: '', currency: 'USD', description: '',
};

function TypePill({ type }: { type: string }) {
  const c = TYPE_COLORS[type] || { bg: '#e2e8f0', text: '#475569', label: type };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}
function OpPill({ op }: { op: string }) {
  const isVenta = op === 'venta';
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: isVenta ? '#fee2e2' : '#cffafe', color: isVenta ? '#991b1b' : '#155e75' }}>
      {isVenta ? 'Venta' : 'Alquiler'}
    </span>
  );
}
function CondPill({ cond }: { cond: string }) {
  const color = COND_COLORS[cond] || '#64748b';
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium capitalize"
      style={{ background: `${color}15`, color }}>
      <span className="w-1 h-1 rounded-full" style={{ background: color }} />
      {cond.replace(/_/g, ' ')}
    </span>
  );
}

/** Status pill estilo Tesorería: icono + label + contador. */
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
        style={{
          background: active ? 'rgba(255,255,255,0.25)' : theme.backgroundSecondary,
          color: active ? '#fff' : theme.text,
        }}>
        {count}
      </span>
    </button>
  );
}

export default function Propiedades() {
  const { theme } = useTheme();
  const [items, setItems] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [wizardOpen, setWizardOpen] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [editing, setEditing] = useState<Property | null>(null);
  const [form, setForm] = useState<any>(emptyForm);

  // Filtros: search + 4 combos + 1 pill set
  const [search, setSearch] = useState('');
  const [filterProvince, setFilterProvince] = useState('');
  const [filterCity, setFilterCity] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterOp, setFilterOp] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all'|'destacadas'|'recientes'|'sin_precio'|'completas'>('all');
  const [sortBy, setSortBy] = useState('recent');

  const [confirm, setConfirm] = useState<Property | null>(null);
  const [aiBusy, setAiBusy] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try { const r = await api.get<Property[]>('/properties'); setItems(r.data); }
    catch { toast.error('Error cargando propiedades'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  // Opciones dinámicas de provincia / ciudad
  const provinceOptions = useMemo(() => {
    const provs = [...new Set(items.map(p => p.province).filter(Boolean))].sort();
    return [{ value: '', label: 'Todas las provincias' }, ...provs.map(p => ({ value: p, label: p }))];
  }, [items]);
  const cityOptions = useMemo(() => {
    const cities = [...new Set(items
      .filter(p => !filterProvince || p.province === filterProvince)
      .map(p => p.city).filter(Boolean))].sort();
    return [{ value: '', label: 'Todas las ciudades' }, ...cities.map(c => ({ value: c, label: c }))];
  }, [items, filterProvince]);

  // Aplicar combos primero (sin status filter) — necesario para los counts
  const baseFiltered = useMemo(() => items.filter(p => {
    if (filterProvince && p.province !== filterProvince) return false;
    if (filterCity && p.city !== filterCity) return false;
    if (filterType && p.property_type !== filterType) return false;
    if (filterOp && p.operation !== filterOp) return false;
    if (search) {
      const q = search.toLowerCase();
      return p.title.toLowerCase().includes(q) || p.address.toLowerCase().includes(q) || p.city.toLowerCase().includes(q);
    }
    return true;
  }), [items, filterProvince, filterCity, filterType, filterOp, search]);

  // Counts para los status pills (calculados sobre baseFiltered)
  const now = Date.now();
  const SEVEN_DAYS = 7 * 24 * 3600 * 1000;
  const counts = useMemo(() => ({
    all: baseFiltered.length,
    destacadas: baseFiltered.filter(p => (p.asking_price || 0) > 300000 || (p.total_area_m2 || 0) > 200).length,
    recientes: baseFiltered.filter(p => now - new Date(p.created_at).getTime() < SEVEN_DAYS).length,
    sin_precio: baseFiltered.filter(p => !p.asking_price).length,
    completas: baseFiltered.filter(p => p.asking_price && p.total_area_m2 && p.condition && p.rooms != null).length,
  }), [baseFiltered, now]);

  // Filtrado final + sort
  const filtered = useMemo(() => {
    let out = baseFiltered.filter(p => {
      if (statusFilter === 'destacadas') return (p.asking_price || 0) > 300000 || (p.total_area_m2 || 0) > 200;
      if (statusFilter === 'recientes') return now - new Date(p.created_at).getTime() < SEVEN_DAYS;
      if (statusFilter === 'sin_precio') return !p.asking_price;
      if (statusFilter === 'completas') return !!(p.asking_price && p.total_area_m2 && p.condition && p.rooms != null);
      return true;
    });
    out = [...out].sort((a, b) => {
      switch (sortBy) {
        case 'price_desc': return (b.asking_price || 0) - (a.asking_price || 0);
        case 'price_asc':  return (a.asking_price || 0) - (b.asking_price || 0);
        case 'area_desc':  return (b.total_area_m2 || 0) - (a.total_area_m2 || 0);
        case 'title':      return a.title.localeCompare(b.title);
        case 'recent':
        default:           return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });
    return out;
  }, [baseFiltered, statusFilter, sortBy, now]);

  const openNew = () => { setEditing(null); setForm(emptyForm); setCurrentStep(0); setWizardOpen(true); };
  const openEdit = (p: Property) => { setEditing(p); setForm({ ...emptyForm, ...p }); setCurrentStep(0); setWizardOpen(true); };

  const buildPayload = () => {
    const payload: any = { ...form };
    ['total_area_m2','covered_area_m2','rooms','bedrooms','bathrooms','age_years','asking_price','latitude','longitude','parking_spots','floor']
      .forEach(k => { if (payload[k] === '' || payload[k] == null) delete payload[k]; else payload[k] = Number(payload[k]); });
    Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k]; });
    return payload;
  };

  const save = async () => {
    setSaving(true);
    try {
      if (editing) await api.put(`/properties/${editing.id}`, buildPayload());
      else await api.post('/properties', buildPayload());
      toast.success(editing ? 'Propiedad actualizada' : 'Propiedad creada');
      setWizardOpen(false);
      load();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  const doDelete = async (p: Property) => {
    try { await api.delete(`/properties/${p.id}`); toast.success('Propiedad eliminada'); load(); }
    catch { toast.error('Error al eliminar'); }
  };

  const analyzeAI = async (p: Property) => {
    setAiBusy(p.id);
    toast.info('Claude analizando la propiedad...');
    try {
      const r = await api.post(`/properties/${p.id}/analyze`);
      const a = r.data;
      toast.success(a.summary || 'Análisis IA listo', { description: a.market_segment ? `Segmento: ${a.market_segment}` : undefined });
      load();
    } catch { toast.error('Análisis IA no disponible'); }
    finally { setAiBusy(null); }
  };

  // === FILA SUPERIOR DE FILTROS: 4 combos a la izquierda + pills estado a la derecha ===
  const filtersTopRow = (
    <div className="flex items-center justify-between gap-3 flex-wrap py-1">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="w-44"><ModernSelect value={filterProvince} onChange={(v: any) => { setFilterProvince(v); setFilterCity(''); }} options={provinceOptions} placeholder="Provincia" searchable /></div>
        <div className="w-44"><ModernSelect value={filterCity} onChange={(v: any) => setFilterCity(v)} options={cityOptions} placeholder="Ciudad" searchable /></div>
        <div className="w-44"><ModernSelect value={filterType} onChange={(v: any) => setFilterType(v)} options={TYPE_OPTIONS} placeholder="Tipo" /></div>
        <div className="w-44"><ModernSelect value={filterOp} onChange={(v: any) => setFilterOp(v)} options={OPERATION_OPTIONS} placeholder="Operación" /></div>
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">
        <StatusPill icon={List} label="Todas" count={counts.all} active={statusFilter === 'all'} onClick={() => setStatusFilter('all')} color={theme.primary} />
        <StatusPill icon={Star} label="Destacadas" count={counts.destacadas} active={statusFilter === 'destacadas'} onClick={() => setStatusFilter('destacadas')} color={theme.warning} />
        <StatusPill icon={CircleDot} label="Recientes" count={counts.recientes} active={statusFilter === 'recientes'} onClick={() => setStatusFilter('recientes')} color={theme.info} />
        <StatusPill icon={Inbox} label="Sin precio" count={counts.sin_precio} active={statusFilter === 'sin_precio'} onClick={() => setStatusFilter('sin_precio')} color={theme.danger} />
        <StatusPill icon={CheckCircle2} label="Completas" count={counts.completas} active={statusFilter === 'completas'} onClick={() => setStatusFilter('completas')} color={theme.success} />
      </div>
    </div>
  );

  // === SORT en headerActions ===
  const headerActions = (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="h-4 w-4" style={{ color: theme.textSecondary }} />
      <div className="w-44">
        <ModernSelect value={sortBy} onChange={(v: any) => setSortBy(v)} options={SORT_OPTIONS} placeholder="Ordenar..." />
      </div>
    </div>
  );

  // === CARDS === (sin grid wrapper — ABMPage ya aplica el grid canónico 1/2/3 cols)
  const cardsView = (
    <>
      {filtered.map((p, i) => (
        <ABMCard key={p.id} index={i} onClick={() => openEdit(p)}>
          <div className="flex flex-col gap-3">
            {/* Header con icono coloreado por tipo + título + subtítulo inline */}
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center"
                style={{ background: TYPE_COLORS[p.property_type]?.bg || theme.backgroundSecondary }}>
                <Building2 className="h-5 w-5"
                  style={{ color: TYPE_COLORS[p.property_type]?.text || theme.textSecondary }} />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-base leading-snug line-clamp-2" style={{ color: theme.text }}>
                  {p.title.replace(/^\[DEMO\]\s*/, '')}
                </h3>
                <div className="text-xs mt-0.5 truncate"
                  style={{ color: TYPE_COLORS[p.property_type]?.text || theme.textSecondary }}>
                  {TYPE_COLORS[p.property_type]?.label || p.property_type}
                  <span className="opacity-60"> · </span>
                  <span className="capitalize">{p.operation}</span>
                  {p.condition && (
                    <>
                      <span className="opacity-60"> · </span>
                      <span className="capitalize">{p.condition.replace(/_/g, ' ')}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs" style={{ color: theme.textSecondary }}>
              <MapPin className="h-3.5 w-3.5 flex-shrink-0" />
              <span className="truncate">{p.neighborhood || p.city}, {p.province}</span>
            </div>
            <div className="flex items-center gap-3 text-xs py-2 px-3 rounded-lg" style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
              {p.total_area_m2 && <span className="flex items-center gap-1 font-medium whitespace-nowrap"><Maximize2 className="h-3 w-3" />{p.total_area_m2}m²</span>}
              {p.rooms != null && <span className="font-medium whitespace-nowrap">{p.rooms} amb</span>}
              {p.bedrooms != null && <span className="flex items-center gap-1 font-medium whitespace-nowrap"><Bed className="h-3 w-3" />{p.bedrooms}</span>}
              {p.bathrooms != null && <span className="flex items-center gap-1 font-medium whitespace-nowrap"><Bath className="h-3 w-3" />{p.bathrooms}</span>}
            </div>
            <div className="flex items-center justify-between pt-3" style={{ borderTop: `1px solid ${theme.border}` }}>
              <div>
                <div className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: theme.textSecondary }}>Precio</div>
                <div className="font-bold text-lg leading-none mt-0.5" style={{ color: theme.text }}>
                  {p.asking_price ? `${p.currency} ${Number(p.asking_price).toLocaleString()}` : '—'}
                </div>
                {p.asking_price && p.total_area_m2 && (
                  <div className="text-[10px] mt-0.5" style={{ color: theme.textSecondary }}>
                    {Math.round(p.asking_price / p.total_area_m2)}/m²
                  </div>
                )}
              </div>
              <ABMCardActions onEdit={() => openEdit(p)} onDelete={() => setConfirm(p)}>
                <button onClick={(e) => { e.stopPropagation(); analyzeAI(p); }} disabled={aiBusy === p.id}
                  className="p-1.5 rounded-lg transition-all active:scale-95 disabled:opacity-50"
                  style={{ background: `${theme.primary}15` }} title="Analizar con IA">
                  <Sparkles className={`h-4 w-4 ${aiBusy === p.id ? 'animate-pulse' : ''}`} style={{ color: theme.primary }} />
                </button>
              </ABMCardActions>
            </div>
          </div>
        </ABMCard>
      ))}
    </>
  );

  // === TABLE ===
  const tableView = (
    <ABMTable<Property>
      data={filtered}
      keyExtractor={(p) => p.id}
      onRowClick={(p) => openEdit(p)}
      columns={[
        {
          key: 'title', header: 'Propiedad',
          render: (p) => {
            const typeColor = TYPE_COLORS[p.property_type];
            const Icon = TYPE_ICONS[p.property_type] || Building2;
            const color = typeColor?.text || theme.textSecondary;
            return (
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: `${color}22` }}>
                  <Icon className="h-4 w-4" style={{ color }} />
                </div>
                <div className="min-w-0">
                  <div className="font-semibold truncate" style={{ color: theme.text }}>
                    {p.title.replace(/^\[DEMO\]\s*/, '')}
                  </div>
                  <div className="text-xs truncate mt-0.5"
                    style={{ color: typeColor?.text || theme.textSecondary }}>
                    {typeColor?.label || p.property_type}
                    <span className="opacity-60"> · </span>
                    <span className="capitalize">{p.operation}</span>
                  </div>
                </div>
              </div>
            );
          },
          sortValue: (p) => p.title,
        },
        {
          key: 'location', header: 'Ubicación',
          render: (p) => (
            <div className="text-sm">
              <div style={{ color: theme.text }}>{p.neighborhood || p.city}</div>
              <div className="text-xs" style={{ color: theme.textSecondary }}>{p.province}</div>
            </div>
          ),
          sortValue: (p) => p.city,
        },
        {
          key: 'area', header: 'Superficie',
          render: (p) => p.total_area_m2 ? <span className="font-medium" style={{ color: theme.text }}>{p.total_area_m2} m²</span> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (p) => p.total_area_m2 || 0,
        },
        {
          key: 'rooms', header: 'Amb',
          render: (p) => p.rooms != null ? <span style={{ color: theme.text }}>{p.rooms}</span> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (p) => p.rooms || 0,
        },
        {
          key: 'condition', header: 'Estado',
          render: (p) => p.condition ? <CondPill cond={p.condition} /> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (p) => p.condition || '',
        },
        {
          key: 'price', header: 'Precio',
          render: (p) => p.asking_price ? (
            <div>
              <div className="font-bold" style={{ color: theme.text }}>{p.currency} {Number(p.asking_price).toLocaleString()}</div>
              {p.total_area_m2 && <div className="text-[10px]" style={{ color: theme.textSecondary }}>{Math.round(p.asking_price / p.total_area_m2)}/m²</div>}
            </div>
          ) : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (p) => p.asking_price || 0,
        },
      ]}
      actions={(p) => (
        <ABMTableAction icon={<Sparkles className="h-4 w-4" />} title="Analizar con IA" onClick={() => analyzeAI(p)} variant="primary" />
      )}
      defaultSortKey="title"
    />
  );

  // === WIZARD STEPS (sin cambios visuales) ===
  const stepLocation = (
    <div className="space-y-4 animate-fade-in">
      <Field label="Título de la propiedad" value={form.title} onChange={(v: any) => setForm({...form, title: v})} placeholder="Ej: Departamento 3 amb. Palermo" />
      <div className="grid grid-cols-2 gap-3">
        <ModernSelect label="Tipo" value={form.property_type} onChange={(v: any) => setForm({...form, property_type: v})} options={TYPE_OPTIONS.filter(t => t.value)} />
        <ModernSelect label="Operación" value={form.operation} onChange={(v: any) => setForm({...form, operation: v})} options={OPERATION_OPTIONS.filter(o => o.value)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Provincia" value={form.province} onChange={(v: any) => setForm({...form, province: v})} placeholder="Buenos Aires" />
        <Field label="Ciudad" value={form.city} onChange={(v: any) => setForm({...form, city: v})} placeholder="CABA" />
      </div>
      <Field label="Barrio" value={form.neighborhood} onChange={(v: any) => setForm({...form, neighborhood: v})} placeholder="Palermo" />
      <Field label="Dirección" value={form.address} onChange={(v: any) => setForm({...form, address: v})} placeholder="Av. Santa Fe 3000" />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Latitud" type="number" value={form.latitude} onChange={(v: any) => setForm({...form, latitude: v})} placeholder="-34.5800" />
        <Field label="Longitud" type="number" value={form.longitude} onChange={(v: any) => setForm({...form, longitude: v})} placeholder="-58.4300" />
      </div>
    </div>
  );
  const stepCharacteristics = (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-3 gap-3">
        <Field label="m² totales" type="number" value={form.total_area_m2} onChange={(v: any) => setForm({...form, total_area_m2: v})} />
        <Field label="m² cubiertos" type="number" value={form.covered_area_m2} onChange={(v: any) => setForm({...form, covered_area_m2: v})} />
        <Field label="Antigüedad" type="number" value={form.age_years} onChange={(v: any) => setForm({...form, age_years: v})} />
      </div>
      <div className="grid grid-cols-3 gap-3">
        <Field label="Ambientes" type="number" value={form.rooms} onChange={(v: any) => setForm({...form, rooms: v})} />
        <Field label="Dormitorios" type="number" value={form.bedrooms} onChange={(v: any) => setForm({...form, bedrooms: v})} />
        <Field label="Baños" type="number" value={form.bathrooms} onChange={(v: any) => setForm({...form, bathrooms: v})} />
      </div>
      <ModernSelect label="Estado" value={form.condition || ''} onChange={(v: any) => setForm({...form, condition: v})}
        options={[{ value: '', label: '—' }, ...CONDITION_OPTIONS]} />
    </div>
  );
  const stepEconomic = (
    <div className="space-y-4 animate-fade-in">
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2"><Field label="Precio" type="number" value={form.asking_price} onChange={(v: any) => setForm({...form, asking_price: v})} placeholder="220000" /></div>
        <ModernSelect label="Moneda" value={form.currency} onChange={(v: any) => setForm({...form, currency: v})} options={[{ value: 'USD', label: 'USD' }, { value: 'ARS', label: 'ARS' }]} />
      </div>
      <Textarea label="Descripción" value={form.description} onChange={(v: any) => setForm({...form, description: v})} />
    </div>
  );
  const stepReview = (
    <div className="space-y-3 animate-fade-in">
      <div className="p-4 rounded-xl" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.primary}30` }}>
        <div className="font-semibold text-lg mb-3" style={{ color: theme.text }}>{form.title || '(sin título)'}</div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <Info k="Tipo" v={form.property_type} />
          <Info k="Operación" v={form.operation} />
          <Info k="m² totales" v={form.total_area_m2 || '—'} />
          <Info k="Ambientes" v={form.rooms || '—'} />
          <Info k="Estado" v={form.condition || '—'} />
          <Info k="Precio" v={form.asking_price ? `${form.currency} ${Number(form.asking_price).toLocaleString()}` : '—'} />
        </div>
      </div>
    </div>
  );

  const steps: WizardStep[] = [
    { id: 'location', title: 'Ubicación', description: 'Dónde está', icon: <MapPin className="h-4 w-4" />, content: stepLocation, isValid: !!(form.title && form.province && form.city && form.address) },
    { id: 'features', title: 'Características', description: 'Metros y ambientes', icon: <HomeIcon className="h-4 w-4" />, content: stepCharacteristics, isValid: true },
    { id: 'price', title: 'Precio', description: 'Valor + descripción', icon: <DollarSign className="h-4 w-4" />, content: stepEconomic, isValid: true },
    { id: 'review', title: 'Revisar', description: 'Confirmar y guardar', icon: <FileText className="h-4 w-4" />, content: stepReview, isValid: true },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <PageHint pageId="propiedades" />
      <ABMPage
        title="Propiedades"
        icon={<Building2 className="h-5 w-5" />}
        backLink="/"
        buttonLabel="Nueva propiedad"
        buttonIcon={<Plus className="h-4 w-4" />}
        onAdd={openNew}
        searchPlaceholder="Buscar por título, dirección o ciudad..."
        searchValue={search}
        onSearchChange={setSearch}
        secondaryFilters={filtersTopRow}
        headerActions={headerActions}
        tableView={tableView}
        viewStorageKey="propiedades_view"
        loading={loading}
        isEmpty={!loading && filtered.length === 0}
        emptyMessage={items.length === 0 ? 'No hay propiedades cargadas todavía' : 'Sin resultados con esos filtros'}
      >
        {cardsView}
      </ABMPage>

      <WizardModal
        open={wizardOpen} onClose={() => setWizardOpen(false)}
        title={editing ? `Editar: ${editing.title.replace(/^\[DEMO\]\s*/, '')}` : 'Nueva propiedad'}
        steps={steps} currentStep={currentStep} onStepChange={setCurrentStep}
        onComplete={save} loading={saving}
        completeLabel={editing ? 'Actualizar' : 'Crear propiedad'}
        headerBadge={{ icon: <Building2 className="h-4 w-4" />, label: editing ? 'Edición' : 'Nuevo', color: theme.primary }}
      />

      <ConfirmModal isOpen={!!confirm} onClose={() => setConfirm(null)} variant="danger"
        onConfirm={() => { if (confirm) doDelete(confirm); setConfirm(null); }}
        title="¿Eliminar propiedad?"
        message={`Vas a eliminar "${confirm?.title.replace(/^\[DEMO\]\s*/, '') ?? ''}". Esta acción no se puede deshacer.`}
        confirmText="Eliminar" />
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder }: any) {
  const { theme } = useTheme();
  return (
    <div>
      <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>{label}</label>
      <input type={type} value={value ?? ''} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all"
        style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
    </div>
  );
}
function Textarea({ label, value, onChange }: any) {
  const { theme } = useTheme();
  return (
    <div>
      <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>{label}</label>
      <textarea rows={4} value={value ?? ''} onChange={e => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all resize-none"
        style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
    </div>
  );
}
function Info({ k, v }: { k: string; v: any }) {
  const { theme } = useTheme();
  return (
    <div>
      <div className="text-xs uppercase tracking-wide" style={{ color: theme.textSecondary }}>{k}</div>
      <div className="font-medium capitalize" style={{ color: theme.text }}>{v || '—'}</div>
    </div>
  );
}
