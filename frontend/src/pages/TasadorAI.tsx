import { useState, useRef, useEffect } from 'react';
import { Send, Bot, User as UserIcon, Sparkles, Loader2 } from 'lucide-react';
import { API_BASE } from '../services/api';
import PageHint from '../components/ui/PageHint';

interface Msg { role: 'user' | 'assistant'; content: string; }

const STARTERS = [
  '¿Cómo ajusto el coeficiente por antigüedad?',
  'Dame una opinión sobre un depto de 3 amb. en Palermo de 95m².',
  '¿Qué peso doy a un comparable a 800m de distancia?',
  'Explicame el método de homogeneización paso a paso.',
];

export default function TasadorAI() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [msgs]);

  const send = async (textOverride?: string) => {
    const text = textOverride ?? input;
    if (!text.trim() || busy) return;
    const userMsg: Msg = { role: 'user', content: text };
    setMsgs(m => [...m, userMsg, { role: 'assistant', content: '' }]);
    setInput('');
    setBusy(true);

    try {
      const token = localStorage.getItem('tasar_token');
      const res = await fetch(`${API_BASE}/ai/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });
      if (!res.body) throw new Error('No stream');

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6);
          if (data === '[DONE]') continue;
          const text = data.replace(/\\n/g, '\n');
          setMsgs(m => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (last.role === 'assistant') last.content += text;
            return copy;
          });
        }
      }
    } catch (e) {
      setMsgs(m => {
        const copy = [...m];
        copy[copy.length - 1] = { role: 'assistant', content: '[Error de conexión con el Tasador AI]' };
        return copy;
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-bg-app">
      <header className="flex-shrink-0 px-8 py-4 border-b border-border-base bg-bg-card">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-text-primary flex items-center gap-2">
              Tasador AI <Sparkles className="h-4 w-4 text-purple-500" />
            </h1>
            <p className="text-xs text-text-secondary">Asistente experto en valuación inmobiliaria — powered by Claude</p>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-8 py-6">
        <div className="max-w-3xl mx-auto">
          <PageHint pageId="tasador-ai" />
        </div>
        <div className="max-w-3xl mx-auto space-y-4">
          {msgs.length === 0 && (
            <div className="text-center py-12">
              <Sparkles className="h-12 w-12 mx-auto text-purple-500 mb-4" />
              <h2 className="text-2xl font-bold text-text-primary mb-2">Charlá con el Tasador AI</h2>
              <p className="text-text-secondary mb-6">Hacele preguntas técnicas, pedile que analice una propiedad, o que te explique métodos.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl mx-auto">
                {STARTERS.map(s => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left p-4 rounded-xl bg-bg-card border border-border-base hover:border-brand transition-all active:scale-95 text-sm text-text-primary">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {msgs.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''} animate-fade-in`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                m.role === 'user' ? 'bg-brand text-white' : 'bg-gradient-to-br from-purple-600 to-indigo-700 text-white'
              }`}>
                {m.role === 'user' ? <UserIcon className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>
              <div className={`max-w-[80%] p-4 rounded-2xl ${
                m.role === 'user'
                  ? 'bg-brand text-white rounded-tr-sm'
                  : 'bg-bg-card border border-border-base text-text-primary rounded-tl-sm'
              }`}>
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {m.content || (busy && i === msgs.length - 1 ? <Loader2 className="h-4 w-4 animate-spin" /> : '')}
                </div>
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-border-base bg-bg-card p-4">
        <div className="max-w-3xl mx-auto flex gap-2">
          <input value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            placeholder="Preguntale lo que quieras..." disabled={busy}
            className="flex-1 px-4 py-3 rounded-xl border border-border-base bg-bg-app text-text-primary focus:outline-none focus:ring-2 focus:ring-brand disabled:opacity-50" />
          <button onClick={() => send()} disabled={busy || !input.trim()}
            className="px-5 py-3 rounded-xl bg-brand hover:bg-brand-hover text-white font-medium flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            Enviar
          </button>
        </div>
      </div>
    </div>
  );
}
