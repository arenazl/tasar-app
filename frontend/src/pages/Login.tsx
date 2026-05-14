import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Loader2, Shield, Eye, User as UserIcon, ArrowRight, Sparkles,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import BrandLogo from '../components/BrandLogo';
import { useTheme } from '../contexts/ThemeContext';

const PROFILES = [
  {
    email: 'admin@tasar.demo', password: 'admin123',
    label: 'Admin', desc: 'Acceso total',
    icon: Shield, gradient: 'from-blue-500 via-blue-600 to-indigo-700',
    initials: 'LA',
  },
  {
    email: 'supervisor@tasar.demo', password: 'supervisor123',
    label: 'Supervisor', desc: 'Revisión + firmas',
    icon: Eye, gradient: 'from-violet-500 via-purple-600 to-fuchsia-700',
    initials: 'PS',
  },
  {
    email: 'vendedor@tasar.demo', password: 'vendedor123',
    label: 'Vendedor', desc: 'Carga + ACM',
    icon: UserIcon, gradient: 'from-emerald-500 via-green-600 to-teal-700',
    initials: 'BV',
  },
];

export default function Login() {
  const { login } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@tasar.demo');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [hoveredProfile, setHoveredProfile] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      navigate('/');
      toast.success('Bienvenido a TasAR');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Error de login');
    } finally {
      setLoading(false);
    }
  };

  const quickLogin = async (p: typeof PROFILES[number]) => {
    setLoading(true);
    setEmail(p.email);
    setPassword(p.password);
    try {
      await login(p.email, p.password);
      navigate('/');
      toast.success(`Bienvenido — ${p.label}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Error de login');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center px-6 py-12"
      style={{ background: theme.background }}>
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <BrandLogo variant="topbar" className="h-12" />
        </div>

        {/* Card */}
        <div className="rounded-3xl shadow-xl p-8"
          style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-3"
              style={{ background: `${theme.primary}15` }}>
              <Sparkles className="h-6 w-6" style={{ color: theme.primary }} />
            </div>
            <h2 className="text-2xl font-black tracking-tight" style={{ color: theme.text }}>Bienvenido</h2>
            <p className="text-sm mt-1" style={{ color: theme.textSecondary }}>
              Elegí tu perfil o usá email + contraseña
            </p>
          </div>

          {/* 3 perfiles demo */}
          <div className="grid grid-cols-3 gap-2 mb-6">
            {PROFILES.map(p => {
              const Icon = p.icon;
              const isHover = hoveredProfile === p.email;
              return (
                <button
                  key={p.email}
                  type="button"
                  onClick={() => quickLogin(p)}
                  onMouseEnter={() => setHoveredProfile(p.email)}
                  onMouseLeave={() => setHoveredProfile(null)}
                  disabled={loading}
                  className="group relative flex flex-col items-center p-3 rounded-2xl transition-all duration-300 active:scale-95 disabled:opacity-50 overflow-hidden"
                  style={{
                    background: theme.backgroundSecondary,
                    border: `1px solid ${theme.border}`,
                  }}
                >
                  <div className={`absolute inset-0 bg-gradient-to-br ${p.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
                  <div className={`relative w-14 h-14 rounded-full bg-gradient-to-br ${p.gradient} shadow-lg flex items-center justify-center mb-2 transition-all duration-300 ${isHover ? 'scale-110 -rotate-6' : ''}`}>
                    <span className="text-white font-black text-base">{p.initials}</span>
                    <div className={`absolute -bottom-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center shadow-md transition-all duration-300 ${isHover ? 'scale-125' : ''}`}
                      style={{ background: theme.card }}>
                      <Icon className="h-3 w-3" style={{ color: theme.primary }} />
                    </div>
                  </div>
                  <div className="relative text-xs font-bold" style={{ color: theme.text }}>{p.label}</div>
                  <div className="relative text-[10px] text-center leading-tight mt-0.5" style={{ color: theme.textSecondary }}>{p.desc}</div>
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 h-px" style={{ background: theme.border }} />
            <span className="text-[10px] uppercase tracking-widest font-bold" style={{ color: theme.textSecondary }}>
              o con email
            </span>
            <div className="flex-1 h-px" style={{ background: theme.border }} />
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required
                className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 transition-all"
                style={{ background: theme.backgroundSecondary, color: theme.text, borderColor: theme.border }} />
            </div>
            <div>
              <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Contraseña</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 transition-all"
                style={{ background: theme.backgroundSecondary, color: theme.text, borderColor: theme.border }} />
            </div>
            <button type="submit" disabled={loading}
              className="group w-full py-3.5 rounded-xl font-bold tracking-wide shadow-lg transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
              style={{
                background: theme.primary, color: theme.primaryText,
                boxShadow: `0 6px 20px ${theme.primary}55`,
              }}>
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : (
                <>
                  <span>Ingresar</span>
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: theme.textSecondary }}>
            ¿Sin cuenta? <Link to="/register" className="font-bold hover:underline" style={{ color: theme.primary }}>Crear workspace</Link>
          </p>
        </div>

        {/* Status badge abajo */}
        <div className="mt-6 flex items-center justify-center gap-3 text-xs" style={{ color: theme.textSecondary }}>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: theme.success }} />
            Sistema operativo
          </span>
          <span className="w-1 h-1 rounded-full" style={{ background: theme.border }} />
          <span>SSL · JWT 24h</span>
        </div>
      </div>
    </div>
  );
}
