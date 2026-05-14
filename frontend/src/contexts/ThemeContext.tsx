import { createContext, useContext, useEffect, useState, ReactNode, useMemo } from 'react';

type Mode = 'light' | 'dark';

export interface Theme {
  name: string;
  label: string;
  background: string;
  backgroundSecondary: string;
  card: string;
  sidebar: string;
  topbar: string;
  text: string;
  textSecondary: string;
  textOnSidebar: string;
  primaryText: string;
  primary: string;
  primaryHover: string;
  primaryLight: string;
  success: string;
  danger: string;
  warning: string;
  info: string;
  border: string;
  borderLight: string;
  // Gradient característico del tema — usado en AI Coach, hero cards, etc.
  gradientFrom: string;
  gradientVia: string;
  gradientTo: string;
}

// Import lazy para evitar dep circular en build (presets importa Theme)
import { THEME_PRESETS, getPreset, type ThemePreset } from '../config/themePresets';
import { FONT_PRESETS, getFontPreset, type FontPreset } from '../config/fontPresets';

interface ThemeCtx {
  mode: Mode;
  theme: Theme;
  presetId: string;
  preset: ThemePreset;
  presets: ThemePreset[];
  toggle: () => void;
  setPreset: (id: string) => void;
  fontId: string;
  font: FontPreset;
  fonts: FontPreset[];
  setFont: (id: string) => void;
}

const Ctx = createContext<ThemeCtx | null>(null);

const LS_MODE = 'tasar_theme_mode';
const LS_PRESET = 'tasar_theme_preset';
const LS_FONT = 'tasar_theme_font';

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>(() =>
    (localStorage.getItem(LS_MODE) as Mode) || 'light'
  );
  const [presetId, setPresetId] = useState<string>(() =>
    localStorage.getItem(LS_PRESET) || 'tasar'
  );
  const [fontId, setFontId] = useState<string>(() =>
    localStorage.getItem(LS_FONT) || 'inter'
  );

  const preset = useMemo(() => getPreset(presetId), [presetId]);
  const theme = useMemo(() => (mode === 'dark' ? preset.dark : preset.light), [mode, preset]);
  const font = useMemo(() => getFontPreset(fontId), [fontId]);

  // Sync CSS vars + dataset
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-theme', mode);
    root.setAttribute('data-preset', presetId);
    root.style.setProperty('--bg-app', theme.background);
    root.style.setProperty('--bg-topbar', theme.topbar);
    root.style.setProperty('--bg-sidebar', theme.sidebar);
    root.style.setProperty('--bg-card', theme.card);
    root.style.setProperty('--text-primary', theme.text);
    root.style.setProperty('--text-secondary', theme.textSecondary);
    root.style.setProperty('--color-primary', theme.primary);
    root.style.setProperty('--color-primary-hover', theme.primaryHover);
    root.style.setProperty('--color-success', theme.success);
    root.style.setProperty('--color-danger', theme.danger);
    root.style.setProperty('--color-warning', theme.warning);
    root.style.setProperty('--border-color', theme.border);
    localStorage.setItem(LS_MODE, mode);
    localStorage.setItem(LS_PRESET, presetId);
  }, [mode, presetId, theme]);

  // Aplicar font CSS vars — el index.css hace que TODO descendiente
  // herede via `*, *::before, *::after { font-family: inherit; }`
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--font-base', font.family);
    root.style.setProperty('--font-display', font.displayFamily || font.family);
    root.style.setProperty('--font-display-tracking', font.displayTracking || '-0.02em');
    localStorage.setItem(LS_FONT, fontId);
  }, [fontId, font]);

  const value = useMemo<ThemeCtx>(() => ({
    mode,
    theme,
    presetId,
    preset,
    presets: THEME_PRESETS,
    toggle: () => setMode(m => m === 'light' ? 'dark' : 'light'),
    setPreset: (id: string) => setPresetId(id),
    fontId,
    font,
    fonts: FONT_PRESETS,
    setFont: (id: string) => setFontId(id),
  }), [mode, theme, presetId, preset, fontId, font]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useTheme() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useTheme fuera de ThemeProvider');
  return ctx;
}
