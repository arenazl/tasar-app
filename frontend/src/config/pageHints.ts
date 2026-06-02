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
  dashboard: {
    title: 'Dashboard',
    body: 'Visión general de tu actividad: KPIs del workspace, distribución por tipo y tasaciones recientes.',
    steps: [
      { title: 'AI Coach', body: 'Card outline arriba — recomendación contextual generada por Gemini en base al estado real del workspace.' },
      { title: 'KPIs', body: '4 métricas: Propiedades cargadas, ACMs activos, Tasaciones en curso y Valor promedio firmado. Cada uno con delta vs mes anterior.' },
      { title: 'Propiedades por tipo', body: 'Gráfico de barras horizontales: departamentos, casas, PHs, terrenos, locales y oficinas. Click en cada barra filtra.' },
      { title: 'Tasaciones recientes', body: 'Últimas 5-10 tasaciones con status (solicitada/en análisis/firmada/entregada) y valor final.' },
      { title: 'Acciones rápidas', body: 'Botones flotantes para crear propiedad, abrir ACM o ir a la bandeja.' },
      { title: 'Tutorial', body: 'Este card pasa por las 3 acciones fundamentales para empezar: cargar propiedad, crear ACM y generar tasación.' },
    ],
  },
  propiedades: {
    title: 'Propiedades',
    body: 'Catálogo de inmuebles del workspace. Cada propiedad es la base para un ACM y, después, para una Tasación firmada.',
    steps: [
      { title: 'Datos básicos', body: 'Título, tipo (depto/casa/PH/terreno/local/oficina), operación (venta/alquiler) y ubicación completa con coordenadas para el mapa de calor.' },
      { title: 'Características físicas', body: 'Superficie total y cubierta, ambientes, dormitorios, baños, cocheras, antigüedad y estado. La IA usa esto para sugerir comparables similares.' },
      { title: 'Vista tabla vs cards', body: 'Toggle arriba a la derecha. Tabla densa (default) para listas largas; cards para ver fotos y status de un vistazo.' },
      { title: 'Análisis IA', body: 'Botón con ✨ — Gemini analiza la propiedad y devuelve segmento (luxury/medio/popular), fortalezas comerciales, riesgos y precio sugerido por m².' },
      { title: 'Fotos y documentos', body: 'Subí imágenes a Cloudinary directamente desde la card. Las fotos viajan con el PDF de la tasación.' },
      { title: 'Conexión con ACM', body: 'Desde el detalle podés disparar un ACM nuevo con esta propiedad como objetivo y el sistema sugiere comparables automáticamente.' },
    ],
  },
  estudios: {
    title: 'ACM — Análisis Comparativo de Mercado',
    body: 'El corazón del trabajo del tasador. Comparás la propiedad objetivo con similares ya vendidas/en venta, aplicás ajustes y obtenés un rango defensible.',
    steps: [
      { title: 'Propiedad objetivo', body: 'Elegís el inmueble que vas a tasar. Sus características (zona, m², ambientes, estado) son la referencia para buscar comparables.' },
      { title: 'Sugerencias IA', body: 'Si elegís método "ai_score" o "hybrid", Gemini consulta tu workspace + external_listings (Zonaprop/Argenprop) y rankea candidatos por similitud.' },
      { title: 'Aceptar/Rechazar', body: 'Cada sugerencia muestra match score y razón ("mismo barrio, similar antigüedad y estado"). Click "Aceptar" la suma al ACM con los ajustes propuestos.' },
      { title: 'Ajustes manuales', body: 'Coeficientes multiplicativos por zona, antigüedad, estado, m², orientación. 1.05 = +5%, 0.92 = -8%. Editables fila por fila.' },
      { title: 'Recalcular', body: 'Dispara homogeneización: cada comparable ajustado aporta a la mediana ponderada por similitud. Devuelve min/máx/modo + score de confianza.' },
      { title: 'Colaboración', body: 'Comentarios del equipo en cada ACM. Cuando un colaborador comenta, los otros reciben email (si tienen la notificación activa).' },
    ],
  },
  tasaciones: {
    title: 'Tasaciones',
    body: 'El deliverable: informe formal con valor final, metodología, firma digital SHA-256 y PDF profesional listo para entregar al cliente.',
    steps: [
      { title: 'Crear', body: 'Wizard de 4 pasos: Propiedad → ACM de soporte → Valor + finalidad (venta/sucesión/judicial/hipoteca/seguro) → Revisar y confirmar.' },
      { title: 'Estados', body: 'Borrador (editable) → En análisis (con IA corriendo) → Firmada (inmutable) → Entregada (notificación al cliente).' },
      { title: 'Firma digital', body: 'Hash SHA-256 de id + user + valor + timestamp. La firma queda en la base, no se puede modificar la tasación después.' },
      { title: 'PDF profesional', body: 'Descarga directa con: datos de la propiedad, comparables del ACM linkeado, ajustes aplicados, valor final, firma y matrícula del tasador.' },
      { title: 'Email al cliente', body: 'Al firmar, si el cliente tiene email cargado, sale un mail automático con el valor final formateado (Brevo SMTP).' },
      { title: 'Detalle 3-paneles', body: 'Click en cualquier tasación abre vista detalle con 4 KPIs, mapa de calor de la zona, sparkline 17 meses, tabla de comparables con match% y rail con cliente + datos + timeline.' },
    ],
  },
  mapa: {
    title: 'Mapa de calor geográfico',
    body: 'Distribución espacial real de USD/m² con Leaflet + OpenStreetMap. Combina tus propiedades, comparables del workspace y snapshots históricos.',
    steps: [
      { title: 'Mapa interactivo', body: 'Tile OpenStreetMap con HeatLayer encima. Zoom in/out, drag para navegar. Cada punto es una propiedad real con popup de USD/m².' },
      { title: 'Filtros', body: 'Ciudad, tipo de propiedad, operación (venta/alquiler) y fuente (todo/props/comparables/histórico). Se combinan con AND.' },
      { title: 'Ranking lateral', body: 'Top 10 zonas por USD/m² mediano. Click en cualquier zona abre drill-down con KPI, stats, listings activos y links contextuales.' },
      { title: 'Drill-down', body: 'Panel lateral con USD/m² + barra vs top + comparación con promedio de ciudad, 4 stats (muestras, listings, min, max) y lista de puntos.' },
      { title: 'Acciones contextuales', body: 'Desde el drill-down podés saltar a Comparables o Mercado pre-filtrados por la zona elegida.' },
      { title: 'Fuente de datos', body: 'Los puntos vienen de propiedades cargadas + market_listings (cache scraping) + price_history. Cuantas más cargues, más fina la grilla.' },
    ],
  },
  'tasador-ai': {
    title: 'Tasador AI',
    body: 'Chat conversacional con Gemini 2.5 Flash. Le hacés preguntas técnicas del rubro, le pedís opinión sobre una propiedad o le dictás un análisis.',
    steps: [
      { title: 'Streaming SSE', body: 'Las respuestas llegan en tiempo real palabra por palabra (Server-Sent Events), no esperás el final del request.' },
      { title: 'Contexto del workspace', body: 'El bot conoce las propiedades, tasaciones, mercado y ACMs cargados. Hablale del rubro inmobiliario argentino y responde con vocabulario técnico.' },
      { title: 'Preguntas útiles', body: '"¿Qué cap rate tiene Palermo?", "Comparame Recoleta vs Belgrano", "¿Cómo defiendo este valor frente al banco?", "Dame el TL;DR de mercado mayo".' },
      { title: 'Persistencia', body: 'El historial de la sesión queda en memoria. Botón reset chat arriba a la derecha para empezar de cero.' },
      { title: 'Provider transparente', body: 'Hoy usa Gemini (Cloud Run). Configurable desde Configuración → Proveedor IA si querés cambiar a Claude.' },
      { title: 'Limitaciones', body: 'No firma tasaciones ni edita ACMs. Es un asistente conversacional, no un agente con autoridad sobre tus datos.' },
    ],
  },
  equipo: {
    title: 'Equipo',
    body: 'Tasadores y colaboradores con acceso al workspace. Cada uno con rol y permisos diferenciados.',
    steps: [
      { title: 'Roles', body: 'Admin (acceso total y firma), Supervisor (revisa y firma de su equipo), Vendedor/Tasador junior (carga datos, arma borradores, no firma).' },
      { title: 'Invitar miembros', body: 'Email + rol. Sale invitación automática con link de registro pre-configurado para tu workspace.' },
      { title: 'Firma múltiple', body: 'Una tasación puede tener firmas de varios tasadores (admin + supervisor). Cada firma queda con hash propio.' },
      { title: 'Colaboración en ACM', body: 'Asignás colaboradores específicos a un ACM. Cuando uno comenta, los demás reciben notificación (email + bandeja).' },
      { title: 'Matrícula profesional', body: 'Cada user puede cargar su número de matrícula colegial. Sale impreso en el PDF de las tasaciones que firma.' },
      { title: 'Auditoría', body: 'Quién creó, modificó y firmó cada propiedad/ACM/tasación queda registrado con timestamp inmutable.' },
    ],
  },
  configuracion: {
    title: 'Configuración del workspace',
    body: 'Personalización visual, preferencias de IA, notificaciones y seguridad de la cuenta.',
    steps: [
      { title: 'Tema visual', body: 'Light/Dark + 14 paletas comerciales (Verde default, Ocean, Coral, Slate, Sunset, Forest, Mono, etc.). Persiste por usuario.' },
      { title: 'Tipografía', body: '9 fuentes con preview en vivo. Cambia toda la app (display + body) según la fuente elegida.' },
      { title: 'Proveedor de IA', body: 'Claude (Anthropic headless) o Gemini (Google REST). Cada uno con selector de modelo: Haiku/Sonnet/Opus o Flash/Pro.' },
      { title: 'Notificaciones', body: '3 toggles independientes: Email general (resumen semanal), Tasaciones firmadas (al cliente), Comentarios del equipo (a colaboradores). Todo vía Brevo SMTP.' },
      { title: 'Test email', body: 'Botón "Enviar email de prueba" valida que la configuración SMTP esté funcionando con un email real a tu casilla.' },
      { title: 'Seguridad', body: 'Cambio de contraseña con validación del password actual y mínimo 6 caracteres. JWT con expiración 24 hs.' },
    ],
  },
  clientes: {
    title: 'Clientes — CRM',
    body: 'Bancos, fondos, estudios jurídicos, inmobiliarias y particulares que te encargan tasaciones. CRM mínimo pero funcional.',
    steps: [
      { title: 'Tipos con color', body: 'Banco (azul), Fondo (violeta), Estudio (ámbar), Inmobiliaria (rosa), Particular (verde). Visible de un vistazo en cada card.' },
      { title: 'Datos completos', body: 'Nombre/razón social, contacto, email, teléfono, CUIT/DNI, dirección y notas. Todo opcional excepto nombre.' },
      { title: 'Búsqueda y filtros', body: 'Search por nombre/contacto/email. Filtros pill por tipo con conteo en vivo. Combo de sort: Nombre A-Z, Más/menos tasaciones.' },
      { title: 'Cruce automático', body: 'El total de tasaciones por cliente se calcula leyendo el client_name de las appraisals. No tenés que enlazar manualmente.' },
      { title: 'CRUD completo', body: 'Crear, editar y eliminar desde el modal. Confirmación antes de borrar para evitar accidentes.' },
      { title: 'Auto-seed inicial', body: 'La primera vez, si el workspace tiene tasaciones con clientes pero la tabla está vacía, se crean automáticamente derivados de los nombres usados.' },
    ],
  },
  bandeja: {
    title: 'Bandeja — Inbox unificado',
    body: 'Centro de mensajes del tasador: clientes, alertas del sistema, menciones del equipo y recordatorios propios.',
    steps: [
      { title: 'Tipos de mensaje', body: 'client_message (de un cliente), system_alert (del sistema), user_mention (un colega te mencionó), self_reminder (vos mismo), appraisal_assigned (te asignaron una tasación), billing.' },
      { title: 'Lista + detalle', body: 'Patrón Gmail. Izquierda: lista con dot sin-leer + preview a 2 líneas. Derecha: detalle con sender, body completo y acciones.' },
      { title: 'Prioridad', body: 'urgent / high / normal / low. Los urgentes aparecen primero y con un acento de color.' },
      { title: 'Referencias', body: 'Cada mensaje puede linkear a una tasación, propiedad o URL interna. Click en el link te lleva al item con contexto preservado.' },
      { title: 'Mark as read', body: 'Click en un mensaje lo marca como leído automáticamente. El timestamp `read_at` queda registrado para auditoría.' },
      { title: 'Mobile-friendly', body: 'En mobile la lista ocupa toda la pantalla. Tap en un mensaje navega a detalle full-screen con back button.' },
    ],
  },
  pipeline: {
    title: 'Pipeline — Kanban del flujo',
    body: 'Visualización tipo Trello del estado de cada tasación. 5 columnas que reflejan el flujo real del trabajo.',
    steps: [
      { title: 'Solicitada', body: 'Recién entró el encargo del cliente. Todavía no empezaste a trabajar. Acá viven mientras juntás datos de la propiedad.' },
      { title: 'En análisis', body: 'Estás armando el ACM, juntando comparables y aplicando ajustes. Es la fase más larga del flujo.' },
      { title: 'Borrador', body: 'Ya tenés el valor final pero no firmaste. Última oportunidad para ajustar antes de hacerla inmutable.' },
      { title: 'Firmada', body: 'Hash SHA-256 generado. La tasación es inmutable. Se dispara email automático al cliente si tiene email cargado.' },
      { title: 'Entregada', body: 'Confirmaste que el cliente recibió el PDF. Cierra el ciclo. Sirve para métricas de tiempo medio del proceso.' },
      { title: 'Drag & drop', body: 'Arrastrá las cards entre columnas para cambiar status. En mobile la vista cambia a scroll horizontal con snap por columna.' },
    ],
  },
  mercado: {
    title: 'Mercado — Dashboard macro',
    body: 'Estado del mercado inmobiliario CABA en tiempo real: índice TasAR, oferta, tiempo de venta y permisos de obra nueva.',
    steps: [
      { title: 'Período', body: 'Selector 7d / 30d / 90d / 12m / 5a. Cambia la ventana de cálculo de YoY/MoM y escala los valores con factor 0.15-3.2.' },
      { title: 'Índice TasAR', body: 'USD/m² mediano ponderado de toda la ciudad. Es el indicador macro principal — sale del último monthly_report publicado.' },
      { title: 'Oferta activa', body: 'Cantidad de unidades publicadas en venta. Si cae con precios subiendo = mercado caliente. Si sube con precios cayendo = correción.' },
      { title: 'Tiempo medio de venta', body: 'Días promedio que tarda una propiedad en venderse. Baja = mercado dinámico; sube = mercado lento.' },
      { title: 'Permisos nuevos', body: 'Permisos de obra aprobados en el mes. Es leading indicator: lo que se aprueba hoy es oferta efectiva en 18-24 meses.' },
      { title: 'Heatmap + ranking', body: 'Grilla 16x12 con intensidad por USD/m² mediano de cada celda. Ranking top 12 zonas al costado con flecha de cambio.' },
    ],
  },
  comparables: {
    title: 'Comparables — Búsqueda live',
    body: 'Motor de búsqueda en vivo sobre la base agregada del mercado (18K+ listings) con filtros precisos y exportación.',
    steps: [
      { title: 'Filtros pill', body: 'Zona, radio (400/800/1200/2000m), tipo (depto/casa/PH), ambientes, condición, antigüedad. Se aplican juntos en cada query.' },
      { title: 'Stats agregadas', body: 'Min, máx, mediana de USD/m² de los resultados. Detectás outliers de un vistazo: si min es muy bajo, probablemente sea ruido.' },
      { title: 'Match score', body: 'Cada comparable tiene un score 0-100 según similitud con tu filtro. Ordenados por score descendente por default.' },
      { title: 'Distancia haversine', body: 'Si filtrás por radio, cada resultado muestra distancia en metros desde el centro de la zona elegida.' },
      { title: 'Export CSV', body: 'Botón "Exportar CSV" descarga todas las columnas (título, precio, m², score, distancia) para análisis externo en Excel.' },
      { title: 'Uso en ACM', body: 'Esta pantalla es para exploración rápida. Para usar un comparable en un informe formal, vas al ACM y lo sumás desde ahí (queda asociado).' },
    ],
  },
  reportes: {
    title: 'Reportes — Editorial mensual',
    body: 'Análisis mensual del mercado en formato Bloomberg/revista financiera. Es el producto que TasAR publica al mercado.',
    steps: [
      { title: 'Cover negro', body: 'Cada reporte arranca con una card cover estilo portada de revista: edición, mes, YoY% y USD/m² grandes. Mini heatmap decorativo.' },
      { title: 'Leer documento', body: 'Click en "Leer" abre el documento largo formato editorial: cover hero, TL;DR 3 cards, secciones §01-§06 con sparklines, barcharts, pull quotes y cap rate table.' },
      { title: 'Filtros', body: 'Combos de año y tipo + pills de los 4 años más recientes con counts. Search por código, mes, año o región.' },
      { title: 'Reporte custom', body: 'Botón "+ Reporte custom" arriba a la derecha. Modal con región (CABA/GBA/Córdoba/Rosario), tipo, año y mes — dispara generación.' },
      { title: 'Sort + CSV', body: 'Ordená por Más recientes/antiguos o por mayor/menor YoY. Botón CSV exporta todos los reportes filtrados con sus KPIs.' },
      { title: 'Compartir', body: 'Cada card tiene botón Share que usa Web Share API o copia el link del documento al portapapeles. PDF descargable aparte.' },
    ],
  },
};
