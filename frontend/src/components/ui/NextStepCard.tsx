import type { ReactNode } from 'react';
import { Target, ArrowRight, X } from 'lucide-react';
import { useTheme } from '../../contexts/ThemeContext';

// Patrón visual ÚNICO de "siguiente paso" — el eslabón que encadena el ciclo
// Captar → Gestionar → Atender → Cerrar (WO F6-03). Un solo componente para que
// TODOS los CTAs encadenados (resultado de tasación, alta de propiedad, visita
// concretada, deal en reserva, chat sin cliente, tasación firmada) se vean igual.

export interface NextStepAction {
  label: string;
  icon?: ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

type Tone = 'primary' | 'success' | 'warning';

interface NextStepCardProps {
  message: string;
  actions: NextStepAction[];
  /** Rótulo superior (eyebrow). Default: "Siguiente paso". */
  eyebrow?: string;
  icon?: ReactNode;
  tone?: Tone;
  onDismiss?: () => void;
  className?: string;
}

export function NextStepCard({
  message, actions, eyebrow = 'Siguiente paso', icon, tone = 'primary', onDismiss, className,
}: NextStepCardProps) {
  const { theme } = useTheme();
  const accent = tone === 'success' ? theme.success : tone === 'warning' ? theme.warning : theme.primary;

  return (
    <div
      className={`rounded-2xl p-4 sm:p-5 ${className || ''}`}
      style={{ background: `${accent}0d`, border: `1px solid ${accent}40` }}
    >
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${accent}20` }}>
          <span style={{ color: accent }}>{icon || <Target className="h-5 w-5" />}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-bold uppercase tracking-wider" style={{ color: accent }}>{eyebrow}</div>
          <div className="text-sm sm:text-base font-semibold mt-0.5" style={{ color: theme.text }}>{message}</div>
          <div className="flex flex-wrap items-center gap-2 mt-3">
            {actions.map((a, i) => {
              const primary = (a.variant ?? (i === 0 ? 'primary' : 'secondary')) === 'primary';
              return (
                <button
                  key={a.label}
                  onClick={a.onClick}
                  disabled={a.disabled}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-sm font-bold transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
                  style={primary
                    ? { background: accent, color: theme.primaryText || '#fff' }
                    : { background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}
                >
                  {a.icon}
                  {a.label}
                  {primary && <ArrowRight className="h-4 w-4" />}
                </button>
              );
            })}
          </div>
        </div>
        {onDismiss && (
          <button onClick={onDismiss} className="p-1.5 rounded-lg flex-shrink-0 active:scale-95" style={{ color: theme.textSecondary }} aria-label="Descartar">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}

export default NextStepCard;
