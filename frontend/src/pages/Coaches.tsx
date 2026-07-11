import { useEffect, useMemo, useState } from 'react';
import { GraduationCap, Pencil, Trash2, ExternalLink, ShieldCheck, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import SideModal from '../components/SideModal';
import { ConfirmModal } from '../components/ui/ConfirmModal';
import type { Coach } from '../types';
import { isManager } from '../lib/roles';

const empty: Partial<Coach> = { name: '', description: '', photo_url: '', source_url: '', is_official: false };

export default function Coaches() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const canEdit = isManager(user?.role);
  const [items, setItems] = useState<Coach[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Partial<Coach> | null>(null);
  const [confirmDel, setConfirmDel] = useState<Coach | null>(null);

  const load = async () => {
    try {
      const r = await api.get<Coach[]>('/coaches');
      setItems(r.data);
    } catch {
      toast.error('Error al cargar coaches');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    if (!q) return items;
    return items.filter((c) => c.name.toLowerCase().includes(q) || (c.description ?? '').toLowerCase().includes(q));
  }, [items, search]);

  const openNew = () => { setEditing({ ...empty }); setModalOpen(true); };
  const openEdit = (c: Coach) => { setEditing({ ...c }); setModalOpen(true); };

  const save = async () => {
    if (!editing?.name?.trim()) { toast.error('Nombre requerido'); return; }
    const payload = {
      name: editing.name,
      description: editing.description || null,
      photo_url: editing.photo_url || null,
      source_url: editing.source_url || null,
      is_official: !!editing.is_official,
    };
    try {
      if (editing.id) await api.patch(`/coaches/${editing.id}`, payload);
      else await api.post('/coaches', payload);
      toast.success('Coach guardado');
      setModalOpen(false);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al guardar');
    }
  };

  const remove = async () => {
    if (!confirmDel) return;
    try {
      await api.delete(`/coaches/${confirmDel.id}`);
      toast.success('Coach eliminado');
      setConfirmDel(null);
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al eliminar');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6 flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
            <GraduationCap className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
            Coaches
          </h1>
          <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
            Metodologías de productividad · {filtered.length} en catálogo
          </p>
        </div>
        {canEdit && (
          <button onClick={openNew} className="inline-flex items-center gap-2 h-10 px-4 rounded-lg text-sm font-semibold text-white active:scale-95 transition-all" style={{ background: theme.primary }}>
            <Plus className="h-4 w-4" /> Nuevo coach
          </button>
        )}
      </header>

      <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar coach, metodología..."
        className="w-full sm:max-w-sm mb-5 px-3 py-2 rounded-lg text-sm bg-transparent"
        style={{ border: `1px solid ${theme.border}`, color: theme.text }} />

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-40 rounded-xl animate-pulse" style={{ background: theme.card }} />)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((c) => (
            <div key={c.id} className="rounded-xl p-5 transition-all hover:-translate-y-0.5"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-white flex-shrink-0"
                  style={{ background: c.is_official ? theme.primary : theme.textSecondary }}>
                  {c.name.slice(0, 2).toUpperCase()}
                </div>
                {canEdit && (
                  <div className="flex items-center gap-1">
                    <button onClick={() => openEdit(c)} className="p-1.5 rounded hover:bg-black/5" title="Editar">
                      <Pencil className="h-4 w-4" style={{ color: theme.textSecondary }} />
                    </button>
                    {!c.is_official && (
                      <button onClick={() => setConfirmDel(c)} className="p-1.5 rounded hover:bg-black/5" title="Eliminar">
                        <Trash2 className="h-4 w-4" style={{ color: theme.danger }} />
                      </button>
                    )}
                  </div>
                )}
              </div>
              <h3 className="font-bold mb-1" style={{ color: theme.text }}>{c.name}</h3>
              <p className="text-sm line-clamp-3 mb-3" style={{ color: theme.textSecondary }}>{c.description}</p>
              <div className="flex items-center gap-3 flex-wrap text-xs">
                <span style={{ color: theme.textSecondary }}>{c.templates_count ?? 0} templates</span>
                {c.is_official && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-semibold text-white" style={{ background: theme.success }}>
                    <ShieldCheck className="h-3 w-3" /> Oficial
                  </span>
                )}
                {c.source_url && (
                  <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:underline" style={{ color: theme.primary }}>
                    <ExternalLink className="h-3 w-3" /> Fuente
                  </a>
                )}
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full text-center py-12 text-sm" style={{ color: theme.textSecondary }}>
              No hay coaches que coincidan.
            </div>
          )}
        </div>
      )}

      <SideModal open={modalOpen} onClose={() => setModalOpen(false)} title={editing?.id ? 'Editar coach' : 'Nuevo coach'}
        footer={
          <>
            <button onClick={() => setModalOpen(false)} className="px-4 py-2 rounded-lg text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }}>Cancelar</button>
            <button onClick={save} className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: theme.primary }}>Guardar</button>
          </>
        }>
        {editing && (
          <div className="space-y-4">
            <Field theme={theme} label="Nombre">
              <input value={editing.name ?? ''} onChange={(e) => setEditing({ ...editing, name: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} placeholder="Tom Ferry, Buffini, ..." />
            </Field>
            <Field theme={theme} label="Descripción">
              <textarea value={editing.description ?? ''} onChange={(e) => setEditing({ ...editing, description: e.target.value })} rows={4}
                className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} />
            </Field>
            <Field theme={theme} label="Foto URL">
              <input value={editing.photo_url ?? ''} onChange={(e) => setEditing({ ...editing, photo_url: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} placeholder="https://..." />
            </Field>
            <Field theme={theme} label="Fuente URL">
              <input value={editing.source_url ?? ''} onChange={(e) => setEditing({ ...editing, source_url: e.target.value })}
                className="w-full px-3 py-2 rounded-lg bg-transparent text-sm" style={{ border: `1px solid ${theme.border}`, color: theme.text }} placeholder="https://tomferry.com/" />
            </Field>
            <label className="flex items-center gap-2 text-sm" style={{ color: theme.text }}>
              <input type="checkbox" checked={!!editing.is_official} onChange={(e) => setEditing({ ...editing, is_official: e.target.checked })} />
              Coach oficial (no puede eliminarse desde la UI)
            </label>
          </div>
        )}
      </SideModal>

      <ConfirmModal isOpen={!!confirmDel} onClose={() => setConfirmDel(null)} onConfirm={remove}
        title="Eliminar coach" message={`¿Eliminar a ${confirmDel?.name}? Sus templates quedarán huérfanos.`}
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
