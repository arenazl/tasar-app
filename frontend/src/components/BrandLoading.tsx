import BrandLogo from './BrandLogo';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
  fullscreen?: boolean;
}

const RING_SIZES = {
  sm: { ring: 'h-10 w-10', logo: 'h-6 w-6', border: '2px' },
  md: { ring: 'h-16 w-16', logo: 'h-9 w-9', border: '3px' },
  lg: { ring: 'h-24 w-24', logo: 'h-14 w-14', border: '4px' },
};

/**
 * Loading oficial TasAR — anillo girando con el logo TasAR pulsante al centro.
 * Combina movimiento (spinner) + identidad (logo) sin quedar estático ni genérico.
 */
export default function BrandLoading({
  message = 'Cargando mercado…',
  size = 'md',
  fullscreen = false,
}: Props) {
  const { theme } = useTheme();
  const sz = RING_SIZES[size];

  const inner = (
    <div className="flex flex-col items-center justify-center gap-4">
      <div className={`relative ${sz.ring} flex items-center justify-center`}>
        {/* Halo blur pulsante detrás (da vida al fondo) */}
        <div className="absolute inset-0 rounded-full blur-2xl opacity-50 animate-pulse"
          style={{ background: theme.primary, animationDuration: '2s' }} />

        {/* Anillo principal girando (rápido, horario) */}
        <div
          className="absolute inset-0 animate-spin rounded-full border-t-transparent"
          style={{
            borderWidth: sz.border,
            borderStyle: 'solid',
            borderColor: `${theme.primary}22`,
            borderTopColor: theme.primary,
            animationDuration: '1.2s',
          }}
        />

        {/* Anillo secundario girando (lento, antihorario) */}
        <div
          className="absolute inset-1 rounded-full border-r-transparent border-l-transparent"
          style={{
            borderWidth: '2px',
            borderStyle: 'solid',
            borderColor: `${theme.primary}66`,
            animation: 'spinReverse 2.4s linear infinite',
          }}
        />

        {/* Logo TasAR contenido en círculo + escala pulsante */}
        <div
          className={`${sz.logo} relative rounded-full overflow-hidden flex items-center justify-center`}
          style={{
            background: `${theme.primary}10`,
            animation: 'logoBreathe 2.4s ease-in-out infinite',
          }}
        >
          <div className="w-[70%] h-[70%] flex items-center justify-center">
            <BrandLogo variant="icon" className="h-full w-full" />
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs" style={{ color: theme.textSecondary }}>
        <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: theme.primary }} />
        <span className="tracking-wider uppercase font-medium">{message}</span>
      </div>

      <style>{`
        @keyframes spinReverse {
          from { transform: rotate(360deg); }
          to   { transform: rotate(0deg); }
        }
        @keyframes logoBreathe {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50%      { transform: scale(1.12) rotate(-3deg); }
        }
      `}</style>
    </div>
  );

  if (fullscreen) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center"
        style={{ background: theme.background }}>
        {inner}
      </div>
    );
  }
  return <div className="w-full py-12 flex items-center justify-center">{inner}</div>;
}

/** Overlay flotante para usar encima de un skeleton (esquina o centro flotante). */
export function BrandLoadingOverlay() {
  const { theme } = useTheme();
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
      <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-full backdrop-blur shadow-lg"
        style={{ background: `${theme.card}ee`, color: theme.textSecondary, border: `1px solid ${theme.border}` }}>
        <div className="relative h-4 w-4 flex items-center justify-center">
          <div
            className="absolute inset-0 animate-spin rounded-full border-2 border-t-transparent"
            style={{
              borderColor: `${theme.primary}33`,
              borderTopColor: theme.primary,
              animationDuration: '1.2s',
            }}
          />
        </div>
        <span className="tracking-wide uppercase font-medium">Cargando…</span>
      </div>
    </div>
  );
}
