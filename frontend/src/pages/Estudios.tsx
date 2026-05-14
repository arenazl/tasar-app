import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, ClipboardList, Calculator, TrendingUp, List, FileEdit, Eye, CheckCircle2,
  Archive, ShieldCheck, AlertTriangle, ArrowUpDown, BarChart3, Brain, Layers,
  Building2, Home as HomeIcon, Castle, Trees, Store, Briefcase,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { ABMPage, ABMCard, ABMTable, ABMTableAction } from '../components/ui/ABMPage';
import { ModernSelect } from '../components/ui/ModernSelect';
import { WizardModal, type WizardStep } from '../components/ui/WizardModal';
import PageHint from '../components/ui/PageHint';
import { useTheme } from '../contexts/ThemeContext';
import type { MarketStudy, Property } from '../types';

const METHOD_OPTIONS = [
  { value: '', label: 'Todos los métodos' },
  { value: 'homogenization', label: 'Homogeneización' },
  { value: 'ai_score', label: 'AI Score' },
  { value: 'hybrid', label: 'Híbrido' },
];

const METHOD_WIZARD_OPTIONS = [
  { value: 'homogenization', label: 'Homogeneización clásica', description: 'Coeficientes por área, estado, antigüedad' },
  { value: 'ai_score', label: 'AI Score (Claude)', description: 'Claude analiza y pondera comparables' },
  { value: 'hybrid', label: 'Híbrido', description: 'Combina ambos métodos' },
];

const SORT_OPTIONS = [
  { value: 'recent', label: 'Más recientes' },
  { value: 'value_desc', label: 'Mayor valor' },
  { value: 'confidence_desc', label: 'Mayor confianza' },
  { value: 'comps_desc', label: 'Más comparables' },
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
        style={{
          background: active ? 'rgba(255,255,255,0.25)' : theme.backgroundSecondary,
          color: active ? '#fff' : theme.text,
        }}>{count}</span>
    </button>
  );
}

function MethodPill({ method }: { method: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    homogenization: { bg: '#dbeafe', text: '#1e40af', label: 'Homog.' },
    ai_score: { bg: '#ede9fe', text: '#5b21b6', label: 'AI Score' },
    hybrid: { bg: '#fce7f3', text: '#9f1239', label: 'Híbrido' },
  };
  const c = map[method] || { bg: '#e2e8f0', text: '#475569', label: method };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    draft: { bg: '#fef3c7', text: '#92400e', label: 'Borrador' },
    in_review: { bg: '#dbeafe', text: '#1e40af', label: 'En revisión' },
    published: { bg: '#d1fae5', text: '#065f46', label: 'Publicado' },
    archived: { bg: '#e5e5e5', text: '#52525b', label: 'Archivado' },
  };
  const c = map[status] || { bg: '#e2e8f0', text: '#475569', label: status };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}

function ConfidencePill({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? '#16a34a' : pct >= 40 ? '#f59e0b' : '#dc2626';
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium"
      style={{ background: `${color}15`, color }}>
      <TrendingUp className="h-2.5 w-2.5" /> {pct}%
    </span>
  );
}

export default function Estudios() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [items, setItems] = useState<MarketStudy[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterMethod, setFilterMethod] = useState('');
  const [filterProperty, setFilterProperty] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all'|'draft'|'in_review'|'published'|'high_conf'|'low_conf'>('all');
  const [sortBy, setSortBy] = useState('recent');

  const [wizardOpen, setWizardOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [propertyId, setPropertyId] = useState<string>('');
  const [method, setMethod] = useState('homogenization');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [s, p] = await Promise.all([
        api.get<MarketStudy[]>('/market-studies'),
        api.get<Property[]>('/properties'),
      ]);
      setItems(s.data); setProperties(p.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const propertyOptions = useMemo(() => [
    { value: '', label: 'Todas las propiedades' },
    ...properties.map(p => ({ value: String(p.id), label: p.title.replace(/^\[DEMO\]\s*/, ''), description: `${p.city}` })),
  ], [properties]);

  const propertyWizardOptions = useMemo(() =>
    properties.map(p => ({
      value: String(p.id),
      label: p.title.replace(/^\[DEMO\]\s*/, ''),
      description: `${p.city} · ${p.total_area_m2 || '?'}m²`,
    })),
  [properties]);

  const baseFiltered = useMemo(() => items.filter(s => {
    if (filterMethod && s.method !== filterMethod) return false;
    if (filterProperty && String(s.property_id) !== filterProperty) return false;
    if (search) {
      const prop = properties.find(p => p.id === s.property_id);
      const q = search.toLowerCase();
      return prop?.title.toLowerCase().includes(q) || s.method.toLowerCase().includes(q);
    }
    return true;
  }), [items, filterMethod, filterProperty, search, properties]);

  const counts = useMemo(() => ({
    all: baseFiltered.length,
    draft: baseFiltered.filter(s => s.status === 'draft').length,
    in_review: baseFiltered.filter(s => s.status === 'in_review').length,
    published: baseFiltered.filter(s => s.status === 'published').length,
    high_conf: baseFiltered.filter(s => (s.confidence_score || 0) >= 0.7).length,
    low_conf: baseFiltered.filter(s => s.suggested_value_mode != null && (s.confidence_score || 0) < 0.4).length,
  }), [baseFiltered]);

  const filtered = useMemo(() => {
    let out = baseFiltered.filter(s => {
      if (statusFilter === 'all') return true;
      if (statusFilter === 'draft') return s.status === 'draft';
      if (statusFilter === 'in_review') return s.status === 'in_review';
      if (statusFilter === 'published') return s.status === 'published';
      if (statusFilter === 'high_conf') return (s.confidence_score || 0) >= 0.7;
      if (statusFilter === 'low_conf') return s.suggested_value_mode != null && (s.confidence_score || 0) < 0.4;
      return true;
    });
    out = [...out].sort((a, b) => {
      switch (sortBy) {
        case 'value_desc': return (b.suggested_value_mode || 0) - (a.suggested_value_mode || 0);
        case 'confidence_desc': return (b.confidence_score || 0) - (a.confidence_score || 0);
        case 'comps_desc': return b.comparables.length - a.comparables.length;
        case 'recent':
        default: return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });
    return out;
  }, [baseFiltered, statusFilter, sortBy]);

  const openWizard = () => { setPropertyId(''); setMethod('homogenization'); setNotes(''); setStep(0); setWizardOpen(true); };

  const create = async () => {
    if (!propertyId) return toast.error('Seleccioná una propiedad');
    setSaving(true);
    try {
      const r = await api.post('/market-studies', { property_id: Number(propertyId), method, notes });
      toast.success('Estudio creado');
      setWizardOpen(false);
      navigate(`/estudios/${r.data.id}`);
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSaving(false); }
  };

  const filtersTopRow = (
    <div className="flex items-center justify-between gap-3 flex-wrap py-1">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="w-56"><ModernSelect value={filterProperty} onChange={(v: any) => setFilterProperty(v)} options={propertyOptions} placeholder="Propiedad" searchable /></div>
        <div className="w-44"><ModernSelect value={filterMethod} onChange={(v: any) => setFilterMethod(v)} options={METHOD_OPTIONS} placeholder="Método" /></div>
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">
        <StatusPill icon={List} label="Todos" count={counts.all} active={statusFilter === 'all'} onClick={() => setStatusFilter('all')} color={theme.primary} />
        <StatusPill icon={FileEdit} label="Borrador" count={counts.draft} active={statusFilter === 'draft'} onClick={() => setStatusFilter('draft')} color={theme.warning} />
        <StatusPill icon={Eye} label="En revisión" count={counts.in_review} active={statusFilter === 'in_review'} onClick={() => setStatusFilter('in_review')} color={theme.info} />
        <StatusPill icon={CheckCircle2} label="Publicados" count={counts.published} active={statusFilter === 'published'} onClick={() => setStatusFilter('published')} color={theme.success} />
        <StatusPill icon={ShieldCheck} label="Alta conf." count={counts.high_conf} active={statusFilter === 'high_conf'} onClick={() => setStatusFilter('high_conf')} color="#16a34a" />
        <StatusPill icon={AlertTriangle} label="Baja conf." count={counts.low_conf} active={statusFilter === 'low_conf'} onClick={() => setStatusFilter('low_conf')} color={theme.danger} />
      </div>
    </div>
  );

  const headerActions = (
    <div className="flex items-center gap-2">
      <ArrowUpDown className="h-4 w-4" style={{ color: theme.textSecondary }} />
      <div className="w-44"><ModernSelect value={sortBy} onChange={(v: any) => setSortBy(v)} options={SORT_OPTIONS} placeholder="Ordenar..." /></div>
    </div>
  );

  const cardsView = (
    <>
      {filtered.map((s, i) => {
        const prop = properties.find(p => p.id === s.property_id);
        return (
          <ABMCard key={s.id} index={i} onClick={() => navigate(`/estudios/${s.id}`)}>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs font-mono" style={{ color: theme.textSecondary }}>#{s.id}</span>
                  <span className="font-semibold truncate" style={{ color: theme.text }}>
                    {prop?.title.replace(/^\[DEMO\]\s*/, '') || `Propiedad #${s.property_id}`}
                  </span>
                  <StatusBadge status={s.status} />
                  <MethodPill method={s.method} />
                </div>
                <div className="text-sm flex items-center gap-3 flex-wrap" style={{ color: theme.textSecondary }}>
                  <span>{s.comparables.length} comparables</span>
                  {s.confidence_score != null && <ConfidencePill score={s.confidence_score} />}
                  <span>· {new Date(s.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                {s.suggested_value_mode ? (
                  <>
                    <div className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: theme.textSecondary }}>Valor sugerido</div>
                    <div className="text-xl font-bold" style={{ color: theme.text }}>USD {Number(s.suggested_value_mode).toLocaleString()}</div>
                    {s.suggested_value_min && s.suggested_value_max && (
                      <div className="text-xs" style={{ color: theme.textSecondary }}>
                        {Math.round(s.suggested_value_min/1000)}k – {Math.round(s.suggested_value_max/1000)}k
                      </div>
                    )}
                  </>
                ) : (
                  <div className="text-sm flex items-center gap-1" style={{ color: theme.textSecondary }}>
                    <Calculator className="h-4 w-4" /> Sin calcular
                  </div>
                )}
              </div>
            </div>
          </ABMCard>
        );
      })}
    </>
  );

  const tableView = (
    <ABMTable<MarketStudy>
      data={filtered}
      keyExtractor={(s) => s.id}
      onRowClick={(s) => navigate(`/estudios/${s.id}`)}
      columns={[
        { key: 'id', header: '#', render: (s) => <span className="font-mono text-xs" style={{ color: theme.textSecondary }}>#{s.id}</span>, sortValue: (s) => s.id },
        {
          key: 'property', header: 'Propiedad',
          render: (s) => {
            const prop = properties.find(p => p.id === s.property_id);
            const typeMap: Record<string, { color: string; Icon: any }> = {
              casa: { color: '#92400e', Icon: HomeIcon },
              departamento: { color: '#1e40af', Icon: Building2 },
              ph: { color: '#9f1239', Icon: Castle },
              terreno: { color: '#166534', Icon: Trees },
              local: { color: '#5b21b6', Icon: Store },
              oficina: { color: '#075985', Icon: Briefcase },
            };
            const t = typeMap[prop?.property_type || ''] || { color: theme.textSecondary, Icon: Building2 };
            return (
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: `${t.color}22` }}>
                  <t.Icon className="h-4 w-4" style={{ color: t.color }} />
                </div>
                <span className="truncate" style={{ color: theme.text }}>
                  {prop?.title.replace(/^\[DEMO\]\s*/, '') || `#${s.property_id}`}
                </span>
              </div>
            );
          },
          sortValue: (s) => properties.find(p => p.id === s.property_id)?.title || '',
        },
        { key: 'status', header: 'Estado', render: (s) => <StatusBadge status={s.status} />, sortValue: (s) => s.status },
        { key: 'method', header: 'Método', render: (s) => <MethodPill method={s.method} />, sortValue: (s) => s.method },
        { key: 'comps', header: 'Comp.', render: (s) => <span style={{ color: theme.text }}>{s.comparables.length}</span>, sortValue: (s) => s.comparables.length },
        {
          key: 'value', header: 'Valor sug.',
          render: (s) => s.suggested_value_mode
            ? <span className="font-bold" style={{ color: theme.text }}>USD {Number(s.suggested_value_mode).toLocaleString()}</span>
            : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (s) => s.suggested_value_mode || 0,
        },
        {
          key: 'confidence', header: 'Confianza',
          render: (s) => s.confidence_score != null ? <ConfidencePill score={s.confidence_score} /> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (s) => s.confidence_score || 0,
        },
        {
          key: 'date', header: 'Fecha',
          render: (s) => <span className="text-xs" style={{ color: theme.textSecondary }}>{new Date(s.created_at).toLocaleDateString()}</span>,
          sortValue: (s) => new Date(s.created_at).getTime(),
        },
      ]}
      actions={(s) => (
        <ABMTableAction icon={<Eye className="h-4 w-4" />} title="Ver detalle" onClick={() => navigate(`/estudios/${s.id}`)} variant="primary" />
      )}
      defaultSortKey="date"
      defaultSortDirection="desc"
    />
  );

  const selectedProp = properties.find(p => p.id === Number(propertyId));
  const stepProperty = (
    <div className="space-y-4 animate-fade-in">
      <ModernSelect label="Propiedad objetivo" value={propertyId} onChange={(v: any) => setPropertyId(v)}
        options={propertyWizardOptions} placeholder="Buscar propiedad..." searchable />
      {selectedProp && (
        <div className="p-4 rounded-xl" style={{ background: `${theme.primary}10`, border: `1px solid ${theme.primary}30` }}>
          <div className="font-semibold" style={{ color: theme.text }}>{selectedProp.title.replace(/^\[DEMO\]\s*/, '')}</div>
          <div className="text-sm mt-1" style={{ color: theme.textSecondary }}>{selectedProp.neighborhood || selectedProp.city}, {selectedProp.province}</div>
          <div className="flex gap-4 text-xs mt-2" style={{ color: theme.textSecondary }}>
            <span>{selectedProp.total_area_m2 || '?'}m²</span>
            <span>{selectedProp.rooms || '?'} amb.</span>
            <span>{selectedProp.age_years != null ? `${selectedProp.age_years}a` : '?'}</span>
          </div>
        </div>
      )}
    </div>
  );
  const stepMethod = (
    <div className="space-y-4 animate-fade-in">
      <ModernSelect label="Método de valuación" value={method} onChange={(v: any) => setMethod(v)} options={METHOD_WIZARD_OPTIONS} />
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>Notas (opcional)</label>
        <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)}
          placeholder="Contexto del estudio, finalidad, observaciones..."
          className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all resize-none"
          style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
      </div>
    </div>
  );
  const steps: WizardStep[] = [
    { id: 'property', title: 'Propiedad', description: 'Qué inmueble estudiar', icon: <ClipboardList className="h-4 w-4" />, content: stepProperty, isValid: !!propertyId },
    { id: 'method', title: 'Método', description: 'Cómo se calcula', icon: <Calculator className="h-4 w-4" />, content: stepMethod, isValid: true },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <PageHint pageId="estudios" />
      <ABMPage
        title="Estudios de Mercado"
        icon={<ClipboardList className="h-5 w-5" />}
        backLink="/"
        buttonLabel="Nuevo estudio"
        buttonIcon={<Plus className="h-4 w-4" />}
        onAdd={openWizard}
        searchPlaceholder="Buscar estudios..."
        searchValue={search}
        onSearchChange={setSearch}
        secondaryFilters={filtersTopRow}
        headerActions={headerActions}
        tableView={tableView}
        viewStorageKey="estudios_view"
        loading={loading}
        isEmpty={!loading && filtered.length === 0}
        emptyMessage={items.length === 0 ? 'No hay estudios todavía. Creá el primero.' : 'Sin resultados'}
      >
        {cardsView}
      </ABMPage>

      <WizardModal
        open={wizardOpen} onClose={() => setWizardOpen(false)}
        title="Nuevo estudio de mercado"
        steps={steps} currentStep={step} onStepChange={setStep}
        onComplete={create} loading={saving}
        completeLabel="Crear estudio"
        headerBadge={{ icon: <ClipboardList className="h-4 w-4" />, label: 'ACM', color: theme.primary }}
      />
    </div>
  );
}
