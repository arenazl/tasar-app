import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sunrise, MessageSquare, CalendarClock, UserPlus, Flame, Clock, Check,
  ChevronRight, Workflow, Users, CircleDot, AlertCircle, ArrowRight, CheckCircle2,
  type LucideIcon,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useDmoDia, type BlockStatus, type BlockWithStatus } from '../hooks/useDmoDia';
import type { CrmKpis, Visit } from '../types';

// ── Tipos locales (shape de los endpoints ya existentes) ──────────────────────
interface ConvRow {
  id: number;
  contact_name?: string | null;
  assignee_id?: number | null;
  status: string;
  unread_count: number;
  last_message?: string | null;
  last_activity_at?: string | null;
}
interface InboxItem {
  id: number;
  kind: string;
  subject: string;
  preview?: string | null;
  is_read: boolean;
  related_url?: string | null;
  created_at: string;
}
interface VendorRow { id: number; full_name: string }
interface TeamDmo { id: number; name: string; pct: number }

// ── Helpers de fecha ──────────────────────────────────────────────────────────
function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
/** Devuelve 'Hoy' / 'Mañana' si la visita cae en esos días; null si no. */
function visitDayLabel(iso: string): 'Hoy' | 'Mañana' | null {
  const day = ymd(new Date(iso));
  const today = new Date();
  const tomorrow = new Date();
  tomorrow.setDate(today.getDate() + 1);
  if (day === ymd(today)) return 'Hoy';
  if (day === ymd(tomorrow)) return 'Mañana';
  return null;
}
function horaDe(iso: string): string {
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}
function saludo(): string {
  const h = new Date().getHours();
  if (h < 13) return 'Buen día';
  if (h < 20) return 'Buenas tardes';
  return 'Buenas noches';
}

// ── Página ────────────────────────────────────────────────────────────────────
export default function Hoy() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const isManager = user?.role === 'supervisor' || user?.role === 'admin';
  const nombre = user?.full_name?.split(' ')[0] || '';

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
            style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
            <Sunrise className="h-5 w-5" style={{ color: theme.primary }} />
          </div>
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight leading-none" style={{ color: theme.text }}>
              {saludo()}{nombre ? `, ${nombre}` : ''}
            </h1>
            <p className="text-xs sm:text-sm mt-1 capitalize" style={{ color: theme.textSecondary }}>
              {new Date().toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' })}
            </p>
          </div>
        </div>
      </header>

      {isManager ? <HoySupervisor /> : <HoyVendedor />}
    </div>
  );
}

// ══════════════════════════════ VENDEDOR ══════════════════════════════════════
function HoyVendedor() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data, loading: dmoLoading, blockStatuses, doneCount } = useDmoDia();

  const [convs, setConvs] = useState<ConvRow[]>([]);
  const [visits, setVisits] = useState<Visit[]>([]);
  const [leads, setLeads] = useState<InboxItem[]>([]);

  useEffect(() => {
    // Una sola llamada: el backend ya scopea al vendedor (lo suyo + sin asignar).
    api.get<ConvRow[]>('/conversations').then((r) => setConvs(r.data)).catch(() => {});
    api.get<Visit[]>('/visits', { params: { upcoming: true } }).then((r) => setVisits(r.data)).catch(() => {});
    api.get<{ items: InboxItem[] }>('/inbox', { params: { filter: 'unread' } })
      .then((r) => setLeads(r.data.items.filter((i) => i.kind === 'bot_lead'))).catch(() => {});
  }, []);

  // "Esperando": sin asignar (nadie las tomó) + las mías con mensajes sin leer.
  const esperando = useMemo(
    () => convs.filter((c) => c.assignee_id == null || (c.assignee_id === user?.id && c.unread_count > 0)),
    [convs, user?.id],
  );
  const proximasVisitas = useMemo(
    () => visits.filter((v) => visitDayLabel(v.scheduled_at) !== null && v.status === 'agendada')
      .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)),
    [visits],
  );

  return (
    <div className="space-y-4">
      {/* (a) DMO del día — línea horaria compacta */}
      <DmoStrip
        loading={dmoLoading}
        hasTemplate={!!data?.template}
        blockStatuses={blockStatuses}
        doneCount={doneCount}
        total={data?.blocks.length ?? 0}
        completionPct={data?.completion_pct ?? 0}
        onOpen={() => navigate('/dmo')}
      />

      {/* (b) Conversaciones esperando */}
      <SectionCard
        icon={MessageSquare}
        title="Conversaciones esperando"
        count={esperando.length}
        onSeeAll={() => navigate('/whatsapp')}
      >
        {esperando.length === 0 ? (
          <EmptyState text="Al día. No hay conversaciones esperando respuesta." />
        ) : (
          esperando.slice(0, 5).map((c) => (
            <ActionRow
              key={c.id}
              title={c.contact_name || 'Contacto sin nombre'}
              subtitle={c.last_message || (c.assignee_id == null ? 'Sin asignar' : 'Mensajes sin leer')}
              badge={c.assignee_id == null ? 'Nueva' : `${c.unread_count} sin leer`}
              badgeColor={c.assignee_id == null ? theme.warning : theme.primary}
              onClick={() => navigate(`/whatsapp?conv=${c.id}`)}
            />
          ))
        )}
      </SectionCard>

      {/* (c) Próximas visitas (hoy/mañana) */}
      <SectionCard
        icon={CalendarClock}
        title="Próximas visitas"
        count={proximasVisitas.length}
        onSeeAll={() => navigate('/visitas')}
      >
        {proximasVisitas.length === 0 ? (
          <EmptyState text="Sin visitas agendadas para hoy ni mañana." />
        ) : (
          proximasVisitas.slice(0, 5).map((v) => (
            <ActionRow
              key={v.id}
              title={v.property_title || 'Propiedad'}
              subtitle={`${v.client_name || 'Cliente'} · ${horaDe(v.scheduled_at)}`}
              badge={visitDayLabel(v.scheduled_at) || undefined}
              badgeColor={visitDayLabel(v.scheduled_at) === 'Hoy' ? theme.success : theme.info}
              onClick={() => navigate('/visitas')}
            />
          ))
        )}
      </SectionCard>

      {/* (d) Leads nuevos (bandeja, bot_lead sin leer) */}
      <SectionCard
        icon={UserPlus}
        title="Leads nuevos"
        count={leads.length}
        onSeeAll={() => navigate('/bandeja')}
      >
        {leads.length === 0 ? (
          <EmptyState text="Sin leads nuevos del bot por ahora." />
        ) : (
          leads.slice(0, 5).map((l) => (
            <ActionRow
              key={l.id}
              title={l.subject}
              subtitle={l.preview || 'Nuevo lead derivado por el bot'}
              badge="Lead"
              badgeColor={theme.primary}
              onClick={() => navigate(l.related_url || '/bandeja')}
            />
          ))
        )}
      </SectionCard>
    </div>
  );
}

// ══════════════════════════════ SUPERVISOR / ADMIN ════════════════════════════
function HoySupervisor() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [kpis, setKpis] = useState<CrmKpis | null>(null);
  const [sinTomar, setSinTomar] = useState<ConvRow[]>([]);
  const [visits, setVisits] = useState<Visit[]>([]);
  const [teamDmo, setTeamDmo] = useState<TeamDmo[] | null>(null);

  useEffect(() => {
    api.get<CrmKpis>('/dashboard/crm').then((r) => setKpis(r.data)).catch(() => {});
    api.get<ConvRow[]>('/conversations', { params: { filter: 'sin_asignar' } })
      .then((r) => setSinTomar(r.data)).catch(() => {});
    api.get<Visit[]>('/visits', { params: { upcoming: true } }).then((r) => setVisits(r.data)).catch(() => {});
    // Pulso DMO del equipo: no existe endpoint agregado "DMO de hoy del equipo",
    // así que se resuelve con lo que YA existe — vendedores + su /dmo/dia. Fan-out
    // acotado (una oficina tiene pocos vendedores); es la vista de manager, no el
    // camino caliente del mobile. Ver reporte del WO.
    (async () => {
      try {
        const vendors = (await api.get<VendorRow[]>('/dmo/vendors')).data;
        const rows = await Promise.all(
          vendors.map(async (v) => {
            try {
              const d = (await api.get<{ completion_pct: number }>('/dmo/dia', { params: { vendor_id: v.id } })).data;
              return { id: v.id, name: v.full_name, pct: d.completion_pct ?? 0 } as TeamDmo;
            } catch {
              return { id: v.id, name: v.full_name, pct: 0 } as TeamDmo;
            }
          }),
        );
        setTeamDmo(rows.sort((a, b) => b.pct - a.pct));
      } catch {
        setTeamDmo([]);
      }
    })();
  }, []);

  const visitasHoyEquipo = useMemo(
    () => visits.filter((v) => visitDayLabel(v.scheduled_at) === 'Hoy')
      .sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)),
    [visits],
  );
  const dmoCompletos = teamDmo?.filter((t) => t.pct >= 100).length ?? 0;

  return (
    <div className="space-y-4">
      {/* Pulso del equipo */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <PulseStat icon={CheckCircle2} label="DMO completo hoy"
          value={teamDmo ? `${dmoCompletos}/${teamDmo.length}` : '—'} color={theme.success} onClick={() => navigate('/dmo-asignaciones')} />
        <PulseStat icon={MessageSquare} label="Conversaciones hoy"
          value={kpis ? `${kpis.conversations_today}/${kpis.conversations_goal}` : '—'} color={theme.primary} onClick={() => navigate('/whatsapp')} />
        <PulseStat icon={CalendarClock} label="Visitas hoy (equipo)"
          value={String(visitasHoyEquipo.length)} color={theme.info} onClick={() => navigate('/visitas')} />
        <PulseStat icon={Workflow} label="Deals abiertos"
          value={kpis ? String(kpis.open_deals) : '—'} color={theme.warning} onClick={() => navigate('/pipeline')} />
      </div>

      {/* Conversaciones derivadas sin tomar */}
      <SectionCard
        icon={MessageSquare}
        title="Derivadas sin tomar"
        count={sinTomar.length}
        onSeeAll={() => navigate('/whatsapp')}
      >
        {sinTomar.length === 0 ? (
          <EmptyState text="Todo tomado. Ninguna conversación quedó sin asignar." />
        ) : (
          sinTomar.slice(0, 5).map((c) => (
            <ActionRow
              key={c.id}
              title={c.contact_name || 'Contacto sin nombre'}
              subtitle={c.last_message || 'Esperando que alguien la tome'}
              badge="Sin asignar"
              badgeColor={theme.warning}
              onClick={() => navigate(`/whatsapp?conv=${c.id}`)}
            />
          ))
        )}
      </SectionCard>

      {/* Visitas del día del equipo */}
      <SectionCard
        icon={CalendarClock}
        title="Visitas del día"
        count={visitasHoyEquipo.length}
        onSeeAll={() => navigate('/visitas')}
      >
        {visitasHoyEquipo.length === 0 ? (
          <EmptyState text="Sin visitas del equipo agendadas para hoy." />
        ) : (
          visitasHoyEquipo.slice(0, 6).map((v) => (
            <ActionRow
              key={v.id}
              title={v.property_title || 'Propiedad'}
              subtitle={`${v.client_name || 'Cliente'} · ${v.vendor_name || ''} · ${horaDe(v.scheduled_at)}`}
              badge="Hoy"
              badgeColor={theme.success}
              onClick={() => navigate('/visitas')}
            />
          ))
        )}
      </SectionCard>

      {/* Quién completó su DMO hoy */}
      <SectionCard icon={Users} title="DMO del equipo hoy" onSeeAll={() => navigate('/dmo-asignaciones')}>
        {teamDmo == null ? (
          <EmptyState text="Cargando el pulso del equipo…" />
        ) : teamDmo.length === 0 ? (
          <EmptyState text="No hay vendedores con DMO asignado." />
        ) : (
          teamDmo.map((t) => (
            <div key={t.id} className="flex items-center gap-3 py-2">
              <span className="flex-1 truncate text-sm font-medium" style={{ color: theme.text }}>{t.name}</span>
              <div className="w-28 h-2 rounded-full overflow-hidden" style={{ background: theme.backgroundSecondary }}>
                <div className="h-full rounded-full transition-all"
                  style={{ width: `${Math.min(100, t.pct)}%`, background: t.pct >= 100 ? theme.success : theme.primary }} />
              </div>
              <span className="text-xs font-semibold tabular-nums w-10 text-right" style={{ color: theme.textSecondary }}>{t.pct}%</span>
            </div>
          ))
        )}
      </SectionCard>
    </div>
  );
}

// ══════════════════════════════ DMO strip (vendedor) ══════════════════════════
function DmoStrip({ loading, hasTemplate, blockStatuses, doneCount, total, completionPct, onOpen }: {
  loading: boolean;
  hasTemplate: boolean;
  blockStatuses: BlockWithStatus[];
  doneCount: number;
  total: number;
  completionPct: number;
  onOpen: () => void;
}) {
  const { theme } = useTheme();
  const statusColor: Record<BlockStatus, string> = {
    done: theme.success,
    now: theme.primary,
    pending: theme.textSecondary,
    overdue: theme.danger,
  };

  if (loading) {
    return <div className="h-28 rounded-2xl animate-pulse" style={{ background: theme.card }} />;
  }
  if (!hasTemplate) {
    return (
      <button onClick={onOpen}
        className="w-full text-left rounded-2xl p-4 flex items-center gap-3 transition-all active:scale-[0.99]"
        style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <AlertCircle className="h-5 w-5 flex-shrink-0" style={{ color: theme.warning }} />
        <div className="flex-1 min-w-0">
          <div className="font-bold text-sm" style={{ color: theme.text }}>Todavía no tenés un DMO asignado</div>
          <div className="text-xs" style={{ color: theme.textSecondary }}>Tocá para ver cómo pedirlo a tu supervisor.</div>
        </div>
        <ChevronRight className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
      </button>
    );
  }

  return (
    <button onClick={onOpen}
      className="w-full text-left rounded-2xl p-4 transition-all active:scale-[0.99]"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" style={{ color: theme.primary }} />
          <span className="font-bold text-sm" style={{ color: theme.text }}>Tu día</span>
          <span className="text-xs" style={{ color: theme.textSecondary }}>· {doneCount}/{total} bloques · {completionPct}%</span>
        </div>
        <span className="flex items-center gap-1 text-xs font-semibold" style={{ color: theme.primary }}>
          Ver DMO <ArrowRight className="h-3.5 w-3.5" />
        </span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1" style={{ scrollbarWidth: 'none' }}>
        {blockStatuses.map(({ block: b, status }) => {
          const color = statusColor[status];
          const isNow = status === 'now';
          return (
            <div key={b.id}
              className="flex-shrink-0 rounded-xl px-3 py-2 min-w-[7.5rem]"
              style={{
                background: isNow ? `${color}15` : theme.backgroundSecondary,
                border: `1px solid ${isNow ? color : 'transparent'}`,
              }}>
              <div className="flex items-center gap-1.5 mb-1">
                {status === 'done'
                  ? <Check className="h-3.5 w-3.5" style={{ color }} />
                  : b.is_money_block
                    ? <Flame className="h-3.5 w-3.5" style={{ color: isNow ? color : theme.danger }} />
                    : <CircleDot className="h-3.5 w-3.5" style={{ color }} />}
                <span className="text-[10px] font-mono font-semibold" style={{ color: theme.textSecondary }}>
                  {b.start_time.slice(0, 5)}
                </span>
              </div>
              <div className="text-xs font-semibold leading-tight truncate" style={{ color: isNow ? theme.text : theme.textSecondary }}>
                {b.name}
              </div>
              <div className="text-[10px] font-bold uppercase tracking-wide mt-0.5" style={{ color }}>
                {status === 'done' ? 'Hecho' : status === 'now' ? 'En curso' : status === 'overdue' ? 'Vencido' : 'Pendiente'}
              </div>
            </div>
          );
        })}
      </div>
    </button>
  );
}

// ══════════════════════════════ UI compartida ═════════════════════════════════
function SectionCard({ icon: Icon, title, count, onSeeAll, children }: {
  icon: LucideIcon;
  title: string;
  count?: number;
  onSeeAll?: () => void;
  children: React.ReactNode;
}) {
  const { theme } = useTheme();
  return (
    <section className="rounded-2xl p-4" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" style={{ color: theme.primary }} />
          <h2 className="font-bold text-sm" style={{ color: theme.text }}>{title}</h2>
          {count != null && count > 0 && (
            <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-full"
              style={{ background: `${theme.primary}18`, color: theme.primary }}>{count}</span>
          )}
        </div>
        {onSeeAll && (
          <button onClick={onSeeAll} className="text-xs font-semibold flex items-center gap-0.5" style={{ color: theme.textSecondary }}>
            Ver todo <ChevronRight className="h-3.5 w-3.5" />
          </button>
        )}
      </div>
      <div className="divide-y" style={{ borderColor: theme.border }}>{children}</div>
    </section>
  );
}

function ActionRow({ title, subtitle, badge, badgeColor, onClick }: {
  title: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
  onClick: () => void;
}) {
  const { theme } = useTheme();
  return (
    <button onClick={onClick}
      className="w-full flex items-center gap-3 py-2.5 text-left transition-all active:scale-[0.99] first:pt-1">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold truncate" style={{ color: theme.text }}>{title}</div>
        {subtitle && <div className="text-xs truncate" style={{ color: theme.textSecondary }}>{subtitle}</div>}
      </div>
      {badge && (
        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0"
          style={{ background: `${badgeColor || theme.primary}18`, color: badgeColor || theme.primary }}>
          {badge}
        </span>
      )}
      <ChevronRight className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
    </button>
  );
}

function EmptyState({ text }: { text: string }) {
  const { theme } = useTheme();
  return (
    <div className="flex items-center gap-2 py-3 text-sm" style={{ color: theme.textSecondary }}>
      <CheckCircle2 className="h-4 w-4 flex-shrink-0" style={{ color: theme.success }} />
      {text}
    </div>
  );
}

function PulseStat({ icon: Icon, label, value, color, onClick }: {
  icon: LucideIcon;
  label: string;
  value: string;
  color: string;
  onClick: () => void;
}) {
  const { theme } = useTheme();
  return (
    <button onClick={onClick}
      className="rounded-2xl p-3 text-left transition-all active:scale-[0.98]"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="w-8 h-8 rounded-lg flex items-center justify-center mb-2" style={{ background: `${color}18` }}>
        <Icon className="h-4 w-4" style={{ color }} />
      </div>
      <div className="text-xl font-black tabular-nums leading-none" style={{ color: theme.text }}>{value}</div>
      <div className="text-[11px] mt-1 leading-tight" style={{ color: theme.textSecondary }}>{label}</div>
    </button>
  );
}
