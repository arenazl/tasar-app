import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Loader2, Sparkles, ArrowRight, ShieldAlert } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import BrandLogo from '../components/BrandLogo';
import { BRAND } from '../config/brand';
import type { InvitationInfo } from '../types';

const ROLE_LABEL: Record<string, string> = {
  admin: 'Administrador', supervisor: 'Supervisor', vendedor: 'Vendedor',
};
const REASON_LABEL: Record<string, string> = {
  usada: 'Esta invitación ya fue utilizada.',
  revocada: 'Esta invitación fue cancelada por el administrador.',
  expirada: 'Esta invitación expiró. Pedile al administrador que la reenvíe.',
};

export default function AceptarInvitacion() {
  const { token } = useParams<{ token: string }>();
  const { acceptInvitation } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();

  const [info, setInfo] = useState<InvitationInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) { setNotFound(true); setLoading(false); return; }
    api.get<InvitationInfo>(`/auth/invitation/${token}`)
      .then(r => { setInfo(r.data); setFullName(r.data.full_name || ''); })
      .catch(() => setNotFound(true))
      .finally(() => setLoading(false));
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { toast.error('La contraseña debe tener al menos 6 caracteres'); return; }
    if (!token) return;
    setSubmitting(true);
    try {
      await acceptInvitation({ token, password, full_name: fullName.trim() || undefined });
      toast.success(`Bienvenido a ${BRAND.name}`);
      navigate('/');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'No se pudo completar el alta');
    } finally {
      setSubmitting(false);
    }
  };

  const invalid = notFound || (info && !info.valid);

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-5 sm:p-8" style={{ background: theme.background }}>
      <div className="w-full max-w-md">
        <div className="flex justify-center mb-6"><BrandLogo variant="topbar" className="h-10" /></div>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-7 w-7 animate-spin" style={{ color: theme.primary }} /></div>
        ) : invalid ? (
          <div className="p-6 rounded-2xl text-center" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-3"
              style={{ background: `${theme.danger}15` }}>
              <ShieldAlert className="h-6 w-6" style={{ color: theme.danger }} />
            </div>
            <h2 className="text-xl font-display font-black" style={{ color: theme.text }}>Invitación no válida</h2>
            <p className="text-sm mt-2" style={{ color: theme.textSecondary }}>
              {notFound ? 'No encontramos esta invitación.' : REASON_LABEL[info?.reason || ''] || 'La invitación no es válida.'}
            </p>
            <Link to="/login" className="inline-block mt-5 font-bold hover:underline" style={{ color: theme.primary }}>
              Ir al inicio de sesión
            </Link>
          </div>
        ) : info && (
          <>
            <div className="mb-6 text-center">
              <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl mb-3"
                style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
                <Sparkles className="h-5 w-5" style={{ color: theme.primary }} />
              </div>
              <h2 className="text-2xl font-display font-black tracking-tight" style={{ color: theme.text }}>
                Sumate a {info.workspace_name}
              </h2>
              <p className="text-sm mt-1.5" style={{ color: theme.textSecondary }}>
                Te invitaron como <b style={{ color: theme.text }}>{ROLE_LABEL[info.role] || info.role}</b>. Creá tu contraseña para empezar.
              </p>
            </div>

            <form onSubmit={submit} className="space-y-3 p-6 rounded-2xl"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div>
                <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Email</label>
                <input type="email" value={info.email} disabled
                  className="w-full px-4 py-3 rounded-xl border"
                  style={{ background: theme.backgroundSecondary, color: theme.textSecondary, borderColor: theme.border, fontSize: 16 }} />
              </div>
              <div>
                <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Nombre y apellido</label>
                <input type="text" value={fullName} onChange={e => setFullName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2"
                  style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: 16 }} />
              </div>
              <div>
                <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>Contraseña</label>
                <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6}
                  placeholder="Mínimo 6 caracteres"
                  className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2"
                  style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: 16 }} />
              </div>
              <button type="submit" disabled={submitting}
                className="group w-full py-3.5 rounded-xl font-bold tracking-wide shadow-lg transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
                style={{ background: theme.primary, color: theme.primaryText, boxShadow: `0 6px 20px ${theme.primary}55` }}>
                {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : (
                  <><span>Crear mi cuenta</span><ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></>
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
