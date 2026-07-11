import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Workflow, Plus, X, Save, ChevronLeft, ChevronRight, GripVertical,
  Building2, User as UserIcon, Trash2, FileSignature,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { isManager as roleIsManager } from '../lib/roles';
import { NextStepCard } from '../components/ui/NextStepCard';
import { ConfirmModal } from '../components/ui/ConfirmModal';
import PageHint from '../components/ui/PageHint';
import type { Deal, DealStage, Property, Authorization } from '../types';

// Las 6 etapas legales, EN ORDEN (mismo contrato que backend api/deals.LEGAL_STAGES).
const STAGES: { key: DealStage; label: string; color: string }[] = [
  { key: 'captado', label: 'Captado', color: '#94a3b8' },
  { key: 'publicado', label: 'Publicado', color: '#3b82f6' },
  { key: 'visita', label: 'Visita', color: '#8b5cf6' },
  { key: 'reserva', label: 'Reserva', color: '#f59e0b' },
  { key: 'boleto', label: 'Boleto', color: '#ec4899' },
  { key: 'escrituracion', label: 'Escrituración', color: '#22c55e' },
];
const STAGE_INDEX: Record<DealStage, number> = Object.fromEntries(
  STAGES.map((s, i) => [s.key, i])
) as Record<DealStage, number>;

interface ClientLite { id: number; name: string }
interface VendorLite { id: number; full_name: string }

function fmtMoney(v?: number | null, currency = 'USD'): string {
  if (v == null) return '';
  return `${currency} ${Math.round(v).toLocaleString('es-AR')}`;
}

export default function PipelineVentas() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const isManager = roleIsManager(user?.role);

  const [deals, setDeals] = useState<Deal[]>([]);
  const [authorizations, setAuthorizations] = useState<Authorization[]>([]);
  const [loading, setLoading] = useState(true);
  const [dragId, setDragId] = useState<number | null>(null);
  const [dragOverStage, setDragOverStage] = useState<DealStage | null>(null);
  const [editing, setEditing] = useState<Partial<Deal> | null>(null);
  const [toDelete, setToDelete] = useState<Deal | null>(null);

  const load = () => {
    setLoading(true);
    api.get<Deal[]>('/deals').then(r => setDeals(r.data)).finally(() => setLoading(false));
    // Autorizaciones: para saber qué deal en reserva ya tiene autorización (eslabón 4).
    api.get<Authorization[]>('/authorizations').then(r => setAuthorizations(r.data)).catch(() => {});
  };
  useEffect(load, []);

  // Pre-carga por query param (WO F6-03): ?cliente=/?propiedad= abren el alta de
  // operación con esas entidades ya seleccionadas (ficha de cliente, visita→deal).
  useEffect(() => {
    const cliente = searchParams.get('cliente');
    const propiedad = searchParams.get('propiedad');
    if (cliente || propiedad) {
      setEditing({
        stage: 'captado', currency: 'USD', probability_pct: 10,
        client_id: cliente ? Number(cliente) : undefined,
        property_id: propiedad ? Number(propiedad) : undefined,
      });
      searchParams.delete('cliente');
      searchParams.delete('propiedad');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  // Eslabón 4 del ciclo: el deal MÁS RECIENTE en etapa "reserva" cuya propiedad
  // NO tiene una autorización activa → ofrecer "Registrar autorización".
  const dealToAuthorize = useMemo(() => {
    const propsWithActiveAuth = new Set(
      authorizations.filter(a => a.status === 'activa').map(a => a.property_id),
    );
    return deals
      .filter(d => d.stage === 'reserva' && !propsWithActiveAuth.has(d.property_id))
      .sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))[0] || null;
  }, [deals, authorizations]);

  const byStage = useMemo(() => {
    const m: Record<DealStage, Deal[]> = {
      captado: [], publicado: [], visita: [], reserva: [], boleto: [], escrituracion: [],
    };
    deals.forEach(d => { (m[d.stage] || (m[d.stage] = [])).push(d); });
    return m;
  }, [deals]);

  // Cambio de etapa optimista (drag-drop o botones). Revierte si el PATCH falla.
  const moveStage = async (deal: Deal, stage: DealStage) => {
    if (deal.stage === stage) return;
    const prev = deals;
    setDeals(ds => ds.map(d => (d.id === deal.id ? { ...d, stage } : d)));
    try {
      await api.patch(`/deals/${deal.id}/stage`, { stage });
    } catch (e: any) {
      setDeals(prev);
      toast.error(e.response?.data?.detail || 'No se pudo mover el deal');
    }
  };

  const onDrop = (stage: DealStage) => {
    setDragOverStage(null);
    const id = dragId;
    setDragId(null);
    if (id == null) return;
    const deal = deals.find(d => d.id === id);
    if (deal) moveStage(deal, stage);
  };

  const remove = async (id: number) => {
    try {
      await api.delete(`/deals/${id}`);
      toast.success('Deal eliminado');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al eliminar');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <PageHint pageId="pipeline" />
      <header className="mb-5 sm:mb-6 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
            <Workflow className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
            Pipeline de ventas
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
            Circuito legal AR · {deals.length} operaciones · arrastrá las tarjetas entre etapas
            <span className="lg:hidden"> · deslizá →</span>
          </p>
        </div>
        <button onClick={() => setEditing({ stage: 'captado', currency: 'USD', probability_pct: 10 })}
          className="flex items-center gap-1.5 px-3 sm:px-4 py-2 rounded-lg text-sm font-bold flex-shrink-0 active:scale-95 transition-all"
          style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
          <Plus className="h-4 w-4" /> <span className="hidden sm:inline">Nuevo deal</span>
        </button>
      </header>

      {dealToAuthorize && (
        <div className="mb-4">
          <NextStepCard
            tone="warning"
            icon={<FileSignature className="h-5 w-5" />}
            message={`La operación de ${dealToAuthorize.property_title || 'la propiedad'} llegó a reserva y la propiedad todavía no tiene una autorización de venta activa.`}
            actions={[{
              label: 'Registrar autorización',
              icon: <FileSignature className="h-4 w-4" />,
              onClick: () => navigate(`/autorizaciones?propiedad=${dealToAuthorize.property_id}`),
            }]}
          />
        </div>
      )}

      <div className="flex gap-3 overflow-x-auto pb-2 lg:grid lg:grid-cols-6 lg:overflow-visible -mx-4 sm:-mx-6 lg:mx-0 px-4 sm:px-6 lg:px-0 snap-x snap-mandatory lg:snap-none">
        {STAGES.map(stage => {
          const stageDeals = byStage[stage.key] || [];
          const isOver = dragOverStage === stage.key;
          return (
            <div key={stage.key}
              onDragOver={(e) => { e.preventDefault(); setDragOverStage(stage.key); }}
              onDragLeave={() => setDragOverStage(s => (s === stage.key ? null : s))}
              onDrop={() => onDrop(stage.key)}
              className="rounded-xl flex flex-col flex-shrink-0 w-[280px] lg:w-auto snap-start transition-colors"
              style={{
                background: isOver ? `${stage.color}12` : theme.card,
                border: `1px solid ${isOver ? stage.color : theme.border}`,
              }}>
              <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: `1px solid ${theme.border}` }}>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: stage.color }} />
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.text }}>{stage.label}</span>
                </div>
                <span className="text-xs font-bold tabular-nums px-2 py-0.5 rounded-full"
                  style={{ background: theme.backgroundSecondary, color: theme.text }}>{stageDeals.length}</span>
              </div>
              <div className="flex-1 p-2 space-y-2 min-h-[400px]">
                {loading && (
                  <div className="text-center text-xs py-8" style={{ color: theme.textSecondary }}>Cargando…</div>
                )}
                {!loading && stageDeals.length === 0 && (
                  <div className="text-center text-xs py-8" style={{ color: theme.textSecondary }}>Vacío</div>
                )}
                {stageDeals.map(deal => {
                  const idx = STAGE_INDEX[deal.stage];
                  return (
                    <div key={deal.id} draggable
                      onDragStart={() => setDragId(deal.id)}
                      onDragEnd={() => { setDragId(null); setDragOverStage(null); }}
                      className="p-3 rounded-lg transition-all hover:shadow-md cursor-grab active:cursor-grabbing group"
                      style={{
                        background: theme.backgroundSecondary,
                        border: `1px solid ${theme.border}`,
                        opacity: dragId === deal.id ? 0.4 : 1,
                      }}>
                      <div className="flex items-start gap-1.5">
                        <GripVertical className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" style={{ color: theme.textSecondary }} />
                        <div className="min-w-0 flex-1">
                          <div className="text-xs font-semibold truncate flex items-center gap-1" style={{ color: theme.text }}>
                            <Building2 className="h-3 w-3 flex-shrink-0" style={{ color: stage.color }} />
                            <span className="truncate">{deal.property_title || `Propiedad #${deal.property_id}`}</span>
                          </div>
                          {deal.client_name && (
                            <div className="text-[11px] truncate flex items-center gap-1 mt-0.5" style={{ color: theme.textSecondary }}>
                              <UserIcon className="h-3 w-3 flex-shrink-0" /> {deal.client_name}
                            </div>
                          )}
                          {deal.negotiated_price != null && (
                            <div className="text-sm font-bold mt-1 tabular-nums" style={{ color: theme.text }}>
                              {fmtMoney(deal.negotiated_price, deal.currency)}
                            </div>
                          )}
                          {isManager && deal.vendor_name && (
                            <div className="text-[10px] mt-0.5 truncate" style={{ color: theme.textSecondary }}>{deal.vendor_name}</div>
                          )}
                        </div>
                      </div>
                      {/* Controles: mover etapa (fallback touch) + eliminar */}
                      <div className="flex items-center justify-between mt-2 pt-2" style={{ borderTop: `1px solid ${theme.border}` }}>
                        <div className="flex items-center gap-1">
                          <button aria-label="Etapa anterior" disabled={idx === 0}
                            onClick={() => idx > 0 && moveStage(deal, STAGES[idx - 1].key)}
                            className="p-1 rounded transition-all active:scale-90 disabled:opacity-30"
                            style={{ color: theme.textSecondary }}>
                            <ChevronLeft className="h-4 w-4" />
                          </button>
                          <button aria-label="Etapa siguiente" disabled={idx === STAGES.length - 1}
                            onClick={() => idx < STAGES.length - 1 && moveStage(deal, STAGES[idx + 1].key)}
                            className="p-1 rounded transition-all active:scale-90 disabled:opacity-30"
                            style={{ color: theme.textSecondary }}>
                            <ChevronRight className="h-4 w-4" />
                          </button>
                        </div>
                        <button aria-label="Eliminar" onClick={() => setToDelete(deal)}
                          className="p-1 rounded transition-all active:scale-90 opacity-0 group-hover:opacity-100"
                          style={{ color: theme.danger }}>
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {editing && (
        <DealModal deal={editing} theme={theme} isManager={isManager} onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load(); }} />
      )}

      <ConfirmModal
        isOpen={!!toDelete}
        onClose={() => setToDelete(null)}
        onConfirm={() => { const id = toDelete!.id; setToDelete(null); remove(id); }}
        title="Eliminar operación"
        message={`¿Eliminar la operación de "${toDelete?.client_name || 'este cliente'}" sobre "${toDelete?.property_title || 'esta propiedad'}"? Esta acción no se puede deshacer.`}
        confirmText="Eliminar"
        cancelText="Cancelar"
        variant="danger"
      />
    </div>
  );
}

function DealModal({ deal, theme, isManager, onClose, onSaved }: {
  deal: Partial<Deal>; theme: any; isManager: boolean; onClose: () => void; onSaved: () => void;
}) {
  const [form, setForm] = useState<Partial<Deal>>(deal);
  const [clients, setClients] = useState<ClientLite[]>([]);
  const [properties, setProperties] = useState<Property[]>([]);
  const [vendors, setVendors] = useState<VendorLite[]>([]);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof Deal, v: any) => setForm(f => ({ ...f, [k]: v }));

  useEffect(() => {
    api.get<ClientLite[]>('/clients').then(r => setClients(r.data)).catch(() => {});
    api.get<Property[]>('/properties').then(r => setProperties(r.data)).catch(() => {});
    if (isManager) api.get<VendorLite[]>('/dmo/vendors').then(r => setVendors(r.data)).catch(() => {});
  }, [isManager]);

  const submit = async () => {
    if (!form.client_id) { toast.error('Elegí un cliente'); return; }
    if (!form.property_id) { toast.error('Elegí una propiedad'); return; }
    if (isManager && !form.vendor_id) { toast.error('Elegí un vendedor'); return; }
    setSaving(true);
    try {
      const payload: any = {
        client_id: form.client_id,
        property_id: form.property_id,
        // Si es vendedor, el backend fuerza vendor_id = usuario; mandamos 0 placeholder valido.
        vendor_id: form.vendor_id ?? 0,
        stage: form.stage || 'captado',
        currency: form.currency || 'USD',
        probability_pct: form.probability_pct ?? 10,
        negotiated_price: form.negotiated_price ?? null,
      };
      await api.post('/deals', payload);
      toast.success('Deal creado');
      onSaved();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose} style={{ background: 'rgba(0,0,0,0.55)' }}>
      <div onClick={e => e.stopPropagation()} className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl shadow-2xl"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-center justify-between px-5 py-4 sticky top-0 z-10" style={{ background: theme.card, borderBottom: `1px solid ${theme.border}` }}>
          <h3 className="font-display font-black text-lg" style={{ color: theme.text }}>Nuevo deal</h3>
          <button onClick={onClose} className="p-1.5 rounded-lg" style={{ color: theme.textSecondary }}><X className="h-4 w-4" /></button>
        </div>
        <div className="p-5 space-y-3">
          <SelectField theme={theme} label="Cliente *" value={form.client_id ?? ''} onChange={(v) => set('client_id', v ? Number(v) : undefined)}
            options={clients.map(c => ({ value: c.id, label: c.name }))} />
          <SelectField theme={theme} label="Propiedad *" value={form.property_id ?? ''} onChange={(v) => set('property_id', v ? Number(v) : undefined)}
            options={properties.map(p => ({ value: p.id, label: p.title }))} />
          {isManager && (
            <SelectField theme={theme} label="Vendedor *" value={form.vendor_id ?? ''} onChange={(v) => set('vendor_id', v ? Number(v) : undefined)}
              options={vendors.map(v => ({ value: v.id, label: v.full_name }))} />
          )}
          <div className="grid grid-cols-2 gap-3">
            <SelectField theme={theme} label="Etapa" value={form.stage || 'captado'} onChange={(v) => set('stage', v)}
              options={STAGES.map(s => ({ value: s.key, label: s.label }))} />
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Precio (USD)</div>
              <input type="text" inputMode="numeric" value={form.negotiated_price ?? ''}
                onChange={(e) => { const n = parseInt(e.target.value.replace(/[^0-9]/g, ''), 10); set('negotiated_price', Number.isFinite(n) ? n : undefined); }}
                className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2"
                style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' }} />
            </div>
          </div>
        </div>
        <div className="px-5 py-4 flex justify-end gap-2 sticky bottom-0" style={{ background: theme.card, borderTop: `1px solid ${theme.border}` }}>
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium" style={{ background: theme.backgroundSecondary, color: theme.text }}>Cancelar</button>
          <button onClick={submit} disabled={saving} className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 disabled:opacity-50"
            style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
            <Save className="h-4 w-4" /> {saving ? 'Guardando…' : 'Guardar'}
          </button>
        </div>
      </div>
    </div>
  );
}

function SelectField({ theme, label, value, onChange, options }: {
  theme: any; label: string; value: string | number; onChange: (v: string) => void;
  options: { value: string | number; label: string }[];
}) {
  return (
    <div>
      <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>{label}</div>
      <select value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 appearance-none"
        style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: '16px' }}>
        <option value="">— Elegir —</option>
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
