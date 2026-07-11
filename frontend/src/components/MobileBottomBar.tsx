import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  MessageSquare, Users, Workflow, Sunrise, Plus, LogOut,
  Building2, FileCheck2, ClipboardList, Store, Database, FileText, Settings,
  Map as MapIcon, Zap, UserPlus, CalendarPlus, FileSignature, type LucideIcon,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useState } from 'react';
import { hasMinRole, type StaffRole } from '../lib/roles';

interface SheetItem {
  to: string;
  icon: LucideIcon;
  label: string;
  /** Nivel minimo de la jerarquia que ve el item (WO F6-06). Omitido = todos. */
  minRole?: StaffRole;
}

// Tabs primarios (esqueleto fijo en mobile, WO F6-04): Hoy · Chat · FAB · Pipeline · Clientes.
const TABS_LEFT = [
  { to: '/', icon: Sunrise, label: 'Hoy' },
  { to: '/whatsapp', icon: MessageSquare, label: 'Chat' },
];
const TABS_RIGHT = [
  { to: '/pipeline', icon: Workflow, label: 'Pipeline' },
  { to: '/clientes', icon: Users, label: 'Clientes' },
];

// Acciones rápidas del FAB (WO F6-04) — navegan a la superficie de creación
// correspondiente (no abren modales nuevos: sin features nuevas).
const QUICK_ACTIONS: { to: string; icon: LucideIcon; label: string }[] = [
  { to: '/tasacion-express', icon: Zap, label: 'Tasación express' },
  { to: '/clientes', icon: UserPlus, label: 'Nuevo cliente' },
  { to: '/visitas', icon: CalendarPlus, label: 'Nueva visita' },
];

// Sheet "Más" — el resto de las pantallas fuera de los tabs, filtradas por rol.
// Equipo/DMO/Bot/Métricas viven dentro de Configuración; Mi DMO se abre desde Hoy.
const MORE_ITEMS: SheetItem[] = [
  { to: '/propiedades', icon: Building2, label: 'Propiedades' },
  { to: '/tasaciones', icon: FileCheck2, label: 'Tasaciones' },
  { to: '/estudios', icon: ClipboardList, label: 'Estudios ACM' },
  { to: '/autorizaciones', icon: FileSignature, label: 'Autorizaciones', minRole: 'coordinador' },
  { to: '/mercado', icon: Store, label: 'Mercado', minRole: 'coordinador' },
  { to: '/comparables', icon: Database, label: 'Comparables', minRole: 'coordinador' },
  { to: '/mapa', icon: MapIcon, label: 'Mapa', minRole: 'coordinador' },
  { to: '/reportes', icon: FileText, label: 'Reportes', minRole: 'coordinador' },
  { to: '/configuracion', icon: Settings, label: 'Configuración', minRole: 'coordinador' },
];

function roleAllows(minRole: StaffRole | undefined, userRole?: string): boolean {
  if (!minRole) return true;
  return hasMinRole(userRole, minRole);
}

export default function MobileBottomBar() {
  const { theme } = useTheme();
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [moreOpen, setMoreOpen] = useState(false);

  if (location.pathname === '/login') return null;

  const initials = (user?.full_name || '?')
    .split(' ').map(s => s.charAt(0)).slice(0, 2).join('').toUpperCase();

  const go = (to: string) => { setMoreOpen(false); navigate(to); };
  const sheetItems = MORE_ITEMS.filter(it => roleAllows(it.minRole, user?.role));

  return (
    <>
      <nav
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 flex items-stretch"
        style={{
          background: theme.card,
          borderTop: `1px solid ${theme.border}`,
          paddingBottom: 'env(safe-area-inset-bottom)',
          boxShadow: '0 -8px 24px -12px rgba(0,0,0,0.15)',
        }}
      >
        {TABS_LEFT.map(({ to, icon: Icon, label }) => (
          <TabLink key={to} to={to} Icon={Icon} label={label} theme={theme} />
        ))}

        {/* FAB central elevado — abre el sheet de acciones + navegación */}
        <div className="flex-1 flex items-start justify-center relative">
          <button
            onClick={() => setMoreOpen(o => !o)}
            aria-label="Acciones y más"
            className="absolute w-14 h-14 rounded-full flex items-center justify-center active:scale-90"
            style={{
              background: theme.primary,
              color: theme.primaryText || '#fff',
              boxShadow: `0 8px 24px -4px ${theme.primary}80, 0 4px 12px -2px rgba(0,0,0,0.2)`,
              border: `3px solid ${theme.card}`,
              top: moreOpen ? '-32px' : '-24px',
              transform: moreOpen ? 'rotate(45deg) scale(1.05)' : 'rotate(0deg) scale(1)',
              transition: 'top 300ms cubic-bezier(0.34, 1.56, 0.64, 1), transform 300ms cubic-bezier(0.34, 1.56, 0.64, 1), background 200ms',
            }}
          >
            <Plus className="h-6 w-6" strokeWidth={2.4} />
          </button>
          <span className="absolute bottom-1.5 text-[10px] font-semibold uppercase tracking-wider"
            style={{ color: theme.textSecondary }}>Crear</span>
        </div>

        {TABS_RIGHT.map(({ to, icon: Icon, label }) => (
          <TabLink key={to} to={to} Icon={Icon} label={label} theme={theme} />
        ))}
      </nav>

      {/* Bottom sheet: acciones rápidas + "Más" */}
      {moreOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setMoreOpen(false)}
          />
          <div
            className="lg:hidden fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl animate-in slide-in-from-bottom duration-300 max-h-[80vh] overflow-y-auto"
            style={{
              background: theme.card,
              borderTop: `1px solid ${theme.border}`,
              paddingBottom: 'calc(env(safe-area-inset-bottom) + 16px)',
            }}
          >
            <div className="flex justify-center py-3">
              <span className="w-12 h-1.5 rounded-full" style={{ background: theme.border }} />
            </div>

            {/* User header */}
            <div className="px-5 pb-4 flex items-center gap-3" style={{ borderBottom: `1px solid ${theme.border}` }}>
              <div className="w-11 h-11 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
                style={{ background: theme.text, color: theme.background }}>{initials}</div>
              <div className="min-w-0 flex-1">
                <div className="font-bold truncate" style={{ color: theme.text }}>{user?.full_name}</div>
                <div className="text-xs capitalize truncate" style={{ color: theme.textSecondary }}>{user?.role}</div>
              </div>
              <button
                onClick={() => { setMoreOpen(false); logout(); navigate('/login'); }}
                className="w-10 h-10 rounded-full flex items-center justify-center transition-all active:scale-90"
                style={{ background: `${theme.danger}15`, color: theme.danger }}
                aria-label="Cerrar sesión"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>

            {/* Acciones rápidas */}
            <div className="px-5 pt-4">
              <div className="text-[10px] uppercase tracking-wider font-bold mb-2.5" style={{ color: theme.textSecondary }}>
                Crear
              </div>
              <div className="grid grid-cols-3 gap-2">
                {QUICK_ACTIONS.map(({ to, icon: Icon, label }) => (
                  <button
                    key={to}
                    onClick={() => go(to)}
                    className="flex flex-col items-center justify-center gap-2 p-3 rounded-2xl transition-all active:scale-95"
                    style={{ background: `${theme.primary}12`, border: `1px solid ${theme.primary}25` }}
                  >
                    <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
                      style={{ background: theme.primary, color: theme.primaryText || '#fff' }}>
                      <Icon className="h-5 w-5" strokeWidth={2.1} />
                    </div>
                    <span className="text-[11px] font-semibold text-center leading-tight" style={{ color: theme.primary }}>
                      {label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Más — navegación */}
            <div className="px-5 pt-5 pb-1">
              <div className="text-[10px] uppercase tracking-wider font-bold mb-2.5" style={{ color: theme.textSecondary }}>
                Ir a
              </div>
            </div>
            <div className="px-4 pb-5 grid grid-cols-3 gap-2">
              {sheetItems.map(({ to, icon: Icon, label }) => {
                const active = location.pathname === to;
                return (
                  <button
                    key={to}
                    onClick={() => go(to)}
                    className="flex flex-col items-center justify-center gap-2 p-3 rounded-2xl transition-all active:scale-95"
                    style={{
                      background: active ? `${theme.primary}15` : theme.backgroundSecondary,
                      border: `1px solid ${active ? theme.primary + '40' : 'transparent'}`,
                    }}
                  >
                    <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
                      style={{
                        background: active ? theme.primary : theme.card,
                        color: active ? (theme.primaryText || '#fff') : theme.text,
                      }}>
                      <Icon className="h-5 w-5" strokeWidth={active ? 2.2 : 1.8} />
                    </div>
                    <span className="text-[11px] font-semibold text-center leading-tight"
                      style={{ color: active ? theme.primary : theme.text }}>
                      {label}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </>
  );
}

function TabLink({ to, Icon, label, theme }: { to: string; Icon: LucideIcon; label: string; theme: any }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className="flex-1 flex flex-col items-center justify-center gap-1 py-2 transition-all active:scale-95 relative"
      style={({ isActive }) => ({
        color: isActive ? theme.primary : theme.textSecondary,
      })}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <span className="absolute top-0 w-10 h-0.5 rounded-b-full"
              style={{ background: theme.primary }} />
          )}
          <Icon className="h-5 w-5" strokeWidth={isActive ? 2.4 : 1.8} />
          <span className="text-[10px] font-semibold uppercase tracking-wider"
            style={{ fontWeight: isActive ? 700 : 500 }}>
            {label}
          </span>
        </>
      )}
    </NavLink>
  );
}
