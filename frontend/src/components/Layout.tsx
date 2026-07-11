import { ReactNode, useState, useEffect, useRef } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Inbox, FileCheck2, Building2, Workflow, Users, Map as MapIcon,
  ClipboardList, FileText, Database, Settings, LogOut, ChevronDown, ChevronLeft, ChevronRight,
  Zap, Target, Layers, GraduationCap, CalendarDays, FileSignature, Bot, MessageSquare,
  Sparkles, Store, TrendingUp, ListChecks, UserCog, Sunrise, type LucideIcon,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { BRAND } from '../config/brand';
import ThemeSelector from './ThemeSelector';
import BrandLogo from './BrandLogo';
import AICoachPanel from './AICoachPanel';
import MobileBottomBar from './MobileBottomBar';

// Vocabulario de roles UNIFICADO de la suite (WO F1-01): admin | supervisor | vendedor.
type Role = 'vendedor' | 'supervisor' | 'admin';

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  badge?: 'unread';
  live?: boolean;
  /** Roles que ven el item. Omitido = todos. */
  roles?: Role[];
}
interface NavModule {
  key: string;
  label: string;
  icon: LucideIcon;
  /** Roles que ven el módulo entero. Omitido = todos. */
  roles?: Role[];
  items: NavItem[];
}

// Items sueltos (sin módulo) — home "Hoy", métricas y asistente, a todos los roles.
// "Hoy" (WO F6-01) es la home accionable: ordena el día. "Métricas" es el
// Dashboard de KPIs, reubicado a vista secundaria (ruta /metricas).
const NAV_TOP: NavItem[] = [
  { to: '/', icon: Sunrise, label: 'Hoy' },
  { to: '/metricas', icon: LayoutDashboard, label: 'Métricas' },
  { to: '/tasador-ai', icon: Sparkles, label: 'Tasador AI' },
];

// La suite se organiza en 5 módulos (WO F4-01).
const NAV_MODULES: NavModule[] = [
  {
    key: 'captar', label: 'Captar', icon: Zap,
    items: [
      { to: '/tasacion-express', icon: Zap, label: 'Tasación express' },
      { to: '/tasaciones', icon: FileCheck2, label: 'Tasaciones' },
      { to: '/estudios', icon: ClipboardList, label: 'Estudios ACM' },
    ],
  },
  {
    key: 'cartera', label: 'Cartera', icon: Building2, roles: ['supervisor', 'admin'],
    items: [
      { to: '/propiedades', icon: Building2, label: 'Propiedades' },
      { to: '/autorizaciones', icon: FileSignature, label: 'Autorizaciones' },
    ],
  },
  {
    key: 'equipo', label: 'Equipo', icon: Users,
    items: [
      { to: '/equipo', icon: UserCog, label: 'Gestión de equipo', roles: ['supervisor', 'admin'] },
      { to: '/dmo', icon: Target, label: 'Mi DMO' },
      { to: '/pipeline', icon: Workflow, label: 'Pipeline de ventas' },
      { to: '/visitas', icon: CalendarDays, label: 'Visitas' },
      { to: '/clientes', icon: Users, label: 'Clientes' },
      { to: '/dmo-templates', icon: Layers, label: 'Templates DMO', roles: ['supervisor', 'admin'] },
      { to: '/dmo-asignaciones', icon: ListChecks, label: 'Asignaciones', roles: ['supervisor', 'admin'] },
      { to: '/coaches', icon: GraduationCap, label: 'Coaches', roles: ['supervisor', 'admin'] },
    ],
  },
  {
    key: 'chat', label: 'Chat', icon: MessageSquare,
    items: [
      { to: '/bandeja', icon: Inbox, label: 'Bandeja', badge: 'unread' },
      { to: '/whatsapp', icon: MessageSquare, label: 'Inbox WhatsApp' },
      { to: '/datos-ia', icon: Bot, label: 'Datos IA · Bot', roles: ['supervisor', 'admin'] },
    ],
  },
  {
    key: 'mercado', label: 'Mercado', icon: Store, roles: ['supervisor', 'admin'],
    items: [
      { to: '/mercado', icon: TrendingUp, label: 'Mercado' },
      { to: '/comparables', icon: Database, label: 'Comparables', live: true },
      { to: '/mapa', icon: MapIcon, label: 'Mapa' },
      { to: '/reportes', icon: FileText, label: 'Reportes' },
    ],
  },
];

// Item suelto inferior — configuración (solo supervisor/admin).
const NAV_BOTTOM: NavItem[] = [
  { to: '/configuracion', icon: Settings, label: 'Configuración', roles: ['supervisor', 'admin'] },
];

const LS_COLLAPSED = 'tasar_sidebar_collapsed';
const LS_MODULES = 'tasar_sidebar_modules';

function roleAllows(roles: Role[] | undefined, userRole?: string): boolean {
  if (!roles || roles.length === 0) return true;
  return !!userRole && (roles as string[]).includes(userRole);
}

/** Items visibles de un módulo según rol. */
function visibleItems(mod: NavModule, role?: string): NavItem[] {
  return mod.items.filter(it => roleAllows(it.roles, role));
}

/** Módulos que el rol puede ver (con al menos un item visible). */
function visibleModules(role?: string): NavModule[] {
  return NAV_MODULES
    .filter(m => roleAllows(m.roles, role))
    .filter(m => visibleItems(m, role).length > 0);
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout, refreshUser } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [availBusy, setAvailBusy] = useState(false);

  const toggleAvailability = async () => {
    setAvailBusy(true);
    try {
      await api.patch('/auth/me', { is_available: !user?.is_available });
      await refreshUser();
    } catch {
      toast.error('No se pudo cambiar tu disponibilidad');
    } finally {
      setAvailBusy(false);
    }
  };
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(LS_COLLAPSED) === '1');
  const [openModules, setOpenModules] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(LS_MODULES);
      if (raw) return JSON.parse(raw) as Record<string, boolean>;
    } catch { /* ignore */ }
    // Default: todos los módulos abiertos.
    return Object.fromEntries(NAV_MODULES.map(m => [m.key, true]));
  });
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const role = user?.role;
  const mods = visibleModules(role);
  const topItems = NAV_TOP.filter(it => roleAllows(it.roles, role));
  const bottomItems = NAV_BOTTOM.filter(it => roleAllows(it.roles, role));

  useEffect(() => {
    localStorage.setItem(LS_COLLAPSED, collapsed ? '1' : '0');
  }, [collapsed]);

  useEffect(() => {
    localStorage.setItem(LS_MODULES, JSON.stringify(openModules));
  }, [openModules]);

  useEffect(() => {
    if (!userMenuOpen) return;
    const h = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) setUserMenuOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [userMenuOpen]);

  const toggleModule = (key: string) => setOpenModules(o => ({ ...o, [key]: !o[key] }));

  const initials = (user?.full_name || '?')
    .split(' ').map(s => s.charAt(0)).slice(0, 2).join('').toUpperCase();

  // En modo colapsado la sidebar aplana todo (sin cabeceras de módulo).
  const flatCollapsedItems: NavItem[] = [
    ...topItems,
    ...mods.flatMap(m => visibleItems(m, role)),
    ...bottomItems,
  ];

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: theme.background }}>
      {/* SIDEBAR (oculto en mobile — reemplazado por bottom bar) */}
      <aside
        className="hidden lg:flex flex-shrink-0 flex-col transition-all duration-300 ease-in-out"
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
                <div className="font-display font-black text-lg leading-none tracking-tight" style={{ color: theme.text }}>{BRAND.name}</div>
                <div className="text-[10px] tracking-wider uppercase mt-0.5" style={{ color: theme.textSecondary }}>{BRAND.tagline}</div>
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
              {/* Disponibilidad para leads (WO F4-05) — el propio usuario la edita;
                  alimenta el round-robin de asignación. */}
              <button onClick={toggleAvailability} disabled={availBusy}
                className="w-full px-4 py-2.5 flex items-center justify-between gap-2 text-sm font-medium transition-all hover:bg-black/5 dark:hover:bg-white/5 disabled:opacity-60"
                style={{ color: theme.text, borderBottom: `1px solid ${theme.border}` }}>
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: user?.is_available ? theme.success : theme.textSecondary }} />
                  Disponible para leads
                </span>
                <span className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{
                    background: user?.is_available ? `${theme.success}18` : theme.backgroundSecondary,
                    color: user?.is_available ? theme.success : theme.textSecondary,
                  }}>
                  {user?.is_available ? 'Sí' : 'No'}
                </span>
              </button>
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
          {collapsed ? (
            flatCollapsedItems.map(item => <NavItemLink key={item.to} item={item} collapsed theme={theme} />)
          ) : (
            <>
              {topItems.map(item => <NavItemLink key={item.to} item={item} collapsed={false} theme={theme} />)}
              {mods.map(mod => (
                <ModuleSection
                  key={mod.key}
                  mod={mod}
                  role={role}
                  open={openModules[mod.key] !== false}
                  onToggle={() => toggleModule(mod.key)}
                  theme={theme}
                />
              ))}
              {bottomItems.length > 0 && (
                <div className="mt-4">
                  {bottomItems.map(item => <NavItemLink key={item.to} item={item} collapsed={false} theme={theme} />)}
                </div>
              )}
            </>
          )}
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
        <header className="flex-shrink-0 h-14 flex items-center justify-between px-4 sm:px-6 gap-3"
          style={{
            background: theme.card,
            borderBottom: `1px solid ${theme.border}`,
            // Header no tapado por status bar/notch/Dynamic Island — base-compartida/11-FIX-VIEWPORT-PWA.md
            paddingTop: 'max(env(safe-area-inset-top), 12px)',
            height: 'calc(3.5rem + max(env(safe-area-inset-top), 12px))',
          }}>
          {/* Logo mobile (sidebar oculta en mobile) */}
          <div className="lg:hidden flex items-center gap-2">
            <BrandLogo variant="icon" className="h-7" />
            <span className="font-display font-black text-lg tracking-tight" style={{ color: theme.text }}>{BRAND.name}</span>
          </div>
          <div className="hidden lg:block" />
          <ThemeSelector />
        </header>
        {/* AI Coach es FAB colapsado por default - no necesita reservar espacio */}
        <main className="flex-1 overflow-y-auto pb-20 lg:pb-0" style={{ background: theme.background }}>
          {children}
        </main>
      </div>

      {/* AI Coach global (desktop) */}
      <AICoachPanel />

      {/* Mobile bottom bar (oculta en lg+) */}
      <MobileBottomBar />
    </div>
  );
}


function ModuleSection({ mod, role, open, onToggle, theme }: {
  mod: NavModule; role?: string; open: boolean; onToggle: () => void; theme: any;
}) {
  const items = visibleItems(mod, role);
  const ModIcon = mod.icon;
  return (
    <div className="mt-3 first:mt-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all duration-200 active:scale-[0.98]"
        style={{ color: theme.textSecondary }}
      >
        <ModIcon className="h-3.5 w-3.5 flex-shrink-0" strokeWidth={2} />
        <span className="flex-1 text-left text-[10px] uppercase tracking-wider font-bold">{mod.label}</span>
        <ChevronDown className={`h-3.5 w-3.5 flex-shrink-0 transition-transform duration-200 ${open ? '' : '-rotate-90'}`} />
      </button>
      {open && (
        <div className="mt-0.5">
          {items.map(item => <NavItemLink key={item.to} item={item} collapsed={false} theme={theme} />)}
        </div>
      )}
    </div>
  );
}


function NavItemLink({ item, collapsed, theme }: { item: NavItem; collapsed: boolean; theme: any }) {
  const { to, icon: Icon, label, live } = item;
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={collapsed ? label : undefined}
      className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 active:scale-[0.98] mb-0.5 ${collapsed ? 'justify-center' : ''}`}
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
