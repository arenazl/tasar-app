import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Plus, FileCheck2, Download, FileSignature, Briefcase, ClipboardList,
  DollarSign, Sparkles, List, FileEdit, ShieldCheck, Send, AlertCircle,
  Link2, ArrowUpDown, Tag, Scroll, Gavel, Landmark, Umbrella, FileText,
  Building2, Home as HomeIcon, Castle, Trees, Store,
} from 'lucide-react';
import { toast } from 'sonner';
import { api, API_BASE } from '../services/api';
import { ABMPage, ABMCard, ABMTable, ABMTableAction, ABMInfoPanel } from '../components/ui/ABMPage';
import { ModernSelect } from '../components/ui/ModernSelect';
import { WizardModal, type WizardStep } from '../components/ui/WizardModal';
import PageHint from '../components/ui/PageHint';
import { useTheme } from '../contexts/ThemeContext';
import type { Appraisal, Property, MarketStudy } from '../types';

const PURPOSE_OPTIONS = [
  { value: '', label: 'Todas las finalidades' },
  { value: 'venta', label: 'Venta' },
  { value: 'sucesion', label: 'Sucesión' },
  { value: 'judicial', label: 'Judicial' },
  { value: 'hipoteca', label: 'Hipoteca' },
  { value: 'seguro', label: 'Seguro' },
  { value: 'otro', label: 'Otro' },
];
const PURPOSE_WIZARD_OPTIONS = PURPOSE_OPTIONS.filter(p => p.value).map(p => ({
  ...p,
  description: ({
    venta: 'Comercialización del inmueble',
    sucesion: 'Trámite sucesorio',
    judicial: 'Pericia / proceso judicial',
    hipoteca: 'Garantía hipotecaria',
    seguro: 'Cobertura aseguradora',
    otro: 'Otra finalidad',
  } as any)[p.value],
}));
const SORT_OPTIONS = [
  { value: 'recent', label: 'Más recientes' },
  { value: 'value_desc', label: 'Mayor valor' },
  { value: 'value_asc', label: 'Menor valor' },
  { value: 'purpose', label: 'Finalidad A-Z' },
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
        style={{ background: active ? 'rgba(255,255,255,0.25)' : theme.backgroundSecondary, color: active ? '#fff' : theme.text }}>{count}</span>
    </button>
  );
}

function PurposePill({ purpose }: { purpose: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    venta: { bg: '#fee2e2', text: '#991b1b', label: 'Venta' },
    sucesion: { bg: '#fef3c7', text: '#92400e', label: 'Sucesión' },
    judicial: { bg: '#ede9fe', text: '#5b21b6', label: 'Judicial' },
    hipoteca: { bg: '#dbeafe', text: '#1e40af', label: 'Hipoteca' },
    seguro: { bg: '#cffafe', text: '#155e75', label: 'Seguro' },
    otro: { bg: '#e2e8f0', text: '#475569', label: 'Otro' },
  };
  const c = map[purpose] || { bg: '#e2e8f0', text: '#475569', label: purpose };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    draft: { bg: '#fef3c7', text: '#92400e', label: 'Borrador' },
    signed: { bg: '#d1fae5', text: '#065f46', label: 'Firmada' },
    delivered: { bg: '#dbeafe', text: '#1e40af', label: 'Entregada' },
  };
  const c = map[status] || { bg: '#e2e8f0', text: '#475569', label: status };
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
      style={{ background: c.bg, color: c.text }}>{c.label}</span>
  );
}

export default function Tasaciones() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [items, setItems] = useState<Appraisal[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [studies, setStudies] = useState<MarketStudy[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterPurpose, setFilterPurpose] = useState('');
  const [filterProperty, setFilterProperty] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all'|'draft'|'signed'|'delivered'|'with_acm'|'old'>('all');
  const [sortBy, setSortBy] = useState('recent');
  const [wizardOpen, setWizardOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<any>({
    property_id: '', market_study_id: '', purpose: 'venta',
    final_value: '', currency: 'USD', methodology: '', observations: '', legal_remarks: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      const [a, p, s] = await Promise.all([
        api.get<Appraisal[]>('/appraisals'),
        api.get<Property[]>('/properties'),
        api.get<MarketStudy[]>('/market-studies'),
      ]);
      setItems(a.data); setProperties(p.data); setStudies(s.data);
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const propertyOptions = useMemo(() => [
    { value: '', label: 'Todas las propiedades' },
    ...properties.map(p => ({ value: String(p.id), label: p.title.replace(/^\[DEMO\]\s*/, ''), description: p.city })),
  ], [properties]);

  const propertyWizardOptions = useMemo(() =>
    properties.map(p => ({ value: String(p.id), label: p.title.replace(/^\[DEMO\]\s*/, ''), description: `${p.city} · USD ${p.asking_price?.toLocaleString() || '?'}` })),
  [properties]);

  const baseFiltered = useMemo(() => items.filter(a => {
    if (filterPurpose && a.purpose !== filterPurpose) return false;
    if (filterProperty && String(a.property_id) !== filterProperty) return false;
    if (search) {
      const prop = properties.find(p => p.id === a.property_id);
      const q = search.toLowerCase();
      return prop?.title.toLowerCase().includes(q) || a.purpose.toLowerCase().includes(q);
    }
    return true;
  }), [items, filterPurpose, filterProperty, search, properties]);

  const THIRTY_DAYS = 30 * 24 * 3600 * 1000;
  const now = Date.now();
  const counts = useMemo(() => ({
    all: baseFiltered.length,
    draft: baseFiltered.filter(a => a.status === 'draft').length,
    signed: baseFiltered.filter(a => a.status === 'signed').length,
    delivered: baseFiltered.filter(a => a.status === 'delivered').length,
    with_acm: baseFiltered.filter(a => a.market_study_id != null).length,
    old: baseFiltered.filter(a => a.status === 'draft' && (now - new Date(a.created_at).getTime() > THIRTY_DAYS)).length,
  }), [baseFiltered, now]);

  const filtered = useMemo(() => {
    let out = baseFiltered.filter(a => {
      if (statusFilter === 'all') return true;
      if (statusFilter === 'draft') return a.status === 'draft';
      if (statusFilter === 'signed') return a.status === 'signed';
      if (statusFilter === 'delivered') return a.status === 'delivered';
      if (statusFilter === 'with_acm') return a.market_study_id != null;
      if (statusFilter === 'old') return a.status === 'draft' && (now - new Date(a.created_at).getTime() > THIRTY_DAYS);
      return true;
    });
    out = [...out].sort((a, b) => {
      switch (sortBy) {
        case 'value_desc': return b.final_value - a.final_value;
        case 'value_asc': return a.final_value - b.final_value;
        case 'purpose': return a.purpose.localeCompare(b.purpose);
        case 'recent':
        default: return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      }
    });
    return out;
  }, [baseFiltered, statusFilter, sortBy, now]);

  const openNew = () => {
    setForm({ property_id: '', market_study_id: '', purpose: 'venta', final_value: '', currency: 'USD', methodology: '', observations: '', legal_remarks: '' });
    setStep(0); setWizardOpen(true);
  };

  const create = async () => {
    const payload: any = { ...form };
    payload.property_id = Number(payload.property_id);
    if (payload.market_study_id) payload.market_study_id = Number(payload.market_study_id);
    else delete payload.market_study_id;
    payload.final_value = Number(payload.final_value);
    if (!payload.property_id || !payload.final_value) return toast.error('Faltan propiedad o valor');
    setSaving(true);
    try {
      await api.post('/appraisals', payload);
      toast.success('Tasación creada');
      setWizardOpen(false); load();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSaving(false); }
  };

  const sign = async (a: Appraisal) => {
    try { await api.post(`/appraisals/${a.id}/sign`); toast.success('Tasación firmada'); load(); }
    catch { toast.error('Error al firmar'); }
  };

  const downloadPdf = (a: Appraisal) => {
    const token = localStorage.getItem('tasar_token');
    fetch(`${API_BASE}/appraisals/${a.id}/pdf`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.blob())
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url; link.download = `tasacion-${a.id}.pdf`; link.click();
        URL.revokeObjectURL(url);
      });
  };

  const filtersTopRow = (
    <div className="flex items-center justify-between gap-3 flex-wrap py-1">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="w-56"><ModernSelect value={filterProperty} onChange={(v: any) => setFilterProperty(v)} options={propertyOptions} placeholder="Propiedad" searchable /></div>
        <div className="w-48"><ModernSelect value={filterPurpose} onChange={(v: any) => setFilterPurpose(v)} options={PURPOSE_OPTIONS} placeholder="Finalidad" /></div>
      </div>
      <div className="flex items-center gap-1.5 flex-wrap">
        <StatusPill icon={List} label="Todas" count={counts.all} active={statusFilter === 'all'} onClick={() => setStatusFilter('all')} color={theme.primary} />
        <StatusPill icon={FileEdit} label="Borrador" count={counts.draft} active={statusFilter === 'draft'} onClick={() => setStatusFilter('draft')} color={theme.warning} />
        <StatusPill icon={ShieldCheck} label="Firmadas" count={counts.signed} active={statusFilter === 'signed'} onClick={() => setStatusFilter('signed')} color={theme.success} />
        <StatusPill icon={Send} label="Entregadas" count={counts.delivered} active={statusFilter === 'delivered'} onClick={() => setStatusFilter('delivered')} color={theme.info} />
        <StatusPill icon={Link2} label="Con ACM" count={counts.with_acm} active={statusFilter === 'with_acm'} onClick={() => setStatusFilter('with_acm')} color="#7c3aed" />
        <StatusPill icon={AlertCircle} label="Por vencer" count={counts.old} active={statusFilter === 'old'} onClick={() => setStatusFilter('old')} color={theme.danger} />
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
      {filtered.map((a, i) => {
        const prop = properties.find(p => p.id === a.property_id);
        const signed = a.status === 'signed' || a.status === 'delivered';
        return (
          <ABMCard key={a.id} index={i} onClick={() => navigate(`/tasaciones/${a.id}`)}>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-xs font-mono" style={{ color: theme.textSecondary }}>#{a.id}</span>
                  <span className="font-semibold truncate" style={{ color: theme.text }}>{prop?.title.replace(/^\[DEMO\]\s*/, '') || `Tasación #${a.id}`}</span>
                  <StatusBadge status={a.status} />
                  <PurposePill purpose={a.purpose} />
                  {a.market_study_id && <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md font-medium" style={{ background: `${theme.info}15`, color: theme.info }}><Link2 className="h-2.5 w-2.5" /> ACM #{a.market_study_id}</span>}
                </div>
                <div className="text-sm flex items-center gap-3 flex-wrap" style={{ color: theme.textSecondary }}>
                  <span>{new Date(a.created_at).toLocaleDateString()}</span>
                  {a.signatures.length > 0 && <span>· {a.signatures.length} firma{a.signatures.length > 1 ? 's' : ''}</span>}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-[10px] uppercase tracking-wide font-semibold" style={{ color: theme.textSecondary }}>Valor final</div>
                  <div className="text-xl font-bold" style={{ color: theme.text }}>{a.currency} {Number(a.final_value).toLocaleString()}</div>
                </div>
                {!signed && (
                  <button onClick={(e) => { e.stopPropagation(); sign(a); }}
                    className="px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1 transition-all active:scale-95"
                    style={{ background: `${theme.success}20`, color: theme.success }}>
                    <FileSignature className="h-4 w-4" /> Firmar
                  </button>
                )}
                <button onClick={(e) => { e.stopPropagation(); downloadPdf(a); }}
                  className="p-2 rounded-lg transition-all active:scale-95"
                  style={{ background: `${theme.primary}15`, color: theme.primary }} title="Descargar PDF">
                  <Download className="h-4 w-4" />
                </button>
              </div>
            </div>
          </ABMCard>
        );
      })}
    </>
  );

  const tableView = (
    <ABMTable<Appraisal>
      data={filtered}
      keyExtractor={(a) => a.id}
      columns={[
        { key: 'id', header: '#', render: (a) => <span className="font-mono text-xs" style={{ color: theme.textSecondary }}>#{a.id}</span>, sortValue: (a) => a.id },
        {
          key: 'property', header: 'Propiedad',
          render: (a) => {
            const prop = properties.find(p => p.id === a.property_id);
            const typeMap: Record<string, { color: string; Icon: any }> = {
              casa: { color: '#92400e', Icon: HomeIcon },
              departamento: { color: '#1e40af', Icon: Building2 },
              ph: { color: '#9f1239', Icon: Castle },
              terreno: { color: '#166534', Icon: Trees },
              local: { color: '#5b21b6', Icon: Store },
              oficina: { color: '#075985', Icon: Briefcase },
            };
            const t = typeMap[prop?.property_type || ''] || { color: theme.textSecondary, Icon: FileText };
            return (
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0 w-9 h-9 rounded-lg flex items-center justify-center"
                  style={{ background: `${t.color}22` }}>
                  <t.Icon className="h-4 w-4" style={{ color: t.color }} />
                </div>
                <span className="truncate" style={{ color: theme.text }}>
                  {prop?.title.replace(/^\[DEMO\]\s*/, '') || `#${a.property_id}`}
                </span>
              </div>
            );
          },
          sortValue: (a) => properties.find(p => p.id === a.property_id)?.title || '',
        },
        { key: 'status', header: 'Estado', render: (a) => <StatusBadge status={a.status} />, sortValue: (a) => a.status },
        { key: 'purpose', header: 'Finalidad', render: (a) => <PurposePill purpose={a.purpose} />, sortValue: (a) => a.purpose },
        {
          key: 'acm', header: 'ACM',
          render: (a) => a.market_study_id ? <span className="font-mono text-xs" style={{ color: theme.info }}>#{a.market_study_id}</span> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (a) => a.market_study_id || 0,
        },
        {
          key: 'signatures', header: 'Firmas',
          render: (a) => a.signatures.length > 0 ? <span className="font-semibold" style={{ color: theme.text }}>{a.signatures.length}</span> : <span style={{ color: theme.textSecondary }}>—</span>,
          sortValue: (a) => a.signatures.length,
        },
        {
          key: 'value', header: 'Valor final',
          render: (a) => <span className="font-bold" style={{ color: theme.text }}>{a.currency} {Number(a.final_value).toLocaleString()}</span>,
          sortValue: (a) => a.final_value,
        },
        {
          key: 'date', header: 'Fecha',
          render: (a) => <span className="text-xs" style={{ color: theme.textSecondary }}>{new Date(a.created_at).toLocaleDateString()}</span>,
          sortValue: (a) => new Date(a.created_at).getTime(),
        },
      ]}
      actions={(a) => (
        <>
          {a.status === 'draft' && <ABMTableAction icon={<FileSignature className="h-4 w-4" />} title="Firmar" onClick={() => sign(a)} variant="primary" />}
          <ABMTableAction icon={<Download className="h-4 w-4" />} title="Descargar PDF" onClick={() => downloadPdf(a)} variant="primary" />
        </>
      )}
      defaultSortKey="date"
      defaultSortDirection="desc"
    />
  );

  const selectedProp = properties.find(p => p.id === Number(form.property_id));
  const availableStudies = studies.filter(s => s.property_id === Number(form.property_id));
  const studyOptions = [
    { value: '', label: 'Sin estudio ACM', description: 'Tasación standalone' },
    ...availableStudies.map(s => ({
      value: String(s.id), label: `Estudio #${s.id}`,
      description: s.suggested_value_mode ? `USD ${Math.round(s.suggested_value_mode).toLocaleString()} (${Math.round((s.confidence_score || 0) * 100)}%)` : 'Sin calcular',
    })),
  ];
  const selectedStudy = studies.find(s => s.id === Number(form.market_study_id));

  const stepProperty = (
    <div className="space-y-4 animate-fade-in">
      <ModernSelect label="Propiedad a tasar" value={form.property_id} onChange={(v: any) => setForm({...form, property_id: v, market_study_id: ''})}
        options={propertyWizardOptions} placeholder="Buscar propiedad..." searchable />
      {selectedProp && (
        <div className="p-4 rounded-xl" style={{ background: `${theme.primary}10`, border: `1px solid ${theme.primary}30` }}>
          <div className="font-semibold" style={{ color: theme.text }}>{selectedProp.title.replace(/^\[DEMO\]\s*/, '')}</div>
          <div className="text-sm mt-1" style={{ color: theme.textSecondary }}>{selectedProp.address}, {selectedProp.city}</div>
        </div>
      )}
    </div>
  );

  const stepStudy = (
    <div className="space-y-4 animate-fade-in">
      <ABMInfoPanel title="Vincular estudio de mercado" icon={<ClipboardList className="h-4 w-4" />} variant="info">
        Si la propiedad tiene un estudio ACM, vinculalo para que aparezca en el PDF con comparables y rango sugerido.
      </ABMInfoPanel>
      {form.property_id ? (
        <ModernSelect label="Estudio ACM" value={form.market_study_id} onChange={(v: any) => setForm({...form, market_study_id: v})} options={studyOptions} />
      ) : (
        <div className="p-3 rounded-lg text-sm" style={{ background: `${theme.warning}15`, color: theme.text }}>
          Volvé al paso anterior y elegí una propiedad primero.
        </div>
      )}
      {selectedStudy && selectedStudy.suggested_value_mode && (
        <div className="p-4 rounded-xl text-white" style={{ background: `linear-gradient(135deg, ${theme.success}, #14b8a6)` }}>
          <div className="text-xs opacity-80">Valor sugerido por ACM</div>
          <div className="text-2xl font-bold mt-1">USD {Math.round(selectedStudy.suggested_value_mode).toLocaleString()}</div>
          <div className="text-xs mt-1 opacity-80">Confianza {Math.round((selectedStudy.confidence_score || 0) * 100)}%</div>
        </div>
      )}
    </div>
  );

  const stepValue = (
    <div className="space-y-4 animate-fade-in">
      <ModernSelect label="Finalidad" value={form.purpose} onChange={(v: any) => setForm({...form, purpose: v})} options={PURPOSE_WIZARD_OPTIONS} />
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2"><Field label="Valor final tasado" type="number" value={form.final_value} onChange={(v: any) => setForm({...form, final_value: v})} placeholder="220000" /></div>
        <ModernSelect label="Moneda" value={form.currency} onChange={(v: any) => setForm({...form, currency: v})} options={[{ value: 'USD', label: 'USD' }, { value: 'ARS', label: 'ARS' }]} />
      </div>
      {selectedStudy?.suggested_value_mode && form.final_value && (
        <div className="p-3 rounded-lg text-xs" style={{ background: `${theme.info}15`, color: theme.text }}>
          <Sparkles className="h-4 w-4 inline mr-1" style={{ color: theme.info }} />
          Tu valor difiere {((Number(form.final_value) / selectedStudy.suggested_value_mode - 1) * 100).toFixed(1)}% del sugerido por el ACM.
        </div>
      )}
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>Metodología</label>
        <textarea rows={3} value={form.methodology} onChange={e => setForm({...form, methodology: e.target.value})}
          placeholder="Descripción de la metodología aplicada..."
          className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all resize-none"
          style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
      </div>
    </div>
  );

  const stepReview = (
    <div className="space-y-3 animate-fade-in">
      <div className="p-4 rounded-xl" style={{ background: `${theme.primary}08`, border: `1px solid ${theme.primary}30` }}>
        <div className="text-xs uppercase tracking-wide" style={{ color: theme.textSecondary }}>Propiedad</div>
        <div className="font-semibold mt-1" style={{ color: theme.text }}>{selectedProp?.title.replace(/^\[DEMO\]\s*/, '') || '—'}</div>
        <div className="mt-3 pt-3" style={{ borderTop: `1px solid ${theme.primary}30` }}>
          <div className="text-xs uppercase tracking-wide" style={{ color: theme.textSecondary }}>Valor final</div>
          <div className="text-3xl font-bold mt-1" style={{ color: theme.success }}>
            {form.currency} {Number(form.final_value || 0).toLocaleString()}
          </div>
        </div>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>Observaciones</label>
        <textarea rows={2} value={form.observations} onChange={e => setForm({...form, observations: e.target.value})}
          className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 resize-none"
          style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
      </div>
    </div>
  );

  const steps: WizardStep[] = [
    { id: 'prop', title: 'Propiedad', description: 'Inmueble a tasar', icon: <Briefcase className="h-4 w-4" />, content: stepProperty, isValid: !!form.property_id },
    { id: 'study', title: 'Estudio ACM', description: 'Soporte de comparables', icon: <ClipboardList className="h-4 w-4" />, content: stepStudy, isValid: true },
    { id: 'value', title: 'Valor + finalidad', description: 'Monto y metodología', icon: <DollarSign className="h-4 w-4" />, content: stepValue, isValid: !!form.final_value && !!form.purpose },
    { id: 'review', title: 'Revisar', description: 'Confirmar y crear', icon: <FileCheck2 className="h-4 w-4" />, content: stepReview, isValid: true },
  ];

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <PageHint pageId="tasaciones" />
      <ABMPage
        title="Tasaciones"
        icon={<FileCheck2 className="h-5 w-5" />}
        backLink="/"
        buttonLabel="Nueva tasación"
        buttonIcon={<Plus className="h-4 w-4" />}
        onAdd={openNew}
        searchPlaceholder="Buscar tasaciones..."
        searchValue={search}
        onSearchChange={setSearch}
        secondaryFilters={filtersTopRow}
        headerActions={headerActions}
        tableView={tableView}
        viewStorageKey="tasaciones_view"
        loading={loading}
        isEmpty={!loading && filtered.length === 0}
        emptyMessage={items.length === 0 ? 'Sin tasaciones todavía' : 'Sin resultados'}
      >
        {cardsView}
      </ABMPage>

      <WizardModal
        open={wizardOpen} onClose={() => setWizardOpen(false)}
        title="Nueva tasación"
        steps={steps} currentStep={step} onStepChange={setStep}
        onComplete={create} loading={saving}
        completeLabel="Crear tasación"
        headerBadge={{ icon: <FileCheck2 className="h-4 w-4" />, label: 'Tasación', color: theme.primary }}
      />
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
