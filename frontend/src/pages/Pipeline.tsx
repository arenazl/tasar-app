import { useEffect, useState } from 'react';
import { Workflow, ArrowRight } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import type { Appraisal } from '../types';

const STAGES = [
  { key: 'solicitada', label: 'Solicitada', color: '#94a3b8' },
  { key: 'en_analisis', label: 'En análisis', color: '#3b82f6' },
  { key: 'en_revision', label: 'En revisión', color: '#f59e0b' },
  { key: 'aprobada', label: 'Aprobada', color: '#10b981' },
  { key: 'entregada', label: 'Entregada', color: '#22c55e' },
];

export default function Pipeline() {
  const { theme } = useTheme();
  const [items, setItems] = useState<Appraisal[]>([]);

  useEffect(() => {
    api.get<Appraisal[]>('/appraisals').then(r => setItems(r.data));
  }, []);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-2xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6">
        <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
          <Workflow className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
          Pipeline
        </h1>
        <p className="text-xs sm:text-sm mt-1" style={{ color: theme.textSecondary }}>
          Embudo de tasaciones por etapa · {items.length} totales
          <span className="lg:hidden"> · deslizá →</span>
        </p>
      </header>

      {/* Mobile: scroll horizontal con columnas fijas. Desktop: grid */}
      <div className="flex gap-3 overflow-x-auto pb-2 lg:grid lg:grid-cols-5 lg:overflow-visible -mx-4 sm:-mx-6 lg:mx-0 px-4 sm:px-6 lg:px-0 snap-x snap-mandatory lg:snap-none">
        {STAGES.map(stage => {
          const stageItems = items.filter(i => (i as any).status === stage.key);
          return (
            <div key={stage.key} className="rounded-xl flex flex-col flex-shrink-0 w-[280px] lg:w-auto snap-start"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div className="px-4 py-3 flex items-center justify-between"
                style={{ borderBottom: `1px solid ${theme.border}` }}>
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: stage.color }} />
                  <span className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.text }}>
                    {stage.label}
                  </span>
                </div>
                <span className="text-xs font-bold tabular-nums px-2 py-0.5 rounded-full"
                  style={{ background: theme.backgroundSecondary, color: theme.text }}>
                  {stageItems.length}
                </span>
              </div>
              <div className="flex-1 p-2 space-y-2 min-h-[400px]">
                {stageItems.length === 0 && (
                  <div className="text-center text-xs py-8" style={{ color: theme.textSecondary }}>
                    Vacío
                  </div>
                )}
                {stageItems.map(item => {
                  const a: any = item;
                  return (
                    <div key={item.id} className="p-3 rounded-lg transition-all hover:scale-[1.01] hover:shadow-md cursor-pointer"
                      style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}` }}>
                      <div className="flex items-baseline justify-between mb-1">
                        <span className="text-[10px] font-mono font-bold" style={{ color: theme.primary }}>
                          {a.code || `#${item.id}`}
                        </span>
                        <span className="text-[10px] uppercase tracking-wider" style={{ color: theme.textSecondary }}>
                          {item.purpose}
                        </span>
                      </div>
                      {a.client_name && (
                        <div className="text-xs truncate font-semibold" style={{ color: theme.text }}>{a.client_name}</div>
                      )}
                      {a.suggested_value_mode && (
                        <div className="text-sm font-bold mt-1 tabular-nums" style={{ color: theme.text }}>
                          USD {Math.round(a.suggested_value_mode).toLocaleString()}
                        </div>
                      )}
                      {a.confidence_score && (
                        <div className="text-[10px] mt-0.5" style={{ color: theme.textSecondary }}>
                          Confianza {Math.round(a.confidence_score * 100)}%
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
