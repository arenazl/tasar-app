export interface HintStep {
  title: string;
  body: string;
  description?: string;
  icon?: string;
  cta?: { label: string; to?: string; href?: string };
}

export interface PageHintConfig {
  title: string;
  body: string;
  description?: string;
  steps?: HintStep[];
}

export const PAGE_HINTS: Record<string, PageHintConfig> = {
  propiedades: {
    title: 'Propiedades',
    body: 'Cargá los inmuebles de tu workspace. Cada propiedad es la base de un Estudio de Mercado (ACM) o una Tasación.',
    steps: [
      { title: 'Datos básicos', body: 'Título, tipo, operación y ubicación completa con coordenadas para el mapa de calor.' },
      { title: 'Características', body: 'Metros, ambientes, estado y antigüedad — Claude usa esto para sugerir comparables.' },
      { title: 'Análisis IA', body: 'Botón con ✨ — Claude analiza la propiedad y devuelve segmento, fortalezas y riesgos.' },
    ],
  },
  estudios: {
    title: 'Estudios de Mercado (ACM)',
    body: 'Análisis comparativo: elegís una propiedad objetivo, sumás comparables (manuales o scrapeados) y el sistema calcula el rango sugerido.',
    steps: [
      { title: 'Comparables', body: 'Cuantos más, mejor. Mínimo 3 ideal. Podés importar desde URL.' },
      { title: 'Ajustes', body: 'Coeficientes multiplicativos: 1.05 = +5%, 0.92 = -8%. Por área, estado, antigüedad, ubicación.' },
      { title: 'Recalcular', body: 'Dispara la homogeneización ponderada por similitud. Devuelve min/máx/modo + confianza.' },
    ],
  },
  tasaciones: {
    title: 'Tasaciones',
    body: 'Informe formal con valor final, metodología, firmas digitales y PDF exportable.',
    steps: [
      { title: 'Propiedad + ACM', body: 'Vinculá el estudio de mercado que da soporte al valor.' },
      { title: 'Firma', body: 'Hash SHA-256 con tu user_id + valor + timestamp. Inmutable.' },
      { title: 'PDF', body: 'Descarga directa con comparables, ajustes y firmas incluidas.' },
    ],
  },
  mapa: {
    title: 'Mapa de calor',
    body: 'Distribución de USD/m² combinando tus propiedades, comparables registrados y snapshots de price history.',
  },
  'tasador-ai': {
    title: 'Tasador AI',
    body: 'Chat con Claude headless. Le hacés preguntas técnicas, le pedís opinión sobre una propiedad o le dictás un análisis.',
  },
  equipo: { title: 'Equipo', body: 'Tasadores y colaboradores con acceso a estudios y firmas múltiples.' },
  configuracion: { title: 'Configuración', body: 'Tema, notificaciones, seguridad.' },
  clientes: {
    title: 'Clientes',
    body: 'CRM de tu workspace. Bancos, fondos, estudios e inmobiliarias que te encargan tasaciones.',
    steps: [
      { title: 'Tipo', body: 'Banco, fondo, estudio, inmobiliaria o particular — cada uno con color propio para identificar de un vistazo.' },
      { title: 'Datos completos', body: 'Contacto, email, teléfono, CUIT/DNI y dirección quedan asociados a cada cliente.' },
      { title: 'Cruce automático', body: 'El total de tasaciones por cliente se calcula leyendo el client_name de las appraisals.' },
    ],
  },
  bandeja: {
    title: 'Bandeja',
    body: 'Inbox unificado: mensajes de clientes, alertas del sistema, menciones del equipo y recordatorios propios.',
  },
  pipeline: {
    title: 'Pipeline',
    body: 'Kanban del flujo: solicitada → análisis → borrador → firmada → entregada. Arrastrá cards entre columnas.',
  },
  mercado: {
    title: 'Mercado',
    body: 'Dashboard macro: índice TasAR, oferta activa, tiempo medio de venta, permisos. Selector de período afecta YoY/MoM.',
  },
  comparables: {
    title: 'Comparables',
    body: 'Búsqueda live en 18K+ listings con filtros por zona, radio, ambientes y condición. Exportable a CSV.',
  },
  reportes: {
    title: 'Reportes',
    body: 'Análisis mensual del mercado en formato editorial. Click en cualquier card para leer el documento completo.',
    steps: [
      { title: 'Leer', body: 'Click en la card abre el documento largo con headline, KPIs, gráficos y secciones.' },
      { title: 'PDF', body: 'Botón download para guardar la versión imprimible.' },
      { title: 'Custom', body: 'Generá un reporte para otra región o período desde el botón superior.' },
    ],
  },
};
