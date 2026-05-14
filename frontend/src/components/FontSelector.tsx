import { useState, useRef, useEffect, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
import { Type, Check } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  collapsed?: boolean;
}

/**
 * Selector de fonts del topbar/sidebar.
 * Usa createPortal para evitar quedar tapado por stacking contexts.
 */
export default function FontSelector({ collapsed = false }: Props) {
  const { fontId, font, fonts, setFont, theme } = useTheme();
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; bottom: number } | null>(null);

  const recalc = () => {
    if (!triggerRef.current) return;
    const r = triggerRef.current.getBoundingClientRect();
    // Aparece arriba del botón (botón está al fondo de sidebar)
    setPos({ left: r.right + 8, bottom: window.innerHeight - r.bottom });
  };
  useLayoutEffect(() => { if (open) recalc(); }, [open]);
  useEffect(() => {
    if (!open) return;
    const f = () => recalc();
    window.addEventListener('scroll', f, true);
    window.addEventListener('resize', f);
    return () => { window.removeEventListener('scroll', f, true); window.removeEventListener('resize', f); };
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t)) return;
      if (dropdownRef.current?.contains(t)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const dropdown = open && pos && createPortal(
    <div
      ref={dropdownRef}
      className="fixed w-72 rounded-xl shadow-2xl border overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-200"
      style={{ left: pos.left, bottom: pos.bottom, background: theme.card, borderColor: theme.border, zIndex: 9999 }}
    >
      <div className="px-4 py-3" style={{ background: theme.backgroundSecondary, borderBottom: `1px solid ${theme.border}` }}>
        <div className="text-xs font-bold uppercase tracking-wider" style={{ color: theme.text }}>Tipografía</div>
        <div className="text-[10px]" style={{ color: theme.textSecondary }}>Aplicada a toda la app</div>
      </div>
      <div className="p-2 max-h-[60vh] overflow-y-auto">
        {fonts.map(f => {
          const isActive = f.id === fontId;
          return (
            <button
              key={f.id}
              onClick={() => setFont(f.id)}
              className="w-full text-left p-3 rounded-lg transition-all duration-200 hover:scale-[1.01] active:scale-95 flex items-center gap-3"
              style={{
                background: isActive ? `${theme.primary}10` : 'transparent',
                border: `1.5px solid ${isActive ? theme.primary : 'transparent'}`,
              }}
            >
              {/* Preview con la propia font */}
              <div className="flex-1 min-w-0">
                <div className="font-bold text-base leading-none" style={{ color: theme.text, fontFamily: f.family }}>
                  {f.label}
                </div>
                <div className="text-[10px] mt-1" style={{ color: theme.textSecondary }}>{f.description}</div>
                <div className="text-sm mt-1.5 leading-snug" style={{ color: theme.textSecondary, fontFamily: f.family }}>
                  TasAR · Mapa de valor por zona
                </div>
              </div>
              {isActive && (
                <div className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center" style={{ background: theme.primary }}>
                  <Check className="h-3 w-3 text-white" strokeWidth={3} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>,
    document.body
  );

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => setOpen(o => !o)}
        title={`Tipografía: ${font.label}`}
        className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold transition-all duration-200 active:scale-95"
        style={{
          background: open ? `${theme.primary}15` : theme.backgroundSecondary,
          color: theme.textSecondary,
          border: `1px solid ${open ? theme.primary : theme.border}`,
        }}
      >
        <Type className="h-4 w-4" />
        {!collapsed && (
          <>
            <span className="flex-1 text-left truncate" style={{ fontFamily: font.family }}>{font.label}</span>
          </>
        )}
      </button>
      {dropdown}
    </>
  );
}
