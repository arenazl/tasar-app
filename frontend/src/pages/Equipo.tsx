import { useEffect, useMemo, useState } from 'react';
import {
  Users, UserPlus, Mail, Crown, ShieldCheck, ClipboardList, User as UserIcon, Send, RotateCw,
  XCircle, Power, Loader2, Clock, CircleCheck, type LucideIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { ModernSelect } from '../components/ui/ModernSelect';
import PageHint from '../components/ui/PageHint';
import type { TeamMember, Invitation, TeamRole } from '../types';
import { ROLE_META as ROLE_INFO, STAFF_ROLES, canManageWorkspace } from '../lib/roles';

// Iconos por rol (el resto de la metadata — label/color/desc — viene de lib/roles).
const ROLE_ICON: Record<TeamRole, LucideIcon> = {
  broker: Crown,
  administrador: ShieldCheck,
  coordinador: ClipboardList,
  asesor: UserIcon,
};

const ROLE_META: Record<TeamRole, { label: string; icon: LucideIcon; color: string; desc: string }> =
  STAFF_ROLES.reduce((acc, r) => {
    acc[r] = { ...ROLE_INFO[r], icon: ROLE_ICON[r] };
    return acc;
  }, {} as Record<TeamRole, { label: string; icon: LucideIcon; color: string; desc: string }>);

const ROLE_OPTIONS = STAFF_ROLES.map(r => ({
  value: r, label: ROLE_META[r].label, color: ROLE_META[r].color,
}));

export default function Equipo() {
  const { user, refreshUser } = useAuth();
  const { theme } = useTheme();
  // Gestion de equipo (invitar / cambiar roles / (des)activar) = administrador+
  // (WO F6-06). El coordinador VE el equipo pero no lo gestiona.
  const canManage = canManageWorkspace(user?.role);

  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Formulario de invitación
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState<TeamRole>('asesor');
  const [inviting, setInviting] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      api.get<TeamMember[]>('/team/members'),
      api.get<Invitation[]>('/team/invitations'),
    ])
      .then(([m, i]) => { setMembers(m.data); setInvitations(i.data); })
      .catch((e) => toast.error(e.response?.data?.detail || 'No se pudo cargar el equipo'))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  const pendingInvitations = useMemo(
    () => invitations.filter(i => i.status === 'pendiente'),
    [invitations],
  );

  const invite = async () => {
    const email = inviteEmail.trim().toLowerCase();
    if (!email) { toast.error('Ingresá un email'); return; }
    setInviting(true);
    try {
      await api.post('/team/invitations', {
        email, role: inviteRole, full_name: inviteName.trim() || undefined,
      });
      toast.success(`Invitación enviada a ${email}`);
      setInviteEmail(''); setInviteName(''); setInviteRole('asesor');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo invitar');
    } finally {
      setInviting(false);
    }
  };

  const changeRole = async (m: TeamMember, role: TeamRole) => {
    if (role === m.role) return;
    setBusyId(m.id);
    try {
      const r = await api.patch<TeamMember>(`/team/members/${m.id}`, { role });
      setMembers(list => list.map(x => (x.id === m.id ? r.data : x)));
      toast.success('Rol actualizado');
      if (m.id === user?.id) refreshUser();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo cambiar el rol');
    } finally {
      setBusyId(null);
    }
  };

  const toggleActive = async (m: TeamMember) => {
    setBusyId(m.id);
    try {
      const r = await api.patch<TeamMember>(`/team/members/${m.id}`, { is_active: !m.is_active });
      setMembers(list => list.map(x => (x.id === m.id ? r.data : x)));
      toast.success(r.data.is_active ? 'Miembro activado' : 'Miembro desactivado');
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo cambiar el estado');
    } finally {
      setBusyId(null);
    }
  };

  const toggleOwnAvailability = async (m: TeamMember) => {
    setBusyId(m.id);
    try {
      const r = await api.patch('/auth/me', { is_available: !m.is_available });
      setMembers(list => list.map(x => (x.id === m.id ? { ...x, is_available: r.data.is_available } : x)));
      refreshUser();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo cambiar tu disponibilidad');
    } finally {
      setBusyId(null);
    }
  };

  const resend = async (inv: Invitation) => {
    setBusyId(-inv.id);
    try {
      await api.post(`/team/invitations/${inv.id}/resend`);
      toast.success('Invitación reenviada');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo reenviar');
    } finally {
      setBusyId(null);
    }
  };

  const cancelInvite = async (inv: Invitation) => {
    if (!confirm(`¿Cancelar la invitación a ${inv.email}?`)) return;
    setBusyId(-inv.id);
    try {
      await api.delete(`/team/invitations/${inv.id}`);
      toast.success('Invitación cancelada');
      load();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'No se pudo cancelar');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in">
      <PageHint pageId="equipo" />
      <header className="mb-6">
        <h1 className="text-3xl font-display font-black flex items-center gap-2.5" style={{ color: theme.text }}>
          <Users className="h-7 w-7" style={{ color: theme.primary }} /> Equipo
        </h1>
        <p className="mt-1" style={{ color: theme.textSecondary }}>
          Tasadores y colaboradores del workspace. Invitá por email, asigná roles y gestioná la disponibilidad para leads.
        </p>
      </header>

      {/* Invitar (administrador+) */}
      {canManage && (
        <section className="mb-8 p-5 rounded-2xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="flex items-center gap-2 mb-4">
            <UserPlus className="h-5 w-5" style={{ color: theme.primary }} />
            <h2 className="font-bold text-lg" style={{ color: theme.text }}>Invitar miembro</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-[1fr_1fr_180px_auto] gap-3 items-end">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Email *</div>
              <input type="email" value={inviteEmail} onChange={e => setInviteEmail(e.target.value)}
                placeholder="colega@inmobiliaria.com"
                className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2"
                style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: 16 }} />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Nombre (opcional)</div>
              <input type="text" value={inviteName} onChange={e => setInviteName(e.target.value)}
                placeholder="Nombre y apellido"
                className="w-full px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2"
                style={{ background: theme.backgroundSecondary, color: theme.text, border: `1px solid ${theme.border}`, fontSize: 16 }} />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Rol</div>
              <ModernSelect value={inviteRole} onChange={(v) => setInviteRole(v as TeamRole)} options={ROLE_OPTIONS} />
            </div>
            <button onClick={invite} disabled={inviting}
              className="px-4 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 active:scale-[0.98] disabled:opacity-50"
              style={{ background: theme.primary, color: theme.primaryText }}>
              {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Invitar
            </button>
          </div>
        </section>
      )}

      {/* Miembros */}
      <section className="mb-8">
        <h2 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: theme.textSecondary }}>
          Miembros ({members.length})
        </h2>
        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" style={{ color: theme.primary }} /></div>
        ) : (
          <div className="space-y-2.5">
            {members.map(m => {
              const meta = ROLE_META[m.role] ?? ROLE_META.asesor;
              const RoleIcon = meta.icon;
              const isSelf = m.id === user?.id;
              const busy = busyId === m.id;
              return (
                <div key={m.id} className="p-4 rounded-xl flex flex-col sm:flex-row sm:items-center gap-3"
                  style={{ background: theme.card, border: `1px solid ${theme.border}`, opacity: m.is_active ? 1 : 0.6 }}>
                  <div className="w-11 h-11 rounded-full flex items-center justify-center font-bold flex-shrink-0"
                    style={{ background: `${meta.color}20`, color: meta.color }}>
                    {(m.full_name || m.email).charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-bold truncate" style={{ color: theme.text }}>{m.full_name}</span>
                      {isSelf && <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: `${theme.primary}18`, color: theme.primary }}>Vos</span>}
                      {!m.is_active && <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold" style={{ background: `${theme.danger}18`, color: theme.danger }}>Inactivo</span>}
                    </div>
                    <div className="text-xs flex items-center gap-1.5 truncate" style={{ color: theme.textSecondary }}>
                      <Mail className="h-3 w-3 flex-shrink-0" /> <span className="truncate">{m.email}</span>
                    </div>
                  </div>

                  {/* Disponibilidad para leads (propia editable; ajena solo indicador) */}
                  <button onClick={() => isSelf && toggleOwnAvailability(m)} disabled={!isSelf || busy}
                    title={isSelf ? 'Tu disponibilidad para recibir leads' : 'Disponibilidad para leads'}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold flex-shrink-0"
                    style={{
                      background: m.is_available ? `${theme.success}15` : theme.backgroundSecondary,
                      color: m.is_available ? theme.success : theme.textSecondary,
                      border: `1px solid ${m.is_available ? `${theme.success}40` : theme.border}`,
                      cursor: isSelf ? 'pointer' : 'default',
                    }}>
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: m.is_available ? theme.success : theme.textSecondary }} />
                    {m.is_available ? 'Disponible' : 'No disponible'}
                  </button>

                  {/* Rol: select editable por admin (excepto se enforce en backend); indicador si no */}
                  {canManage ? (
                    <div className="w-44 flex-shrink-0">
                      <ModernSelect value={m.role} onChange={(v) => changeRole(m, v as TeamRole)} options={ROLE_OPTIONS} disabled={busy} />
                    </div>
                  ) : (
                    <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold flex-shrink-0"
                      style={{ background: `${meta.color}15`, color: meta.color }}>
                      <RoleIcon className="h-3.5 w-3.5" /> {meta.label}
                    </span>
                  )}

                  {/* Activar / desactivar (admin, no sobre sí mismo) */}
                  {canManage && !isSelf && (
                    <button onClick={() => toggleActive(m)} disabled={busy}
                      title={m.is_active ? 'Desactivar' : 'Activar'}
                      className="p-2 rounded-lg flex-shrink-0 active:scale-95 disabled:opacity-50"
                      style={{
                        background: m.is_active ? `${theme.danger}12` : `${theme.success}12`,
                        color: m.is_active ? theme.danger : theme.success,
                      }}>
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Power className="h-4 w-4" />}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Invitaciones pendientes */}
      {canManage && pendingInvitations.length > 0 && (
        <section>
          <h2 className="text-xs font-bold uppercase tracking-wider mb-3" style={{ color: theme.textSecondary }}>
            Invitaciones pendientes ({pendingInvitations.length})
          </h2>
          <div className="space-y-2.5">
            {pendingInvitations.map(inv => {
              const meta = ROLE_META[inv.role] ?? ROLE_META.asesor;
              const busy = busyId === -inv.id;
              return (
                <div key={inv.id} className="p-4 rounded-xl flex flex-col sm:flex-row sm:items-center gap-3"
                  style={{ background: theme.card, border: `1px dashed ${theme.border}` }}>
                  <div className="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0"
                    style={{ background: theme.backgroundSecondary }}>
                    <Clock className="h-5 w-5" style={{ color: theme.textSecondary }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="font-bold truncate" style={{ color: theme.text }}>{inv.email}</div>
                    <div className="text-xs" style={{ color: theme.textSecondary }}>
                      Vence: {new Date(inv.expires_at).toLocaleDateString('es-AR')}
                    </div>
                  </div>
                  <span className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-bold flex-shrink-0"
                    style={{ background: `${meta.color}15`, color: meta.color }}>{meta.label}</span>
                  <div className="flex gap-1.5 flex-shrink-0">
                    <button onClick={() => resend(inv)} disabled={busy}
                      className="p-2 rounded-lg active:scale-95 disabled:opacity-50"
                      style={{ background: `${theme.primary}12`, color: theme.primary }} title="Reenviar">
                      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
                    </button>
                    <button onClick={() => cancelInvite(inv)} disabled={busy}
                      className="p-2 rounded-lg active:scale-95 disabled:opacity-50"
                      style={{ background: `${theme.danger}12`, color: theme.danger }} title="Cancelar">
                      <XCircle className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {!loading && members.length > 0 && !canManage && (
        <div className="mt-6 p-4 rounded-xl flex items-center gap-2.5 text-sm"
          style={{ background: theme.backgroundSecondary, color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
          <CircleCheck className="h-4 w-4 flex-shrink-0" style={{ color: theme.success }} />
          Solo un administrador puede invitar miembros o cambiar roles. Podés editar tu propia disponibilidad.
        </div>
      )}
    </div>
  );
}
