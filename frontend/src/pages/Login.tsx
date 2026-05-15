import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Loader2, Shield, Eye, User as UserIcon, ArrowRight, Sparkles, TrendingUp, Database, Zap,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import BrandLogo from '../components/BrandLogo';
import { useTheme } from '../contexts/ThemeContext';

const PROFILES = [
  { email: 'admin@tasar.demo', password: 'admin123', label: 'Admin', desc: 'Acceso total', icon: Shield, initials: 'LA' },
  { email: 'supervisor@tasar.demo', password: 'supervisor123', label: 'Supervisor', desc: 'Revisión + firmas', icon: Eye, initials: 'PS' },
  { email: 'vendedor@tasar.demo', password: 'vendedor123', label: 'Vendedor', desc: 'Carga + ACM', icon: UserIcon, initials: 'BV' },
];

export default function Login() {
  const { login } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [email, setEmail] = useState('admin@tasar.demo');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);

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
    <div className="min-h-screen w-full flex flex-col lg:flex-row" style={{ background: theme.background }}>
      {/* IZQUIERDA — Hero estilo landing (oculto en mobile) */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-[55%] flex-col justify-between p-10 xl:p-14 relative overflow-hidden"
        style={{ background: theme.card, borderRight: `1px solid ${theme.border}` }}>
        {/* Blob decorativo */}
        <div className="absolute top-0 right-0 w-[600px] h-[600px] rounded-full blur-3xl opacity-10 pointer-events-none"
          style={{ background: theme.primary, transform: 'translate(30%, -30%)' }} />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] rounded-full blur-3xl opacity-[0.06] pointer-events-none"
          style={{ background: theme.primary, transform: 'translate(-20%, 30%)' }} />

        {/* Top: brand */}
        <div className="relative flex items-center gap-3">
          <BrandLogo variant="icon" className="h-10" />
          <div>
            <div className="font-display font-black text-2xl tracking-tight" style={{ color: theme.text }}>TasAR</div>
            <div className="text-[10px] uppercase tracking-[0.2em] font-bold" style={{ color: theme.textSecondary }}>Mapa de valor</div>
          </div>
        </div>

        {/* Centro: hero */}
        <div className="relative max-w-xl">
          <div className="text-[11px] font-bold uppercase tracking-[0.25em] mb-5" style={{ color: theme.textSecondary }}>
            Mayo 2026 · Reporte #047
          </div>
          <h1 className="font-display font-black tracking-tight leading-[0.95] mb-6 text-[44px] xl:text-[60px]"
            style={{ color: theme.text }}>
            El mercado<br />inmobiliario,<br />
            <span style={{ color: theme.primary }}>en datos.</span>
          </h1>
          <p className="text-base xl:text-lg leading-relaxed max-w-md" style={{ color: theme.textSecondary }}>
            TasAR procesa millones de avisos, escrituras y permisos al mes
            para darte el precio real de cada zona, edificio y tipología.
            Sin opiniones. Sin "estimaciones".
          </p>

          {/* 3 features */}
          <div className="mt-8 grid grid-cols-3 gap-3 max-w-md">
            <Stat icon={Database} value="2.1M" label="Avisos" theme={theme} />
            <Stat icon={TrendingUp} value="48 hs" label="Update" theme={theme} />
            <Stat icon={Zap} value="IA" label="Tasador" theme={theme} />
          </div>
        </div>

        {/* Bottom: footer status */}
        <div className="relative flex items-center gap-3 text-xs" style={{ color: theme.textSecondary }}>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: theme.success }} />
            Sistema operativo
          </span>
          <span className="w-1 h-1 rounded-full" style={{ background: theme.border }} />
          <span>SSL · JWT 24h</span>
          <span className="w-1 h-1 rounded-full" style={{ background: theme.border }} />
          <span>{new Date().getFullYear()} TasAR</span>
        </div>
      </div>

      {/* DERECHA — Formulario */}
      <div className="flex-1 flex items-center justify-center p-5 sm:p-8 lg:p-12">
        <div className="w-full max-w-md">
          {/* Logo mobile (en desktop ya está a la izquierda) */}
          <div className="lg:hidden flex justify-center mb-6">
            <BrandLogo variant="topbar" className="h-10" />
          </div>

          <div className="mb-7">
            <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl mb-3"
              style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
              <Sparkles className="h-5 w-5" style={{ color: theme.primary }} />
            </div>
            <h2 className="text-3xl font-display font-black tracking-tight" style={{ color: theme.text }}>Bienvenido</h2>
            <p className="text-sm mt-1.5" style={{ color: theme.textSecondary }}>
              Elegí tu perfil o usá email + contraseña
            </p>
          </div>

          {/* 3 perfiles demo — pills compactas */}
          <div className="grid grid-cols-3 gap-2 mb-6">
            {PROFILES.map(p => {
              const Icon = p.icon;
              return (
                <button
                  key={p.email}
                  type="button"
                  onClick={() => quickLogin(p)}
                  disabled={loading}
                  className="group relative flex flex-col items-center p-3 rounded-xl transition-all duration-200 active:scale-95 disabled:opacity-50"
                  style={{
                    background: theme.card,
                    border: `1px solid ${theme.border}`,
                  }}
                >
                  <div className="w-10 h-10 rounded-full flex items-center justify-center mb-1.5 transition-all group-hover:scale-110"
                    style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
                    <Icon className="h-4 w-4" style={{ color: theme.primary }} />
                  </div>
                  <div className="text-xs font-bold" style={{ color: theme.text }}>{p.label}</div>
                  <div className="text-[10px] text-center leading-tight mt-0.5" style={{ color: theme.textSecondary }}>{p.desc}</div>
                </button>
              );
            })}
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 my-5">
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
                style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: '16px' }} />
            </div>
            <div>
              <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Contraseña</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required
                className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 transition-all"
                style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: '16px' }} />
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
      </div>
    </div>
  );
}

function Stat({ icon: Icon, value, label, theme }: any) {
  return (
    <div className="p-3 rounded-xl" style={{ background: theme.background, border: `1px solid ${theme.border}` }}>
      <Icon className="h-4 w-4 mb-1.5" style={{ color: theme.primary }} />
      <div className="font-display font-black text-xl tracking-tight" style={{ color: theme.text }}>{value}</div>
      <div className="text-[10px] uppercase tracking-wider font-bold" style={{ color: theme.textSecondary }}>{label}</div>
    </div>
  );
}
