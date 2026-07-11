import type { LucideIcon } from 'lucide-react';
import { Sunrise, MessageSquare, Users, Workflow, Zap } from 'lucide-react';
import type { StaffRole } from '../lib/roles';

// Tour de primer día (WO F6-05) — guiado sobre el mismo mecanismo visual que
// PageHint (banner con acento del theme activo, wizard con puntos + Siguiente),
// pero CROSS-PAGE: cada paso vive en una pantalla distinta y el botón
// "Siguiente" navega + avanza. Recorre el circuito completo de trabajo:
// Hoy -> Chat -> Clientes -> Pipeline -> Tasar (mismo orden que documenta el WO).
export interface TourStep {
  /** Ruta a la que navega "Siguiente" para llegar a este paso. */
  route: string;
  /** Label corto para el botón "Siguiente: {navLabel}". */
  navLabel: string;
  icon: LucideIcon;
  title: string;
  /** El cuerpo varía según jerarquia del rol (broker/administrador ven el
   * ángulo "equipo", coordinador/asesor el ángulo "operativo del día"). */
  body: (role?: StaffRole | string) => string;
}

const isLead = (role?: StaffRole | string) => role === 'broker' || role === 'administrador';

export const FIRST_DAY_TOUR_STEPS: TourStep[] = [
  {
    route: '/',
    navLabel: 'Hoy',
    icon: Sunrise,
    title: 'Así arranca tu día',
    body: (role) => isLead(role)
      ? '"Hoy" te muestra el pulso del equipo: qué DMO se está cumpliendo, leads sin asignar y las visitas del día. Es tu primera parada, siempre.'
      : '"Hoy" ordena tu jornada: tu DMO, las conversaciones que están esperando respuesta y tus visitas agendadas. Es tu primera parada, siempre.',
  },
  {
    route: '/whatsapp',
    navLabel: 'Chat',
    icon: MessageSquare,
    title: 'Todo el chat en un solo lugar',
    body: () => 'Las conversaciones de WhatsApp entran acá. Respondé vos, asigná a un colega o dejá que el bot atienda mientras estás en una visita.',
  },
  {
    route: '/clientes',
    navLabel: 'Clientes',
    icon: Users,
    title: 'La ficha de cada cliente',
    body: () => 'Cada cliente tiene una ficha con historial completo: chat, visitas, operaciones y tasaciones en una sola línea de tiempo.',
  },
  {
    route: '/pipeline',
    navLabel: 'Pipeline',
    icon: Workflow,
    title: 'El circuito de una operación',
    body: (role) => isLead(role)
      ? 'Arrastrá cada operación por las 6 etapas legales, de captación a escrituración. De un vistazo ves dónde se traba el equipo y qué falta cerrar para facturar.'
      : 'Arrastrá cada operación por las 6 etapas legales, de captación a escrituración. Vas a ver cuánto falta para cerrar y cobrar tu comisión.',
  },
  {
    route: '/tasacion-express',
    navLabel: 'Tasar',
    icon: Zap,
    title: 'Tasá en 30 segundos',
    body: () => 'Cuando necesites un número rápido para un cliente nuevo, Tasación express te da un valor anclado a comparables reales del mercado — nada inventado.',
  },
];

const DONE_PREFIX = 'tasar_first_day_tour_done_';
const STEP_PREFIX = 'tasar_first_day_tour_step_';

export function tourDoneKey(userId: number | string): string {
  return `${DONE_PREFIX}${userId}`;
}
export function tourStepKey(userId: number | string): string {
  return `${STEP_PREFIX}${userId}`;
}

/** Evento custom para que FirstDayTour se re-evalúe al reabrirse desde
 * Configuración (mismo patrón que 'municipio-changed' en PageHint.tsx). */
export const FIRST_DAY_TOUR_RESET_EVENT = 'first-day-tour-reset';
