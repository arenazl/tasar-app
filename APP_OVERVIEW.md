# TasAR — Plataforma de Tasaciones y Mapa de Valor

> SaaS multi-tenant para tasadores inmobiliarios en Argentina.
> Stack: React + Vite + Tailwind (front) · FastAPI + aiomysql + Aiven (back) · Claude/Gemini (IA).
> Producción: [app](https://tasar-app.netlify.app) · [landing](https://tasar-landing.netlify.app) · API: `tasar-api.herokuapp.com`.

---

## Arquitectura general

- **Multi-tenant** por `workspace_id` — cada usuario pertenece a un workspace y todos los recursos quedan aislados.
- **Auth JWT** con 3 roles: `admin`, `supervisor`, `vendedor`. Login con perfiles demo o email+password.
- **IA transparente**: adapter que conmuta entre Claude (headless local) y Gemini (REST cloud) sin tocar el código que la consume. Se elige desde Configuración.
- **App Shell**: sidebar fija a la izquierda (oculta en mobile, reemplazada por bottom bar con FAB central), AI Coach fijo a la derecha en desktop, contenido scroll independiente en el medio.
- **Bottom bar mobile**: 4 tabs principales (Bandeja, Tasaciones, Mercado, AI) + FAB central "Más" que abre bottom-sheet con 8 pantallas adicionales.

---

## Login

**Ruta**: `/login`

Diseño split-screen estilo landing:
- **Izquierda (desktop)**: hero negro con branding TasAR, headline "El mercado inmobiliario, en datos.", tagline, 3 stats (avisos, update, IA) y footer de estado SSL/JWT.
- **Derecha**: card con 3 perfiles demo (Admin / Supervisor / Vendedor) en pills + form email+password tradicional + link a registro.

**Funcionalidad real**:
- Quick login con 1 click por perfil demo (carga credenciales y dispara `/auth/login`).
- Form email+password con validación y toasts de error.
- En mobile el hero se oculta y queda solo el form centrado.

---

## Dashboard (`/`)

**Visión general de la actividad del workspace.**

- **AI Coach contextual** en card outline arriba de la página (no gradient verde, consistente con el resto): pide a Claude/Gemini un tip basado en el estado del workspace (propiedades cargadas, tasaciones recientes, etc.).
- **KPIs** (4 cards): total propiedades, tasaciones en progreso, valor total firmado USD, comparables analizados. Cada KPI con icono, valor grande y delta % vs mes anterior.
- **Gráfico Propiedades por tipo**: barras horizontales con gradient primary→info por categoría (casa / depto / PH / terreno / local / oficina).
- **PageHint dismissable**: tutorial paso a paso al primer uso.

**Endpoint**: `GET /api/dashboard` agrega counts + suma de valores del workspace.

---

## Bandeja (`/bandeja`)

**Inbox unificado del tasador** (patrón Gmail).

- Lista a la izquierda con dot sin-leer + preview a 2 líneas + timestamp.
- Detalle a la derecha con asunto, sender, body completo y acciones contextuales.
- Soporta múltiples kinds: `client_message`, `system_alert`, `user_mention`, `self_reminder`, `billing`, `overdue_task`, `appraisal_assigned`, `comparable_added`.
- **Mobile**: solo lista, tap navega a detalle full-screen con back button.

**Acciones**: marcar leído / archivar / responder (deep-link contextual).

**Endpoints**: `GET /api/inbox` · `POST /api/inbox/{id}/mark-read`.

---

## Tasaciones (`/tasaciones`)

**Módulo principal**. Cada tasación es una unidad de trabajo identificada como `TR-XXXX`.

### Listado
- ABMPage canónico con search por código/cliente/dirección.
- Filtros pill: `Todas / Borrador / Firmadas / Entregadas / Con ACM / Por vencer`.
- Combos secundarios: filtro por propiedad + finalidad (compraventa, hipoteca, sucesión, etc.).
- Vista cards (default) + vista tabla.

### Card
- Código TR-XXXX, cliente, badge de status (color por estado), pill de finalidad, link a ACM si tiene.
- **Valor final** destacado.
- Acciones: Firmar (si no firmada) → genera firma SHA-256 + dispara email al cliente · Descargar PDF · Editar.

### Detalle
- Análisis embebido (IA-generated): `suggested_value_min`, `max`, `mode`, `confidence_score`, `cap_rate`, `comparables_count`.
- Lista de comparables linkeados con `match_score` y ajustes aplicados.

**Endpoints**: `GET/POST/PUT /api/appraisals` · `POST /api/appraisals/{id}/sign` · `GET /api/appraisals/{id}/pdf`.

---

## Propiedades (`/propiedades`)

**Catálogo de propiedades del workspace** (lo que el tasador va a tasar).

- ABMPage con search por título/dirección/barrio.
- Wizard de creación multi-step (datos básicos → ubicación → superficie → estado → fotos).
- Análisis AI on-demand por propiedad: dispara Claude/Gemini con system prompt de tasador.
- Filtros: tipo de propiedad, operación (venta/alquiler), estado (a estrenar / excelente / muy bueno / bueno).

**Vista guiada**: tab a tab para tasadores nuevos (datos + ACM + comparables + valor final).

**Endpoints**: `GET/POST/PUT/DELETE /api/properties` · `POST /api/properties/{id}/analyze`.

---

## Pipeline (`/pipeline`)

**Kanban visual del flujo de tasaciones**.

- 5 columnas: `Solicitada → En análisis → Borrador → Firmada → Entregada`.
- Cards arrastrables entre columnas (cambia status).
- Count por columna en header.
- **Mobile**: scroll horizontal con snap-x, columnas `w-[280px]` para que se vea una completa por vez.

**Endpoint**: `GET /api/appraisals?status=...` agrupado por status.

---

## Clientes (`/clientes`)

**CRM mínimo del workspace** (tabla propia `clients`, no derivada).

- ABMPage con search por nombre/contacto/email.
- Filtros pill por tipo con conteos: Banco (azul) / Fondo (violeta) / Estudio (ámbar) / Inmobiliaria (rosa) / Particular (verde).
- Card: avatar con color del tipo, nombre, contacto, email, teléfono, dirección, CUIT/DNI, total de tasaciones.
- Modal create/edit con todos los campos.
- Delete con confirm.

**Endpoints**: `GET/POST/PUT/DELETE /api/clients` (enriquece response con `appraisals_count` por cruce con `client_name` legacy).

---

## Mercado (`/mercado`)

**Dashboard macro del mercado inmobiliario CABA**.

- Header con período: `7d / 30d / 90d / 12m / 5a`. El backend escala YoY/MoM/permits según ventana (factor 0.15 a 3.2).
- **4 KPIs**: Índice TasAR, Oferta activa, Tiempo medio de venta, Permisos nuevos.
- **Mapa de calor grid 16×12**: forma circular tipo CABA con intensidad por distancia al centro, color primario del theme activo.
- **Ranking por zona top 12**: USD/m² con flecha de cambio % y conteo de muestras. Click en zona → drill-down (ver siguiente).

**Endpoint**: `GET /api/market/dashboard?period=X` lee último `monthly_report` y agrega listings activos por zona.

---

## Mapa de Calor (`/mapa`)

**Heatmap geográfico real con Leaflet + leaflet.heat**.

- Tile OpenStreetMap.
- Puntos del workspace (propiedades + comparables + histórico) con `circleMarker` y popup `USD/m²`.
- HeatLayer con radius 28, blur 22, maxZoom 14.
- **Filtros**: ciudad (combo), tipo de propiedad, operación, fuente (todo/props/comps/histórico).
- **Ranking lateral top 10** con click → abre drill-down panel:
  - KPI hero USD/m² con barra de % del top y comparación vs promedio de ciudad.
  - 4 stats: muestras, listings activos, min/max.
  - Lista de puntos en la zona.
  - Links contextuales a Comparables y Mercado pre-filtrados.

**Endpoints**: `GET /api/heatmap/points` · `GET /api/heatmap/zones`.

---

## Estudios (ACM) (`/estudios` y `/estudios/:id`)

**Análisis Comparativo de Mercado** — la herramienta core del tasador profesional.

### Listado
- Tabla de ACMs con código, propiedad, status, fecha, mediana USD/m², número de comparables.

### Detalle (`EstudioDetail`)
- Editor enriched con:
  - Datos de la propiedad target (origen).
  - **Sugerencias auto-disparadas de IA**: panel de candidatos con score + accept/reject buttons.
  - Tabla editable de comparables con campos: dirección, m², precio, USD/m², ajustes (zona, antigüedad, estado, m²).
  - Drag-and-drop de campos de cálculo.
  - Bloques colapsibles: estructura ponderada, ajustes detallados, conclusión.
- **Generador IA** de comparables vía `comparable_ai_service` (consulta workspace + external_listings + Claude evaluation con system prompt).
- Comentarios colaborativos del equipo (dispara email a colaboradores).

**Endpoints**: `GET/POST/PUT /api/market_studies` · `POST /api/market_studies/{id}/suggest-comparables` · `POST/GET /api/collaboration/{id}/comments`.

---

## Comparables (`/comparables`)

**Búsqueda live en la base agregada del mercado** (18K+ listings seed + scraping).

- Filtros pill: zona, radio (400/800/1200/2000m), tipo, ambientes, condición, antigüedad (7/30/90/180 días).
- Stats arriba: total, min, max, mediana.
- Cards con título, dirección, m², ambientes, precio, USD/m², días en mercado, match_score, distancia.
- **Export CSV funcional**: descarga real con columnas (título, precio, m², score, distancia) usando util reusable.

**Endpoint**: `GET /api/market/comparables` con haversine distance + match score por similitud.

---

## Reportes (`/reportes`)

**Análisis mensual del mercado** publicado el primer día hábil del mes.

- Grid de cards con hero negro (código + tipo + nuevo badge + período), mini heatmap decorativo, stats (YoY % en verde/rojo, USD/m² mediana, fecha y páginas).
- **Filtros modal**: chips por año + tipo, chips activos al header.
- **Reporte custom modal**: region (CABA / GBA / Córdoba / Rosario) + tipo (Residencial / Comercial / Industrial / Mixto) + año + mes → POST `/reports/custom`.
- **Export CSV global** de todos los reportes filtrados.
- **Compartir** por card: usa Web Share API o copia link al portapapeles.
- **Abrir PDF** abre `pdf_url` en tab nueva.

**Endpoints**: `GET /api/reports` · `POST /api/reports/custom`.

---

## Tasador AI (`/tasador-ai`)

**Chat conversacional contextual** con Claude (o Gemini si está configurado).

- Stream-JSON via SSE (Server-Sent Events).
- System prompt: "Sos el asistente del tasador. Conocés contexto del workspace (propiedades, tasaciones, mercado). Respondé en español, conciso, accionable."
- Persistencia en memoria de la sesión.
- Header con avatar IA + estado "en línea" + reset chat.

**Endpoint**: `POST /api/ai/chat` con streaming SSE.

---

## AI Coach (panel global)

**Sidebar fija a la derecha en desktop, bottom-sheet on demand en mobile**.

- **Desktop**: always-open, 320px ancho, header sticky + footer sticky + scroll interno solo en la lista de tips. Sin FAB ni botón cerrar.
- **Mobile**: FAB con icono Sparkles arriba del bottom bar, tap abre bottom-sheet `max-h-[80vh]` con drag handle.
- Cambia de contenido **automáticamente al cambiar de ruta** (route-context aware).
- Cada tip tiene `severity` (info/warning/success), título, body, action_label opcional + action_url.
- Refresh manual button + indicador "Claude analizando..." durante carga.

**Endpoint**: `POST /api/ai/coach` con `{route}` → backend genera tips contextualizados con stats del workspace.

---

## Configuración (`/configuracion`)

**Preferencias del workspace y del usuario**.

### Tema visual
- Toggle Light/Dark.
- 14 paletas comerciales (Default Verde, Ocean, Coral, Slate, Sunset, Forest, Mono, etc.) — cada una con preview de 3 colores (accent + sidebar + card).
- Persistencia en localStorage.

### Tipografías
- 9 fuentes con preview en vivo del label + texto de muestra TasAR.

### Proveedor de IA
- Claude (Anthropic) — calidad alta, headless local en backend.
- Gemini (Google) — rápido, API cloud.
- Persistencia en `app_settings.ai_provider` + cache invalidation.
- Selector de modelo según provider:
  - Claude: Haiku / Sonnet / Opus.
  - Gemini: Flash 2.5 / Pro 2.5.

### Notificaciones
- 3 toggles independientes con persistencia en `/settings/notify_*`:
  - **Email general** — resumen semanal del workspace.
  - **Tasaciones firmadas** — cuando se firma una tasación.
  - **Comentarios del equipo** — cuando un colaborador comenta un estudio.
- **Botón "Enviar email de prueba"** — dispara `POST /settings/test-email` y valida SMTP en vivo.

### Cambiar contraseña
- Modal con campos: actual + nueva + confirmar.
- Valida pass actual contra hash.
- Mínimo 6 caracteres + match entre nueva y confirmar.

**Endpoints**: `GET/PUT /api/settings/{key}` · `POST /api/auth/change-password` · `POST /api/settings/test-email`.

---

## Sistema de Email (Brevo SMTP)

**Integración real con cuenta Brevo activa**.

- Service canónico `email_service.py` con `smtplib + MIMEMultipart + starttls + thread pool async`.
- Template HTML TasAR (header negro + brand + footer con disclaimer).
- Helper `_notify_enabled(workspace_id, key)` que respeta los toggles de Configuración.
- **3 triggers reales en producción**:
  1. **Tasación firmada** → email a `client_email` con valor final formateado.
  2. **Comentario en estudio** → email a colaboradores (excluye autor).
  3. **Test manual** → desde Configuración para validar SMTP.
- Heroku config con creds reales: `SMTP_HOST=smtp-relay.brevo.com`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM=arenazl@gmail.com`.

---

## Sistema de IA (adapter Claude ↔ Gemini)

**Switch transparente entre providers**.

- `ai_router.py` con `chat_complete(prompt, system)` que internamente:
  - Lee provider activo desde `app_settings.ai_provider` (cache 15s).
  - Despacha a `claude_service` o `gemini_service`.
  - Cache de provider invalidable cuando settings cambian.
- **Claude headless** vía subprocess.run en thread pool (Windows ProactorEventLoop safe):
  - Resuelve `claude.cmd` o `claude` con `shutil.which`.
  - `env.pop("CLAUDECODE")` para evitar nested session.
  - Prompt via stdin, stream-JSON parsing.
- **Gemini** vía REST API `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.

**Casos de uso en la app**:
- AI Coach contextual (cada ruta).
- Análisis de propiedades (Tasador AI chat).
- Sugerencias de comparables en EstudioDetail.
- Tasador AI conversacional.

---

## Bottom Bar Mobile + FAB Central

**Navegación principal en mobile (`<lg`)**.

- 4 tabs fijos: Bandeja · Tasaciones · `[FAB]` · Mercado · AI.
- **FAB central elevado** (`-top-8`, 56×56px, color primario del theme, rotate 135° + scale al abrir, transición spring cubic-bezier).
- Tap abre bottom-sheet con grid 3-cols de 8 pantallas adicionales: Dashboard, Propiedades, Pipeline, Clientes, Estudios, Reportes, Comparables, Configuración.
- Header del sheet con avatar usuario + nombre + rol + botón logout circular.

---

## Stack técnico

### Frontend
- React 18 + Vite 5 + TypeScript strict.
- Tailwind CSS 3 (con CSS vars dinámicas por theme).
- React Router 6.
- Axios para HTTP (interceptor con JWT).
- Sonner para toasts.
- Lucide para iconos (regla `JAMÁS emojis`).
- Leaflet + leaflet.heat para mapas.

### Backend
- FastAPI 0.104 + SQLAlchemy 2.0 async + aiomysql.
- MySQL Aiven (`mysql-aiven-arenazl.e.aivencloud.com:23108`).
- Pydantic v2 para schemas.
- JWT 24h con bcrypt hash.
- Playwright para scraping on-demand.
- `asyncio.to_thread` para subprocess Claude (Windows safe).

### Deploy
- Frontend: Netlify (`tasar-app.netlify.app` + `tasar-landing.netlify.app`).
- Backend: Heroku (`tasar-api`, gunicorn + uvicorn worker, release hook con migración).
- DB: Aiven managed MySQL.
- Repo: `github.com/arenazl/tasar-app`.

---

## Componentes canónicos reutilizados (de APP_GUIDE)

- **ABMPage** (1800 líneas): wrapper con header unificado (search + filtros + botón +), vista cards/tabla/guided, skeleton loader flotante, sticky header, secondary filters con scroll horizontal forzado en mobile.
- **ABMCard**, **ABMCardActions**, **ABMCardSkeleton**.
- **ModernSelect**: combo con búsqueda + portal para escapar stacking context.
- **WizardModal**: multi-step form.
- **PageHint**: tutorial dismissable por pageId.
- **ConfirmModal**, **Modal**, **Sheet**.
- **DatePicker**, **DateRangePicker**, **MonthRangeNavigator**.
- **BrandLogo** (SVG inline grid 6×4 viewBox 60×60).
- **MapPicker**, **HeatmapMapWidget**, **AddressAutocomplete**.

---

## Gaps conocidos / Roadmap

### Pendiente
- Generación real de PDF de tasaciones (hoy `pdf_url` es string mockeado).
- Scraping batch programado con cron (hoy es on-demand).
- Equipo / invitación de usuarios al workspace.
- Dashboard widgets configurables (drag-and-drop).

### Considerado pero descartado por costo
- Proxies rotativos para scraping a escala (USD ~500/mes).
- Generación de PDFs con templates corporativos custom (requiere diseñador).

---

> Última actualización: estado deployado en producción al cierre del bloque "email Brevo + handlers Reportes/Comparables/Mercado + Clientes CRUD + MapaCalor drill-down + Config persistencia + AI Coach sidebar fija".
