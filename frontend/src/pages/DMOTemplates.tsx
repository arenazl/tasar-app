import { useEffect, useState } from 'react';
import { Layers, Plus, Pencil, Trash2, Copy, Flame, Star, ArrowUp, ArrowDown, ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import SideModal from '../components/SideModal';
import { ConfirmModal } from '../components/ui/ConfirmModal';
import type { Coach, DmoTemplate, DmoBlock, MetricType } from '../types';
import { isManager } from '../lib/roles';

type BlockDraft = Omit<DmoBlock, 'id' | 'template_id'> & { id?: number };

const emptyBlock: BlockDraft = {
  name: '', description: '', start_time: '09:00:00', end_time: '10:00:00',
  color: '#3b82f6', sort_order: 0, is_money_block: false,
  metric_type: 'checkbox', metric_label: '', metric_goal: 0,
};

interface TemplateDraft {
  id?: number;
  coach_id: number | null;
  name: string;
  description: string;
  market: string;
  is_active: boolean;
  is_office_default: boolean;
  blocks: BlockDraft[];
}

const emptyTemplate: TemplateDraft = {
  coach_id: null, name: '', description: '', market: 'AR', is_active: true, is_office_default: false, blocks: [],
};

function addHour(hhmmss: string): string {
  const [h, m] = hhmmss.slice(0, 5).split(':').map(Number);
  const tot = (h * 60 + m + 60) % (24 * 60);
  return `${String(Math.floor(tot / 60)).padStart(2, '0')}:${String(tot % 60).padStart(2, '0')}:00`;
}

export default function DMOTemplates() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const canEdit = isManager(user?.role);
  const [templates, setTemplates] = useState<DmoTemplate[]>([]);
  const [coaches, setCoaches] = useState<Coach[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TemplateDraft | null>(null);
  const [confirmDel, setConfirmDel] = useState<DmoTemplate | null>(null);

  const load = async () => {
    try {
      const [tr, cr] = await Promise.all([api.get<DmoTemplate[]>('/dmo/templates'), api.get<Coach[]>('/coaches')]);
      setTemplates(tr.data);
      setCoaches(cr.data);
    } catch {
      toast.error('Error al cargar templates');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const openNew = () => { setEditing({ ...emptyTemplate, coach_id: coaches[0]?.id ?? null, blocks: [] }); setModalOpen(true); };
  const openEdit = (t: DmoTemplate) => {
    setEditing({
      id: t.id, coach_id: t.coach_id, name: t.name, description: t.description ?? '',
      market: t.market ?? '', is_active: t.is_active, is_office_default: t.is_office_default,
      blocks: t.blocks.map(({ id, template_id, ...rest }) => ({ id, ...rest })),
    });
    setModalOpen(true);
  };

  const save = async () => {
    if (!editing) return;
    if (!editing.name.trim()) return toast.error('Nombre requerido');
    if (!editing.coach_id) return toast.error('Coach requerido');
    if (editing.blocks.length === 0) return toast.error('Agregá al menos un bloque');
    const payload = {
      coach_id: editing.coach_id, name: editing.name, description: editing.description || null,
      market: editing.market || null, is_active: editing.is_active, is_office_default: editing.is_office_default,
      blocks: editing.blocks.map((b, i) => ({
        name: b.name, description: b.description || null, start_time: b.start_time, end_time: b.end_time,
        color: b.color, sort_order: i + 1, is_money_block: b.is_money_block,
        metric_type: b.metric_type, metric_label: b.metric_label || null, metric_goal: b.metric_goal,
      })),
    };
    try {
      if (editing.id) await api.patch(`/dmo/templates/${editing.id}`, payload);
      else await api.post('/dmo/templates', payload);
      toast.success('Template guardado');
      setModalOpen(false);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al guardar');
    }
  };

  const clone = async (t: DmoTemplate) => {
    try {
      await api.post(`/dmo/templates/${t.id}/clone`);
      toast.success('Template clonado a tu workspace');
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al clonar');
    }
  };

  const remove = async () => {
    if (!confirmDel) return;
    try {
      await api.delete(`/dmo/templates/${confirmDel.id}`);
      toast.success('Template eliminado');
      setConfirmDel(null);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al eliminar');
    }
  };

  const addBlock = () => {
    if (!editing) return;
    const last = editing.blocks[editing.blocks.length - 1];
    const nextStart = last ? last.end_time : '09:00:00';
    setEditing({ ...editing, blocks: [...editing.blocks, { ...emptyBlock, start_time: nextStart, end_time: addHour(nextStart) }] });
  };
  const updateBlock = (idx: number, patch: Partial<BlockDraft>) => {
    if (!editing) return;
    const next = [...editing.blocks];
    next[idx] = { ...next[idx], ...patch };
    setEditing({ ...editing, blocks: next });
  };
  const removeBlock = (idx: number) => {
    if (!editing) return;
    setEditing({ ...editing, blocks: editing.blocks.filter((_, i) => i !== idx) });
  };
  const moveBlock = (idx: number, dir: -1 | 1) => {
    if (!editing) return;
    const next = [...editing.blocks];
    const tgt = idx + dir;
    if (tgt < 0 || tgt >= next.length) return;
    [next[idx], next[tgt]] = [next[tgt], next[idx]];
    setEditing({ ...editing, blocks: next });
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
            <Layers className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
            Templates DMO
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
            Rutinas diarias que pueden seguir los vendedores · {templates.length} disponibles
          </p>
        </div>
        {canEdit && (
          <button onClick={openNew} className="inline-flex items-center gap-2 h-10 px-4 rounded-lg text-sm font-semibold text-white active:scale-95 transition-all" style={{ background: theme.primary }}>
            <Plus className="h-4 w-4" /> Nuevo template
          </button>
        )}
      </header>

      {loading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-48 rounded-xl animate-pulse" style={{ background: theme.card }} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {templates.map((t) => (
            <div key={t.id} className="rounded-xl p-5 transition-all hover:-translate-y-0.5"
              style={{ background: theme.card, border: `1px solid ${t.is_office_default ? theme.primary : theme.border}`, boxShadow: t.is_office_default ? `0 0 0 1px ${theme.primary}` : 'none' }}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <h3 className="font-bold" style={{ color: theme.text }}>{t.name}</h3>
                    {t.is_office_default && (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded font-semibold text-white" style={{ background: theme.primary }}>
                        <Star className="h-3 w-3" /> Default oficina
                      </span>
                    )}
                    {t.is_official && (
                      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded font-semibold text-white" style={{ background: theme.success }}>
                        <ShieldCheck className="h-3 w-3" /> Catálogo oficial
                      </span>
                    )}
                    {t.market && (
                      <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>{t.market}</span>
                    )}
                  </div>
                  <p className="text-xs" style={{ color: theme.textSecondary }}>
                    Coach: <span className="font-semibold">{t.coach_name || '—'}</span> · {t.blocks.length} bloques · {t.assignments_count ?? 0} asignaciones
                  </p>
                </div>
              </div>
              {t.description && <p className="text-sm mb-3 line-clamp-2" style={{ color: theme.textSecondary }}>{t.description}</p>}
              <div className="space-y-1.5 mb-3">
                {t.blocks.slice(0, 6).map((b) => (
                  <div key={b.id} className="flex items-center gap-2 text-xs">
                    <div className="w-1 h-4 rounded-full flex-shrink-0" style={{ background: b.color }} />
                    <span className="font-mono" style={{ color: theme.textSecondary }}>{b.start_time.slice(0, 5)}</span>
                    <span className="truncate flex-1" style={{ color: theme.text }}>{b.name}</span>
                    {b.is_money_block && <Flame className="h-3 w-3 flex-shrink-0" style={{ color: theme.danger }} />}
                  </div>
                ))}
              </div>
              {canEdit && (
                <div className="flex items-center justify-end gap-1 pt-3" style={{ borderTop: `1px solid ${theme.border}` }}>
                  <button onClick={() => clone(t)} className="p-1.5 rounded hover:bg-black/5" title="Clonar a mi workspace">
                    <Copy className="h-4 w-4" style={{ color: theme.textSecondary }} />
                  </button>
                  {!t.is_official && (
                    <>
                      <button onClick={() => openEdit(t)} className="p-1.5 rounded hover:bg-black/5" title="Editar">
                        <Pencil className="h-4 w-4" style={{ color: theme.textSecondary }} />
                      </button>
                      <button onClick={() => setConfirmDel(t)} className="p-1.5 rounded hover:bg-black/5" title="Eliminar">
                        <Trash2 className="h-4 w-4" style={{ color: theme.danger }} />
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
          {templates.length === 0 && (
            <div className="col-span-full text-center py-12 text-sm" style={{ color: theme.textSecondary }}>
              No hay templates. Cloná uno del catálogo oficial para empezar.
            </div>
          )}
        </div>
      )}

      <SideModal open={modalOpen} onClose={() => setModalOpen(false)} title={editing?.id ? 'Editar template' : 'Nuevo template'} width="xl"
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="px-4 py-2 rounded-lg text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }}>Cancelar</button>
            <button onClick={save} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: theme.primary }}>Guardar</button>
          </>
        }>
        {editing && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Field theme={theme} label="Nombre">
                <input value={editing.name} onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
              </Field>
              <Field theme={theme} label="Coach">
                <select value={editing.coach_id ?? ''} onChange={(e) => setEditing({ ...editing, coach_id: e.target.value ? Number(e.target.value) : null })}
                  className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }}>
                  <option value="">— elegir —</option>
                  {coaches.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </Field>
            </div>
            <Field theme={theme} label="Descripción">
              <textarea value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} rows={2}
                className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
            </Field>
            <div className="grid grid-cols-3 gap-3 items-end">
              <Field theme={theme} label="Mercado">
                <input value={editing.market} onChange={(e) => setEditing({ ...editing, market: e.target.value })} placeholder="AR, USA..."
                  className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
              </Field>
              <label className="flex items-center gap-2 text-sm pb-2" style={{ color: theme.text }}>
                <input type="checkbox" checked={editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} /> Activo
              </label>
              <label className="flex items-center gap-2 text-sm pb-2" style={{ color: theme.text }}>
                <input type="checkbox" checked={editing.is_office_default} onChange={(e) => setEditing({ ...editing, is_office_default: e.target.checked })} /> Default oficina
              </label>
            </div>

            <div className="pt-2" style={{ borderTop: `1px solid ${theme.border}` }}>
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-semibold text-sm" style={{ color: theme.text }}>Bloques del día</h4>
                <button onClick={addBlock} className="flex items-center gap-1 text-xs px-2 py-1 rounded" style={{ border: `1px solid ${theme.border}`, color: theme.text }}>
                  <Plus className="h-3 w-3" /> Agregar bloque
                </button>
              </div>
              <div className="space-y-2">
                {editing.blocks.map((b, idx) => (
                  <BlockEditor key={idx} theme={theme} block={b} onChange={(p) => updateBlock(idx, p)} onRemove={() => removeBlock(idx)}
                    onUp={() => moveBlock(idx, -1)} onDown={() => moveBlock(idx, 1)} isFirst={idx === 0} isLast={idx === editing.blocks.length - 1} />
                ))}
                {editing.blocks.length === 0 && (
                  <div className="text-center py-6 text-sm rounded-lg" style={{ border: `2px dashed ${theme.border}`, color: theme.textSecondary }}>
                    Agregá al menos un bloque
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </SideModal>

      <ConfirmModal isOpen={!!confirmDel} onClose={() => setConfirmDel(null)} onConfirm={remove}
        title="Eliminar template" message="¿Eliminar este template? Si tiene vendedores asignados, primero reasignalos."
        confirmText="Eliminar" variant="danger" />
    </div>
  );
}

function Field({ theme, label, children }: { theme: any; label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-semibold uppercase tracking-wider mb-1" style={{ color: theme.textSecondary }}>{label}</label>
      {children}
    </div>
  );
}

function BlockEditor({ theme, block, onChange, onRemove, onUp, onDown, isFirst, isLast }: {
  theme: any; block: BlockDraft; onChange: (p: Partial<BlockDraft>) => void; onRemove: () => void;
  onUp: () => void; onDown: () => void; isFirst: boolean; isLast: boolean;
}) {
  return (
    <div className="rounded-lg p-3" style={{ background: theme.backgroundSecondary, border: `1px solid ${block.is_money_block ? theme.danger : theme.border}` }}>
      <div className="flex items-center gap-2 mb-2">
        <input value={block.name} onChange={(e) => onChange({ name: e.target.value })} placeholder="Nombre del bloque"
          className="flex-1 px-2 py-1 rounded bg-transparent text-sm font-semibold" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
        <button onClick={onUp} disabled={isFirst} className="p-1 disabled:opacity-30" style={{ color: theme.textSecondary }}><ArrowUp className="h-3 w-3" /></button>
        <button onClick={onDown} disabled={isLast} className="p-1 disabled:opacity-30" style={{ color: theme.textSecondary }}><ArrowDown className="h-3 w-3" /></button>
        <button onClick={onRemove} className="p-1"><Trash2 className="h-4 w-4" style={{ color: theme.danger }} /></button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-2">
        <input type="time" value={block.start_time.slice(0, 5)} onChange={(e) => onChange({ start_time: e.target.value + ':00' })}
          className="px-2 py-1 rounded bg-transparent text-xs" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
        <input type="time" value={block.end_time.slice(0, 5)} onChange={(e) => onChange({ end_time: e.target.value + ':00' })}
          className="px-2 py-1 rounded bg-transparent text-xs" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
        <input type="color" value={block.color} onChange={(e) => onChange({ color: e.target.value })}
          className="px-1 py-0.5 rounded bg-transparent h-7" style={{ border: `1px solid ${theme.border}` }} />
        <label className="flex items-center gap-1 text-xs" style={{ color: theme.text }}>
          <input type="checkbox" checked={block.is_money_block} onChange={(e) => onChange({ is_money_block: e.target.checked })} />
          <Flame className="h-3 w-3" style={{ color: theme.danger }} /> Money
        </label>
      </div>
      <textarea value={block.description ?? ''} onChange={(e) => onChange({ description: e.target.value })} placeholder="Descripción / instrucciones" rows={2}
        className="w-full px-2 py-1 rounded bg-transparent text-xs mb-2" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
      <div className="grid grid-cols-3 gap-2">
        <select value={block.metric_type} onChange={(e) => onChange({ metric_type: e.target.value as MetricType })}
          className="px-2 py-1 rounded bg-transparent text-xs" style={{ border: `1px solid ${theme.border}`, color: theme.text }}>
          <option value="checkbox">Solo check</option>
          <option value="quantity">Cantidad</option>
        </select>
        <input value={block.metric_label ?? ''} onChange={(e) => onChange({ metric_label: e.target.value })} placeholder="ej: Conversaciones"
          disabled={block.metric_type === 'checkbox'}
          className="px-2 py-1 rounded bg-transparent text-xs disabled:opacity-40" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
        <input type="number" min="0" value={block.metric_goal} onChange={(e) => onChange({ metric_goal: parseInt(e.target.value) || 0 })} placeholder="Meta"
          disabled={block.metric_type === 'checkbox'}
          className="px-2 py-1 rounded bg-transparent text-xs disabled:opacity-40" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
      </div>
    </div>
  );
}
