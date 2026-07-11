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
  'tasacion-express': {
    title: 'Tu gancho comercial en 30 segundos',
    body: 'Cargá una propiedad y obtené un rango de valor anclado a comparables reales del catálogo, con IA que ajusta sobre esa ancla. Es lo primero que le mostrás a un cliente nuevo.',
    steps: [
      { title: 'Anclado, no inventado', body: 'El motor arranca de la mediana real de USD/m² de la zona (market_listings) y recién ahí la IA ajusta por estado, antigüedad y features. Nunca "adivina" un precio de la nada.' },
      { title: 'Confianza según datos', body: 'Alta con 30+ comparables, media con 10+, baja con menos. Si no hay datos de la zona, te lo dice — no te muestra un número sin sustento.' },
      { title: 'PDF listo para mandar', body: 'Cada tasación express se guarda y se puede descargar en PDF brandeado con tu logo, para mandarlo al cliente en el momento.' },
    ],
  },
  dashboard: {
    title: 'Tu día arranca acá',
    body: 'Antes de abrir cualquier ACM, mirá esta pantalla: te dice cuánto facturás, cuántas tasaciones tenés en curso y qué está esperando tu atención.',
    steps: [
      { title: '4 números que importan', body: 'Propiedades cargadas, ACMs activos, tasaciones en proceso y valor promedio firmado. Si alguno cayó vs el mes pasado, ya sabés dónde poner foco.' },
      { title: 'Mix por tipo de inmueble', body: 'Si tasás 80% departamentos y 20% otros, sos un especialista. Si está parejo, sos generalista. El gráfico te muestra tu perfil real, no el que creés.' },
      { title: 'IA Coach contextual', body: 'Arriba aparece una recomendación generada por IA según el estado real de tu workspace: qué priorizar hoy, qué te falta cargar, qué cliente está parado.' },
    ],
  },
  propiedades: {
    title: 'Tu inventario reutilizable',
    body: 'Cada propiedad bien cargada es un activo: la tasás hoy, la podés volver a tasar el año que viene, y la usás como comparable en otros ACMs.',
    steps: [
      { title: 'Cargar bien = trabajar menos', body: 'Si cargás m², ambientes, antigüedad, estado y coords desde el día 1, después la IA te sugiere comparables automáticamente cuando armás un ACM.' },
      { title: 'Filtros que importan', body: 'Pills "Destacadas >300k" (clientes premium), "Recientes" (lo que entró esta semana), "Sin precio" (a completar) y "Completas" (listas para tasar).' },
      { title: 'Análisis IA por propiedad', body: 'El botón con el ícono de IA pide a Claude/Gemini un análisis con segmento, fortalezas comerciales y rango sugerido. Te ahorra 30 min de pensar la propiedad antes del ACM.' },
    ],
  },
  estudios: {
    title: 'ACM — Tu metodología defendible',
    body: 'Es la base técnica que justifica el valor final de una tasación ante un banco, un juez o un comprador. Sin ACM, es opinión. Con ACM, es trabajo profesional.',
    steps: [
      { title: 'Elegir el método', body: 'Homogenización clásica (manual), AI Score (IA rankea comparables por similitud) o Híbrido (sugerencia IA + tu criterio). Más data, más confianza.' },
      { title: 'Confianza cuantificada', body: 'Cada ACM tiene score 0-100%. Verde ≥70% = inatacable. Rojo <40% = necesitás más comparables o ajustar criterios antes de firmar la tasación.' },
      { title: 'De ACM a tasación', body: 'Cuando el ACM está sólido, lo linkeás a la tasación con un click. El valor sugerido min/máx/modo viaja al PDF firmado.' },
    ],
  },
  tasaciones: {
    title: 'Tu producto facturable',
    body: 'Cada tasación es honorarios. Esta pantalla es el control central: estado de cada una, finalidad, valor final y si está por vencer.',
    steps: [
      { title: 'Estado = caja', body: 'Borrador (no facturás), Firmadas (entregables), Entregadas (cobrables). El pill "Por vencer" te muestra las que tienen plazo legal por cumplir.' },
      { title: 'Finalidad cambia el formato', body: 'Venta, sucesión, judicial, hipoteca, seguro: cada una se entrega distinto. La finalidad del informe define qué información destacar en el PDF.' },
      { title: 'Firmar es irreversible', body: 'Una vez firmada, queda inmutable con hash SHA-256 + tu matrícula. Revisá comparables y ACM linkeado antes de hacer el click definitivo.' },
    ],
  },
  mapa: {
    title: 'Inteligencia geográfica del mercado',
    body: 'Lo que un broker tarda años en intuir lo ves en un mapa: dónde están los valores altos, dónde se movió este mes, dónde tenés cobertura y dónde no.',
    steps: [
      { title: 'Visualizar precios reales', body: 'Cada punto es una propiedad o comparable con precio efectivo. El calor de zona te muestra USD/m² mediano por barrio — argumento visual para mostrar al cliente.' },
      { title: 'Drill-down por zona', body: 'Click en una zona del ranking lateral abre panel con KPI, count de muestras y comparación vs promedio de la ciudad. Es tu análisis micro de barrio.' },
      { title: 'Saltar a comparables', body: 'Desde el panel de zona, link directo a Comparables prefiltrado por ese barrio para usar en un ACM nuevo.' },
    ],
  },
  equipo: {
    title: 'Escalar el estudio sin perder control',
    body: 'Un tasador solo factura X por mes. Con equipo + roles bien definidos multiplicás capacidad sin perder calidad ni responsabilidad legal de firma.',
    steps: [
      { title: 'Roles que protegen', body: 'Admin firma y ve todo. Supervisor revisa el trabajo del equipo. Tasador junior carga datos y arma ACMs pero no firma. Distribuís trabajo sin riesgo.' },
      { title: 'Matrícula = identidad legal', body: 'Cada user firma con su número de matrícula. En el PDF aparece quién firmó. Te cubre legalmente y le da carrera al junior cuando crece.' },
      { title: 'Colaboración en ACMs', body: 'Asignás colaboradores a un estudio. Cuando uno comenta, los demás reciben email + entrada en bandeja. No se pierde nada.' },
    ],
  },
  configuracion: {
    title: 'Adaptá la herramienta a vos',
    body: 'Pasás 6+ horas por día acá. Elegí motor de IA, tipografía, paleta y notificaciones que te hagan trabajar mejor, no que te molesten.',
    steps: [
      { title: 'Motor de IA', body: 'Claude piensa profundo, ideal para análisis críticos. Gemini es rápido y barato, perfecto para tareas masivas. Cambiá según necesidad sin tocar código.' },
      { title: 'Notificaciones email', body: '3 toggles: resumen semanal, tasaciones firmadas (mail al cliente), comentarios del equipo. Activá solo lo que te aporta, no satures tu inbox.' },
      { title: 'Tema y tipografía', body: 'Modo oscuro a la noche, claro de día = menos fatiga visual. La fuente que elegís aplica a toda la app, incluso los PDFs.' },
    ],
  },
  clientes: {
    title: 'Tu cartera vale oro',
    body: 'Los clientes recurrentes (bancos, fondos, estudios) son ingresos predecibles. Esta pantalla te muestra quiénes son y cuánto te encargaron.',
    steps: [
      { title: 'Tipo define el trato', body: 'Banco quiere rapidez y formularios. Estudio jurídico quiere rigor técnico. Particular quiere explicación. Los pills te dejan ver de un vistazo tu mix.' },
      { title: 'Conteo de tasaciones', body: 'Cada card muestra cuántas tasaciones le hiciste a ese cliente. Los top 3 son tus pilares: dales atención premium para que no se vayan.' },
      { title: 'Datos completos', body: 'Email + teléfono + CUIT cargados te ahorran tiempo en cada operación: avisos de entrega, facturas, llamadas urgentes.' },
    ],
  },
  bandeja: {
    title: 'No perder oportunidades',
    body: 'Los buenos negocios se pierden por no responder rápido. Acá vivís todo: consultas de clientes, alertas del sistema, menciones del equipo y recordatorios.',
    steps: [
      { title: 'Tabs por urgencia', body: 'Sin leer / Asignadas a mí / Todo. Empezás el día por las sin leer y las asignadas. Lo demás puede esperar.' },
      { title: 'Tipos de mensaje', body: 'Mensaje de cliente, alerta de sistema, mención del equipo, tasación asignada, comparable agregado, factura vencida. Cada uno con icono propio.' },
      { title: 'Link directo a la tasación', body: 'Si el mensaje se refiere a una tasación específica, hay un link directo. Click y vas al detalle sin perder contexto.' },
    ],
  },
  pipeline: {
    title: 'Visualizar el flujo de caja',
    body: 'Cada tarjeta es facturación potencial. Ver el flujo entero en kanban te muestra dónde se traba el trabajo y qué urge cerrar para cobrar.',
    steps: [
      { title: '5 columnas = ciclo completo', body: 'Solicitada → En análisis → En revisión → Aprobada → Entregada. Cada movimiento hacia la derecha es más cerca de facturar.' },
      { title: 'Predecir el mes', body: 'Contando tarjetas por columna estimás facturación. 5 en "Aprobada" pendientes de entrega = X pesos que entran este mes.' },
      { title: 'Detectar embudos', body: 'Si "En análisis" tiene 15 cards y "Aprobada" tiene 0, hay un problema de cierre. Si "Entregada" no crece, los clientes están esperando.' },
    ],
  },
  mercado: {
    title: 'Inteligencia macro del rubro',
    body: 'Saber si el mercado está caliente, frío o lateral te permite asesorar mejor. Esta pantalla te muestra en 1 vistazo lo que un broker tarda años en intuir.',
    steps: [
      { title: 'Índice TasAR + tendencia', body: 'El USD/m² mediano de toda CABA y su variación YoY/MoM. Si sube, justifica precios al alza. Si cae, justificá recomendar bajar la oferta.' },
      { title: 'Selector de período', body: '7d / 30d / 90d / 12m / 5a. Comparás momentum corto (mercado caliente) vs largo (tendencia estructural). Datos diferentes, decisiones diferentes.' },
      { title: 'Permisos = oferta futura', body: 'Permisos nuevos te anticipan oferta efectiva en 18-24 meses. Si crecen mucho en tu zona, planificá especialización en obra nueva.' },
    ],
  },
  comparables: {
    title: 'La prueba en 1 segundo',
    body: 'En vez de revisar Zonaprop/Argenprop a mano y armar Excel, acá tenés en una búsqueda los comparables con USD/m² y match score listos para usar.',
    steps: [
      { title: 'Filtros estrictos', body: 'Zona + radio + tipo + ambientes + condición + antigüedad. Cuanto más estricto el filtro, más defendible cada comparable que uses en un ACM.' },
      { title: 'Match score', body: 'Cada resultado tiene score 0-100. Por arriba de 85 = casi gemelo de tu propiedad. Abajo de 60 = mirá con cuidado antes de usarlo.' },
      { title: 'Exportar para el cliente', body: 'Si el cliente cuestiona el valor, mostrale el CSV de comparables. Te muestra como profesional con metodología, no opinión.' },
    ],
  },
  reportes: {
    title: 'Tu autoridad de mercado',
    body: 'Mandarle a un cliente el reporte mensual del mercado vale más que 10 emails de seguimiento. Te posiciona como referente, no como simple proveedor.',
    steps: [
      { title: 'Lectura editorial', body: 'No son data dumps: cada reporte abre como artículo Bloomberg con headline, conclusiones, gráficos y secciones. Ideal para forwardear al cliente.' },
      { title: 'Cerrar ventas con autoridad', body: 'Adjuntá el reporte al pasar una tasación. El cliente lee "esto está respaldado por análisis institucional", no por una opinión tuya.' },
      { title: 'Reportes custom', body: 'Para un cliente grande (banco, fondo), generás un reporte específico de su zona o tipo de inmueble. Es un servicio premium adicional cobrable.' },
    ],
  },
};
