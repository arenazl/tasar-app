import { useEffect, useState, useCallback } from 'react';
import {
  Inbox as InboxIcon, MailOpen, CheckCheck, Reply, Forward, Bot, AlertTriangle,
  AtSign, Bell, DollarSign, ClipboardList, ChevronRight, FileCheck2,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useTheme } from '../contexts/ThemeContext';

interface InboxItem {
  id: number;
  kind: string;
  sender_type: string;
  sender_name?: string;
  sender_subtitle?: string;
  avatar_color?: string;
  subject: string;
  preview?: string;
  body?: string;
  is_read: boolean;
  is_assigned_to_me: boolean;
  priority: string;
  created_at: string;
  related_appraisal_id?: number;
  related_url?: string;
}

const AVATAR_COLORS: Record<string, string> = {
  green: '#10b981', yellow: '#eab308', blue: '#3b82f6', orange: '#f97316', purple: '#a855f7',
};

const KIND_ICON: Record<string, any> = {
  client_message: Reply, system_alert: AlertTriangle, user_mention: AtSign,
  self_reminder: Bell, billing: DollarSign, overdue_task: AlertTriangle,
  appraisal_assigned: FileCheck2, comparable_added: ClipboardList,
};

function fmtTime(iso: string): string {
  const d = new Date(iso); const now = new Date();
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return 'ahora';
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  if (diff < 172800) return `ayer · ${d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })}`;
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: 'short' });
}

export default function Bandeja() {
  const { theme } = useTheme();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [counts, setCounts] = useState({ total: 0, unread: 0, assigned: 0 });
  const [filter, setFilter] = useState<'unread' | 'assigned' | 'all'>('unread');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get<{ items: InboxItem[]; total: number; unread: number; assigned_to_me: number }>(
        `/inbox?filter=${filter}`
      );
      setItems(r.data.items);
      setCounts({ total: r.data.total, unread: r.data.unread, assigned: r.data.assigned_to_me });
      if (!selectedId && r.data.items.length > 0) {
        setSelectedId(r.data.items[0].id);
      }
    } catch { toast.error('Error cargando bandeja'); }
    finally { setLoading(false); }
  }, [filter, selectedId]);

  useEffect(() => { load(); }, [filter]); // eslint-disable-line

  const selected = items.find(i => i.id === selectedId);

  const markRead = async (id: number) => {
    try {
      await api.post(`/inbox/${id}/read`);
      setItems(prev => prev.map(i => i.id === id ? { ...i, is_read: true } : i));
      setCounts(c => ({ ...c, unread: Math.max(0, c.unread - 1) }));
    } catch {}
  };

  const readAll = async () => {
    await api.post('/inbox/read-all');
    setItems(prev => prev.map(i => ({ ...i, is_read: true })));
    setCounts(c => ({ ...c, unread: 0 }));
    toast.success('Todo marcado como leído');
  };

  return (
    <div className="h-full flex" style={{ background: theme.background }}>
      {/* Lista */}
      <div className="w-[420px] flex flex-col flex-shrink-0" style={{ borderRight: `1px solid ${theme.border}` }}>
        {/* Header lista */}
        <div className="flex-shrink-0 p-5" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <div className="flex items-center justify-between mb-1">
            <h1 className="text-2xl font-black tracking-tight" style={{ color: theme.text }}>Bandeja</h1>
            <button onClick={readAll}
              className="p-2 rounded-lg transition-all active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}
              title="Marcar todo como leído">
              <CheckCheck className="h-4 w-4" />
            </button>
          </div>
          <p className="text-sm mb-3" style={{ color: theme.textSecondary }}>
            <b>{counts.unread} sin leer</b> · {counts.total} totales hoy
          </p>
          <div className="flex gap-1 text-sm" style={{ borderBottom: `1px solid ${theme.border}` }}>
            <TabBtn label="Sin leer" count={counts.unread} active={filter === 'unread'} onClick={() => setFilter('unread')} theme={theme} />
            <TabBtn label="Asignadas a mí" count={counts.assigned} active={filter === 'assigned'} onClick={() => setFilter('assigned')} theme={theme} />
            <TabBtn label="Todo" count={counts.total} active={filter === 'all'} onClick={() => setFilter('all')} theme={theme} />
          </div>
        </div>

        {/* Items */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {loading && (
            <div className="p-8 text-center text-sm" style={{ color: theme.textSecondary }}>Cargando…</div>
          )}
          {!loading && items.length === 0 && (
            <div className="p-8 text-center text-sm" style={{ color: theme.textSecondary }}>
              No hay mensajes en este filtro.
            </div>
          )}
          {items.map(item => {
            const isSelected = item.id === selectedId;
            const Icon = KIND_ICON[item.kind] || InboxIcon;
            const avatarColor = AVATAR_COLORS[item.avatar_color || 'blue'] || '#3b82f6';
            return (
              <div key={item.id}
                onClick={() => { setSelectedId(item.id); if (!item.is_read) markRead(item.id); }}
                className="px-4 py-3 cursor-pointer transition-all"
                style={{
                  background: isSelected ? `${theme.primary}10` : 'transparent',
                  borderLeft: `3px solid ${isSelected ? theme.primary : 'transparent'}`,
                  borderBottom: `1px solid ${theme.border}`,
                }}>
                <div className="flex items-start gap-3">
                  {/* Avatar */}
                  <div className="relative flex-shrink-0">
                    <div className="w-9 h-9 rounded-full flex items-center justify-center"
                      style={{ background: `${avatarColor}25`, color: avatarColor }}>
                      <Icon className="h-4 w-4" />
                    </div>
                    {!item.is_read && (
                      <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full"
                        style={{ background: avatarColor, border: `2px solid ${theme.card}` }} />
                    )}
                  </div>
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2">
                      <div className="text-xs truncate" style={{ color: theme.textSecondary, fontWeight: item.is_read ? 400 : 600 }}>
                        <span style={{ color: item.is_read ? theme.textSecondary : theme.text }}>{item.sender_name}</span>
                        {item.sender_subtitle && <span className="opacity-60"> · {item.sender_subtitle}</span>}
                      </div>
                      <span className="text-[10px] flex-shrink-0" style={{ color: theme.textSecondary }}>
                        {fmtTime(item.created_at)}
                      </span>
                    </div>
                    <div className="text-sm truncate mt-0.5"
                      style={{ color: theme.text, fontWeight: item.is_read ? 500 : 700 }}>
                      {item.subject}
                    </div>
                    {item.preview && (
                      <div className="text-xs mt-0.5 line-clamp-2" style={{ color: theme.textSecondary }}>
                        {item.preview}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detalle */}
      <div className="flex-1 flex flex-col min-w-0">
        {selected ? (
          <>
            <div className="flex-shrink-0 px-8 py-5 flex items-start justify-between gap-4"
              style={{ borderBottom: `1px solid ${theme.border}` }}>
              <div className="min-w-0">
                <div className="text-xs uppercase tracking-wider font-semibold mb-1" style={{ color: theme.textSecondary }}>
                  DE {selected.sender_name?.toUpperCase()}
                  {selected.sender_subtitle && <span> · {selected.sender_subtitle.toUpperCase()}</span>}
                </div>
                <h2 className="text-2xl font-black tracking-tight" style={{ color: theme.text }}>{selected.subject}</h2>
                <div className="text-xs mt-1" style={{ color: theme.textSecondary }}>{fmtTime(selected.created_at)}</div>
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <button className="px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-all active:scale-95"
                  style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
                  <Forward className="h-4 w-4" /> Reenviar
                </button>
                <button className="px-4 py-2 rounded-lg text-sm font-bold flex items-center gap-1.5 transition-all active:scale-95"
                  style={{ background: theme.primary, color: theme.primaryText }}>
                  Responder <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto px-8 py-6">
              <div className="max-w-2xl">
                <div className="text-sm whitespace-pre-wrap leading-relaxed" style={{ color: theme.text }}>
                  {selected.body || selected.preview || ''}
                </div>
                {selected.related_appraisal_id && (
                  <div className="mt-8 p-4 rounded-xl"
                    style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
                    <div className="text-xs uppercase tracking-wider font-semibold mb-2" style={{ color: theme.textSecondary }}>
                      Tasación referida
                    </div>
                    <a href={`/tasaciones/${selected.related_appraisal_id}`}
                      className="flex items-center gap-3 p-3 rounded-lg transition-all hover:scale-[1.01]"
                      style={{ background: theme.backgroundSecondary }}>
                      <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ background: `${theme.primary}20` }}>
                        <FileCheck2 className="h-5 w-5" style={{ color: theme.primary }} />
                      </div>
                      <div className="flex-1">
                        <div className="font-semibold text-sm" style={{ color: theme.text }}>
                          Tasación #{selected.related_appraisal_id}
                        </div>
                        <div className="text-xs" style={{ color: theme.textSecondary }}>
                          Abrir detalle →
                        </div>
                      </div>
                    </a>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <MailOpen className="h-12 w-12 mx-auto mb-3" style={{ color: theme.textSecondary }} />
              <div className="text-sm" style={{ color: theme.textSecondary }}>Seleccioná un mensaje para verlo</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TabBtn({ label, count, active, onClick, theme }: any) {
  return (
    <button onClick={onClick}
      className="px-3 py-2 text-xs font-semibold transition-all relative"
      style={{
        color: active ? theme.text : theme.textSecondary,
        borderBottom: `2px solid ${active ? theme.primary : 'transparent'}`,
        marginBottom: '-1px',
      }}>
      {label} <span className="ml-1 px-1.5 rounded-full text-[10px]"
        style={{ background: active ? theme.primary : theme.backgroundSecondary, color: active ? theme.primaryText : theme.text }}>
        {count}
      </span>
    </button>
  );
}
