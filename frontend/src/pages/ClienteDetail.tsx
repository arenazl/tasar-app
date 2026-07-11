import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, Phone, Mail, MapPin, Building2, User as UserIcon, Flame, Snowflake,
  Thermometer, CalendarDays, Briefcase, MessageSquare, FileCheck2, Target,
  ArrowRight, Zap, Send, Inbox, MessageCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

// ==== Tipos del endpoint agregador GET /api/clients/{id}/timeline (WO F6-02) ====
type EventKind = 'mensaje' | 'visita' | 'deal' | 'tasacion';

interface TimelineEvent {
  kind: EventKind;
  ref_id: number;
  ts: string | null;
  title: string | null;
  subtitle: string | null;
  status: string | null;
  amount: number | null;
  currency: string | null;
}

interface NextStep {
  code: 'recontactar' | 'agendar_visita' | 'abrir_deal' | 'avanzar_etapa' | 'al_dia';
  label: string;
  reason: string;
  action_type: 'navigate' | 'chat' | 'wa' | 'none';
  target: string | null;
}

interface ClientTimeline {
  id: number;
  name: string;
  type?: string | null;
  contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  tax_id?: string | null;
  notes?: string | null;
  lead_status?: string | null;
  temperature?: string | null;
  origin?: string | null;
  assigned_to?: number | null;
  assigned_to_name?: string | null;
  pref_zona?: string | null;
  pref_m2_min?: number | null;
  pref_m2_max?: number | null;
  pref_ambientes?: number | null;
  pref_budget_min?: number | null;
  pref_budget_max?: number | null;
  pref_currency?: string | null;
  last_contact_at?: string | null;
  created_at?: string | null;
  visits_count: number;
  deals_count: number;
  conversations_count: number;
  appraisals_count: number;
  messages_count: number;
  primary_conversation_id?: number | null;
  next_step: NextStep;
  timeline: TimelineEvent[];
}

const LEAD_META: Record<string, { label: string; color: string }> = {
  nuevo: { label: 'Nuevo', color: '#64748b' },
  contactado: { label: 'Contactado', color: '#3b82f6' },
  calificado: { label: 'Calificado', color: '#8b5cf6' },
  cita: { label: 'Con cita', color: '#f59e0b' },
  propuesta: { label: 'Propuesta', color: '#ec4899' },
  cerrado: { label: 'Cerrado', color: '#22c55e' },
  perdido: { label: 'Perdido', color: '#ef4444' },
};

const VISIT_META: Record<string, { label: string; color: string }> = {
  agendada: { label: 'Agendada', color: '#3b82f6' },
  concretada: { label: 'Concretada', color: '#22c55e' },
  cancelada: { label: 'Cancelada', color: '#ef4444' },
  ausente: { label: 'Ausente', color: '#f59e0b' },
};

const STAGE_META: Record<string, { label: string; color: string }> = {
  captado: { label: 'Captado', color: '#64748b' },
  publicado: { label: 'Publicado', color: '#3b82f6' },
  visita: { label: 'Visita', color: '#8b5cf6' },
  reserva: { label: 'Reserva', color: '#f59e0b' },
  boleto: { label: 'Boleto', color: '#ec4899' },
  escrituracion: { label: 'Escrituración', color: '#22c55e' },
};

function digitsOnly(phone?: string | null): string {
  return (phone || '').replace(/\D/g, '');
}

function fmtDate(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short', year: 'numeric' })
    + ' · ' + d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}

function fmtMoney(amount: number | null, currency: string | null): string {
  if (amount == null) return '';
  const cur = currency || 'USD';
  try {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency: cur, maximumFractionDigits: 0 }).format(amount);
  } catch {
    return `${cur} ${Math.round(amount).toLocaleString('es-AR')}`;
  }
}

export default function ClienteDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const [data, setData] = useState<ClientTimeline | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    api.get<ClientTimeline>(`/clients/${id}/timeline`)
      .then(r => setData(r.data))
      .catch((e) => {
        toast.error(e.response?.status === 404 ? 'Cliente no encontrado' : 'Error al cargar la ficha');
        navigate('/clientes');
      })
      .finally(() => setLoading(false));
  }, [id, navigate]);

  const waHref = useMemo(() => {
    const d = digitsOnly(data?.phone);
    return d ? `https://wa.me/${d}` : null;
  }, [data?.phone]);

  const runNextStep = (ns: NextStep) => {
    if (ns.action_type === 'navigate' || ns.action_type === 'chat') {
      if (!ns.target) return;
      // Las rutas de alta (visitas/pipeline) reciben ?cliente= para pre-cargar el
      // cliente actual en el formulario (WO F6-03). El chat ya trae ?conv=.
      let target = ns.target;
      if (data && (target === '/visitas' || target === '/pipeline')) {
        target = `${target}?cliente=${data.id}`;
      }
      navigate(target);
    } else if (ns.action_type === 'wa') {
      if (waHref) window.open(waHref, '_blank', 'noopener');
      else toast.info('Este cliente no tiene teléfono cargado');
    }
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 max-w-screen-lg mx-auto">
        <div className="animate-pulse space-y-4">
          <div className="h-32 rounded-2xl" style={{ background: theme.card }} />
          <div className="h-24 rounded-2xl" style={{ background: theme.card }} />
          <div className="h-64 rounded-2xl" style={{ background: theme.card }} />
        </div>
      </div>
    );
  }
  if (!data) return null;

  const lead = LEAD_META[data.lead_status || 'nuevo'] || { label: data.lead_status || '—', color: theme.textSecondary };
  const tempColor = data.temperature === 'caliente' ? '#ef4444' : data.temperature === 'tibio' ? '#f59e0b' : '#3b82f6';
  const TempIcon = data.temperature === 'caliente' ? Flame : data.temperature === 'frio' ? Snowflake : Thermometer;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-lg mx-auto animate-fade-in space-y-4">
      {/* Volver */}
      <button onClick={() => navigate('/clientes')}
        className="flex items-center gap-1.5 text-sm font-semibold active:scale-95 transition-all"
        style={{ color: theme.primary }}>
        <ArrowLeft className="h-4 w-4" /> Clientes
      </button>

      {/* Cabecera */}
      <div className="rounded-2xl p-5" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0"
            style={{ background: `${theme.primary}18` }}>
            <Building2 className="h-7 w-7" style={{ color: theme.primary }} />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-2xl font-display font-black tracking-tight truncate" style={{ color: theme.text }}>
              {data.name}
            </h1>
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <Badge label={lead.label} color={lead.color} />
              {data.temperature && (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
                  style={{ background: `${tempColor}18`, color: tempColor }}>
                  <TempIcon className="h-3 w-3" /> {data.temperature}
                </span>
              )}
              {data.origin && (
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold"
                  style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                  Origen: {data.origin}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Datos de contacto + vendedor */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4">
          {data.phone && (
            <div className="flex items-center gap-2 text-sm" style={{ color: theme.text }}>
              <Phone className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
              <span className="truncate">{data.phone}</span>
              {waHref && (
                <a href={waHref} target="_blank" rel="noopener noreferrer"
                  className="ml-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-xs font-bold active:scale-95"
                  style={{ background: '#25D36618', color: '#128C4B' }}>
                  <MessageCircle className="h-3 w-3" /> WhatsApp
                </a>
              )}
            </div>
          )}
          {data.email && (
            <div className="flex items-center gap-2 text-sm truncate" style={{ color: theme.text }}>
              <Mail className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
              <span className="truncate">{data.email}</span>
            </div>
          )}
          {data.address && (
            <div className="flex items-center gap-2 text-sm truncate" style={{ color: theme.text }}>
              <MapPin className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
              <span className="truncate">{data.address}</span>
            </div>
          )}
          {data.assigned_to_name && (
            <div className="flex items-center gap-2 text-sm" style={{ color: theme.text }}>
              <UserIcon className="h-4 w-4 flex-shrink-0" style={{ color: theme.textSecondary }} />
              <span className="truncate">Asignado a {data.assigned_to_name}</span>
            </div>
          )}
        </div>

        {/* Conteos */}
        <div className="flex flex-wrap gap-4 mt-4 pt-4" style={{ borderTop: `1px solid ${theme.border}` }}>
          <Stat icon={<CalendarDays className="h-4 w-4" />} value={data.visits_count} label="visitas" theme={theme} />
          <Stat icon={<Briefcase className="h-4 w-4" />} value={data.deals_count} label="operaciones" theme={theme} />
          <Stat icon={<MessageSquare className="h-4 w-4" />} value={data.conversations_count} label="chats" theme={theme} />
          {data.appraisals_count > 0 && (
            <Stat icon={<FileCheck2 className="h-4 w-4" />} value={data.appraisals_count} label="tasaciones" theme={theme} />
          )}
        </div>
      </div>

      {/* Siguiente paso */}
      {data.next_step.code !== 'al_dia' ? (
        <div className="rounded-2xl p-5" style={{ background: `${theme.primary}0d`, border: `1px solid ${theme.primary}40` }}>
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${theme.primary}20` }}>
              <Target className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[11px] font-bold uppercase tracking-wider" style={{ color: theme.primary }}>Siguiente paso</div>
              <div className="text-lg font-bold mt-0.5" style={{ color: theme.text }}>{data.next_step.label}</div>
              <div className="text-sm mt-0.5" style={{ color: theme.textSecondary }}>{data.next_step.reason}</div>
            </div>
            <button onClick={() => runNextStep(data.next_step)}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-bold active:scale-95 transition-all flex-shrink-0"
              style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
              {data.next_step.label} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl p-4 flex items-center gap-2 text-sm"
          style={{ background: theme.card, border: `1px solid ${theme.border}`, color: theme.textSecondary }}>
          <Target className="h-4 w-4" style={{ color: theme.success }} /> {data.next_step.reason}
        </div>
      )}

      {/* Acciones rapidas */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <QuickAction icon={<CalendarDays className="h-4 w-4" />} label="Agendar visita" onClick={() => navigate(`/visitas?cliente=${data.id}`)} theme={theme} />
        <QuickAction icon={<Briefcase className="h-4 w-4" />} label="Abrir operación" onClick={() => navigate(`/pipeline?cliente=${data.id}`)} theme={theme} />
        <QuickAction icon={<Zap className="h-4 w-4" />} label="Tasación express" onClick={() => navigate(`/tasacion-express?cliente=${data.id}`)} theme={theme} />
        <QuickAction
          icon={<MessageSquare className="h-4 w-4" />}
          label="Abrir chat"
          disabled={!data.primary_conversation_id}
          onClick={() => data.primary_conversation_id && navigate(`/whatsapp?conv=${data.primary_conversation_id}`)}
          theme={theme}
        />
      </div>

      {/* Preferencias de busqueda */}
      {(data.pref_zona || data.pref_ambientes || data.pref_m2_min || data.pref_budget_min || data.pref_budget_max) && (
        <div className="rounded-2xl p-5" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="text-[11px] font-bold uppercase tracking-wider mb-3" style={{ color: theme.textSecondary }}>
            Preferencias de búsqueda
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {data.pref_zona && <Pref label="Zona" value={data.pref_zona} theme={theme} />}
            {data.pref_ambientes != null && <Pref label="Ambientes" value={String(data.pref_ambientes)} theme={theme} />}
            {(data.pref_m2_min || data.pref_m2_max) && (
              <Pref label="Superficie" value={`${data.pref_m2_min || '?'}–${data.pref_m2_max || '?'} m²`} theme={theme} />
            )}
            {(data.pref_budget_min || data.pref_budget_max) && (
              <Pref label="Presupuesto"
                value={`${fmtMoney(data.pref_budget_min ?? null, data.pref_currency ?? 'USD') || '?'} – ${fmtMoney(data.pref_budget_max ?? null, data.pref_currency ?? 'USD') || '?'}`}
                theme={theme} />
            )}
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="rounded-2xl p-5" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
        <div className="text-[11px] font-bold uppercase tracking-wider mb-4" style={{ color: theme.textSecondary }}>
          Historial ({data.timeline.length})
        </div>
        {data.timeline.length === 0 ? (
          <div className="text-center py-8 text-sm" style={{ color: theme.textSecondary }}>
            Todavía no hay actividad registrada para este cliente.
          </div>
        ) : (
          <div className="space-y-0">
            {data.timeline.map((e, i) => (
              <TimelineRow key={`${e.kind}-${e.ref_id}-${i}`} event={e} theme={theme} last={i === data.timeline.length - 1} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span className="px-2.5 py-1 rounded-full text-xs font-bold" style={{ background: `${color}18`, color }}>
      {label}
    </span>
  );
}

function Stat({ icon, value, label, theme }: { icon: React.ReactNode; value: number; label: string; theme: any }) {
  return (
    <div className="flex items-center gap-2">
      <span style={{ color: theme.primary }}>{icon}</span>
      <span className="text-sm" style={{ color: theme.text }}>
        <span className="font-bold">{value}</span> <span style={{ color: theme.textSecondary }}>{label}</span>
      </span>
    </div>
  );
}

function QuickAction({ icon, label, onClick, theme, disabled }: {
  icon: React.ReactNode; label: string; onClick: () => void; theme: any; disabled?: boolean;
}) {
  return (
    <button onClick={onClick} disabled={disabled}
      className="flex flex-col items-center justify-center gap-1.5 py-3 px-2 rounded-xl text-xs font-semibold transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
      style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}`, color: theme.text }}>
      <span style={{ color: theme.primary }}>{icon}</span>
      {label}
    </button>
  );
}

function Pref({ label, value, theme }: { label: string; value: string; theme: any }) {
  return (
    <div>
      <div className="text-[11px]" style={{ color: theme.textSecondary }}>{label}</div>
      <div className="text-sm font-semibold" style={{ color: theme.text }}>{value}</div>
    </div>
  );
}

function TimelineRow({ event, theme, last }: { event: TimelineEvent; theme: any; last: boolean }) {
  const { icon, color, heading, badge } = describeEvent(event, theme);
  return (
    <div className="flex gap-3">
      {/* Rail */}
      <div className="flex flex-col items-center">
        <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: `${color}18`, color }}>
          {icon}
        </div>
        {!last && <div className="w-px flex-1 my-1" style={{ background: theme.border }} />}
      </div>
      {/* Contenido */}
      <div className="pb-4 min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold" style={{ color: theme.text }}>{heading}</span>
          {badge && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={{ background: `${badge.color}18`, color: badge.color }}>
              {badge.label}
            </span>
          )}
        </div>
        {event.title && event.kind !== 'mensaje' && (
          <div className="text-sm truncate mt-0.5" style={{ color: theme.textSecondary }}>{event.title}</div>
        )}
        {event.kind === 'mensaje' && event.title && (
          <div className="text-sm mt-0.5 line-clamp-2" style={{ color: theme.textSecondary }}>{event.title}</div>
        )}
        {event.amount != null && (
          <div className="text-sm font-bold mt-0.5" style={{ color: theme.text }}>{fmtMoney(event.amount, event.currency)}</div>
        )}
        {event.kind === 'visita' && event.subtitle && event.subtitle !== 'sin_resultado' && (
          <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>Resultado: {event.subtitle}</div>
        )}
        <div className="text-[11px] mt-1" style={{ color: theme.textSecondary }}>{fmtDate(event.ts)}</div>
      </div>
    </div>
  );
}

function describeEvent(event: TimelineEvent, theme: any): {
  icon: React.ReactNode; color: string; heading: string; badge?: { label: string; color: string };
} {
  switch (event.kind) {
    case 'visita': {
      const m = VISIT_META[event.status || ''] || { label: event.status || '', color: theme.textSecondary };
      return { icon: <CalendarDays className="h-4 w-4" />, color: '#3b82f6', heading: 'Visita', badge: m };
    }
    case 'deal': {
      const m = STAGE_META[event.status || ''] || { label: event.status || '', color: theme.textSecondary };
      return { icon: <Briefcase className="h-4 w-4" />, color: '#8b5cf6', heading: 'Operación', badge: m };
    }
    case 'tasacion': {
      return {
        icon: <FileCheck2 className="h-4 w-4" />, color: '#f59e0b', heading: 'Tasación',
        badge: event.status ? { label: event.status, color: '#f59e0b' } : undefined,
      };
    }
    case 'mensaje':
    default: {
      const inbound = event.status === 'inbound';
      return {
        icon: inbound ? <Inbox className="h-4 w-4" /> : <Send className="h-4 w-4" />,
        color: inbound ? '#22c55e' : theme.primary,
        heading: inbound ? 'Mensaje recibido' : 'Mensaje enviado',
      };
    }
  }
}
