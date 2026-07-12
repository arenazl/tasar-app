# TasAR — Brief de diseño de UI (para la app de diseño / Claude Design)

> **Requerimiento + contexto completo del producto para que un agente de diseño ORGANICE la UI de la
> suite.** La app nació de fusionar dos aplicaciones distintas (TasAR-tasaciones + AgentFlow-CRM) en un
> solo producto. Funcionalmente está completa y anda; **lo que falta es coherencia visual y de flujo** —
> hoy se siente, en palabras del dueño, "una bolsa de gatos sin propósito ni flujo intuitivo".
> Este doc es el *qué diseñar* y el *por qué*; el detalle técnico del rework vive en
> `base-compartida/tasar/` (01-analisis, 02-hoja-de-ruta, 04-curaduria-flujo).
>
> **Fecha:** 2026-07-11 · **App:** `d:\Code\ACM` (backend FastAPI + frontend React/Vite/TS). Corre contra
> base MySQL real (Aiven). **No implementar UI sin el diseño aprobado.**

---

## 1. Qué es (y el norte)

**Hoy:** TasAR es una **suite inmobiliaria integral** para inmobiliarias argentinas. Cubre todo el ciclo de
una operación en una sola app multi-inmobiliaria (multi-tenant): **Captar → Gestionar → Atender → Cerrar**.

- **Captar:** tasación express anclada a datos de mercado reales + tasaciones formales + estudios de mercado (ACM).
- **Gestionar:** CRM (clientes/leads), cartera de propiedades, pipeline de ventas, y el **DMO** (método diario de trabajo del vendedor — el diferencial).
- **Atender:** bot de WhatsApp multi-tenant con 7 herramientas + inbox humano.
- **Cerrar:** visitas, pipeline legal AR de 6 etapas, autorizaciones.

**El norte:** que una inmobiliaria opere TODO su negocio acá adentro, sin herramientas sueltas — y que un
usuario entienda el recorrido de un vistazo. **El diseño tiene que hacer que la suite se sienta UN
producto, no dos apps pegadas.**

## 2. Cómo funciona (contexto mínimo para diseñar bien)

- **Multi-tenant:** cada inmobiliaria es un *workspace* aislado. Un login → un workspace → todas las
  funciones según el rol. NO hay "app de tasación" y "app de CRM" separadas: es una sola.
- **Jerarquía de roles (4 niveles, cada uno hace TODO con distinto alcance):**
  `broker (titular) > administrador > coordinador > asesor (vendedor)`. La navegación y los permisos se
  filtran por nivel (helper `require_min_role` en back, `lib/roles.ts` en front). El asesor ve su
  operación; coordinador+ ve todo el workspace y la gestión.
- **Cuatro piezas que se relacionan:** (a) **motor de valuación** (ACM + anchor sobre `market_listings`,
  miles de propiedades reales) alimenta tasación express/estudios; (b) **CRM** (clientes, propiedades,
  visitas, deals, autorizaciones, DMO) es el centro; (c) **bot WhatsApp** (canal Baileys o Meta →
  pipeline entrante único → 7 tools que operan sobre el CRM); (d) **notificaciones** (Bandeja de eventos +
  push PWA + email). El ciclo se retroalimenta: cada cliente atendido alimenta la próxima captación.
- **Datos reales para diseñar (no inventar):** hay un workspace **Beyker** con datos reales migrados
  (9 usuarios, 35 clientes, 20 propiedades, 45 visitas, 22 deals, 254 mensajes WhatsApp, DMO completo con
  179 logs). Usar esos datos en los mockups, o placeholders marcados `[DEMO]`.

## 3. El problema (por qué se diseña ahora) — el "frankenstein"

Funciona, pero **la experiencia no está curada**. Diagnóstico honesto:

1. **Dos generaciones de UI conviven con costuras.** Las pantallas nativas de TasAR (tasación, estudios,
   mercado, propiedades) y las portadas de AgentFlow (DMO, pipeline, visitas, inbox, bot, clientes) usan
   patrones parecidos pero **no idénticos** (headers, spacing, tablas, modales, tipografía). Se nota que
   son dos orígenes.
2. **Creció por acumulación, no por flujo.** Se hizo el *wiring* (traer y conectar features) pero recién
   ahora la *curaduría*. La navegación llegó a ~22 entradas; una poda la bajó a 7+1, pero la poda fue
   **demasiado agresiva** y escondió gestión que se usa seguido (el DMO — templates/asignaciones/coaches —
   quedó enterrado dentro de Configuración; el dueño no lo encontraba).
3. **Las entidades eran islas.** La tasación terminaba en un PDF sin desembocar en lead→visita→deal. Se
   agregaron **CTAs encadenados** (componente `NextStepCard`) y una **ficha de cliente eje** con timeline,
   pero el diseño de esos hilos es funcional, no pulido.
4. **El cliente recién ahora es el eje.** Se creó `/clientes/:id` con timeline unificado (chat + visitas +
   deals + tasaciones) y "siguiente paso" derivado — es el corazón conceptual y merece el mejor diseño.
5. **Riqueza de theming sin gobierno visual.** Hay 12 presets de tema (light/dark) + fuentes seleccionables;
   el estilo se aplica por **objeto `theme` inline** (no CSS vars), lo que hace fácil desalinear una
   pantalla de otra. No hay un sistema de componentes estricto que garantice consistencia.

**Este brief es sobre ORGANIZAR y dar COHERENCIA de flujo + visual, no sobre repintar de cero.** La
identidad (TasAR, verde `#10b981`, dark/light) se mantiene.

## 4. Objetivo del diseño

Que un usuario —según su rol— entienda **qué hacer al entrar** (la home "Hoy"), **navegue sin perderse**
(estructura clara, sin cosas escondidas ni huérfanas), **recorra el ciclo por CTAs** (no de memoria), y que
**todas las pantallas se vean del mismo sistema** (borrar las costuras TasAR/AgentFlow). Y resolver las
tensiones abiertas de navegación (qué va en la barra, qué en Configuración, qué accesos directos).

---

## 5. Mapa completo de la navegación (estado actual, post-curaduría F6)

### 5.1 Sidebar desktop (7 entradas de trabajo + Configuración)
Filtradas por rol (nivel mínimo entre paréntesis). Las secciones con subnav se auto-expanden al entrar.

| Entrada | Ruta | Subnav | Rol mínimo |
|---|---|---|---|
| **Hoy** | `/` | — | asesor (todos) |
| **Chat** | `/whatsapp` | Bandeja (`/bandeja`) | asesor |
| **Clientes** | `/clientes` | ficha `/clientes/:id` | asesor |
| **Propiedades** | `/propiedades` | — | asesor |
| **Pipeline** | `/pipeline` | Autorizaciones (`/autorizaciones`) | asesor / autoriz. coordinador |
| **Tasar** | `/tasacion-express` | Tasaciones (`/tasaciones`), Estudios (`/estudios`) | asesor |
| **Mercado** | `/mercado` | Comparables (`/comparables`), Mapa (`/mapa`), Reportes (`/reportes`) | coordinador |
| **Configuración** | `/configuracion` | (in-page) Gestión: Equipo, DMO (templates/asignaciones/coaches), Bot (Datos IA), Métricas | coordinador |

### 5.2 Mobile (bottom bar de 5 + sheet "Más")
Tabs fijos: **Hoy · Chat · FAB · Pipeline · Clientes**. El FAB abre un sheet "Crear" (nueva tasación
express / nuevo cliente / nueva visita) + "Ir a" (el resto de las secciones según rol). Sheet "Más":
Propiedades, Tasar, Mercado, Configuración (por rol).

### 5.3 Todas las rutas (32) — para que el diseño no deje ninguna huérfana
`/login` · `/registro` (wizard alta de inmobiliaria) · `/invitacion/:token` (alta por invitación) ·
`/` (Hoy) · `/metricas` (Dashboard KPI, ex-home) · `/bandeja` · `/whatsapp` (Inbox) · `/clientes` ·
`/clientes/:id` (ficha) · `/propiedades` · `/pipeline` (kanban deals) · `/visitas` · `/autorizaciones` ·
`/tasacion-express` · `/tasaciones` · `/tasaciones/:id` · `/tasaciones/pipeline` (PipelineTasaciones) ·
`/estudios` · `/estudios/:id` · `/mercado` · `/comparables` · `/mapa` · `/reportes` · `/reportes/:id` ·
`/dmo` (Mi DMO) · `/dmo-templates` · `/dmo-asignaciones` · `/coaches` · `/equipo` · `/datos-ia` (bot config) ·
`/configuracion`. *(Deprecada, sin entrada: `/tasador-ai` — el asistente IA vive como panel contextual.)*

### 5.4 Elementos de shell transversales
- **AI Coach:** panel contextual por ruta (`AICoachPanel`) — un asistente que explica cada pantalla.
- **Tour de primer día:** 5 pasos por rol (Hoy→Chat→Clientes→Pipeline→Tasar), sobre el mecanismo `PageHint`.
- **Selector de tema y fuente:** 12 presets + fuentes, en Configuración.

---

## 6. Las partes — todas las pantallas, propósito y estado

> **Origen** indica la costura a resolver: `TasAR` = nativa (más pulida, es el canon visual); `AgentFlow` =
> portada (a alinear al canon); `nueva` = creada en la curaduría F6.

### Inicio
- **Hoy** (`/`, *nueva*): home accionable por rol. Vendedor: su DMO del día (línea horaria) + conversaciones
  esperando + próximas visitas + leads nuevos, todo clickeable. Coordinador+: pulso del equipo. **Es la
  pantalla más importante y la que primero hay que dejar impecable** (y es LA pantalla mobile del asesor).
- **Métricas** (`/metricas`, *TasAR*): dashboard de KPIs (ex-home). Vista secundaria.

### Captar
- **Tasación express** (`/tasacion-express`, *TasAR*): form corto → rango de valor anclado + confianza +
  factores + PDF. Tiene `NextStepCard` (guardar cliente / cargar propiedad). El gancho comercial.
- **Tasaciones** (`/tasaciones`, `/tasaciones/:id`, *TasAR*): listado + detalle con workflow de estados +
  firma + PDF. Sub-vista `PipelineTasaciones` (`/tasaciones/pipeline`).
- **Estudios ACM** (`/estudios`, `/estudios/:id`, *TasAR*): análisis comparativo con comparables + consenso
  del equipo. **`EstudioEditorial`** es una vista "editorial" extensa de un reporte (revisar si se mantiene).

### Gestionar (Cartera + Equipo)
- **Clientes** (`/clientes`, *AgentFlow*): CRM — leads con estado/temperatura/origen/preferencias.
- **Ficha de cliente** (`/clientes/:id`, *nueva*): **el eje.** Cabecera + timeline unificado + "siguiente
  paso" derivado + acciones rápidas. Merece el mejor diseño de la suite.
- **Propiedades** (`/propiedades`, *TasAR*): inventario con fotos. Tiene `NextStepCard` post-alta.
- **Autorizaciones** (`/autorizaciones`, *AgentFlow*): contratos de autorización (subnav de Pipeline).
- **Pipeline de ventas** (`/pipeline`, *AgentFlow*): kanban de deals de 6 etapas legales con drag-and-drop.
- **Visitas** (`/visitas`, *AgentFlow*): calendario (semana/mes) + alta rápida. Pre-carga por `?cliente=`/`?propiedad=`.
- **Mi DMO** (`/dmo`, *AgentFlow*): rutina diaria del vendedor con bloques + money-blocks + % completitud.
- **Templates DMO / Asignaciones / Coaches** (`/dmo-templates`, `/dmo-asignaciones`, `/coaches`, *AgentFlow*):
  la cocina del DMO (catálogo de 5 metodologías, personalización, asignación). **Hoy enterradas en
  Configuración — el punto de dolor #1 de la navegación (ver §11).**

### Atender (Chat)
- **Inbox WhatsApp** (`/whatsapp`, *AgentFlow*): conversaciones; tomar mando (pausa el bot), responder,
  reasignar, reactivar bot. Texto + notas de voz. `NextStepCard` "crear cliente desde el chat".
- **Bandeja** (`/bandeja`, *TasAR + producer AgentFlow*): centro de eventos reales (lead, visita,
  derivación, firma, comentario). Subnav de Chat.
- **Datos IA · Bot** (`/datos-ia`, *AgentFlow*): config del bot por workspace (mensajes, horario, FAQs,
  conexión Baileys/Meta). En Configuración → Gestión → Bot.

### Mercado (coordinador+)
- **Mercado** (`/mercado`, *TasAR*), **Comparables** (`/comparables`, *TasAR*), **Mapa** (`/mapa`, *TasAR*,
  heatmap Leaflet), **Reportes** (`/reportes`, `/reportes/:id`, *TasAR*, custom + PDF).

### Transversales / gestión
- **Equipo** (`/equipo`, *TasAR ampliada*): usuarios, invitaciones por email, roles, disponibilidad.
- **Configuración** (`/configuracion`, *TasAR*): preferencias, tema/fuente, notificaciones, datos demo, y la
  sección "Gestión del workspace" que concentra DMO/Bot/Equipo/Métricas.
- **Registro** (`/registro`, *nueva/TasAR*): wizard de alta self-service (4 pasos).
- **Login** (`/login`, *TasAR*): hero de suite (desktop) + form con 3 perfiles demo (Broker/Coordinador/Asesor).
- **Aceptar invitación** (`/invitacion/:token`, *nueva*).

---

## 7. Sistema de diseño actual (para que el diseño sea implementable)

- **Stack:** React 18 + Vite 5 + TypeScript + **Tailwind 3.4** + **@headlessui/react** (modales/menus) +
  **lucide-react** (iconos) + **sonner** (toasts) + **react-router-dom 6** + **leaflet/react-leaflet** (mapas).
- **Theming — clave y particular:** NO usa CSS variables. Usa un **objeto `theme`** (contexto
  `ThemeContext`) con ~25 tokens que se aplican **inline**: `style={{ color: theme.text, background: theme.card }}`.
  Tokens: `background, backgroundSecondary, card, sidebar, topbar, text, textSecondary, textOnSidebar,
  primary, primaryText, primaryHover, primaryLight, success, danger, warning, info, border, borderLight,
  gradientFrom/Via/To`. Hay **12 presets** (light+dark cada uno; default `tasar`, verde `#10b981`) y
  **fuentes seleccionables** (default Inter; familias cargadas en `index.html`). Clase `font-display` para
  títulos. **El diseño debe proponer un patrón que garantice consistencia sobre este esquema inline** (ej.
  componentes que encapsulen los tokens), porque el estilo suelto por pantalla es la causa raíz de las costuras.
- **Componentes canónicos existentes (reusar/elevar, no reemplazar):**
  - `components/ui/ABMPage` + `Table` + `SideModal` + `ConfirmModal` — el patrón ABM de listado/alta/edición
    (las pantallas nativas de TasAR lo usan; las de AgentFlow no siempre → costura a cerrar).
  - `components/ui/NextStepCard` (nuevo) — el patrón visual único de "siguiente paso" (CTAs del ciclo).
  - `components/Layout` (sidebar + subnav) + `MobileBottomBar` (tabs + FAB + sheet).
  - `components/BrandLogo` (SVG del brand book, variantes icon/topbar/standard).
  - `components/AICoachPanel` (asistente contextual) + `PageHint` + `FirstDayTour`.
  - `config/brand.ts` (fuente única del nombre "TasAR" + tagline + color), `lib/roles.ts` (jerarquía).
- **Datos/API:** `services/api.ts` (axios, proxy same-origin `/api`). Cada pantalla llama endpoints REST ya
  existentes. El diseño no puede pedir campos que no existen sin marcarlos `[propuesta]`.

## 8. Requisitos de UI/UX (obligatorios)

1. **Una sola familia visual.** Definir el sistema (header de página, cards, tablas, modales, empty-states,
   badges, botones) y aplicarlo a TODAS las pantallas para borrar la costura TasAR/AgentFlow. El canon es la
   estética nativa de TasAR; las portadas se alinean.
2. **"Hoy" impecable, por rol.** Es la entrada y la pantalla mobile del asesor. Debe responder "¿qué hago
   ahora?" — no ser un dashboard de números.
3. **Ficha de cliente como eje.** Timeline unificado legible (chat/visitas/deals/tasaciones diferenciados
   por tipo), "siguiente paso" destacado, acciones rápidas claras.
4. **Navegación resuelta (ver §11 la tensión abierta):** la gestión del DMO no puede quedar escondida; hay
   que decidir su lugar. Ninguna ruta huérfana; subnav clara; qué es trabajo diario vs setup.
5. **CTAs del ciclo visibles pero no ruidosos:** `NextStepCard` aparece solo cuando aplica; un lenguaje
   visual único para "el siguiente paso".
6. **Lenguaje de artefactos consistente:** estados de tasación, etapas del pipeline (6), estados de lead,
   temperatura, disponibilidad — mismos colores/badges en todas las pantallas.
7. **Roles visibles en la UX:** que se entienda qué ve/hace cada nivel (broker/administrador/coordinador/
   asesor) sin que el asesor tropiece con cosas que no puede tocar.
8. **Multi-formato de datos:** la suite maneja mapas (heatmap), calendarios (visitas), kanban (pipeline),
   timelines (cliente/DMO), tablas (ABM) — el sistema visual tiene que servir a todos sin romperse.

## 9. Restricciones técnicas (para que el diseño sea implementable)

- Reusar el **objeto `theme` + presets** existentes (no meter CSS vars nuevas sin migrar el esquema; si se
  propone migrar a CSS vars, marcarlo como decisión de arquitectura).
- Reusar **Tailwind + Headless UI + lucide + los componentes canónicos**. No sumar librerías de UI pesadas
  sin justificar (no hay design-system externo instalado).
- **Endpoints ya existen** (REST `/api/*`); el diseño no debe pedir datos que el backend no expone sin
  marcarlo `[propuesta]`.
- **Bundle:** hoy ~928 kB sin code-splitting. El diseño no debe empeorarlo; idealmente habilita `React.lazy`
  por ruta.

## 10. Reglas duras (no negociables)

- **Sin emojis.** Solo iconos SVG (lucide, ya en uso).
- **Español rioplatense** (voseo) en toda la UI.
- **Dark Y light:** ambos modos deben verse intencionales (hay 12 presets; el default es `tasar` verde).
- **Viewport PWA estándar** (ya aplicado, mantener): sin zoom en inputs (`font-size ≥16px`), sin scroll
  horizontal, safe-area de iPhone (`env(safe-area-inset-top)`). Ver `base-compartida/11-FIX-VIEWPORT-PWA.md`.
- **Honestidad de datos (regla dura del proyecto):** ningún número inventado en mockups; usar datos reales
  de Beyker o marcar `[DEMO]`.
- **No romper el modelo de datos ni los endpoints** — el rediseño es de experiencia y presentación.
- **Multi-tenant y roles intactos:** el diseño respeta el aislamiento por workspace y la jerarquía.

## 11. Dudas técnicas y deuda abierta (lo que hay que resolver o tener en cuenta)

1. **[NAVEGACIÓN — el #1] La poda agresiva escondió la gestión del DMO.** Templates/Asignaciones/Coaches
   quedaron dentro de Configuración → Gestión; el dueño (que los usa) no los encontraba. **Decisión de
   diseño pendiente:** ¿un módulo "Equipo/DMO" propio y visible en la barra (coordinador+), o mejorar el
   acceso dentro de Configuración? El equilibrio poda-vs-accesibilidad es el tema central de navegación.
2. **Dos generaciones de UI.** Es la costura principal (§3.1). El diseño tiene que unificar sin reescribir
   la lógica.
3. **Theming por objeto inline (no CSS vars).** Escala mal y facilita el desalineo. Evaluar si el sistema de
   diseño encapsula los tokens en componentes o migra a CSS vars (decisión de arquitectura, con impacto).
4. **Badge de "no leídos" en Chat sin cablear** (nunca tuvo el contador real). Definir el patrón de badges de
   notificación (Chat, Bandeja) y cablearlo.
5. **Ficha de cliente — chat vacío por dato faltante.** Las conversaciones migradas de Beyker quedaron con
   `client_id` NULL (no enlazadas). Hay un backfill por teléfono pendiente; el diseño debe contemplar el
   estado "sin conversaciones enlazadas" con gracia.
6. **`EstudioEditorial`** es una vista larga tipo "revista" de un reporte de mercado. Definir si se mantiene,
   se integra al detalle de estudio, o se simplifica.
7. **AI Coach vs Tasador AI.** El panel `AICoachPanel` (contextual) se queda; la página standalone
   `/tasador-ai` se deprecó. Confirmar que el panel cubre la necesidad y definir su lugar en el layout.
8. **PageHints / Tour.** Hay hints por pantalla + un tour de primer día; algunos hints quedaron huérfanos.
   El diseño debe integrarlos como parte del onboarding, no como pop-ups sueltos.
9. **Login con dos layouts** (hero desktop + form mobile con 3 perfiles demo). Revisar coherencia con la
   landing pública (`landing/`, que ya se rehizo sobre el ciclo Captar→Cerrar).
10. **Manifest PWA ausente** (faltan íconos 192/512 de marca) → la app no es instalable. Si diseño provee los
    íconos, se completa el manifest.
11. **Bundle sin code-splitting** (~928 kB). Oportunidad de `React.lazy` por ruta al reorganizar.
12. **Reportes servidos por streaming del backend** (el Cloudinary del proyecto bloquea PDFs) — el botón
    "abrir PDF" descarga vía API. Detalle a considerar en el patrón de "abrir documento".

## 12. Entregable esperado de la app de diseño (Claude Design)

1. **Sistema visual unificado:** tokens (sobre el `theme` existente), tipografía, escala de spacing, y el set
   de componentes canónicos (header de página, card, tabla/ABM, modal, empty-state, badge, `NextStepCard`,
   panel AI Coach) que borre la costura TasAR/AgentFlow.
2. **Arquitectura de navegación resuelta:** la barra final (desktop + mobile), dónde vive la gestión del DMO
   (§11.1), la lógica de subnav, y el mapa de qué es trabajo diario vs setup — por rol.
3. **Mockups de las pantallas clave:** **Hoy** (asesor y coordinador+), **Ficha de cliente** (el eje),
   **Pipeline** (kanban), **Inbox WhatsApp**, **Tasación express** (con su `NextStepCard`), y **Configuración**
   (cómo se ordena la gestión). Light y dark.
4. **El lenguaje de artefactos** (estados/etapas/temperatura/roles) como parte del sistema.
5. Todo expresado sobre el stack real (Tailwind + objeto `theme` + Headless UI + lucide) y listo para que el
   implementador lo traduzca a los componentes, sin pedir librerías nuevas ni datos inexistentes.

---

## 13. Material de apoyo (leer para contexto)

- **Guía de producto para socios** (qué hace cada pantalla, con diagramas): `docs/reportes/02-guia-producto-suite.html`.
- **Reporte del rework** (28 WOs, estado técnico): `docs/reportes/01-rework-suite-inmobiliaria.html`.
- **Plan de curaduría de flujo** (F6, decisiones de UX ya tomadas): `base-compartida/tasar/04-curaduria-flujo.md`.
- **Análisis integral y hoja de ruta** originales: `base-compartida/tasar/01-analisis-integral.md`, `02-hoja-de-ruta.md`.
- **Datos reales para mockups:** workspace **Beyker** (login de prueba a coordinar con el dueño).
