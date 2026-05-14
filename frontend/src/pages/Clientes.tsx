import { useEffect, useState, useMemo } from 'react';
import { Users, Mail, Phone, Building2, FileCheck2 } from 'lucide-react';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';
import type { Appraisal } from '../types';

interface Cliente {
  name: string;
  type: 'banco' | 'fondo' | 'estudio' | 'particular' | 'inmobiliaria';
  contact?: string;
  email?: string;
  appraisals: number;
}

const TYPE_FROM_NAME = (name: string): Cliente['type'] => {
  const n = name.toLowerCase();
  if (n.includes('banco')) return 'banco';
  if (n.includes('fondo')) return 'fondo';
  if (n.includes('estudio') || n.includes('aldao')) return 'estudio';
  if (n.includes('remax') || n.includes('argencapital') || n.includes('atlas')) return 'inmobiliaria';
  return 'particular';
};
const TYPE_COLOR: Record<Cliente['type'], string> = {
  banco: '#3b82f6', fondo: '#a855f7', estudio: '#f59e0b', particular: '#10b981', inmobiliaria: '#ec4899',
};

export default function Clientes() {
  const { theme } = useTheme();
  const [items, setItems] = useState<Appraisal[]>([]);

  useEffect(() => { api.get<Appraisal[]>('/appraisals').then(r => setItems(r.data)); }, []);

  const clientes = useMemo<Cliente[]>(() => {
    const map = new Map<string, Cliente>();
    items.forEach(a => {
      const name = (a as any).client_name;
      if (!name) return;
      if (!map.has(name)) {
        map.set(name, {
          name,
          type: TYPE_FROM_NAME(name),
          contact: (a as any).client_contact,
          email: (a as any).client_email,
          appraisals: 0,
        });
      }
      map.get(name)!.appraisals += 1;
    });
    return Array.from(map.values()).sort((a, b) => b.appraisals - a.appraisals);
  }, [items]);

  return (
    <div className="p-8 max-w-7xl mx-auto animate-fade-in">
      <header className="mb-6">
        <h1 className="text-3xl font-display font-black tracking-tight flex items-center gap-2" style={{ color: theme.text }}>
          <Users className="h-7 w-7" style={{ color: theme.primary }} />
          Clientes
        </h1>
        <p className="text-sm mt-1" style={{ color: theme.textSecondary }}>
          {clientes.length} clientes activos
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {clientes.map(c => {
          const color = TYPE_COLOR[c.type];
          return (
            <div key={c.name} className="p-5 rounded-xl transition-all hover:scale-[1.01] hover:shadow-md"
              style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
              <div className="flex items-start gap-3 mb-3">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: `${color}20` }}>
                  <Building2 className="h-6 w-6" style={{ color }} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-bold" style={{ color: theme.text }}>{c.name}</div>
                  <div className="text-[10px] uppercase tracking-wider font-bold mt-0.5" style={{ color }}>
                    {c.type}
                  </div>
                </div>
              </div>
              {c.contact && (
                <div className="text-xs mb-1 flex items-center gap-2" style={{ color: theme.textSecondary }}>
                  <Users className="h-3 w-3" /> {c.contact}
                </div>
              )}
              {c.email && (
                <div className="text-xs flex items-center gap-2 truncate" style={{ color: theme.textSecondary }}>
                  <Mail className="h-3 w-3" /> {c.email}
                </div>
              )}
              <div className="mt-3 pt-3 flex items-center justify-between" style={{ borderTop: `1px solid ${theme.border}` }}>
                <span className="text-xs flex items-center gap-1" style={{ color: theme.textSecondary }}>
                  <FileCheck2 className="h-3 w-3" /> {c.appraisals} tasaciones
                </span>
                <button className="text-xs font-bold transition-all hover:underline" style={{ color: theme.primary }}>
                  Ver →
                </button>
              </div>
            </div>
          );
        })}
        {clientes.length === 0 && (
          <div className="col-span-full p-12 text-center rounded-xl"
            style={{ background: theme.card, border: `2px dashed ${theme.border}`, color: theme.textSecondary }}>
            Cargá tasaciones con cliente para que aparezcan aquí
          </div>
        )}
      </div>
    </div>
  );
}
