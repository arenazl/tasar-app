import { ReactNode, useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Inbox, FileCheck2, Building2, Workflow, Users, Map as MapIcon,
  ClipboardList, FileText, Database, Settings, LogOut, ChevronDown, ChevronLeft, ChevronRight,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import ThemeSelector from './ThemeSelector';
import BrandLogo from './BrandLogo';
import AICoachPanel from './AICoachPanel';

const NAV_TRABAJO = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/bandeja', icon: Inbox, label: 'Bandeja', badge: 'unread' as const },
  { to: '/tasaciones', icon: FileCheck2, label: 'Tasaciones' },
  { to: '/propiedades', icon: Building2, label: 'Propiedades' },
  { to: '/pipeline', icon: Workflow, label: 'Pipeline' },
  { to: '/clientes', icon: Users, label: 'Clientes' },
  { to: '/mercado', icon: MapIcon, label: 'Mercado' },
  { to: '/estudios', icon: ClipboardList, label: 'Estudios' },
  { to: '/reportes', icon: FileText, label: 'Reportes' },
];
const NAV_DATOS = [
  { to: '/comparables', icon: Database, label: 'Comparables', live: true },
  { to: '/configuracion', icon: Settings, label: 'Configuración' },
];

const LS_COLLAPSED = 'tasar_sidebar_collapsed';

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(LS_COLLAPSED) === '1');
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(LS_COLLAPSED, collapsed ? '1' : '0');
  }, [collapsed]);

  useEffect(() => {
    if (!userMenuOpen) return;
    const h = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setUserMenuOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [userMenuOpen]);

  const initials = (user?.full_name || '?')
    .split(' ').map(s => s.charAt(0)).slice(0, 2).join('').toUpperCase();

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: theme.background }}>
      {/* SIDEBAR */}
      <aside
        className="flex-shrink-0 flex flex-col transition-all duration-300 ease-in-out"
        style={{
          width: collapsed ? '76px' : '240px',
          background: theme.card,
          borderRight: `1px solid ${theme.border}`,
        }}
      >
        {/* Logo */}
        <div className="flex-shrink-0 px-4 pt-5 pb-4 flex items-center justify-center"
          style={{ borderBottom: `1px solid ${theme.border}` }}>
          {collapsed ? (
            <BrandLogo variant="icon" className="h-7" />
          ) : (
            <div className="flex items-center gap-2.5 w-full">
              <BrandLogo variant="icon" className="h-8 flex-shrink-0" />
              <div className="min-w-0">
                <div className="font-display font-black text-lg leading-none tracking-tight" style={{ color: theme.text }}>TasAR</div>
                <div className="text-[10px] tracking-wider uppercase mt-0.5" style={{ color: theme.textSecondary }}>Mapa de valor</div>
              </div>
            </div>
          )}
        </div>

        {/* User selector */}
        <div className="flex-shrink-0 px-3 pt-3 pb-2 relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen(o => !o)}
            className="w-full flex items-center gap-2.5 p-2 rounded-xl transition-all duration-200 active:scale-[0.98]"
            style={{
              background: userMenuOpen ? theme.backgroundSecondary : 'transparent',
              border: `1px solid ${userMenuOpen ? theme.border : 'transparent'}`,
            }}>
            <div className="w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
              style={{ background: theme.text, color: theme.background }}>{initials}</div>
            {!collapsed && (
              <>
                <div className="flex-1 min-w-0 text-left">
                  <div className="font-bold text-sm truncate" style={{ color: theme.text }}>
                    {user?.full_name?.split(' ').slice(0, 2).join(' ')}
                  </div>
                  <div className="text-xs capitalize truncate" style={{ color: theme.textSecondary }}>{user?.role}</div>
                </div>
                <ChevronDown className={`h-4 w-4 flex-shrink-0 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`}
                  style={{ color: theme.textSecondary }} />
              </>
            )}
          </button>
          {userMenuOpen && (
            <div className="absolute left-3 right-3 top-full mt-1 rounded-xl shadow-2xl z-50 overflow-hidden"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div className="px-4 py-3" style={{ borderBottom: `1px solid ${theme.border}` }}>
                <div className="text-xs" style={{ color: theme.textSecondary }}>Sesión iniciada como</div>
                <div className="font-semibold text-sm mt-0.5 truncate" style={{ color: theme.text }}>{user?.email}</div>
              </div>
              <button onClick={() => { logout(); navigate('/login'); }}
                className="w-full px-4 py-2.5 flex items-center gap-2 text-sm font-medium transition-all hover:bg-black/5 dark:hover:bg-white/5"
                style={{ color: theme.danger }}>
                <LogOut className="h-4 w-4" /> Cerrar sesión
              </button>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 min-h-0 overflow-y-auto px-3 pb-3">
          {!collapsed && <SectionLabel theme={theme}>Trabajo</SectionLabel>}
          {NAV_TRABAJO.map(item => <NavItem key={item.to} item={item} collapsed={collapsed} theme={theme} />)}
          {!collapsed && <SectionLabel theme={theme} className="mt-4">Datos</SectionLabel>}
          {NAV_DATOS.map(item => <NavItem key={item.to} item={item} collapsed={collapsed} theme={theme} />)}
        </nav>

        {/* Collapse button */}
        <div className="flex-shrink-0 p-3" style={{ borderTop: `1px solid ${theme.border}` }}>
          <button onClick={() => setCollapsed(c => !c)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95"
            style={{ background: theme.backgroundSecondary, color: theme.textSecondary, border: `1px solid ${theme.border}` }}
            title={collapsed ? 'Expandir' : 'Colapsar'}>
            {collapsed ? <ChevronRight className="h-4 w-4" /> : (<><ChevronLeft className="h-4 w-4" /><span>Colapsar</span></>)}
          </button>
        </div>
      </aside>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex-shrink-0 h-14 flex items-center justify-end px-6 gap-3"
          style={{ background: theme.card, borderBottom: `1px solid ${theme.border}` }}>
          <ThemeSelector />
        </header>
        <main className="flex-1 overflow-y-auto" style={{ background: theme.background }}>
          {children}
        </main>
      </div>

      {/* AI Coach global */}
      <AICoachPanel />
    </div>
  );
}


function SectionLabel({ theme, children, className = '' }: any) {
  return (
    <div className={`text-[10px] uppercase tracking-wider font-bold mb-1.5 mt-2 px-3 ${className}`}
      style={{ color: theme.textSecondary }}>
      {children}
    </div>
  );
}


function NavItem({ item, collapsed, theme }: any) {
  const { to, icon: Icon, label, badge, live } = item;
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={collapsed ? label : undefined}
      className={({ isActive }) =>
        `relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 active:scale-[0.98] mb-0.5 ${collapsed ? 'justify-center' : ''}`
      }
      style={({ isActive }) => ({
        background: isActive ? theme.text : 'transparent',
        color: isActive ? theme.background : theme.textSecondary,
      })}
    >
      {({ isActive }) => (
        <>
          <Icon className="h-[18px] w-[18px] flex-shrink-0" strokeWidth={isActive ? 2.2 : 1.8} />
          {!collapsed && (
            <>
              <span className="flex-1 truncate" style={{ fontWeight: isActive ? 700 : 500 }}>{label}</span>
              {live && (
                <span className="text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase tracking-wide"
                  style={{ background: '#22c55e20', color: '#22c55e' }}>
                  live
                </span>
              )}
              {isActive && !live && (
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: theme.background }} />
              )}
            </>
          )}
          {collapsed && isActive && (
            <span className="absolute -right-1 top-1/2 -translate-y-1/2 w-1 h-6 rounded-l-full"
              style={{ background: theme.primary }} />
          )}
        </>
      )}
    </NavLink>
  );
}
