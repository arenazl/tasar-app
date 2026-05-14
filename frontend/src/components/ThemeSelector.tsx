import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { Palette, Check, Moon, Sun } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

export default function ThemeSelector() {
  const { presetId, presets, setPreset, mode, toggle, theme } = useTheme();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);

  // Posición del dropdown calculada al abrir + reactiva a scroll/resize
  const recalc = () => {
    if (!triggerRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    setPos({ top: r.bottom + 8, right: window.innerWidth - r.right });
  };

  useLayoutEffect(() => {
    if (open) recalc();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onScroll = () => recalc();
    window.addEventListener('scroll', onScroll, true);
    window.addEventListener('resize', onScroll);
    return () => {
      window.removeEventListener('scroll', onScroll, true);
      window.removeEventListener('resize', onScroll);
    };
  }, [open]);

  // Click outside (incluyendo el portal)
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) return;
      if (dropdownRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const current = presets.find(p => p.id === presetId) || presets[0];

  const dropdown = open && pos && createPortal(
    <div
      ref={dropdownRef}
      className="fixed w-80 rounded-xl shadow-2xl border overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200"
      style={{
        top: pos.top,
        right: pos.right,
        background: theme.card,
        borderColor: theme.border,
        zIndex: 9999,
      }}
    >
      {/* Header con toggle light/dark */}
      <div
        className="px-4 py-3 flex items-center justify-between"
        style={{ background: theme.backgroundSecondary, borderBottom: `1px solid ${theme.border}` }}
      >
        <div>
          <div className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.text }}>
            Apariencia
          </div>
          <div className="text-[10px]" style={{ color: theme.textSecondary }}>
            Elegí paleta y modo
          </div>
        </div>
        <button
          onClick={toggle}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold transition-all active:scale-95"
          style={{ background: theme.card, color: theme.text, border: `1px solid ${theme.border}` }}
        >
          {mode === 'light' ? (
            <><Sun className="h-3 w-3" /> Light</>
          ) : (
            <><Moon className="h-3 w-3" /> Dark</>
          )}
        </button>
      </div>

      {/* Grid de presets (scrollable si hay muchos) */}
      <div className="p-3 grid grid-cols-2 gap-2 max-h-[60vh] overflow-y-auto">
        {presets.map(p => {
          const isActive = p.id === presetId;
          const variant = mode === 'dark' ? p.dark : p.light;
          return (
            <button
              key={p.id}
              onClick={() => { setPreset(p.id); }}
              className="relative p-3 rounded-lg text-left transition-all duration-200 hover:scale-[1.02] active:scale-95"
              style={{
                background: isActive ? `${p.accent}10` : theme.backgroundSecondary,
                border: `1.5px solid ${isActive ? p.accent : theme.border}`,
              }}
            >
              <div className="flex items-center gap-1 mb-2">
                <div className="w-5 h-5 rounded-md shadow-sm" style={{ background: p.accent }} />
                <div className="w-3 h-5 rounded-md shadow-sm" style={{ background: variant.sidebar }} />
                <div className="w-2 h-5 rounded-md shadow-sm border" style={{ background: variant.card, borderColor: variant.border }} />
                {isActive && (
                  <div className="ml-auto w-4 h-4 rounded-full flex items-center justify-center"
                    style={{ background: p.accent }}>
                    <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />
                  </div>
                )}
              </div>
              <div className="font-semibold text-xs" style={{ color: theme.text }}>
                {p.label}
              </div>
              <div className="text-[10px] leading-tight mt-0.5" style={{ color: theme.textSecondary }}>
                {p.description}
              </div>
            </button>
          );
        })}
      </div>

      <div className="px-4 py-2 text-[10px]"
        style={{ background: theme.backgroundSecondary, color: theme.textSecondary, borderTop: `1px solid ${theme.border}` }}>
        Se guarda en este navegador
      </div>
    </div>,
    document.body
  );

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg transition-all duration-200 hover:scale-105 active:scale-95"
        style={{
          background: open ? `${theme.primary}15` : 'transparent',
          border: `1px solid ${open ? theme.primary : theme.border}`,
        }}
        title="Cambiar tema"
      >
        <div className="flex -space-x-1">
          <div className="w-3.5 h-3.5 rounded-full ring-2"
            style={{ background: current.accent, ['--tw-ring-color' as any]: theme.card }} />
          <div className="w-3.5 h-3.5 rounded-full ring-2"
            style={{ background: mode === 'dark' ? current.dark.background : current.light.sidebar, ['--tw-ring-color' as any]: theme.card }} />
        </div>
        <Palette className="h-4 w-4" style={{ color: theme.textSecondary }} />
      </button>
      {dropdown}
    </>
  );
}
