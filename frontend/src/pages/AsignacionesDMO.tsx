import { useEffect, useMemo, useState } from 'react';
import { Users, GraduationCap, Star } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import type { DmoTemplate, DmoAssignment, VendorOut } from '../types';
import { isManager } from '../lib/roles';

export default function AsignacionesDMO() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const canEdit = isManager(user?.role);
  const [vendors, setVendors] = useState<VendorOut[]>([]);
  const [templates, setTemplates] = useState<DmoTemplate[]>([]);
  const [assignments, setAssignments] = useState<DmoAssignment[]>([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const [v, t, a] = await Promise.all([
        api.get<VendorOut[]>('/dmo/vendors'),
        api.get<DmoTemplate[]>('/dmo/templates'),
        api.get<DmoAssignment[]>('/dmo/assignments'),
      ]);
      setVendors(v.data);
      setTemplates(t.data.filter((x) => x.is_active));
      setAssignments(a.data);
    } catch {
      toast.error('Error al cargar asignaciones');
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, []);

  const defaultTemplate = useMemo(() => templates.find((t) => t.is_office_default), [templates]);
  const asignByVendor = useMemo(() => {
    const m = new Map<number, DmoAssignment>();
    assignments.forEach((a) => m.set(a.vendor_id, a));
    return m;
  }, [assignments]);

  const assign = async (vendor_id: number, template_id: number | null) => {
    if (!template_id) {
      try {
        await api.delete(`/dmo/assignments/${vendor_id}`);
        toast.success('Asignación eliminada (usará el default)');
        load();
      } catch { toast.error('Error al desasignar'); }
      return;
    }
    try {
      await api.post('/dmo/assignments', { vendor_id, template_id });
      toast.success('Asignación guardada');
      load();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail || 'Error al asignar');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6">
        <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
          <Users className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
          Asignaciones DMO
        </h1>
        <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
          Qué rutina diaria sigue cada vendedor
        </p>
      </header>

      {defaultTemplate && (
        <div className="mb-6 flex items-center gap-3 p-3 rounded-lg" style={{ background: theme.card, border: `1px solid ${theme.primary}` }}>
          <Star className="h-4 w-4 flex-shrink-0" style={{ color: theme.primary }} />
          <div className="text-sm" style={{ color: theme.text }}>
            <span style={{ color: theme.textSecondary }}>Template default de la oficina:</span>{' '}
            <span className="font-semibold">{defaultTemplate.name}</span>{' '}
            <span style={{ color: theme.textSecondary }}>(se usa cuando un vendedor no tiene asignación explícita)</span>
          </div>
        </div>
      )}

      {loading ? (
        <div className="h-64 rounded-xl animate-pulse" style={{ background: theme.card }} />
      ) : (
        <div className="rounded-xl overflow-x-auto" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <table className="w-full text-sm" style={{ minWidth: 680 }}>
            <thead>
              <tr style={{ background: theme.backgroundSecondary }}>
                <th className="text-left px-4 py-3 font-semibold" style={{ color: theme.text }}>Vendedor</th>
                <th className="text-left px-4 py-3 font-semibold" style={{ color: theme.text }}>Coach</th>
                <th className="text-left px-4 py-3 font-semibold" style={{ color: theme.text }}>Template asignado</th>
                <th className="text-left px-4 py-3 font-semibold" style={{ color: theme.text }}>Meta diaria</th>
              </tr>
            </thead>
            <tbody>
              {vendors.map((v) => {
                const a = asignByVendor.get(v.id);
                const currentId = a?.template_id ?? defaultTemplate?.id ?? null;
                const current = templates.find((t) => t.id === currentId);
                return (
                  <tr key={v.id} style={{ borderTop: `1px solid ${theme.border}` }}>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0" style={{ background: theme.primary }}>
                          {v.full_name.slice(0, 2).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold truncate" style={{ color: theme.text }}>{v.full_name}</div>
                          <div className="text-xs truncate" style={{ color: theme.textSecondary }}>{v.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5 text-xs" style={{ color: theme.text }}>
                        <GraduationCap className="h-3.5 w-3.5" style={{ color: theme.textSecondary }} />
                        <span>{current?.coach_name ?? '—'}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <select value={a?.template_id ? String(a.template_id) : ''} disabled={!canEdit}
                        onChange={(e) => assign(v.id, e.target.value ? Number(e.target.value) : null)}
                        className="w-full max-w-xs px-3 py-2 rounded-lg bg-transparent text-sm disabled:opacity-60"
                        style={{ border: `1px solid ${theme.border}`, color: theme.text }}>
                        <option value="">— Usar default —</option>
                        {templates.map((t) => (
                          <option key={t.id} value={t.id}>{t.name}{t.is_office_default ? ' (default)' : ''}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3 text-sm" style={{ color: theme.textSecondary }}>
                      {v.daily_conversations_goal} conv/día
                    </td>
                  </tr>
                );
              })}
              {vendors.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center py-8" style={{ color: theme.textSecondary }}>
                    No hay vendedores cargados en el workspace.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
