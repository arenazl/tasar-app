import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  MessageSquare, Send, Search, Phone, ArrowLeft, RefreshCw, CheckCheck,
  Bot, UserCheck, Hand, Circle, Mic, Square,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';

// ── Tipos ────────────────────────────────────────────────────────────────
type ConvStatus = 'nueva' | 'abierta' | 'cerrada' | 'bloqueada';

interface ConvRow {
  id: number;
  phone_jid: string;
  contact_name?: string | null;
  client_id?: number | null;
  assignee_id?: number | null;
  assignee_name?: string | null;
  status: ConvStatus;
  unread_count: number;
  bot_paused_until?: string | null;
  bot_paused: boolean;
  voice_mode?: string | null;
  last_activity_at?: string | null;
  last_message?: string | null;
  last_direction?: 'inbound' | 'outbound' | null;
}

interface ConvMessage {
  id: number;
  direction: 'inbound' | 'outbound';
  type: string;
  content?: string | null;
  media_url?: string | null;
  sender_id?: number | null;
  created_at?: string | null;
}

interface ConvDetail extends ConvRow {
  messages: ConvMessage[];
}

interface Assignee { id: number; full_name: string; role: string; }

type Filter = 'todas' | 'mias' | 'nuevas' | 'sin_asignar';

const STATUS_META: Record<ConvStatus, { label: string; color: string }> = {
  nueva: { label: 'Nueva', color: '#f97316' },
  abierta: { label: 'Abierta', color: '#3b82f6' },
  cerrada: { label: 'Cerrada', color: '#10b981' },
  bloqueada: { label: 'Bloqueada', color: '#6b7280' },
};

function phoneFromJid(jid: string): string {
  const digits = (jid || '').split('@')[0].replace(/[^0-9+]/g, '');
  return digits || jid;
}
function timeAgo(iso?: string | null): string {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return 'recién';
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  if (diff < 7 * 86400) return `${Math.floor(diff / 86400)}d`;
  return new Date(iso).toLocaleDateString('es-AR');
}
function formatHora(iso?: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' });
}
function formatFecha(iso?: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
}

const POLL_MS = 30_000;

export default function InboxWhatsApp() {
  const { user } = useAuth();
  const { theme } = useTheme();
  const [searchParams, setSearchParams] = useSearchParams();

  const [convs, setConvs] = useState<ConvRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const q = searchParams.get('conv');
    return q ? parseInt(q, 10) : null;
  });
  const [detail, setDetail] = useState<ConvDetail | null>(null);
  const [filter, setFilter] = useState<Filter>('todas');
  const [search, setSearch] = useState('');
  const [assignees, setAssignees] = useState<Assignee[]>([]);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [sendingAudio, setSendingAudio] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const audioStreamRef = useRef<MediaStream | null>(null);

  const isManager = user?.role === 'supervisor' || user?.role === 'admin';

  const load = useCallback(async () => {
    try {
      const r = await api.get<ConvRow[]>('/conversations');
      setConvs(r.data);
    } catch { toast.error('Error al cargar el inbox'); }
    finally { setLoading(false); }
  }, []);

  const loadDetail = useCallback(async (id: number) => {
    try {
      const r = await api.get<ConvDetail>(`/conversations/${id}`);
      setDetail(r.data);
      if (r.data.unread_count > 0) {
        await api.post(`/conversations/${id}/mark-read`);
        setConvs((cs) => cs.map((c) => (c.id === id ? { ...c, unread_count: 0 } : c)));
      }
    } catch { toast.error('Error al cargar la conversación'); }
  }, []);

  useEffect(() => {
    load();
    api.get<Assignee[]>('/conversations/assignees').then((r) => setAssignees(r.data)).catch(() => {});
    const t = setInterval(load, POLL_MS);
    return () => clearInterval(t);
  }, [load]);

  // Deep-link ?conv=X y auto-selección de la primera en desktop.
  useEffect(() => {
    if (loading || convs.length === 0) return;
    const fromQuery = searchParams.get('conv');
    if (fromQuery) {
      const id = parseInt(fromQuery, 10);
      if (convs.some((c) => c.id === id)) {
        setSelectedId(id);
        searchParams.delete('conv');
        setSearchParams(searchParams, { replace: true });
        return;
      }
    }
    if (selectedId === null && typeof window !== 'undefined' && window.innerWidth >= 1024) {
      setSelectedId(convs[0].id);
    }
  }, [loading, convs, selectedId, searchParams, setSearchParams]);

  useEffect(() => { if (selectedId) loadDetail(selectedId); }, [selectedId, loadDetail]);

  // Re-cargar el detalle en cada poll si hay una conv abierta (mensajes nuevos).
  useEffect(() => {
    if (!selectedId) return;
    const t = setInterval(() => loadDetail(selectedId), POLL_MS);
    return () => clearInterval(t);
  }, [selectedId, loadDetail]);

  useEffect(() => {
    if (detail?.messages.length) messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [detail?.messages.length]);

  const filtered = useMemo(() => {
    let list = convs;
    if (filter === 'mias') list = list.filter((c) => c.assignee_id === user?.id);
    else if (filter === 'nuevas') list = list.filter((c) => c.status === 'nueva');
    else if (filter === 'sin_asignar') list = list.filter((c) => !c.assignee_id);
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((c) =>
        (c.contact_name ?? '').toLowerCase().includes(q) ||
        c.phone_jid.toLowerCase().includes(q) ||
        (c.last_message ?? '').toLowerCase().includes(q));
    }
    return list;
  }, [convs, filter, search, user]);

  const counts = useMemo(() => ({
    todas: convs.length,
    mias: convs.filter((c) => c.assignee_id === user?.id).length,
    nuevas: convs.filter((c) => c.status === 'nueva').length,
    sin_asignar: convs.filter((c) => !c.assignee_id).length,
  }), [convs, user]);

  const handleSend = async () => {
    if (!detail || !draft.trim() || sending) return;
    setSending(true);
    try {
      const r = await api.post(`/conversations/${detail.id}/reply`, { contenido: draft.trim() });
      if (!r.data?.sent_via_gateway) toast.warning('Guardado, pero el gateway no confirmó el envío');
      setDraft('');
      await loadDetail(detail.id);
      load();
    } catch { toast.error('No se pudo enviar'); }
    finally { setSending(false); }
  };

  // Nota de voz del vendedor (press-and-hold, WO F3-01). Se sube tal cual se
  // grabo -- sin TTS -- por `/conversations/{id}/reply-audio`.
  const stopStream = () => {
    audioStreamRef.current?.getTracks().forEach((t) => t.stop());
    audioStreamRef.current = null;
  };

  const startRecording = async () => {
    if (!detail || recording || sendingAudio || detail.status === 'bloqueada') return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus' : 'audio/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      audioChunksRef.current = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      recorder.onstop = async () => {
        stopStream();
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        audioChunksRef.current = [];
        if (blob.size < 500) return; // grabacion demasiado corta (toque accidental)
        setSendingAudio(true);
        try {
          const form = new FormData();
          form.append('file', blob, 'nota-de-voz.webm');
          const r = await api.post(`/conversations/${detail.id}/reply-audio`, form);
          if (!r.data?.sent_via_gateway) toast.warning('Guardado, pero el gateway no confirmó el envío');
          await loadDetail(detail.id);
          load();
        } catch { toast.error('No se pudo enviar la nota de voz'); }
        finally { setSendingAudio(false); }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      toast.error('No se pudo acceder al micrófono');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setRecording(false);
  };

  useEffect(() => () => { stopStream(); }, []);

  const takeControl = async () => {
    if (!detail || busy) return;
    setBusy(true);
    try {
      await api.post(`/conversations/${detail.id}/assign-me`);
      toast.success('Tomaste el mando · bot pausado');
      await loadDetail(detail.id);
      load();
    } catch { toast.error('No se pudo tomar el mando'); }
    finally { setBusy(false); }
  };

  const reactivateBot = async () => {
    if (!detail || busy) return;
    setBusy(true);
    try {
      await api.post(`/conversations/${detail.id}/reactivate-bot`);
      toast.success('Bot reactivado');
      await loadDetail(detail.id);
      load();
    } catch { toast.error('No se pudo reactivar el bot'); }
    finally { setBusy(false); }
  };

  const changeAssignee = async (assigneeId: number | null) => {
    if (!detail) return;
    try {
      await api.patch(`/conversations/${detail.id}`, { assignee_id: assigneeId });
      await loadDetail(detail.id);
      load();
      toast.success(assigneeId ? 'Asignada' : 'Desasignada');
    } catch { toast.error('No se pudo asignar'); }
  };

  const changeStatus = async (status: ConvStatus) => {
    if (!detail) return;
    try {
      await api.patch(`/conversations/${detail.id}`, { status });
      await loadDetail(detail.id);
      load();
    } catch { toast.error('No se pudo cambiar el estado'); }
  };

  const showListOnMobile = selectedId === null;

  return (
    <div className="h-full flex min-h-0" style={{ background: theme.background }}>
      {/* Lista */}
      <aside
        className={`flex-shrink-0 flex-col lg:flex lg:w-96 ${showListOnMobile ? 'flex w-full' : 'hidden lg:flex'}`}
        style={{ background: theme.card, borderRight: `1px solid ${theme.border}` }}
      >
        <div className="flex-shrink-0 p-4" style={{ borderBottom: `1px solid ${theme.border}` }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black tracking-tight" style={{ color: theme.text }}>WhatsApp</h1>
              <span className="text-[11px] px-1.5 py-0.5 rounded-full font-bold"
                style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>{convs.length}</span>
            </div>
            <button onClick={load} className="p-2 rounded-lg transition-all active:scale-95"
              style={{ background: theme.backgroundSecondary, color: theme.textSecondary }} title="Refrescar">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4" style={{ color: theme.textSecondary }} />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Buscar nombre, teléfono…"
              className="w-full h-10 pl-10 pr-3 rounded-lg text-base lg:text-sm focus:outline-none"
              style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}`, color: theme.text }} />
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(['todas', 'mias', 'nuevas', 'sin_asignar'] as Filter[]).map((f) => {
              const labels: Record<Filter, string> = { todas: 'Todas', mias: 'Mías', nuevas: 'Nuevas', sin_asignar: 'Sin asignar' };
              const active = filter === f;
              return (
                <button key={f} onClick={() => setFilter(f)}
                  className="px-2.5 py-1 rounded-full text-xs font-semibold transition-all active:scale-95"
                  style={{
                    background: active ? theme.primary : theme.backgroundSecondary,
                    color: active ? theme.primaryText : theme.textSecondary,
                  }}>
                  {labels[f]} <span className="opacity-70">{counts[f]}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          {loading && <div className="p-8 text-center text-sm" style={{ color: theme.textSecondary }}>Cargando…</div>}
          {!loading && filtered.length === 0 && (
            <div className="p-8 text-center text-sm" style={{ color: theme.textSecondary }}>Sin conversaciones.</div>
          )}
          {!loading && filtered.map((c) => {
            const isSelected = c.id === selectedId;
            const sm = STATUS_META[c.status];
            const name = c.contact_name || phoneFromJid(c.phone_jid);
            return (
              <button key={c.id} onClick={() => setSelectedId(c.id)}
                className="w-full flex items-start gap-3 p-3 text-left transition-all"
                style={{
                  background: isSelected ? `${theme.primary}12` : 'transparent',
                  borderLeft: `3px solid ${isSelected ? theme.primary : 'transparent'}`,
                  borderBottom: `1px solid ${theme.border}`,
                }}>
                <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm"
                  style={{ background: theme.backgroundSecondary, color: theme.text }}>
                  {name.slice(0, 2).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-sm truncate" style={{ color: theme.text }}>{name}</span>
                    <span className="flex-shrink-0 text-[10px]" style={{ color: theme.textSecondary }}>{timeAgo(c.last_activity_at)}</span>
                  </div>
                  <div className="flex items-center gap-1 mt-0.5">
                    {c.last_direction === 'outbound' && <CheckCheck className="h-3 w-3 flex-shrink-0" style={{ color: theme.primary }} />}
                    <span className="text-xs truncate" style={{ color: theme.textSecondary }}>{c.last_message || '(sin mensajes)'}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded font-semibold"
                      style={{ background: `${sm.color}1f`, color: sm.color }}>{sm.label}</span>
                    {c.bot_paused && (
                      <span className="inline-flex items-center gap-1 text-[10px]" style={{ color: theme.textSecondary }}>
                        <Hand className="h-2.5 w-2.5" /> humano
                      </span>
                    )}
                    {c.assignee_name && <span className="text-[10px] truncate" style={{ color: theme.textSecondary }}>{c.assignee_name}</span>}
                    {c.unread_count > 0 && (
                      <span className="ml-auto inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full text-[10px] font-bold px-1"
                        style={{ background: theme.primary, color: theme.primaryText }}>{c.unread_count}</span>
                    )}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </aside>

      {/* Chat */}
      <main className={`flex-1 min-w-0 flex-col lg:flex ${selectedId === null ? 'hidden lg:flex' : 'flex'}`}
        style={{ background: theme.background }}>
        {!detail ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-8" style={{ color: theme.textSecondary }}>
            <MessageSquare className="h-12 w-12 mb-3" style={{ color: theme.primary }} />
            <p className="text-sm">Seleccioná una conversación de la izquierda</p>
          </div>
        ) : (
          <>
            <header className="flex-shrink-0 flex items-center gap-2 p-3"
              style={{ background: theme.card, borderBottom: `1px solid ${theme.border}`, paddingTop: 'max(0.75rem, env(safe-area-inset-top))' }}>
              <button onClick={() => setSelectedId(null)}
                className="lg:hidden flex-shrink-0 p-2 -ml-1 rounded-lg active:scale-95" style={{ color: theme.textSecondary }} aria-label="Volver">
                <ArrowLeft className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-semibold"
                  style={{ background: theme.backgroundSecondary, color: theme.text }}>
                  {(detail.contact_name || phoneFromJid(detail.phone_jid)).slice(0, 2).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="font-semibold truncate" style={{ color: theme.text }}>
                    {detail.contact_name || 'Sin nombre'}
                  </div>
                  <div className="flex items-center gap-2 text-xs truncate" style={{ color: theme.textSecondary }}>
                    <Phone className="h-3 w-3 flex-shrink-0" />
                    <span className="truncate">{phoneFromJid(detail.phone_jid)}</span>
                    {detail.client_id && <span className="hidden sm:inline">· Cliente #{detail.client_id}</span>}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {detail.bot_paused ? (
                  <button onClick={reactivateBot} disabled={busy}
                    className="text-xs px-2.5 py-1.5 rounded inline-flex items-center gap-1.5 active:scale-95 disabled:opacity-50 font-semibold"
                    style={{ border: `1px solid ${theme.border}`, color: theme.textSecondary }} title="Reactivar el bot en esta conversación">
                    <Bot className="h-3.5 w-3.5" /> Reactivar bot
                  </button>
                ) : (
                  <button onClick={takeControl} disabled={busy}
                    className="text-xs px-2.5 py-1.5 rounded inline-flex items-center gap-1.5 active:scale-95 disabled:opacity-50 font-semibold text-white"
                    style={{ background: theme.primary, color: theme.primaryText }} title="Tomar el mando y pausar el bot">
                    <Hand className="h-3.5 w-3.5" /> Tomar mando
                  </button>
                )}
                {isManager && (
                  <select value={detail.assignee_id ?? ''} onChange={(e) => changeAssignee(e.target.value ? Number(e.target.value) : null)}
                    className="hidden sm:block text-xs px-2 py-1.5 rounded border bg-transparent"
                    style={{ borderColor: theme.border, color: theme.text }}>
                    <option value="">Sin asignar</option>
                    {assignees.map((a) => <option key={a.id} value={a.id}>{a.full_name}</option>)}
                  </select>
                )}
                <select value={detail.status} onChange={(e) => changeStatus(e.target.value as ConvStatus)}
                  className="hidden sm:block text-xs px-2 py-1.5 rounded border bg-transparent"
                  style={{ borderColor: theme.border, color: theme.text }}>
                  <option value="nueva">Nueva</option>
                  <option value="abierta">Abierta</option>
                  <option value="cerrada">Cerrada</option>
                  <option value="bloqueada">Bloqueada</option>
                </select>
              </div>
            </header>

            {/* Barra de estado del bot */}
            <div className="flex-shrink-0 px-4 py-1.5 text-[11px] flex items-center gap-2"
              style={{ background: theme.card, borderBottom: `1px solid ${theme.border}`, color: theme.textSecondary }}>
              {detail.bot_paused ? (
                <><Hand className="h-3 w-3" /> Atendida por un humano · el bot no responde{detail.assignee_name ? ` · ${detail.assignee_name}` : ''}</>
              ) : (
                <><Bot className="h-3 w-3" style={{ color: theme.primary }} /> El bot está atendiendo esta conversación</>
              )}
            </div>

            {/* Mensajes */}
            <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
              {detail.messages.map((m, idx) => {
                const isOut = m.direction === 'outbound';
                const prevDate = idx > 0 ? new Date(detail.messages[idx - 1].created_at || '').toDateString() : '';
                const thisDate = new Date(m.created_at || '').toDateString();
                const showSep = prevDate !== thisDate;
                return (
                  <div key={m.id}>
                    {showSep && (
                      <div className="text-center my-3">
                        <span className="text-[10px] uppercase tracking-wider px-2 py-1 rounded"
                          style={{ background: theme.card, color: theme.textSecondary }}>{formatFecha(m.created_at)}</span>
                      </div>
                    )}
                    <div className={`flex ${isOut ? 'justify-end' : 'justify-start'}`}>
                      <div className="max-w-[85%] md:max-w-[70%] rounded-2xl px-3 py-2 shadow-sm"
                        style={{
                          background: isOut ? theme.primary : theme.card,
                          color: isOut ? theme.primaryText : theme.text,
                          borderTopRightRadius: isOut ? '0.25rem' : '1rem',
                          borderTopLeftRadius: isOut ? '1rem' : '0.25rem',
                        }}>
                        {m.type === 'audio' && m.media_url
                          ? <audio controls src={m.media_url} preload="none" className="w-full max-w-xs" style={{ height: 36 }} />
                          : <div className="text-sm whitespace-pre-wrap break-words">{m.content}</div>}
                        <div className="flex items-center gap-1 justify-end mt-1 text-[10px] opacity-70">
                          {isOut && (m.sender_id ? <UserCheck className="h-3 w-3" /> : <Bot className="h-3 w-3" />)}
                          <span>{formatHora(m.created_at)}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>

            {/* Composer */}
            <footer className="flex-shrink-0 p-3"
              style={{ background: theme.card, borderTop: `1px solid ${theme.border}`, paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
              <div className="flex items-end gap-2">
                <textarea rows={1} value={draft}
                  onChange={(e) => {
                    setDraft(e.target.value);
                    const el = e.target as HTMLTextAreaElement;
                    el.style.height = 'auto';
                    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
                  }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey && !('ontouchstart' in window)) { e.preventDefault(); handleSend(); } }}
                  placeholder={detail.status === 'bloqueada' ? 'Conversación bloqueada' : 'Escribí un mensaje…'}
                  disabled={detail.status === 'bloqueada' || sending}
                  className="flex-1 px-3 py-2.5 rounded-2xl border focus:outline-none disabled:opacity-50 text-base md:text-sm resize-none"
                  style={{ background: theme.background, borderColor: theme.border, color: theme.text, minHeight: 44 }} />
                {draft.trim() ? (
                  <button onClick={handleSend} disabled={sending || detail.status === 'bloqueada'}
                    className="flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full transition-all active:scale-95 disabled:opacity-40"
                    style={{ background: theme.primary, color: theme.primaryText }} aria-label="Enviar">
                    <Send className="h-5 w-5" />
                  </button>
                ) : (
                  <button
                    onMouseDown={startRecording}
                    onMouseUp={stopRecording}
                    onMouseLeave={() => { if (recording) stopRecording(); }}
                    onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
                    onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
                    disabled={sendingAudio || detail.status === 'bloqueada'}
                    className={`flex-shrink-0 flex items-center justify-center w-11 h-11 rounded-full transition-all active:scale-95 disabled:opacity-40 select-none ${recording ? 'animate-pulse' : ''}`}
                    style={{ background: recording ? '#ef4444' : theme.primary, color: theme.primaryText }}
                    aria-label="Mantener presionado para grabar una nota de voz"
                    title="Mantener presionado para grabar">
                    {recording ? <Square className="h-4 w-4" /> : <Mic className="h-5 w-5" />}
                  </button>
                )}
              </div>
              <div className="mt-1.5 text-[10px] flex items-center gap-1" style={{ color: theme.textSecondary }}>
                {recording ? (
                  <><Circle className="h-2 w-2 text-red-500" /> Grabando… soltá para enviar.</>
                ) : sendingAudio ? (
                  <><Circle className="h-2 w-2" /> Enviando nota de voz…</>
                ) : (
                  <><Circle className="h-2 w-2" /> Responder toma el mando y pausa el bot 45 min.</>
                )}
              </div>
            </footer>
          </>
        )}
      </main>
    </div>
  );
}
