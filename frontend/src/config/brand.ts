/**
 * Marca de la suite — FUENTE ÚNICA del nombre/identidad en el front.
 *
 * TasAR es la marca paraguas de toda la suite inmobiliaria (gate de marca
 * resuelto por el dueño, WO F4-01). Los módulos se rotulan TasAR Tasaciones /
 * TasAR CRM / TasAR Bot cuando hace falta.
 *
 * Renombrar la suite = cambiar `name` acá (1 línea). Residuales fuera de este
 * módulo que también llevan el nombre y NO se pueden importar desde TS:
 *   - `frontend/index.html` (<title> + meta description, HTML estático)
 *   - `frontend/src/config/themePresets.ts` (labels del catálogo de temas)
 * El resto del shell / login / loading / logo / PDFs del front consume `BRAND`.
 */
export const BRAND = {
  /** Nombre de la suite. Único lugar con el nombre en el shell/PDF del front. */
  name: 'TasAR',
  /** Bajada corta (header colapsado, sidebar). */
  tagline: 'Mapa de valor',
  /** Bajada larga (logo standard, login, config, previews de fuente). */
  taglineLong: 'Mapa de valor · Por zona',
  /**
   * Color primario de marca (FALLBACK). El color real de la UI viene del tema
   * activo del workspace (ThemeContext → `theme.primary`). Usar `BRAND.primaryColor`
   * solo cuando no hay tema disponible.
   */
  primaryColor: '#10b981',
  /**
   * Logo: se renderiza vía `<BrandLogo/>` (SVG fiel al brand book). El logo por
   * workspace vive en BD; este es el fallback cuando el workspace no definió uno.
   */
  logoFallback: '/logo.svg',
} as const;

export type Brand = typeof BRAND;
