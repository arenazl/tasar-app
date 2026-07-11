import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FileSignature, X, Save, Trash2, Edit3, Plus, Building2, Calendar, ShieldCheck, DollarSign,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { isManager as roleIsManager } from '../lib/roles';
import { ABMPage, ABMCard } from '../components/ui/ABMPage';
import type { Authorization, AuthorizationStatus, Property } from '../types';

const STATUS_OPTIONS: { value: AuthorizationStatus; label: string; color: string }[] = [
  { value: 'activa', label: 'Activa', color: '#22c55e' },
  { value: 'vencida', label: 'Vencida', color: '#f59e0b' },
  { value: 'ejecutada', label: 'Ejecutada', color: '#3b82f6' },
  { value: 'cancelada', label: 'Cancelada', color: '#ef4444' },
];
const STATUS_COLOR = Object.fromEntries(STATUS_OPTIONS.map(o => [o.value, o.color]));
const STATUS_LABEL = Object.fromEntries(STATUS_OPTIONS.map(o => [o.value, o.label]));

interface VendorLite { id: number; full_name: string }

function today(): string {
  return new Date().toISOString().slice(0, 10);
}
function plusMonths(months: number): string {
  const d = new Date();
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

export default function Autorizaciones() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const isManager = roleIsManager(user?.role);

  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<Authorization[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [editing, setEditing] = useState<Partial<Authorization> | null>(null);

  const load = () => {
    setLoading(true);
    api.get<Authorization[]>('/authorizations').then(r => setItems(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  // Pre-carga por query param (WO F6-03): el CTA "Registrar autorización" del
  // pipeline (deal en reserva) llega con ?propiedad= y abre el alta con esa
  // propiedad ya seleccionada.
  useEffect(() => {
    const propiedad = searchParams.get('propiedad');
    if (propiedad) {
      setEditing({
        status: 'activa', currency: 'USD', commission_pct: 4, exclusivity: false,
        signed_date: today(), expiry_date: plusMonths(6),
        property_id: Number(propiedad),
      });
      searchParams.delete('propiedad');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const filtered = useMemo(() => {
    const s = search.toLowerCase().trim();
    return items.filter(a =>
      (filterStatus === 'all' || a.status === filterStatus) &&
      (!s || (a.property_title || '').toLowerCase().includes(s) || (a.captador_name || '').toLowerCase().includes(s))
    );
  }, [items, search, filterStatus]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    STATUS_OPTIONS.forEach(o => { c[o.value] = items.filter(i => i.status === o.value).length; });
    return c;
  }, [items]);

  const save = async (data: Partial<Authorization>) => {
    try {
      if (data.id) {
        await api.patch(`/authorizations/${data.id}`, data);
        toast.success('Autorización actualizada');
      } else {
        await api.post('/authorizations', data);
        toast.success('Autorización creada');
      }
      setEditing(null);
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    }
  };

  const remove = async (id: number) => {
    if (!confirm('¿Eliminar esta autorización?')) return;
    try {
      await api.delete(`/authorizations/${id}`);
      toast.success('Autorización eliminada');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al eliminar');
    }
  };

  const secondaryFilters = (
    <div className="flex items-center gap-1.5 flex-wrap">
      <Pill label={`Todas (${counts.all})`} active={filterStatus === 'all'} onClick={() => setFilterStatus('all')} color={theme.primary} />
      {STATUS_OPTIONS.map(o => (
        <Pill key={o.value} label={`${o.label} (${counts[o.value] || 0})`} active={filterStatus === o.value} onClick={() => setFilterStatus(o.value)} color={o.color} />
      ))}
    </div>
  );

  return (
    <div className="p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <ABMPage
        title="Autorizaciones"
        icon={<FileSignature className="h-5 w-5" />}
        backLink="/"
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Buscar por propiedad o captador..."
        onAdd={() => setEditing({ status: 'activa', currency: 'USD', commission_pct: 4, exclusivity: false, signed_date: today(), expiry_date: plusMonths(6) })}
        buttonLabel="Nueva autorización"
        buttonIcon={<Plus className="h-4 w-4" />}
        loading={loading}
        isEmpty={!loading && filtered.length === 0}
        emptyMessage={items.length === 0 ? 'Sin autorizaciones todavía' : 'Sin resultados con esos filtros'}
        secondaryFilters={secondaryFilters}
      >
        {filtered.map((a, i) => {
          const color = STATUS_COLOR[a.status] || theme.primary;
          return (
            <ABMCard key={a.id} index={i}>
              <div className="flex items-start gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}20` }}>
                  <Building2 className="h-6 w-6" style={{ color }} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold truncate" style={{ color: theme.text }}>{a.property_title || `Propiedad #${a.property_id}`}</div>
                  <div className="text-[10px] uppercase tracking-wider font-bold mt-0.5" style={{ color }}>
                    {STATUS_LABEL[a.status] || a.status}{a.exclusivity ? ' · Exclusiva' : ''}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={() => setEditing(a)} className="p-1.5 rounded-lg active:scale-95" style={{ background: `${theme.primary}15`, color: theme.primary }} aria-label="Editar"><Edit3 className="h-3.5 w-3.5" /></button>
                  <button onClick={() => remove(a.id)} className="p-1.5 rounded-lg active:scale-95" style={{ background: `${theme.danger}15`, color: theme.danger }} aria-label="Eliminar"><Trash2 className="h-3.5 w-3.5" /></button>
                </div>
              </div>
              <div className="text-xs mb-1 flex items-center gap-2" style={{ color: theme.textSecondary }}>
                <DollarSign className="h-3 w-3" /> Mínimo {a.currency} {Math.round(a.min_price).toLocaleString('es-AR')} · Comisión {a.commission_pct}%
              </div>
              <div className="text-xs mb-1 flex items-center gap-2" style={{ color: theme.textSecondary }}>
                <Calendar className="h-3 w-3" /> {a.signed_date} → {a.expiry_date}
              </div>
              {a.captador_name && (
                <div className="text-xs flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <ShieldCheck className="h-3 w-3" /> {a.captador_name}
                </div>
              )}
            </ABMCard>
          );
        })}
      </ABMPage>

      {editing && (
        <AuthModal auth={editing} theme={theme} isManager={isManager} onClose={() => setEditing(null)} onSave={save} />
      )}
    </div>
  );
}

function Pill({ label, active, onClick, color }: { label: string; active: boolean; onClick: () => void; color: string }) {
  return (
    <button onClick={onClick} data-pill="true" className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all active:scale-95"
      style={{ background: active ? color : `${color}12`, color: active ? '#fff' : color, border: `1px solid ${active ? color : color + '40'}` }}>{label}</button>
  );
}

function AuthModal({ auth, theme, isManager, onClose, onSave }: {
  auth: Partial<Authorization>; theme: any; isManager: boolean; onClose: () => void; onSave: (d: Partial<Authorization>) => void;
}) {
  const [form, setForm] = useState<Partial<Authorization>>(auth);
  const [properties, setProperties] = useState<Property[]>([]);
  const [vendors, setVendors] = useState<VendorLite[]>([]);
  const set = (k: keyof Authorization, v: any) => setForm(f => ({ ...f, [k]: v }));

  useEffect(() => {
    api.get<Property[]>('/properties').then(r => setProperties(r.data)).catch(() => {});
    if (isManager) api.get<VendorLite[]>('/dmo/vendors').then(r => setVendors(r.data)).catch(() => {});
  }, [isManager]);

  const submit = () => {
    if (!form.property_id) { toast.error('Elegí una propiedad'); return; }
    if (!form.min_price) { toast.error('Cargá el precio mínimo'); return; }
    // El backend fuerza captador = usuario si es vendedor; mandamos 0 placeholder valido.
    onSave({ ...form, captador_id: form.captador_id ?? 0 });
  };

  const selStyle = { background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' as const };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4 sticky top-0 z-10" style={{ background: theme.card, borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>{form.id ? 'Editar autorización' : 'Nueva autorización'}</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Propiedad *</div>
            <select value={form.property_id ?? ''} onChange={(e) => set('property_id', e.target.value ? Number(e.target.value) : undefined)} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
              <option value="">— Elegir —</option>
              {properties.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>
          {isManager && (
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Captador *</div>
              <select value={form.captador_id ?? ''} onChange={(e) => set('captador_id', e.target.value ? Number(e.target.value) : undefined)} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
                <option value="">— Elegir —</option>
                {vendors.map(v => <option key={v.id} value={v.id}>{v.full_name}</option>)}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <Field theme={theme} label="Firma" type="date" value={form.signed_date || ''} onChange={(v) => set('signed_date', v)} />
            <Field theme={theme} label="Vencimiento" type="date" value={form.expiry_date || ''} onChange={(v) => set('expiry_date', v)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Precio mínimo (USD) *</div>
              <input type="text" inputMode="numeric" value={form.min_price ?? ''} onChange={(e) => { const n = parseInt(e.target.value.replace(/[^0-9]/g, ''), 10); set('min_price', Number.isFinite(n) ? n : undefined); }} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2" style={selStyle} />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Comisión %</div>
              <input type="text" inputMode="decimal" value={form.commission_pct ?? ''} onChange={(e) => { const n = parseFloat(e.target.value.replace(/[^0-9.]/g, '')); set('commission_pct', Number.isFinite(n) ? n : undefined); }} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2" style={selStyle} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Estado</div>
              <select value={form.status || 'activa'} onChange={(e) => set('status', e.target.value)} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
                {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            <div className="flex items-end">
              <button type="button" onClick={() => set('exclusivity', !form.exclusivity)} className="w-full px-3 py-2.5 rounded-lg text-sm font-semibold transition-all active:scale-95"
                style={{ background: form.exclusivity ? theme.primary : theme.backgroundSecondary, color: form.exclusivity ? (theme.primaryText || '#fff') : theme.text, border: `1px solid ${theme.border}` }}>
                {form.exclusivity ? 'Con exclusividad' : 'Sin exclusividad'}
              </button>
            </div>
          </div>
          <Field theme={theme} label="Notas" value={form.notes || ''} onChange={(v) => set('notes', v)} textarea />
        </div>
        <div className="px-5 py-4 flex justify-end gap-2 sticky bottom-0" style={{ background: theme.card, borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={submit} className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5" style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
            <Save className="h-4 w-4" /> Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ theme, label, value, onChange, type = 'text', textarea = false }: {
  theme: any; label: string; value: string; onChange: (v: string) => void; type?: string; textarea?: boolean;
}) {
  const common = {
    value,
    onChange: (e: any) => onChange(e.target.value),
    className: 'w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2',
    style: { background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' as const },
  };
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>{label}</div>
      {textarea ? <textarea rows={3} {...common} /> : <input type={type} {...common} />}
    </div>
  );
}
