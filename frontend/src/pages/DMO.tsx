import { useEffect, useState } from 'react';
import { ClipboardList, Check, Flame, Clock, AlertCircle, Minus, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { useDmoDia, type BlockStatus } from '../hooks/useDmoDia';

export default function DMO() {
  const { theme } = useTheme();
  // Fetch + derivación de estados compartidos con Hoy.tsx (hook único, WO F6-01).
  const { data, loading, now, blockStatuses, doneCount, toggleBloque } = useDmoDia();

  const statusColor: Record<BlockStatus, string> = {
    done: theme.success,
    now: theme.primary,
    pending: theme.textSecondary,
    overdue: theme.danger,
  };

  if (loading) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-screen-xl mx-auto">
        <div className="h-8 w-64 rounded animate-pulse mb-6" style={{ background: theme.backgroundSecondary }} />
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-24 rounded-xl animate-pulse" style={{ background: theme.card }} />
          ))}
        </div>
      </div>
    );
  }
  if (!data) return null;

  if (!data.template) {
    return (
      <div className="flex flex-col h-full items-center justify-center p-8 text-center">
        <AlertCircle className="h-12 w-12 mb-3" style={{ color: theme.warning }} />
        <h2 className="text-xl font-bold mb-2" style={{ color: theme.text }}>No tenés un DMO asignado todavía</h2>
        <p className="text-sm mb-4 max-w-md" style={{ color: theme.textSecondary }}>
          Pedile a tu supervisor que te asigne una metodología (WhatsApp-first AR, Tom Ferry, Buffini, etc.)
          o que cargue el template default de la oficina.
        </p>
        <Link to="/dmo-asignaciones" className="px-4 py-2 rounded-lg text-sm font-medium text-white" style={{ background: theme.primary }}>
          Ir a asignaciones
        </Link>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-screen-xl mx-auto animate-fade-in">
      <header className="mb-5 sm:mb-6">
        <h1 className="text-2xl sm:text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
          <ClipboardList className="h-6 sm:h-7 w-6 sm:w-7" style={{ color: theme.primary }} />
          Mi DMO de hoy
        </h1>
        <p className="text-xs sm:text-sm mt-1 flex items-center gap-2 flex-wrap" style={{ color: theme.textSecondary }}>
          <span className="tabular-nums">{now}</span>
          <span>·</span>
          <span className="font-semibold" style={{ color: theme.text }}>{data.template.name}</span>
          {data.template.coach_name && <span>· {data.template.coach_name}</span>}
          <span>·</span>
          <span>{doneCount} de {data.blocks.length} bloques · {data.completion_pct}% completitud</span>
        </p>
      </header>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
        <KpiCard theme={theme} label="Conversaciones hoy" value={`${data.conversations_done} / ${data.conversations_goal}`}
          progress={Math.min(100, Math.round((data.conversations_done / Math.max(data.conversations_goal, 1)) * 100))}
          color={data.conversations_done >= data.conversations_goal ? theme.success : theme.primary} />
        <KpiCard theme={theme} label="Completitud DMO" value={`${data.completion_pct}%`} progress={data.completion_pct} color={theme.primary} />
        <KpiCard theme={theme} label="Bloques completados" value={`${doneCount} / ${data.blocks.length}`}
          progress={Math.round((doneCount / Math.max(data.blocks.length, 1)) * 100)} color={theme.success} />
      </div>

      {/* Bloques */}
      <div className="space-y-3">
        {blockStatuses.map(({ block: b, status, log }) => {
          const completed = !!log?.completed;
          const value = log?.metric_value ?? 0;
          const color = statusColor[status];
          const hasMetric = b.metric_type === 'quantity';
          return (
            <div key={b.id} className="relative rounded-xl overflow-hidden transition-all"
              style={{
                background: theme.card,
                border: `1px solid ${status === 'now' ? color : theme.border}`,
                boxShadow: status === 'now' ? `0 0 0 1px ${color}` : 'none',
              }}>
              <div className="absolute left-0 top-0 bottom-0 w-1" style={{ background: b.color || color }} />
              <div className="flex items-start gap-4 p-4 pl-5">
                <div className="flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center text-white"
                  style={{ background: b.is_money_block ? theme.danger : b.color || color }}>
                  {b.is_money_block ? <Flame className="h-5 w-5" /> : <Clock className="h-5 w-5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-bold" style={{ color: theme.text }}>{b.name}</h3>
                    <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                      {b.start_time.slice(0, 5)} – {b.end_time.slice(0, 5)}
                    </span>
                    {b.is_money_block && <StatusPill label="No negociable" bg={theme.danger} />}
                    {status === 'now' && <StatusPill label="En curso" bg={theme.primary} />}
                    {status === 'overdue' && !completed && <StatusPill label="Vencido" bg={theme.danger} />}
                    {status === 'done' && <StatusPill label="Completado" bg={theme.success} icon />}
                  </div>
                  {b.description && <p className="text-sm mt-1" style={{ color: theme.textSecondary }}>{b.description}</p>}

                  {hasMetric && b.metric_goal > 0 && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span style={{ color: theme.textSecondary }}>{b.metric_label || 'Cantidad'}</span>
                        <span className="font-semibold" style={{ color: theme.text }}>{value} / {b.metric_goal}</span>
                      </div>
                      <div className="h-2 rounded-full overflow-hidden" style={{ background: theme.backgroundSecondary }}>
                        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, (value / Math.max(b.metric_goal, 1)) * 100)}%`, background: b.color || theme.primary }} />
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-3 mt-3 flex-wrap">
                    <button onClick={() => toggleBloque(b, !completed, value)}
                      className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium active:scale-95 transition-all"
                      style={{
                        background: completed ? theme.success : 'transparent',
                        color: completed ? '#fff' : theme.text,
                        border: `1px solid ${completed ? theme.success : theme.border}`,
                      }}>
                      <Check className="h-4 w-4" /> {completed ? 'Completado' : 'Marcar completado'}
                    </button>
                    {hasMetric && (
                      <MetricStepper theme={theme} value={value} label={b.metric_label || 'cantidad'} onCommit={(next) => toggleBloque(b, completed, next)} />
                    )}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function StatusPill({ label, bg, icon }: { label: string; bg: string; icon?: boolean }) {
  return (
    <span className="text-xs px-2 py-0.5 rounded font-semibold inline-flex items-center gap-1 text-white" style={{ background: bg }}>
      {icon && <Check className="h-3 w-3" />} {label}
    </span>
  );
}

function KpiCard({ theme, label, value, progress, color }: { theme: any; label: string; value: string; progress: number; color: string }) {
  return (
    <div className="rounded-xl p-4" style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <div className="text-xs uppercase tracking-wider mb-1" style={{ color: theme.textSecondary }}>{label}</div>
      <div className="text-2xl font-bold mb-2 tabular-nums" style={{ color }}>{value}</div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: theme.backgroundSecondary }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${progress}%`, background: color }} />
      </div>
    </div>
  );
}

function MetricStepper({ theme, value, label, onCommit }: { theme: any; value: number; label: string; onCommit: (n: number) => void }) {
  const [local, setLocal] = useState(value);
  useEffect(() => { setLocal(value); }, [value]);
  const commit = (n: number) => { const v = Math.max(0, n); setLocal(v); onCommit(v); };
  return (
    <div className="inline-flex items-center gap-2">
      <div className="inline-flex items-stretch rounded-lg overflow-hidden h-9" style={{ border: `1px solid ${theme.border}`, background: theme.backgroundSecondary }}>
        <button type="button" onClick={() => commit(local - 1)} aria-label="Restar" className="w-9 flex items-center justify-center active:scale-95" style={{ color: theme.text }}>
          <Minus className="h-4 w-4" />
        </button>
        <input type="text" inputMode="numeric" value={local}
          onChange={(e) => { const n = parseInt(e.target.value.replace(/[^0-9]/g, ''), 10); commit(Number.isFinite(n) ? n : 0); }}
          className="w-12 text-center font-semibold bg-transparent focus:outline-none"
          style={{ borderLeft: `1px solid ${theme.border}`, borderRight: `1px solid ${theme.border}`, color: theme.text }} />
        <button type="button" onClick={() => commit(local + 1)} aria-label="Sumar" className="w-9 flex items-center justify-center active:scale-95" style={{ color: theme.text }}>
          <Plus className="h-4 w-4" />
        </button>
      </div>
      <span className="text-xs" style={{ color: theme.textSecondary }}>{label.toLowerCase()}</span>
    </div>
  );
}
