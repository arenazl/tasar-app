import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Inbox, FileCheck2, Map as MapIcon, Sparkles, LayoutGrid,
  LayoutDashboard, Building2, Workflow, Users, ClipboardList, FileText, Database, Settings, LogOut,
} from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useState } from 'react';

const TABS_LEFT = [
  { to: '/bandeja', icon: Inbox, label: 'Bandeja' },
  { to: '/tasaciones', icon: FileCheck2, label: 'Tasaciones' },
];
const TABS_RIGHT = [
  { to: '/mercado', icon: MapIcon, label: 'Mercado' },
  { to: '/tasador-ai', icon: Sparkles, label: 'AI' },
];

const MORE_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/propiedades', icon: Building2, label: 'Propiedades' },
  { to: '/pipeline', icon: Workflow, label: 'Pipeline' },
  { to: '/clientes', icon: Users, label: 'Clientes' },
  { to: '/estudios', icon: ClipboardList, label: 'Estudios' },
  { to: '/reportes', icon: FileText, label: 'Reportes' },
  { to: '/comparables', icon: Database, label: 'Comparables' },
  { to: '/configuracion', icon: Settings, label: 'Configuración' },
];

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

        {/* FAB central elevado */}
        <div className="flex-1 flex items-start justify-center relative">
          <button
            onClick={() => setMoreOpen(o => !o)}
            aria-label="Más opciones"
            className="absolute -top-6 w-14 h-14 rounded-full flex items-center justify-center transition-all active:scale-90 duration-200"
            style={{
              background: theme.primary,
              color: theme.primaryText || '#fff',
              boxShadow: `0 8px 24px -4px ${theme.primary}80, 0 4px 12px -2px rgba(0,0,0,0.2)`,
              border: `3px solid ${theme.card}`,
              transform: moreOpen ? 'rotate(45deg)' : 'rotate(0deg)',
            }}
          >
            <LayoutGrid className="h-6 w-6" strokeWidth={2.2} />
          </button>
          <span className="absolute bottom-1.5 text-[10px] font-semibold uppercase tracking-wider"
            style={{ color: theme.textSecondary }}>Más</span>
        </div>

        {TABS_RIGHT.map(({ to, icon: Icon, label }) => (
          <TabLink key={to} to={to} Icon={Icon} label={label} theme={theme} />
        ))}
      </nav>

      {/* Bottom sheet "Más" */}
      {moreOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 z-40 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
            onClick={() => setMoreOpen(false)}
          />
          <div
            className="lg:hidden fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl animate-in slide-in-from-bottom duration-300"
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

            {/* Grid 3-cols */}
            <div className="px-4 py-5 grid grid-cols-3 gap-2">
              {MORE_ITEMS.map(({ to, icon: Icon, label }) => {
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

function TabLink({ to, Icon, label, theme }: any) {
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
