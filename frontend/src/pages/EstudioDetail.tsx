import { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Plus, Calculator, Globe, MessageSquare, Users, Sparkles,
  TrendingUp, ListChecks, X, Check, RefreshCw, Bot, Pencil,
} from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import { ABMCollapsible, ABMInfoPanel, ABMBadge } from '../components/ui/ABMPage';
import { WizardModal, type WizardStep } from '../components/ui/WizardModal';
import { ModernSelect } from '../components/ui/ModernSelect';
import { useTheme } from '../contexts/ThemeContext';
import type { MarketStudy, Comparable } from '../types';

interface Suggestion {
  candidate_id: number;
  candidate_kind: 'workspace' | 'external';
  include: boolean;
  similarity_reason: string;
  reject_reason?: string;
  similarity_score: number;
  candidate: any;
  adjustments: { factor: string; coefficient: number; description?: string }[];
}

interface SuggestionsResponse {
  candidates_evaluated: number;
  ai_evaluated: boolean;
  fallback_used: boolean;
  workspace_candidates: number;
  external_candidates: number;
  suggestions: Suggestion[];
  message?: string;
}

const CONDITION_OPTIONS = [
  { value: '', label: '—' },
  { value: 'a_estrenar', label: 'A estrenar' },
  { value: 'excelente', label: 'Excelente' },
  { value: 'muy_bueno', label: 'Muy bueno' },
  { value: 'bueno', label: 'Bueno' },
  { value: 'regular', label: 'Regular' },
  { value: 'a_reciclar', label: 'A reciclar' },
];

const emptyComp: any = {
  source: 'manual', title: '', address: '',
  total_area_m2: '', covered_area_m2: '', rooms: '', bedrooms: '', bathrooms: '',
  age_years: '', condition: '', price: '', currency: 'USD', source_url: '',
};

export default function EstudioDetail() {
  const { id } = useParams();
  const { theme } = useTheme();
  const [study, setStudy] = useState<MarketStudy | null>(null);
  const [loading, setLoading] = useState(true);

  // AI sugerencias
  const [aiLoading, setAiLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [suggestMeta, setSuggestMeta] = useState<{
    ai_evaluated: boolean; workspace: number; external: number; msg?: string;
  } | null>(null);
  const [acceptingId, setAcceptingId] = useState<number | null>(null);

  // Wizard manual / URL
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(0);
  const [comp, setComp] = useState<any>(emptyComp);
  const [scrapeUrl, setScrapeUrl] = useState('');
  const [scraping, setScraping] = useState(false);
  const [savingComp, setSavingComp] = useState(false);

  // Colaboración
  const [consensus, setConsensus] = useState<any>(null);
  const [opinion, setOpinion] = useState('');
  const [comments, setComments] = useState<any[]>([]);
  const [newComment, setNewComment] = useState('');

  const isIAFirst = study?.method === 'ai_score' || study?.method === 'hybrid';

  const loadStudy = useCallback(async () => {
    try {
      const r = await api.get<MarketStudy>(`/market-studies/${id}`);
      setStudy(r.data);
    } catch { toast.error('Error cargando estudio'); }
  }, [id]);

  const loadCollab = useCallback(async () => {
    try {
      const [c, com] = await Promise.all([
        api.get(`/collaboration/${id}/consensus`),
        api.get(`/collaboration/${id}/comments`),
      ]);
      setConsensus(c.data);
      setComments(com.data);
    } catch {}
  }, [id]);

  const fetchSuggestions = useCallback(async () => {
    if (!id) return;
    setAiLoading(true);
    try {
      const r = await api.post<SuggestionsResponse>(`/market-studies/${id}/suggest-comparables`, {}, { timeout: 300000 });
      const data = r.data;
      // Filtrar IDs ya aceptados como comparables
      const acceptedSourceIds = new Set<string>();
      study?.comparables.forEach(c => {
        if ((c as any).source_property_id) acceptedSourceIds.add(`workspace:${(c as any).source_property_id}`);
        if ((c as any).external_listing_id) acceptedSourceIds.add(`external:${(c as any).external_listing_id}`);
      });
      const filtered = data.suggestions.filter(s =>
        !acceptedSourceIds.has(`${s.candidate_kind}:${s.candidate_id}`)
      );
      setSuggestions(filtered);
      setSuggestMeta({
        ai_evaluated: data.ai_evaluated,
        workspace: data.workspace_candidates,
        external: data.external_candidates,
        msg: data.message,
      });
      if (filtered.length === 0 && data.message) {
        toast.info(data.message);
      } else if (data.ai_evaluated) {
        toast.success(`Claude analizó ${data.candidates_evaluated} candidatos`);
      } else {
        toast.info('Sugerencias rankeadas (sin evaluación IA)');
      }
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error al pedir sugerencias');
    } finally {
      setAiLoading(false);
    }
  }, [id, study?.comparables]);

  // Carga inicial
  useEffect(() => {
    setLoading(true);
    loadStudy().finally(() => setLoading(false));
    loadCollab();
  }, [loadStudy, loadCollab]);

  // Auto-trigger sugerencias cuando el método es IA + estudio sin comparables aún
  useEffect(() => {
    if (study && isIAFirst && study.comparables.length === 0 && suggestions.length === 0 && !aiLoading && !suggestMeta) {
      fetchSuggestions();
    }
  }, [study, isIAFirst, suggestions.length, aiLoading, suggestMeta, fetchSuggestions]);

  const acceptSuggestion = async (s: Suggestion) => {
    setAcceptingId(s.candidate_id);
    try {
      await api.post(`/market-studies/${id}/accept-suggestion`, {
        candidate_id: s.candidate_id,
        candidate_kind: s.candidate_kind,
        similarity_reason: s.similarity_reason,
        adjustments: s.adjustments,
      });
      toast.success('Comparable agregado');
      setSuggestions(prev => prev.filter(x => !(x.candidate_id === s.candidate_id && x.candidate_kind === s.candidate_kind)));
      await loadStudy();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Error');
    } finally {
      setAcceptingId(null);
    }
  };

  const rejectSuggestion = (s: Suggestion) => {
    setSuggestions(prev => prev.filter(x => !(x.candidate_id === s.candidate_id && x.candidate_kind === s.candidate_kind)));
  };

  const updateSuggestionAdjustment = (s: Suggestion, idx: number, coef: number) => {
    setSuggestions(prev => prev.map(x => {
      if (x.candidate_id !== s.candidate_id || x.candidate_kind !== s.candidate_kind) return x;
      const adjs = [...x.adjustments];
      adjs[idx] = { ...adjs[idx], coefficient: coef };
      return { ...x, adjustments: adjs };
    }));
  };

  const deleteComparable = async (c: Comparable) => {
    try {
      await api.delete(`/market-studies/${id}/comparables/${c.id}`);
      toast.success('Comparable eliminado');
      await loadStudy();
    } catch { toast.error('Error al eliminar'); }
  };

  const recalc = async () => {
    try {
      await api.post(`/market-studies/${id}/recalc`);
      toast.success('Recalculado');
      await loadStudy();
    } catch { toast.error('Error al recalcular'); }
  };

  // ====== Wizard: agregar comparable manual / URL ======
  const doScrape = async () => {
    if (!scrapeUrl) return toast.error('Ingresá una URL');
    setScraping(true);
    toast.info('Claude extrayendo datos del portal…');
    try {
      const r = await api.post('/scraping/extract', { url: scrapeUrl }, { timeout: 300000 });
      const d = r.data.extracted || {};
      setComp({ ...emptyComp, ...d, source_url: scrapeUrl, source: 'scraped', title: d.title || `Listing ${new URL(scrapeUrl).hostname}` });
      toast.success('Datos extraídos — revisalos antes de guardar');
      setWizardStep(1);
    } catch { toast.error('No se pudo extraer'); }
    finally { setScraping(false); }
  };

  const saveCompManual = async () => {
    const payload: any = { ...comp };
    ['total_area_m2','covered_area_m2','rooms','bedrooms','bathrooms','age_years','price']
      .forEach(k => { if (payload[k] === '' || payload[k] == null) delete payload[k]; else payload[k] = Number(payload[k]); });
    if (!payload.title || !payload.price) return toast.error('Faltan título y precio');
    setSavingComp(true);
    try {
      await api.post(`/market-studies/${id}/comparables`, { ...payload, adjustments: [] });
      toast.success('Comparable agregado');
      setWizardOpen(false);
      setComp(emptyComp);
      await loadStudy();
    } catch (e: any) { toast.error(e.response?.data?.detail || 'Error'); }
    finally { setSavingComp(false); }
  };

  // ====== Colaboración ======
  const submitOpinion = async () => {
    const v = Number(opinion);
    if (!v) return;
    await api.post(`/collaboration/${id}/opinion`, { opinion_value: v });
    toast.success('Opinión registrada');
    setOpinion('');
    api.get(`/collaboration/${id}/consensus`).then(c => setConsensus(c.data));
  };
  const submitComment = async () => {
    if (!newComment.trim()) return;
    await api.post(`/collaboration/${id}/comments`, { body: newComment });
    setNewComment('');
    api.get(`/collaboration/${id}/comments`).then(c => setComments(c.data));
  };

  if (loading || !study) {
    return (
      <div className="p-8 max-w-7xl mx-auto">
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <div className="relative h-16 w-16 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full blur-2xl opacity-50 animate-pulse"
              style={{ background: theme.primary }} />
            <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-t-transparent"
              style={{ borderColor: `${theme.primary}22`, borderTopColor: theme.primary, animationDuration: '1.2s' }} />
            <Sparkles className="h-7 w-7 relative" style={{ color: theme.primary }} />
          </div>
          <p className="text-xs tracking-wider uppercase font-medium" style={{ color: theme.textSecondary }}>
            Cargando estudio…
          </p>
        </div>
      </div>
    );
  }

  const conf = Math.round((study.confidence_score || 0) * 100);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      <Link to="/estudios" className="inline-flex items-center gap-1 text-sm mb-4 transition-all hover:gap-2" style={{ color: theme.textSecondary }}>
        <ArrowLeft className="h-4 w-4" /> Volver a Estudios
      </Link>

      <header className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h1 className="text-3xl font-bold" style={{ color: theme.text }}>Estudio #{study.id}</h1>
            <ABMBadge label={study.status} active={study.status === 'published'} activeLabel={study.status} />
            {isIAFirst && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider"
                style={{ background: `${theme.primary}15`, color: theme.primary }}>
                <Sparkles className="h-3 w-3" /> Asistido por IA
              </span>
            )}
          </div>
          <p className="text-sm" style={{ color: theme.textSecondary }}>
            Método <b className="capitalize">{study.method.replace(/_/g,' ')}</b> · {study.comparables.length} comparables
          </p>
        </div>
        <div className="flex gap-2">
          {isIAFirst && (
            <button onClick={fetchSuggestions} disabled={aiLoading}
              className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95 disabled:opacity-50"
              style={{ background: theme.primary, color: theme.primaryText }}>
              <Sparkles className={`h-4 w-4 ${aiLoading ? 'animate-pulse' : ''}`} />
              {aiLoading ? 'Analizando…' : 'Sugerir con IA'}
            </button>
          )}
          <button onClick={() => { setComp(emptyComp); setScrapeUrl(''); setWizardStep(0); setWizardOpen(true); }}
            className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Plus className="h-4 w-4" /> Manual / URL
          </button>
          <button onClick={recalc}
            className="px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-all active:scale-95"
            style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}>
            <Calculator className="h-4 w-4" /> Recalcular
          </button>
        </div>
      </header>

      {/* Valor sugerido */}
      {study.suggested_value_mode != null && (
        <div className="mb-6 p-6 rounded-2xl text-white shadow-xl animate-fade-in"
          style={{ background: `linear-gradient(135deg, ${theme.success}, #14b8a6)` }}>
          <div className="text-sm opacity-80 mb-1">Valor sugerido (modo)</div>
          <div className="text-4xl font-bold mb-2">USD {Number(study.suggested_value_mode).toLocaleString()}</div>
          <div className="flex gap-6 text-sm flex-wrap">
            <span>Rango: USD {Number(study.suggested_value_min).toLocaleString()} – {Number(study.suggested_value_max).toLocaleString()}</span>
            <span className="px-2 py-0.5 rounded-full bg-white/20 backdrop-blur text-xs font-semibold">Confianza {conf}%</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* ============ PANEL DE SUGERENCIAS IA ============ */}
          {isIAFirst && (
            <SuggestionsPanel
              loading={aiLoading}
              suggestions={suggestions}
              meta={suggestMeta}
              method={study.method}
              acceptingId={acceptingId}
              onAccept={acceptSuggestion}
              onReject={rejectSuggestion}
              onUpdateAdjustment={updateSuggestionAdjustment}
              onRefresh={fetchSuggestions}
            />
          )}

          {/* ============ COMPARABLES ACEPTADOS ============ */}
          <section>
            <h2 className="font-semibold flex items-center gap-2 mb-3" style={{ color: theme.text }}>
              <ListChecks className="h-5 w-5" style={{ color: theme.primary }} />
              Comparables del estudio
              <span className="text-sm font-normal" style={{ color: theme.textSecondary }}>
                ({study.comparables.length})
              </span>
            </h2>
            {study.comparables.length === 0 && (
              <div className="p-8 rounded-xl text-center" style={{ background: theme.card, border: `2px dashed ${theme.border}`, color: theme.textSecondary }}>
                {isIAFirst
                  ? 'Aceptá sugerencias del panel arriba o agregá comparables manualmente.'
                  : 'Agregá comparables con el botón "Manual / URL".'}
              </div>
            )}
            <div className="space-y-2">
              {study.comparables.map((c, i) => (
                <CompCard key={c.id} c={c} index={i} onDelete={() => deleteComparable(c)} />
              ))}
            </div>
          </section>
        </div>

        {/* ============ SIDEBAR colaboración ============ */}
        <div className="space-y-4">
          <ABMCollapsible title="Consenso multi-tasador" icon={<Users className="h-4 w-4" />} variant="default" defaultOpen>
            {consensus && consensus.participants > 0 ? (
              <div className="space-y-1.5 text-sm">
                <Row k="Participantes" v={consensus.participants} />
                {consensus.avg_value && <Row k="Promedio" v={`USD ${Math.round(consensus.avg_value).toLocaleString()}`} />}
                {consensus.min_value && <Row k="Mín / Máx" v={`USD ${Math.round(consensus.min_value).toLocaleString()} – ${Math.round(consensus.max_value).toLocaleString()}`} />}
                {consensus.agreement_score != null && (
                  <Row k="Acuerdo" v={
                    <span className="font-semibold" style={{ color: consensus.agreement_score >= 0.7 ? theme.success : theme.warning }}>
                      {Math.round(consensus.agreement_score * 100)}%
                    </span>
                  } />
                )}
              </div>
            ) : (
              <div className="text-sm" style={{ color: theme.textSecondary }}>Sin opiniones todavía</div>
            )}
            <div className="mt-3 pt-3" style={{ borderTop: `1px solid ${theme.border}` }}>
              <label className="block text-xs font-medium mb-1" style={{ color: theme.text }}>Tu opinión (USD)</label>
              <div className="flex gap-2">
                <input type="number" value={opinion} onChange={e => setOpinion(e.target.value)} placeholder="150000"
                  className="flex-1 px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2"
                  style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
                <button onClick={submitOpinion}
                  className="px-3 py-2 rounded-lg text-white text-sm font-medium transition-all active:scale-95"
                  style={{ background: theme.primary }}>Enviar</button>
              </div>
            </div>
          </ABMCollapsible>

          <ABMCollapsible title={`Comentarios (${comments.length})`} icon={<MessageSquare className="h-4 w-4" />} defaultOpen>
            <div className="space-y-2 max-h-64 overflow-y-auto mb-3">
              {comments.length === 0 && <div className="text-sm" style={{ color: theme.textSecondary }}>Sin comentarios</div>}
              {comments.map(c => (
                <div key={c.id} className="text-sm p-2.5 rounded-lg" style={{ background: theme.backgroundSecondary }}>
                  <div style={{ color: theme.text }}>{c.body}</div>
                  <div className="text-xs mt-1" style={{ color: theme.textSecondary }}>{new Date(c.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <input value={newComment} onChange={e => setNewComment(e.target.value)} placeholder="Escribir comentario..."
                onKeyDown={e => e.key === 'Enter' && submitComment()}
                className="flex-1 px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2"
                style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
              <button onClick={submitComment}
                className="px-3 py-2 rounded-lg text-white text-sm transition-all active:scale-95"
                style={{ background: theme.primary }}>Enviar</button>
            </div>
          </ABMCollapsible>
        </div>
      </div>

      {/* ====== WIZARD: agregar comparable manual / scraping ====== */}
      <WizardModal
        open={wizardOpen}
        onClose={() => setWizardOpen(false)}
        title="Agregar comparable"
        steps={[
          {
            id: 'import',
            title: 'Importar',
            description: 'Desde URL o manual',
            icon: <Globe className="h-4 w-4" />,
            isValid: true,
            content: (
              <div className="space-y-4 animate-fade-in">
                <ABMInfoPanel title="Importar desde portal" icon={<Globe className="h-4 w-4" />} variant="info">
                  Pegá la URL de un listing (ZonaProp, Argenprop, MercadoLibre). Claude extrae automáticamente título, precio, m², ambientes y dirección.
                </ABMInfoPanel>
                <div className="flex gap-2">
                  <input value={scrapeUrl} onChange={e => setScrapeUrl(e.target.value)} placeholder="https://www.zonaprop.com.ar/..."
                    className="flex-1 px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2"
                    style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
                  <button onClick={doScrape} disabled={scraping || !scrapeUrl}
                    className="px-4 py-2.5 rounded-lg text-white font-medium transition-all active:scale-95 disabled:opacity-50 flex items-center gap-2"
                    style={{ background: theme.primary }}>
                    <Sparkles className="h-4 w-4" /> {scraping ? 'Extrayendo…' : 'Extraer'}
                  </button>
                </div>
                <div className="text-center text-xs" style={{ color: theme.textSecondary }}>
                  — o saltá este paso y completá manualmente —
                </div>
              </div>
            ),
          },
          {
            id: 'data',
            title: 'Datos',
            description: 'Características del comparable',
            icon: <ListChecks className="h-4 w-4" />,
            isValid: !!(comp.title && comp.price),
            content: (
              <div className="space-y-3 animate-fade-in">
                <Field label="Título" value={comp.title} onChange={(v: any) => setComp({...comp, title: v})} />
                <Field label="Dirección" value={comp.address} onChange={(v: any) => setComp({...comp, address: v})} />
                <div className="grid grid-cols-3 gap-3">
                  <Field label="m² totales" type="number" value={comp.total_area_m2} onChange={(v: any) => setComp({...comp, total_area_m2: v})} />
                  <Field label="m² cubiertos" type="number" value={comp.covered_area_m2} onChange={(v: any) => setComp({...comp, covered_area_m2: v})} />
                  <Field label="Antigüedad" type="number" value={comp.age_years} onChange={(v: any) => setComp({...comp, age_years: v})} />
                </div>
                <div className="grid grid-cols-3 gap-3">
                  <Field label="Ambientes" type="number" value={comp.rooms} onChange={(v: any) => setComp({...comp, rooms: v})} />
                  <Field label="Dormitorios" type="number" value={comp.bedrooms} onChange={(v: any) => setComp({...comp, bedrooms: v})} />
                  <Field label="Baños" type="number" value={comp.bathrooms} onChange={(v: any) => setComp({...comp, bathrooms: v})} />
                </div>
                <ModernSelect label="Estado" value={comp.condition || ''} onChange={(v: any) => setComp({...comp, condition: v})} options={CONDITION_OPTIONS} />
                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <Field label="Precio" type="number" value={comp.price} onChange={(v: any) => setComp({...comp, price: v})} />
                  </div>
                  <ModernSelect label="Moneda" value={comp.currency} onChange={(v: any) => setComp({...comp, currency: v})}
                    options={[{ value: 'USD', label: 'USD' }, { value: 'ARS', label: 'ARS' }]} />
                </div>
              </div>
            ),
          },
        ] as WizardStep[]}
        currentStep={wizardStep}
        onStepChange={setWizardStep}
        onComplete={saveCompManual}
        loading={savingComp}
        completeLabel="Guardar comparable"
        headerBadge={{ icon: <Plus className="h-4 w-4" />, label: 'Comparable', color: theme.primary }}
      />
    </div>
  );
}

// ============================================================
//  SuggestionsPanel — corazón IA-first
// ============================================================
function SuggestionsPanel({
  loading, suggestions, meta, method, acceptingId,
  onAccept, onReject, onUpdateAdjustment, onRefresh,
}: {
  loading: boolean;
  suggestions: Suggestion[];
  meta: { ai_evaluated: boolean; workspace: number; external: number; msg?: string } | null;
  method: string;
  acceptingId: number | null;
  onAccept: (s: Suggestion) => void;
  onReject: (s: Suggestion) => void;
  onUpdateAdjustment: (s: Suggestion, idx: number, coef: number) => void;
  onRefresh: () => void;
}) {
  const { theme } = useTheme();
  const editable = method === 'hybrid';
  const included = suggestions.filter(s => s.include);
  const rejected = suggestions.filter(s => !s.include);

  return (
    <section className="rounded-2xl overflow-hidden shadow-sm"
      style={{ background: theme.card, border: `1px solid ${theme.border}` }}>
      <header className="px-5 py-4 flex items-center justify-between gap-3"
        style={{ borderBottom: `1px solid ${theme.border}`,
                 background: `linear-gradient(135deg, ${theme.primary}10, transparent)` }}>
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: `${theme.primary}20` }}>
            <Bot className="h-5 w-5" style={{ color: theme.primary }} />
          </div>
          <div className="min-w-0">
            <div className="font-bold flex items-center gap-2" style={{ color: theme.text }}>
              <Sparkles className="h-3.5 w-3.5" style={{ color: theme.primary }} />
              Sugerencias de Claude
            </div>
            <div className="text-xs" style={{ color: theme.textSecondary }}>
              {loading
                ? 'Analizando candidatos…'
                : meta
                  ? `${meta.workspace} del workspace · ${meta.external} externos${meta.ai_evaluated ? ' · IA' : ' · ranking auto'}`
                  : 'Esperando análisis'}
            </div>
          </div>
        </div>
        <button onClick={onRefresh} disabled={loading}
          className="p-2 rounded-lg transition-all active:scale-95 disabled:opacity-50"
          style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}
          title="Volver a pedir sugerencias">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>

      {loading && (
        <div className="p-8 flex flex-col items-center gap-4">
          <div className="relative h-14 w-14 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full blur-xl opacity-50 animate-pulse"
              style={{ background: theme.primary }} />
            <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-t-transparent"
              style={{ borderColor: `${theme.primary}22`, borderTopColor: theme.primary }} />
            <Sparkles className="h-6 w-6 relative animate-pulse" style={{ color: theme.primary }} />
          </div>
          <div className="text-sm tracking-wider uppercase font-medium" style={{ color: theme.textSecondary }}>
            Claude evaluando mercado…
          </div>
        </div>
      )}

      {!loading && included.length === 0 && (
        <div className="p-8 text-center text-sm" style={{ color: theme.textSecondary }}>
          {meta?.msg || 'No hay sugerencias disponibles. Probá agregar comparables manualmente.'}
        </div>
      )}

      {!loading && included.length > 0 && (
        <div className="p-4 space-y-3">
          {included.map((s) => (
            <SuggestionCard
              key={`${s.candidate_kind}-${s.candidate_id}`}
              s={s}
              editable={editable}
              accepting={acceptingId === s.candidate_id}
              onAccept={() => onAccept(s)}
              onReject={() => onReject(s)}
              onUpdateAdjustment={(idx, coef) => onUpdateAdjustment(s, idx, coef)}
            />
          ))}
        </div>
      )}

      {!loading && rejected.length > 0 && (
        <details className="border-t" style={{ borderColor: theme.border }}>
          <summary className="px-5 py-3 text-xs uppercase tracking-wider font-semibold cursor-pointer transition-colors"
            style={{ color: theme.textSecondary }}>
            {rejected.length} descartado{rejected.length > 1 ? 's' : ''} por Claude — ver razones
          </summary>
          <div className="px-5 pb-3 space-y-2">
            {rejected.map(s => (
              <div key={`${s.candidate_kind}-${s.candidate_id}`}
                className="p-2.5 rounded-lg text-xs flex items-start gap-2"
                style={{ background: theme.backgroundSecondary, color: theme.textSecondary }}>
                <X className="h-3.5 w-3.5 flex-shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <div className="font-medium" style={{ color: theme.text }}>{s.candidate.title}</div>
                  <div className="mt-0.5">{s.reject_reason || 'Descartado'}</div>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function SuggestionCard({
  s, editable, accepting, onAccept, onReject, onUpdateAdjustment,
}: {
  s: Suggestion;
  editable: boolean;
  accepting: boolean;
  onAccept: () => void;
  onReject: () => void;
  onUpdateAdjustment: (idx: number, coef: number) => void;
}) {
  const { theme } = useTheme();
  const c = s.candidate;
  const scorePct = Math.round(s.similarity_score * 100);
  const scoreColor = scorePct >= 70 ? theme.success : scorePct >= 40 ? theme.warning : theme.danger;
  const isExternal = s.candidate_kind === 'external';

  return (
    <div className="p-4 rounded-xl animate-fade-in"
      style={{ background: theme.backgroundSecondary, border: `1px solid ${theme.border}` }}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          {/* Header tags */}
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            {isExternal ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
                style={{ background: '#ede9fe', color: '#5b21b6' }}>
                <Globe className="h-2.5 w-2.5" /> {c.source || 'externo'}
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
                style={{ background: '#dbeafe', color: '#1e40af' }}>
                Workspace
              </span>
            )}
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold"
              style={{ background: `${scoreColor}15`, color: scoreColor }}>
              <TrendingUp className="h-2.5 w-2.5" /> Similitud {scorePct}%
            </span>
            {s.adjustments.length > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium"
                style={{ background: `${theme.primary}15`, color: theme.primary }}>
                {s.adjustments.length} ajuste{s.adjustments.length > 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Título + ubicación */}
          <div className="font-semibold" style={{ color: theme.text }}>{c.title}</div>
          {c.address && <div className="text-xs mt-0.5" style={{ color: theme.textSecondary }}>{c.address}</div>}

          {/* Specs */}
          <div className="flex gap-3 text-xs mt-2" style={{ color: theme.textSecondary }}>
            {c.total_area_m2 && <span>{c.total_area_m2}m²</span>}
            {c.rooms && <span>{c.rooms} amb.</span>}
            {c.age_years != null && <span>{c.age_years} años</span>}
            {c.condition && <span className="capitalize">{c.condition.replace(/_/g, ' ')}</span>}
          </div>

          {/* Razón IA */}
          {s.similarity_reason && (
            <div className="mt-2 text-xs px-2.5 py-1.5 rounded-lg flex items-start gap-1.5"
              style={{ background: `${theme.primary}10`, color: theme.text }}>
              <Bot className="h-3 w-3 mt-0.5 flex-shrink-0" style={{ color: theme.primary }} />
              <span>{s.similarity_reason}</span>
            </div>
          )}

          {/* Ajustes */}
          {s.adjustments.length > 0 && (
            <div className="mt-2 space-y-1">
              <div className="text-[10px] uppercase tracking-wider font-semibold" style={{ color: theme.textSecondary }}>
                Ajustes propuestos
              </div>
              {s.adjustments.map((a, idx) => (
                <div key={idx} className="flex items-center gap-2 text-xs">
                  <span className="capitalize font-medium" style={{ color: theme.text, minWidth: 70 }}>
                    {a.factor}
                  </span>
                  {editable ? (
                    <>
                      <input
                        type="number" step="0.01"
                        value={a.coefficient}
                        onChange={e => onUpdateAdjustment(idx, parseFloat(e.target.value))}
                        className="w-16 px-2 py-0.5 rounded text-xs focus:outline-none focus:ring-2"
                        style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}
                      />
                      <Pencil className="h-3 w-3" style={{ color: theme.textSecondary }} />
                    </>
                  ) : (
                    <span className="font-mono" style={{ color: theme.text }}>{a.coefficient}</span>
                  )}
                  {a.description && (
                    <span className="text-[10px] truncate" style={{ color: theme.textSecondary }}>· {a.description}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Precio + acciones */}
        <div className="text-right flex-shrink-0">
          <div className="font-bold text-lg" style={{ color: theme.text }}>
            {c.currency || 'USD'} {Number(c.price || 0).toLocaleString()}
          </div>
          {c.total_area_m2 && c.price && (
            <div className="text-[10px]" style={{ color: theme.textSecondary }}>
              {Math.round(c.price / c.total_area_m2)}/m²
            </div>
          )}
          <div className="flex gap-1 mt-2">
            <button onClick={onReject} disabled={accepting}
              className="p-2 rounded-lg transition-all active:scale-95 disabled:opacity-50"
              style={{ background: `${theme.danger}15`, color: theme.danger }}
              title="Descartar">
              <X className="h-4 w-4" />
            </button>
            <button onClick={onAccept} disabled={accepting}
              className="px-3 py-2 rounded-lg text-white text-xs font-bold transition-all active:scale-95 disabled:opacity-50 flex items-center gap-1"
              style={{ background: theme.success }}>
              <Check className="h-3.5 w-3.5" /> {accepting ? '...' : 'Aceptar'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================================
//  CompCard — comparables ya aceptados en el estudio
// ============================================================
function CompCard({ c, index, onDelete }: { c: Comparable; index: number; onDelete: () => void }) {
  const { theme } = useTheme();
  const cAny = c as any;
  const isAI = cAny.source_type === 'ai_suggested';
  const isExternal = cAny.external_listing_id != null;
  return (
    <div className="p-4 rounded-xl animate-fade-in"
      style={{ background: theme.card, border: `1px solid ${theme.border}`, animationDelay: `${index * 50}ms` }}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-mono" style={{ color: theme.textSecondary }}>#{index + 1}</span>
            {isAI && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
                style={{ background: `${theme.primary}20`, color: theme.primary }}>
                <Sparkles className="h-2.5 w-2.5" /> IA
              </span>
            )}
            {isExternal && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wide"
                style={{ background: '#ede9fe', color: '#5b21b6' }}>
                <Globe className="h-2.5 w-2.5" /> {c.source}
              </span>
            )}
            {c.weight != null && (
              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium"
                style={{ background: `${theme.success}15`, color: theme.success }}>
                peso {c.weight}
              </span>
            )}
            {c.adjustments.length > 0 && (
              <span className="text-[10px] px-2 py-0.5 rounded-md font-medium"
                style={{ background: `${theme.warning}15`, color: theme.warning }}>
                {c.adjustments.length} ajuste{c.adjustments.length > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="font-medium truncate" style={{ color: theme.text }}>{c.title}</div>
          {c.address && <div className="text-xs truncate" style={{ color: theme.textSecondary }}>{c.address}</div>}
          <div className="flex gap-4 text-xs mt-2" style={{ color: theme.textSecondary }}>
            {c.total_area_m2 && <span>{c.total_area_m2}m²</span>}
            {c.rooms && <span>{c.rooms} amb.</span>}
            {c.age_years != null && <span>{c.age_years} años</span>}
            {c.condition && <span className="capitalize">{c.condition.replace(/_/g,' ')}</span>}
          </div>
          {cAny.ai_reason && (
            <div className="mt-2 text-[11px] italic" style={{ color: theme.textSecondary }}>
              "{cAny.ai_reason}"
            </div>
          )}
        </div>
        <div className="text-right ml-4 flex-shrink-0">
          <div className="font-bold" style={{ color: theme.text }}>{c.currency} {Number(c.price).toLocaleString()}</div>
          {c.price_per_m2 && <div className="text-xs" style={{ color: theme.textSecondary }}>{Math.round(c.price_per_m2)}/m²</div>}
          {c.adjusted_price_per_m2 && (
            <div className="text-xs mt-1 font-semibold" style={{ color: theme.success }}>→ {Math.round(c.adjusted_price_per_m2)}/m² aj.</div>
          )}
          <button onClick={onDelete}
            className="mt-2 p-1.5 rounded-lg transition-all active:scale-95"
            style={{ background: `${theme.danger}15`, color: theme.danger }}
            title="Eliminar comparable">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder }: any) {
  const { theme } = useTheme();
  return (
    <div>
      {label && <label className="block text-sm font-medium mb-1" style={{ color: theme.text }}>{label}</label>}
      <input type={type} value={value ?? ''} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full px-3 py-2.5 rounded-lg border focus:outline-none focus:ring-2 transition-all"
        style={{ background: theme.card, color: theme.text, borderColor: theme.border }} />
    </div>
  );
}

function Row({ k, v }: { k: string; v: any }) {
  const { theme } = useTheme();
  return (
    <div className="flex justify-between">
      <span style={{ color: theme.textSecondary }}>{k}</span>
      <span className="font-medium" style={{ color: theme.text }}>{v}</span>
    </div>
  );
}
