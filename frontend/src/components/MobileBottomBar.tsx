import { NavLink, useLocation } from 'react-router-dom';
import { Inbox, FileCheck2, MapIcon, Sparkles, User } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useState } from 'react';

/**
 * Bottom tab bar para mobile. Visible solo <lg breakpoint.
 * Reemplaza a la sidebar (oculta en mobile) para navegación core.
 * Cinco slots: Bandeja, Tasaciones, Mercado, AI Coach, Perfil.
 */
const TABS = [
  { to: '/bandeja', icon: Inbox, label: 'Bandeja' },
  { to: '/tasaciones', icon: FileCheck2, label: 'Tasaciones' },
  { to: '/mercado', icon: MapIcon, label: 'Mercado' },
  { to: '/tasador-ai', icon: Sparkles, label: 'AI' },
];

export default function MobileBottomBar() {
  const { theme } = useTheme();
  const { user } = useAuth();
  const location = useLocation();
  const [profileMenuOpen, setProfileMenuOpen] = useState(false);

  // No mostrar en /login
  if (location.pathname === '/login') return null;

  const initials = (user?.full_name || '?')
    .split(' ').map(s => s.charAt(0)).slice(0, 2).join('').toUpperCase();

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
        {TABS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className="flex-1 flex flex-col items-center justify-center gap-1 py-2 transition-all active:scale-95"
            style={({ isActive }) => ({
              color: isActive ? theme.primary : theme.textSecondary,
            })}
          >
            {({ isActive }) => (
              <>
                <Icon className="h-5 w-5" strokeWidth={isActive ? 2.4 : 1.8} />
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{
                  fontWeight: isActive ? 700 : 500,
                }}>
                  {label}
                </span>
                {isActive && (
                  <span className="absolute top-0 w-10 h-0.5 rounded-b-full"
                    style={{ background: theme.primary }} />
                )}
              </>
            )}
          </NavLink>
        ))}

        {/* Slot perfil */}
        <button
          onClick={() => setProfileMenuOpen(o => !o)}
          className="flex-1 flex flex-col items-center justify-center gap-1 py-2 transition-all active:scale-95 relative"
          style={{ color: profileMenuOpen ? theme.primary : theme.textSecondary }}
        >
          <div className="w-6 h-6 rounded-full flex items-center justify-center font-bold text-[10px]"
            style={{ background: theme.text, color: theme.background }}>
            {initials}
          </div>
          <span className="text-[10px] font-semibold uppercase tracking-wider">Perfil</span>
        </button>
      </nav>

      {/* Profile sheet (mobile bottom-sheet style) */}
      {profileMenuOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 z-40 bg-black/40 animate-in fade-in"
            onClick={() => setProfileMenuOpen(false)}
          />
          <div
            className="lg:hidden fixed bottom-0 left-0 right-0 z-50 rounded-t-2xl pb-20 animate-in slide-in-from-bottom duration-200"
            style={{ background: theme.card, borderTop: `1px solid ${theme.border}` }}
          >
            <div className="flex justify-center py-2.5">
              <span className="w-10 h-1 rounded-full" style={{ background: theme.border }} />
            </div>
            <div className="px-5 pb-3">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-full flex items-center justify-center font-bold"
                  style={{ background: theme.text, color: theme.background }}>{initials}</div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold truncate" style={{ color: theme.text }}>{user?.full_name}</div>
                  <div className="text-xs truncate" style={{ color: theme.textSecondary }}>{user?.email}</div>
                </div>
              </div>
              <nav className="flex flex-col">
                <a href="/propiedades" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Propiedades</a>
                <a href="/pipeline" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Pipeline</a>
                <a href="/clientes" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Clientes</a>
                <a href="/comparables" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Comparables</a>
                <a href="/reportes" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Reportes</a>
                <a href="/configuracion" className="px-3 py-3 rounded-lg text-sm font-medium" style={{ color: theme.text }}>Configuración</a>
              </nav>
            </div>
          </div>
        </>
      )}
    </>
  );
}
