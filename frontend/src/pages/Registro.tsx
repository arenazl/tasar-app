import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { toast } from 'sonner';
import {
  Loader2, ArrowRight, Building2, Home, Sparkles, UserPlus, Send,
  Rocket, CircleCheck, ChevronRight, SkipForward,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { api } from '../services/api';
import BrandLogo from '../components/BrandLogo';
import { BRAND } from '../config/brand';
import { ModernSelect } from '../components/ui/ModernSelect';
import type { TeamRole } from '../types';

type WizardStep = 1 | 2 | 3 | 4;

const STEP_LABELS: Record<WizardStep, string> = {
  1: 'Tu inmobiliaria',
  2: 'Cargar datos',
  3: 'Invitar equipo',
  4: 'Listo',
};

const ROLE_OPTIONS: { value: TeamRole; label: string }[] = [
  { value: 'vendedor', label: 'Vendedor' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'admin', label: 'Administrador' },
];

/**
 * Wizard de onboarding self-service (WO F5-03). Ruta publica `/registro`
 * (destino del CTA "Crear una cuenta" de la landing, `landing/index.html`).
 *
 * 4 pasos, cada uno deja avanzar sin bloquear (los pasos 2 y 3 son opcionales
 * -- "Saltar por ahora"): nombre de la inmobiliaria + alta del admin -> cargar
 * 1 propiedad real O datos de ejemplo -> invitar al equipo -> primera
 * tasación express (deep-link a `/tasacion-express`).
 */
export default function Registro() {
  const { register } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();

  const [step, setStep] = useState<WizardStep>(1);

  // Paso 1 — alta
  const [workspaceName, setWorkspaceName] = useState('');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [registering, setRegistering] = useState(false);

  // Paso 2 — datos iniciales
  const [dataChoice, setDataChoice] = useState<'demo' | 'propiedad' | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [demoSummary, setDemoSummary] = useState<{ properties_created: number; vendors_created: number; conversations_created: number } | null>(null);
  const [propTitle, setPropTitle] = useState('');
  const [propCity, setPropCity] = useState('');
  const [propAddress, setPropAddress] = useState('');
  const [propBusy, setPropBusy] = useState(false);
  const [propCreated, setPropCreated] = useState(false);

  // Paso 3 — invitar equipo
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<TeamRole>('vendedor');
  const [inviteBusy, setInviteBusy] = useState(false);
  const [invited, setInvited] = useState(false);

  const submitStep1 = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { toast.error('La contraseña debe tener al menos 6 caracteres'); return; }
    setRegistering(true);
    try {
      await register({ email, password, full_name: fullName, workspace_name: workspaceName });
      toast.success(`${workspaceName} está listo`);
      setStep(2);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'No se pudo crear la cuenta');
    } finally {
      setRegistering(false);
    }
  };

  const loadDemoData = async () => {
    setDataChoice('demo');
    setDemoBusy(true);
    try {
      const r = await api.post('/demo/generate', { n_properties: 12 });
      setDemoSummary(r.data);
      toast.success('Datos de ejemplo cargados');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'No se pudieron cargar los datos de ejemplo');
    } finally {
      setDemoBusy(false);
    }
  };

  const createProperty = async () => {
    if (!propTitle.trim() || !propCity.trim() || !propAddress.trim()) {
      toast.error('Completá título, ciudad y dirección');
      return;
    }
    setPropBusy(true);
    try {
      await api.post('/properties', {
        title: propTitle, property_type: 'departamento', operation: 'venta',
        province: propCity, city: propCity, address: propAddress, currency: 'USD',
      });
      setPropCreated(true);
      toast.success('Propiedad cargada');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'No se pudo cargar la propiedad');
    } finally {
      setPropBusy(false);
    }
  };

  const sendInvite = async () => {
    const emailTrim = inviteEmail.trim().toLowerCase();
    if (!emailTrim) { toast.error('Ingresá un email'); return; }
    setInviteBusy(true);
    try {
      await api.post('/team/invitations', { email: emailTrim, role: inviteRole });
      setInvited(true);
      toast.success(`Invitación enviada a ${emailTrim}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'No se pudo invitar');
    } finally {
      setInviteBusy(false);
    }
  };

  const goToExpress = () => navigate('/tasacion-express');

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-5 sm:p-8" style={{ background: theme.background }}>
      <div className="w-full max-w-lg">
        <div className="flex justify-center mb-5"><BrandLogo variant="topbar" className="h-10" /></div>

        {/* Progreso */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {([1, 2, 3, 4] as WizardStep[]).map((s) => (
            <div key={s} className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                style={{
                  background: s <= step ? theme.primary : theme.backgroundSecondary,
                  color: s <= step ? theme.primaryText : theme.textSecondary,
                  border: `1px solid ${s <= step ? theme.primary : theme.border}`,
                }}
              >
                {s < step ? <CircleCheck className="h-4 w-4" /> : s}
              </div>
              {s < 4 && <div className="w-6 h-0.5" style={{ background: s < step ? theme.primary : theme.border }} />}
            </div>
          ))}
        </div>
        <p className="text-center text-xs font-bold uppercase tracking-wider mb-6" style={{ color: theme.textSecondary }}>
          Paso {step} de 4 · {STEP_LABELS[step]}
        </p>

        <div className="p-6 rounded-2xl" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
          {/* ── PASO 1: nombre de la inmobiliaria + alta admin ── */}
          {step === 1 && (
            <form onSubmit={submitStep1} className="space-y-3">
              <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl mb-3"
                  style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
                  <Building2 className="h-5 w-5" style={{ color: theme.primary }} />
                </div>
                <h2 className="text-2xl font-display font-black tracking-tight" style={{ color: theme.text }}>
                  Creá tu {BRAND.name}
                </h2>
                <p className="text-sm mt-1.5" style={{ color: theme.textSecondary }}>
                  Empezás en minutos, sin tarjeta ni instalación.
                </p>
              </div>
              <Field label="Nombre de tu inmobiliaria" value={workspaceName} onChange={setWorkspaceName} theme={theme} placeholder="Ej: Inmobiliaria del Sur" required />
              <Field label="Tu nombre y apellido" value={fullName} onChange={setFullName} theme={theme} placeholder="Ej: María Fernández" required />
              <Field label="Email" type="email" value={email} onChange={setEmail} theme={theme} placeholder="vos@tuinmobiliaria.com" required />
              <Field label="Contraseña" type="password" value={password} onChange={setPassword} theme={theme} placeholder="Mínimo 6 caracteres" required minLength={6} />
              <button type="submit" disabled={registering}
                className="group w-full py-3.5 rounded-xl font-bold tracking-wide shadow-lg transition-all active:scale-[0.98] disabled:opacity-50 flex items-center justify-center gap-2"
                style={{ background: theme.primary, color: theme.primaryText, boxShadow: `0 6px 20px ${theme.primary}55` }}>
                {registering ? <Loader2 className="h-5 w-5 animate-spin" /> : (
                  <><span>Crear mi cuenta</span><ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" /></>
                )}
              </button>
              <p className="text-center text-sm pt-1" style={{ color: theme.textSecondary }}>
                ¿Ya tenés cuenta? <Link to="/login" className="font-bold hover:underline" style={{ color: theme.primary }}>Iniciar sesión</Link>
              </p>
            </form>
          )}

          {/* ── PASO 2: 1 propiedad real o datos de ejemplo ── */}
          {step === 2 && (
            <div className="space-y-4">
              <StepHeader icon={Home} theme={theme}
                title="Cargá tus primeros datos"
                desc="Elegí cómo querés empezar a ver la app funcionando." />

              <div className="grid grid-cols-1 gap-3">
                <button type="button" onClick={loadDemoData} disabled={demoBusy || !!demoSummary}
                  className="p-4 rounded-xl text-left transition-all hover:scale-[1.01] active:scale-95 disabled:opacity-70"
                  style={{
                    background: dataChoice === 'demo' ? `${theme.primary}10` : theme.backgroundSecondary,
                    border: `2px solid ${dataChoice === 'demo' ? theme.primary : 'transparent'}`,
                  }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles className="h-4 w-4" style={{ color: theme.primary }} />
                    <span className="font-bold" style={{ color: theme.text }}>Cargar datos de ejemplo</span>
                  </div>
                  <p className="text-xs" style={{ color: theme.textSecondary }}>
                    12 propiedades + 3 vendedores + rutina DMO + 5 conversaciones de WhatsApp, todo marcado [DEMO]. Ideal para probar la app ya mismo.
                  </p>
                  {demoBusy && <div className="mt-2 flex items-center gap-2 text-xs" style={{ color: theme.primary }}><Loader2 className="h-3.5 w-3.5 animate-spin" /> Generando…</div>}
                  {demoSummary && (
                    <div className="mt-2 text-xs font-semibold flex items-center gap-1.5" style={{ color: theme.success }}>
                      <CircleCheck className="h-3.5 w-3.5" />
                      {demoSummary.properties_created} propiedades · {demoSummary.vendors_created} vendedores · {demoSummary.conversations_created} conversaciones
                    </div>
                  )}
                </button>

                <button type="button" onClick={() => setDataChoice('propiedad')} disabled={!!demoSummary}
                  className="p-4 rounded-xl text-left transition-all hover:scale-[1.01] active:scale-95 disabled:opacity-50"
                  style={{
                    background: dataChoice === 'propiedad' ? `${theme.primary}10` : theme.backgroundSecondary,
                    border: `2px solid ${dataChoice === 'propiedad' ? theme.primary : 'transparent'}`,
                  }}>
                  <div className="flex items-center gap-2 mb-1">
                    <Home className="h-4 w-4" style={{ color: theme.primary }} />
                    <span className="font-bold" style={{ color: theme.text }}>Cargar 1 propiedad real</span>
                  </div>
                  <p className="text-xs" style={{ color: theme.textSecondary }}>
                    Preferís arrancar directo con tu cartera real.
                  </p>
                </button>
              </div>

              {dataChoice === 'propiedad' && !propCreated && (
                <div className="p-4 rounded-xl space-y-2.5" style={{ background: theme.backgroundSecondary }}>
                  <Field label="Título" value={propTitle} onChange={setPropTitle} theme={theme} placeholder="Depto 3 amb. Palermo" required />
                  <Field label="Ciudad" value={propCity} onChange={setPropCity} theme={theme} placeholder="CABA" required />
                  <Field label="Dirección" value={propAddress} onChange={setPropAddress} theme={theme} placeholder="Av. Santa Fe 3000" required />
                  <button type="button" onClick={createProperty} disabled={propBusy}
                    className="w-full py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
                    style={{ background: theme.primary, color: theme.primaryText }}>
                    {propBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Home className="h-4 w-4" />}
                    Guardar propiedad
                  </button>
                </div>
              )}
              {propCreated && (
                <div className="text-xs font-semibold flex items-center gap-1.5" style={{ color: theme.success }}>
                  <CircleCheck className="h-3.5 w-3.5" /> Propiedad cargada
                </div>
              )}

              <WizardNav theme={theme}
                onSkip={() => setStep(3)}
                onNext={() => setStep(3)}
                nextDisabled={dataChoice === 'propiedad' && !propCreated}
                nextLabel="Continuar" />
            </div>
          )}

          {/* ── PASO 3: invitar equipo ── */}
          {step === 3 && (
            <div className="space-y-4">
              <StepHeader icon={UserPlus} theme={theme}
                title="Invitá a tu equipo"
                desc="Opcional — podés hacerlo después desde Equipo." />

              {!invited ? (
                <div className="space-y-2.5">
                  <Field label="Email del colega" type="email" value={inviteEmail} onChange={setInviteEmail} theme={theme} placeholder="colega@inmobiliaria.com" />
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color: theme.textSecondary }}>Rol</div>
                    <ModernSelect value={inviteRole} onChange={(v) => setInviteRole(v as TeamRole)} options={ROLE_OPTIONS} />
                  </div>
                  <button type="button" onClick={sendInvite} disabled={inviteBusy}
                    className="w-full py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
                    style={{ background: theme.primary, color: theme.primaryText }}>
                    {inviteBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    Enviar invitación
                  </button>
                </div>
              ) : (
                <div className="text-xs font-semibold flex items-center gap-1.5" style={{ color: theme.success }}>
                  <CircleCheck className="h-3.5 w-3.5" /> Invitación enviada
                </div>
              )}

              <WizardNav theme={theme} onSkip={() => setStep(4)} onNext={() => setStep(4)} nextLabel="Continuar" />
            </div>
          )}

          {/* ── PASO 4: listo, deep-link a tasación express ── */}
          {step === 4 && (
            <div className="text-center space-y-4 py-2">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl mb-1"
                style={{ background: `${theme.success}15`, border: `1px solid ${theme.success}40` }}>
                <Rocket className="h-6 w-6" style={{ color: theme.success }} />
              </div>
              <h2 className="text-2xl font-display font-black tracking-tight" style={{ color: theme.text }}>Todo listo</h2>
              <p className="text-sm max-w-sm mx-auto" style={{ color: theme.textSecondary }}>
                Tu workspace está armado. El último paso: hacé tu primera tasación express y vas a ver el motor anclado a mercado en acción.
              </p>
              <button type="button" onClick={goToExpress}
                className="group w-full py-3.5 rounded-xl font-bold tracking-wide shadow-lg transition-all active:scale-[0.98] flex items-center justify-center gap-2"
                style={{ background: theme.primary, color: theme.primaryText, boxShadow: `0 6px 20px ${theme.primary}55` }}>
                <span>Hacer mi primera tasación express</span>
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </button>
              <button type="button" onClick={() => navigate('/')} className="text-sm font-semibold hover:underline" style={{ color: theme.textSecondary }}>
                Prefiero ir al panel primero
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, theme, type = 'text', placeholder, required, minLength }: {
  label: string; value: string; onChange: (v: string) => void; theme: any;
  type?: string; placeholder?: string; required?: boolean; minLength?: number;
}) {
  return (
    <div>
      <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: theme.textSecondary }}>{label}</label>
      <input type={type} value={value} onChange={e => onChange(e.target.value)} required={required} minLength={minLength}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 transition-all"
        style={{ background: theme.card, color: theme.text, borderColor: theme.border, fontSize: 16 }} />
    </div>
  );
}

function StepHeader({ icon: Icon, title, desc, theme }: { icon: typeof Home; title: string; desc: string; theme: any }) {
  return (
    <div className="text-center mb-1">
      <div className="inline-flex items-center justify-center w-11 h-11 rounded-2xl mb-3"
        style={{ background: `${theme.primary}15`, border: `1px solid ${theme.primary}30` }}>
        <Icon className="h-5 w-5" style={{ color: theme.primary }} />
      </div>
      <h2 className="text-xl font-display font-black tracking-tight" style={{ color: theme.text }}>{title}</h2>
      <p className="text-sm mt-1" style={{ color: theme.textSecondary }}>{desc}</p>
    </div>
  );
}

function WizardNav({ theme, onSkip, onNext, nextDisabled, nextLabel }: {
  theme: any; onSkip: () => void; onNext: () => void; nextDisabled?: boolean; nextLabel: string;
}) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <button type="button" onClick={onSkip}
        className="flex-1 py-2.5 rounded-lg text-sm font-semibold flex items-center justify-center gap-1.5"
        style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
        <SkipForward className="h-3.5 w-3.5" /> Saltar por ahora
      </button>
      <button type="button" onClick={onNext} disabled={nextDisabled}
        className="flex-1 py-2.5 rounded-lg text-sm font-bold flex items-center justify-center gap-1.5 disabled:opacity-50"
        style={{ background: theme.primary, color: theme.primaryText }}>
        {nextLabel} <ChevronRight className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
