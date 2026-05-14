export interface FontPreset {
  id: string;
  label: string;
  description: string;
  /** CSS font-family stack que se aplica al --font-base. */
  family: string;
  /** Font para headings (.font-display). Si igual al body, omitir. */
  displayFamily?: string;
  /** Letter-spacing recomendado para display, en em. */
  displayTracking?: string;
}

export const FONT_PRESETS: FontPreset[] = [
  {
    id: 'inter',
    label: 'Inter',
    description: 'Editorial moderno (default)',
    family: `'Inter', system-ui, sans-serif`,
    displayFamily: `'Inter Tight', 'Inter', sans-serif`,
    displayTracking: '-0.04em',
  },
  {
    id: 'nunito',
    label: 'Nunito',
    description: 'Amigable (estilo Munify)',
    family: `'Nunito', system-ui, sans-serif`,
    displayTracking: '-0.02em',
  },
  {
    id: 'manrope',
    label: 'Manrope',
    description: 'Amigable + comercial',
    family: `'Manrope', system-ui, sans-serif`,
    displayTracking: '-0.03em',
  },
  {
    id: 'space-grotesk',
    label: 'Space Grotesk',
    description: 'Geométrica tech',
    family: `'Space Grotesk', system-ui, sans-serif`,
    displayTracking: '-0.02em',
  },
  {
    id: 'plus-jakarta',
    label: 'Plus Jakarta Sans',
    description: 'Limpia + profesional',
    family: `'Plus Jakarta Sans', system-ui, sans-serif`,
    displayTracking: '-0.03em',
  },
  {
    id: 'outfit',
    label: 'Outfit',
    description: 'Display contemporánea',
    family: `'Outfit', system-ui, sans-serif`,
    displayTracking: '-0.03em',
  },
  {
    id: 'ibm-plex',
    label: 'IBM Plex Sans',
    description: 'Corporativa clásica',
    family: `'IBM Plex Sans', system-ui, sans-serif`,
    displayTracking: '-0.02em',
  },
  {
    id: 'dm-sans',
    label: 'DM Sans',
    description: 'Neutra balanceada',
    family: `'DM Sans', system-ui, sans-serif`,
    displayTracking: '-0.03em',
  },
  {
    id: 'system',
    label: 'Sistema',
    description: 'Fuente nativa del SO',
    family: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`,
    displayTracking: '-0.02em',
  },
];

export function getFontPreset(id: string): FontPreset {
  return FONT_PRESETS.find(f => f.id === id) || FONT_PRESETS[0];
}
