import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { DmoDay, DmoBlock, DmoLog } from '../types';

/**
 * Lógica compartida del "DMO del día" (WO F6-01).
 *
 * Fuente ÚNICA de la carga + derivación de estados de bloque del DMO. La consumen
 * `pages/DMO.tsx` (pantalla completa, con toggle) y `pages/Hoy.tsx` (línea horaria
 * compacta, solo lectura). No duplicar `getBlockStatus` ni el fetch en cada página.
 */

export type BlockStatus = 'done' | 'now' | 'pending' | 'overdue';

export function fechaHoy(): string {
  return new Date().toISOString().slice(0, 10);
}

export function ahoraHHMM(): string {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export function hhmmToMin(hhmm: string): number {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}

/** Estado de un bloque según la hora actual y su log del día. */
export function getBlockStatus(b: DmoBlock, log: DmoLog | undefined, nowMin: number): BlockStatus {
  const ini = hhmmToMin(b.start_time.slice(0, 5));
  const fin = hhmmToMin(b.end_time.slice(0, 5));
  if (log?.completed) return 'done';
  if (nowMin >= ini && nowMin < fin) return 'now';
  if (nowMin >= fin) return 'overdue';
  return 'pending';
}

export interface BlockWithStatus {
  block: DmoBlock;
  status: BlockStatus;
  log: DmoLog | undefined;
}

interface UseDmoDiaOptions {
  /** Fecha ISO (YYYY-MM-DD). Default: hoy. */
  fecha?: string;
  /** Ver el DMO de otro vendedor (solo manager, el backend valida el rol). */
  vendorId?: number;
}

export interface UseDmoDiaResult {
  data: DmoDay | null;
  loading: boolean;
  /** Hora actual HH:MM — se refresca cada 60s para mover el "En curso". */
  now: string;
  nowMin: number;
  fecha: string;
  logsByBlock: Map<number, DmoLog>;
  blockStatuses: BlockWithStatus[];
  doneCount: number;
  reload: () => Promise<void>;
  toggleBloque: (block: DmoBlock, completed: boolean, metricValue: number) => Promise<void>;
}

export function useDmoDia(options: UseDmoDiaOptions = {}): UseDmoDiaResult {
  const fecha = options.fecha ?? fechaHoy();
  const vendorId = options.vendorId;
  const [data, setData] = useState<DmoDay | null>(null);
  const [loading, setLoading] = useState(true);
  const [now, setNow] = useState(ahoraHHMM());

  const reload = useCallback(async () => {
    try {
      const params: Record<string, string | number> = { fecha };
      if (vendorId != null) params.vendor_id = vendorId;
      const r = await api.get<DmoDay>('/dmo/dia', { params });
      setData(r.data);
    } catch {
      toast.error('Error al cargar el DMO');
    } finally {
      setLoading(false);
    }
  }, [fecha, vendorId]);

  useEffect(() => {
    reload();
    const t = setInterval(() => setNow(ahoraHHMM()), 60_000);
    return () => clearInterval(t);
  }, [reload]);

  const toggleBloque = useCallback(
    async (block: DmoBlock, completed: boolean, metricValue: number) => {
      try {
        await api.post('/dmo/log', {
          block_id: block.id,
          date: fecha,
          completed,
          metric_value: metricValue,
          notes: null,
        });
        toast.success(completed ? `${block.name}: completado` : `${block.name}: desmarcado`);
        await reload();
      } catch {
        toast.error('Error al guardar');
      }
    },
    [fecha, reload],
  );

  const logsByBlock = useMemo(() => {
    const m = new Map<number, DmoLog>();
    data?.logs.forEach((l) => m.set(l.block_id, l));
    return m;
  }, [data]);

  const nowMin = hhmmToMin(now);

  const blockStatuses = useMemo<BlockWithStatus[]>(() => {
    if (!data) return [];
    return data.blocks.map((b) => ({
      block: b,
      status: getBlockStatus(b, logsByBlock.get(b.id), nowMin),
      log: logsByBlock.get(b.id),
    }));
  }, [data, logsByBlock, nowMin]);

  const doneCount = data?.logs.filter((l) => l.completed).length ?? 0;

  return { data, loading, now, nowMin, fecha, logsByBlock, blockStatuses, doneCount, reload, toggleBloque };
}
