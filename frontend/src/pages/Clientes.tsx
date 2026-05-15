import { useEffect, useMemo, useState } from 'react';
import { Users, Mail, Phone, Building2, FileCheck2, X, Save, Trash2, Edit3, MapPin } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { ABMPage, ABMCard } from '../components/ui/ABMPage';

interface Cliente {
  id: number;
  name: string;
  type: string;
  contact_name?: string;
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  notes?: string;
  appraisals_count: number;
}

const TYPE_OPTIONS = [
  { value: 'banco', label: 'Banco', color: '#3b82f6' },
  { value: 'fondo', label: 'Fondo', color: '#a855f7' },
  { value: 'estudio', label: 'Estudio', color: '#f59e0b' },
  { value: 'inmobiliaria', label: 'Inmobiliaria', color: '#ec4899' },
  { value: 'particular', label: 'Particular', color: '#10b981' },
];
const TYPE_COLOR = Object.fromEntries(TYPE_OPTIONS.map(o => [o.value, o.color]));
const TYPE_LABEL = Object.fromEntries(TYPE_OPTIONS.map(o => [o.value, o.label]));

export default function Clientes() {
  const { theme } = useTheme();
  const [items, setItems] = useState<Cliente[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [editing, setEditing] = useState<Partial<Cliente> | null>(null);

  const load = () => {
    setLoading(true);
    api.get<Cliente[]>('/clients').then(r => setItems(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = useMemo(() => {
    const s = search.toLowerCase().trim();
    return items.filter(c =>
      (filterType === 'all' || c.type === filterType) &&
      (!s || c.name.toLowerCase().includes(s) || (c.email || '').toLowerCase().includes(s) || (c.contact_name || '').toLowerCase().includes(s))
    );
  }, [items, search, filterType]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    TYPE_OPTIONS.forEach(t => { c[t.value] = items.filter(i => i.type === t.value).length; });
    return c;
  }, [items]);

  const save = async (data: Partial<Cliente>) => {
    try {
      if (data.id) {
        await api.put(`/clients/${data.id}`, data);
        toast.success('Cliente actualizado');
      } else {
        await api.post('/clients', data);
        toast.success('Cliente creado');
      }
      setEditing(null);
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    }
  };

  const remove = async (id: number) => {
    if (!confirm('¿Eliminar este cliente?')) return;
    try {
      await api.delete(`/clients/${id}`);
      toast.success('Cliente eliminado');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al eliminar');
    }
  };

  const secondaryFilters = (
    <div className="flex items-center gap-1.5 flex-wrap">
      <Pill label={`Todos (${counts.all})`} active={filterType === 'all'} onClick={() => setFilterType('all')} color={theme.primary} theme={theme} />
      {TYPE_OPTIONS.map(t => (
        <Pill key={t.value} label={`${t.label} (${counts[t.value] || 0})`}
          active={filterType === t.value} onClick={() => setFilterType(t.value)} color={t.color} theme={theme} />
      ))}
    </div>
  );

  return (
    <>
      <ABMPage
        title="Clientes"
        icon={<Users className="h-5 w-5" />}
        searchValue={search}
        onSearchChange={setSearch}
        searchPlaceholder="Buscar por nombre, contacto o email..."
        onAdd={() => setEditing({ type: 'particular' })}
        buttonLabel="Nuevo cliente"
        loading={loading}
        isEmpty={filtered.length === 0}
        secondaryFilters={secondaryFilters}
      >
        {filtered.map((c, i) => {
          const color = TYPE_COLOR[c.type] || theme.primary;
          return (
            <ABMCard key={c.id} index={i}>
              <div className="flex items-start gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `${color}20` }}>
                  <Building2 className="h-6 w-6" style={{ color }} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold truncate" style={{ color: theme.text }}>{c.name}</div>
                  <div className="text-[10px] uppercase tracking-wider font-bold mt-0.5" style={{ color }}>
                    {TYPE_LABEL[c.type] || c.type}
                  </div>
                </div>
                <div className="flex gap-1">
                  <button onClick={(e) => { e.stopPropagation(); setEditing(c); }}
                    className="p-1.5 rounded-lg transition-all active:scale-95"
                    style={{ background: `${theme.primary}15`, color: theme.primary }} aria-label="Editar">
                    <Edit3 className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={(e) => { e.stopPropagation(); remove(c.id); }}
                    className="p-1.5 rounded-lg transition-all active:scale-95"
                    style={{ background: `${theme.danger}15`, color: theme.danger }} aria-label="Eliminar">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              {c.contact_name && (
                <div className="text-xs mb-1 flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <Users className="h-3 w-3" /> {c.contact_name}
                </div>
              )}
              {c.email && (
                <div className="text-xs flex items-center gap-2 truncate" style={{ color: theme.textSecondary }}>
                  <Mail className="h-3 w-3 flex-shrink-0" /> <span className="truncate">{c.email}</span>
                </div>
              )}
              {c.phone && (
                <div className="text-xs flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <Phone className="h-3 w-3" /> {c.phone}
                </div>
              )}
              {c.address && (
                <div className="text-xs flex items-center gap-2 truncate" style={{ color: theme.textSecondary }}>
                  <MapPin className="h-3 w-3 flex-shrink-0" /> <span className="truncate">{c.address}</span>
                </div>
              )}
              <div className="mt-3 pt-3 flex items-center justify-between" style={{ borderTop: `1px solid ${theme.border}` }}>
                <span className="text-xs flex items-center gap-1" style={{ color: theme.textSecondary }}>
                  <FileCheck2 className="h-3 w-3" /> {c.appraisals_count} tasaciones
                </span>
                {c.tax_id && (
                  <span className="text-[10px] font-mono" style={{ color: theme.textSecondary }}>{c.tax_id}</span>
                )}
              </div>
            </ABMCard>
          );
        })}
      </ABMPage>

      {editing && (
        <ClientModal client={editing} theme={theme} onClose={() => setEditing(null)} onSave={save} />
      )}
    </>
  );
}

function Pill({ label, active, onClick, color }: any) {
  return (
    <button onClick={onClick}
      className="px-3 py-1.5 rounded-full text-xs font-semibold transition-all active:scale-95"
      style={{
        background: active ? color : `${color}12`,
        color: active ? '#fff' : color,
        border: `1px solid ${active ? color : color + '40'}`,
      }}>{label}</button>
  );
}

function ClientModal({ client, theme, onClose, onSave }: any) {
  const [form, setForm] = useState<Partial<Cliente>>(client);
  const set = (k: keyof Cliente, v: any) => setForm(f => ({ ...f, [k]: v }));

  const submit = () => {
    if (!form.name?.trim()) { toast.error('El nombre es obligatorio'); return; }
    onSave(form);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-200"
      onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl animate-in zoom-in-95 duration-200"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4 sticky top-0 z-10" style={{ background: theme.card, borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>
            {form.id ? 'Editar cliente' : 'Nuevo cliente'}
          </h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <Field theme={theme} label="Nombre / Razón social *" value={form.name || ''} onChange={(v: string) => set('name', v)} />
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: theme.textSecondary }}>Tipo</div>
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
              {TYPE_OPTIONS.map(t => (
                <button key={t.value} type="button" onClick={() => set('type', t.value)}
                  className="px-2 py-2 rounded-lg text-xs font-semibold transition-all active:scale-95"
                  style={{
                    background: form.type === t.value ? t.color : `${t.color}12`,
                    color: form.type === t.value ? '#fff' : t.color,
                    border: `1px solid ${form.type === t.value ? t.color : t.color + '40'}`,
                  }}>{t.label}</button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field theme={theme} label="Contacto" value={form.contact_name || ''} onChange={(v: string) => set('contact_name', v)} />
            <Field theme={theme} label="CUIT / DNI" value={form.tax_id || ''} onChange={(v: string) => set('tax_id', v)} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field theme={theme} label="Email" value={form.email || ''} onChange={(v: string) => set('email', v)} type="email" />
            <Field theme={theme} label="Teléfono" value={form.phone || ''} onChange={(v: string) => set('phone', v)} type="tel" />
          </div>
          <Field theme={theme} label="Dirección" value={form.address || ''} onChange={(v: string) => set('address', v)} />
          <Field theme={theme} label="Notas" value={form.notes || ''} onChange={(v: string) => set('notes', v)} textarea />
        </div>
        <div className="px-5 py-4 flex justify-end gap-2 sticky bottom-0" style={{ background: theme.card, borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium"
            style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={submit}
            className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5"
            style={{ background: theme.primary, color: theme.primaryText }}>
            <Save className="h-4 w-4" /> Guardar
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ theme, label, value, onChange, type = 'text', textarea = false }: any) {
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
