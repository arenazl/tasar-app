import { useEffect, useMemo, useState } from 'react';
import {
  CalendarDays, Plus, X, Save, ChevronLeft, ChevronRight, Clock, MapPin, User as UserIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import type { Visit, VisitStatus, Property } from '../types';

const STATUS_META: Record<VisitStatus, { label: string; color: string }> = {
  agendada: { label: 'Agendada', color: '#3b82f6' },
  concretada: { label: 'Concretada', color: '#22c55e' },
  cancelada: { label: 'Cancelada', color: '#ef4444' },
  ausente: { label: 'Ausente', color: '#f59e0b' },
};
const DOW = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];
const MONTHS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

interface ClientLite { id: number; name: string }
interface VendorLite { id: number; full_name: string }

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
// Lunes como primer día (rioplatense).
function startOfWeek(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (x.getDay() + 6) % 7; // 0 = lunes
  return addDays(x, -day);
}
function hhmm(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export default function Visitas() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const isManager = user?.role === 'admin' || user?.role === 'supervisor';

  const [view, setView] = useState<'month' | 'week'>('month');
  const [anchor, setAnchor] = useState(() => new Date());
  const [visits, setVisits] = useState<Visit[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<{ date?: string } | null>(null);

  const load = () => {
    setLoading(true);
    api.get<Visit[]>('/visits').then(r => setVisits(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, []);

  // Agrupar por día (YYYY-MM-DD en hora local).
  const byDay = useMemo(() => {
    const m = new Map<string, Visit[]>();
    visits.forEach(v => {
      const key = ymd(new Date(v.scheduled_at));
      const arr = m.get(key) || [];
      arr.push(v);
      m.set(key, arr);
    });
    m.forEach(arr => arr.sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)));
    return m;
  }, [visits]);

  const todayKey = ymd(new Date());

  // Celdas del mes: desde el lunes de la semana del día 1 hasta completar 6 semanas.
  const monthCells = useMemo(() => {
    const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
    const start = startOfWeek(first);
    return Array.from({ length: 42 }, (_, i) => addDays(start, i));
  }, [anchor]);

  const weekCells = useMemo(() => {
    const start = startOfWeek(anchor);
    return Array.from({ length: 7 }, (_, i) => addDays(start, i));
  }, [anchor]);

  const goPrev = () => setAnchor(a => view === 'month' ? new Date(a.getFullYear(), a.getMonth() - 1, 1) : addDays(a, -7));
  const goNext = () => setAnchor(a => view === 'month' ? new Date(a.getFullYear(), a.getMonth() + 1, 1) : addDays(a, 7));
  const goToday = () => setAnchor(new Date());

  const periodLabel = view === 'month'
    ? `${MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`
    : `Semana del ${weekCells[0].getDate()} ${MONTHS[weekCells[0].getMonth()].slice(0, 3)}`;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <header className="mb-4 sm:mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
            <CalendarDays className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
            Visitas
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
            {visits.length} visitas · {isManager ? 'todo el equipo' : 'las tuyas'}
          </p>
        </div>
        <button onClick={() => setEditing({ date: todayKey })}
          className="flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-lg text-sm font-bold active:scale-95 transition-all"
          style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
          <Plus className="h-4 w-4" /> <span className="hidden sm:inline">Agendar visita</span>
        </button>
      </header>

      {/* Toolbar del calendario */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-1">
          <button onClick={goPrev} className="p-2 rounded-lg active:scale-90" style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.text }}><ChevronLeft className="h-4 w-4" /></button>
          <button onClick={goToday} className="px-3 py-2 rounded-lg text-xs font-semibold active:scale-95" style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.text }}>Hoy</button>
          <button onClick={goNext} className="p-2 rounded-lg active:scale-90" style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.text }}><ChevronRight className="h-4 w-4" /></button>
          <span className="ml-2 text-sm font-bold capitalize" style={{ color: theme.text }}>{periodLabel}</span>
        </div>
        <div className="flex items-center rounded-lg p-1" style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}` }}>
          {(['month', 'week'] as const).map(v => (
            <button key={v} onClick={() => setView(v)}
              className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
              style={{ background: view === v ? theme.primary : 'transparent', color: view === v ? (theme.primaryText || '#fff') : theme.textSecondary }}>
              {v === 'month' ? 'Mes' : 'Semana'}
            </button>
          ))}
        </div>
      </div>

      {loading && <div className="text-center text-sm py-10" style={{ color: theme.textSecondary }}>Cargando…</div>}

      {!loading && view === 'month' && (
        <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${theme.border}`, background: theme.card }}>
          <div className="grid grid-cols-7">
            {DOW.map(d => (
              <div key={d} className="px-2 py-2 text-center text-[10px] sm:text-xs font-bold uppercase tracking-wider" style={{ color: theme.textSecondary, borderBottom: `1px solid ${theme.border}` }}>{d}</div>
            ))}
            {monthCells.map((cell, i) => {
              const key = ymd(cell);
              const inMonth = cell.getMonth() === anchor.getMonth();
              const dayVisits = byDay.get(key) || [];
              const isToday = key === todayKey;
              return (
                <button key={i} onClick={() => setEditing({ date: key })}
                  className="min-h-[74px] sm:min-h-[96px] p-1.5 text-left align-top transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                  style={{
                    borderRight: (i % 7 !== 6) ? `1px solid ${theme.border}` : undefined,
                    borderBottom: `1px solid ${theme.border}`,
                    background: inMonth ? 'transparent' : theme.backgroundSecondary,
                    opacity: inMonth ? 1 : 0.55,
                  }}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold w-5 h-5 flex items-center justify-center rounded-full"
                      style={{ background: isToday ? theme.primary : 'transparent', color: isToday ? (theme.primaryText || '#fff') : theme.text }}>
                      {cell.getDate()}
                    </span>
                    {dayVisits.length > 0 && (
                      <span className="text-[9px] font-bold px-1 rounded" style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>{dayVisits.length}</span>
                    )}
                  </div>
                  <div className="mt-1 space-y-0.5">
                    {dayVisits.slice(0, 3).map(v => {
                      const meta = STATUS_META[v.status];
                      return (
                        <div key={v.id} className="text-[9px] sm:text-[10px] truncate rounded px-1 py-0.5 leading-tight"
                          style={{ background: `${meta.color}20`, color: meta.color }}>
                          {hhmm(v.scheduled_at)} {v.property_title || v.client_name || 'Visita'}
                        </div>
                      );
                    })}
                    {dayVisits.length > 3 && (
                      <div className="text-[9px]" style={{ color: theme.textSecondary }}>+{dayVisits.length - 3} más</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {!loading && view === 'week' && (
        <div className="grid grid-cols-1 sm:grid-cols-7 gap-2">
          {weekCells.map((cell, i) => {
            const key = ymd(cell);
            const dayVisits = byDay.get(key) || [];
            const isToday = key === todayKey;
            return (
              <div key={i} className="rounded-xl flex flex-col" style={{ background: theme.card, border: `1px solid ${isToday ? theme.primary : theme.border}` }}>
                <button onClick={() => setEditing({ date: key })} className="px-3 py-2 flex items-center justify-between" style={{ borderBottom: `1px solid ${theme.border}` }}>
                  <span className="text-xs font-bold" style={{ color: theme.text }}>{DOW[i]} {cell.getDate()}</span>
                  <Plus className="h-3.5 w-3.5" style={{ color: theme.textSecondary }} />
                </button>
                <div className="flex-1 p-2 space-y-1.5 min-h-[120px]">
                  {dayVisits.length === 0 && <div className="text-center text-[10px] py-4" style={{ color: theme.textSecondary }}>—</div>}
                  {dayVisits.map(v => {
                    const meta = STATUS_META[v.status];
                    return (
                      <div key={v.id} className="rounded-lg p-2" style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}` }}>
                        <div className="flex items-center gap-1 text-[11px] font-semibold" style={{ color: meta.color }}>
                          <Clock className="h-3 w-3" /> {hhmm(v.scheduled_at)}
                          <span className="ml-auto px-1.5 rounded-full text-[9px]" style={{ background: `${meta.color}20` }}>{meta.label}</span>
                        </div>
                        <div className="text-[11px] truncate flex items-center gap-1 mt-1" style={{ color: theme.text }}>
                          <MapPin className="h-3 w-3 flex-shrink-0" /> {v.property_title || `#${v.property_id}`}
                        </div>
                        {v.client_name && (
                          <div className="text-[10px] truncate flex items-center gap-1" style={{ color: theme.textSecondary }}>
                            <UserIcon className="h-3 w-3 flex-shrink-0" /> {v.client_name}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {editing && (
        <VisitModal defaultDate={editing.date} theme={theme} isManager={isManager}
          onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />
      )}
    </div>
  );
}

function VisitModal({ defaultDate, theme, isManager, onClose, onSaved }: {
  defaultDate?: string; theme: any; isManager: boolean; onClose: () => void; onSaved: () => void;
}) {
  const [clients, setClients] = useState<ClientLite[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [vendors, setVendors] = useState<VendorLite[]>([]);
  const [saving, setSaving] = useState(false);
  const [clientId, setClientId] = useState<number | ''>('');
  const [propertyId, setPropertyId] = useState<number | ''>('');
  const [vendorId, setVendorId] = useState<number | ''>('');
  const [date, setDate] = useState(defaultDate || ymd(new Date()));
  const [time, setTime] = useState('10:00');

  useEffect(() => {
    api.get<ClientLite[]>('/clients').then(r => setClients(r.data)).catch(() => {});
    api.get<Property[]>('/properties').then(r => setProperties(r.data)).catch(() => {});
    if (isManager) api.get<VendorLite[]>('/dmo/vendors').then(r => setVendors(r.data)).catch(() => {});
  }, [isManager]);

  const submit = async () => {
    if (!clientId) { toast.error('Elegí un cliente'); return; }
    if (!propertyId) { toast.error('Elegí una propiedad'); return; }
    if (isManager && !vendorId) { toast.error('Elegí un vendedor'); return; }
    setSaving(true);
    try {
      // scheduled_at en hora local -> ISO (el backend guarda con tz).
      const scheduled_at = new Date(`${date}T${time}:00`).toISOString();
      await api.post('/visits', {
        client_id: clientId,
        property_id: propertyId,
        vendor_id: vendorId || 0, // vendedor: el backend fuerza al usuario actual
        scheduled_at,
        status: 'agendada',
      });
      toast.success('Visita agendada');
      onSaved();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al agendar');
    } finally {
      setSaving(false);
    }
  };

  const selStyle = { background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' as const };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4 sticky top-0 z-10" style={{ background: theme.card, borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>Agendar visita</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Cliente *</div>
            <select value={clientId} onChange={(e) => setClientId(e.target.value ? Number(e.target.value) : '')} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
              <option value="">— Elegir —</option>
              {clients.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Propiedad *</div>
            <select value={propertyId} onChange={(e) => setPropertyId(e.target.value ? Number(e.target.value) : '')} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
              <option value="">— Elegir —</option>
              {properties.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
          </div>
          {isManager && (
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Vendedor *</div>
              <select value={vendorId} onChange={(e) => setVendorId(e.target.value ? Number(e.target.value) : '')} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none" style={selStyle}>
                <option value="">— Elegir —</option>
                {vendors.map(v => <option key={v.id} value={v.id}>{v.full_name}</option>)}
              </select>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Fecha</div>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2" style={selStyle} />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Hora</div>
              <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2" style={selStyle} />
            </div>
          </div>
        </div>
        <div className="px-5 py-4 flex justify-end gap-2 sticky bottom-0" style={{ background: theme.card, borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 disabled:opacity-50" style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
            <Save className="h-4 w-4" /> {saving ? 'Guardando…' : 'Agendar'}
          </button>
        </div>
      </div>
    </div>
  );
}
