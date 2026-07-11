import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Rocket, X } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import {
  FIRST_DAY_TOUR_RESET_EVENT, FIRST_DAY_TOUR_STEPS, tourDoneKey, tourStepKey,
} from '../config/firstDayTour';

/**
 * Tour de primer día (WO F6-05) — guía cross-page sobre el circuito de trabajo
 * completo (Hoy -> Chat -> Clientes -> Pipeline -> Tasar). Se dispara UNA VEZ
 * por usuario (flag en localStorage, no por municipio como PageHint) y es
 * reabrible desde Configuración vía FIRST_DAY_TOUR_RESET_EVENT.
 *
 * Vive montado en Layout (fuera del árbol de cada página) porque, a diferencia
 * de PageHint, sus pasos cruzan rutas: "Siguiente" navega Y avanza el paso.
 */
export default function FirstDayTour() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const navigate = useNavigate();

  const [active, setActive] = useState(false);
  const [stepIdx, setStepIdx] = useState(0);

  const evaluate = useCallback(() => {
    if (!user || user.role === 'cliente') { setActive(false); return; }
    const done = localStorage.getItem(tourDoneKey(user.id)) === 'true';
    if (done) { setActive(false); return; }
    const saved = parseInt(localStorage.getItem(tourStepKey(user.id)) || '0', 10);
    setStepIdx(Number.isFinite(saved) ? Math.max(0, Math.min(saved, FIRST_DAY_TOUR_STEPS.length - 1)) : 0);
    setActive(true);
  }, [user]);

  useEffect(() => { evaluate(); }, [evaluate]);

  useEffect(() => {
    window.addEventListener(FIRST_DAY_TOUR_RESET_EVENT, evaluate);
    return () => window.removeEventListener(FIRST_DAY_TOUR_RESET_EVENT, evaluate);
  }, [evaluate]);

  if (!active || !user) return null;

  const step = FIRST_DAY_TOUR_STEPS[stepIdx];
  const isLast = stepIdx === FIRST_DAY_TOUR_STEPS.length - 1;
  const Icon = step.icon;

  const finish = () => {
    localStorage.setItem(tourDoneKey(user.id), 'true');
    setActive(false);
  };

  const advance = () => {
    if (isLast) { finish(); return; }
    const next = stepIdx + 1;
    localStorage.setItem(tourStepKey(user.id), String(next));
    setStepIdx(next);
    navigate(FIRST_DAY_TOUR_STEPS[next].route);
  };

  return (
    <div
      className="fixed left-3 right-3 sm:left-4 sm:right-auto bottom-[88px] lg:bottom-6 z-40 sm:w-96 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-300"
      style={{ background: theme.card, border: `1px solid ${theme.primary}40` }}
    >
      <div className="h-1" style={{ background: theme.primary }} />
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: `${theme.primary}18`, color: theme.primary }}>
            <Icon className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded-full mb-1"
              style={{ background: `${theme.primary}18`, color: theme.primary }}>
              Tour de bienvenida · {stepIdx + 1}/{FIRST_DAY_TOUR_STEPS.length}
            </div>
            <h3 className="text-sm font-bold" style={{ color: theme.text }}>{step.title}</h3>
            <p className="text-xs mt-1 leading-snug" style={{ color: theme.textSecondary }}>{step.body(user.role)}</p>

            <div className="mt-3 flex items-center justify-between gap-2">
              <div className="flex items-center gap-1.5">
                {FIRST_DAY_TOUR_STEPS.map((_, i) => (
                  <span key={i} className="h-1.5 rounded-full transition-all"
                    style={{ width: i === stepIdx ? 20 : 6, background: i === stepIdx ? theme.primary : `${theme.primary}40` }} />
                ))}
              </div>
              <button onClick={advance}
                className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95"
                style={{ background: theme.primary, color: theme.primaryText }}>
                {isLast
                  ? <>Empezar a trabajar <Rocket className="h-3.5 w-3.5" /></>
                  : <>Siguiente: {FIRST_DAY_TOUR_STEPS[stepIdx + 1].navLabel} <ChevronRight className="h-3.5 w-3.5" /></>}
              </button>
            </div>
          </div>
          <button onClick={finish}
            className="flex-shrink-0 w-6 h-6 rounded-md flex items-center justify-center transition-colors hover:brightness-125"
            style={{ background: `${theme.primary}15`, color: theme.primary }}
            aria-label="Cerrar tour">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}
