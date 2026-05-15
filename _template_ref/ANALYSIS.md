# Análisis comparativo · Template TasAR CRM vs App actual

> Bundle del template: `_template_ref/project/` (4.135 líneas de JSX)
> App actual: `frontend/src/` (deployado en `tasar-app.netlify.app`)

---

## Identidad y stack visual

| | Template | App actual | Coincide? |
|---|---|---|---|
| **Logo** | Heatmap grid 6×4 | BrandLogo 6×4 SVG inline | ✅ Idéntico |
| **Tipografía** | Sora (display) + Inter | Sora + Inter (9 fuentes opcionales) | ✅ |
| **Acento** | Verde `#00B37E` con palette light/dark | 14 paletas dinámicas, default verde | ✅ Compatible |
| **Estilo** | Bloomberg / data-room / editorial | Mismo lenguaje (cards outline, mono fonts, dark sidebar) | ✅ |
| **Densidad** | Alta (CRM denso, mucha info por pixel) | Media (más respiración) | ⚠️ Ajustar |

**Conclusión**: el template no inventa una identidad nueva. Refuerza la que ya tenemos pero con **densidad mayor** — más datos visibles por pantalla, menos padding.

---

## Sidebar / Navegación

### Template
```
TasAR (logo + brand)
├── [Org selector: "Río Plata · Tasaciones · Plan Empresa · 12 usuarios"]
├── TRABAJO
│   ├── Bandeja           [12]
│   ├── Tasaciones        [142]
│   ├── Propiedades       [2.4k]
│   ├── Pipeline
│   ├── Clientes          [318]
│   ├── Mercado
│   ├── Estudios          [#047]
│   └── Reportes
├── DATOS
│   ├── Comparables       [live]
│   └── Configuración
└── [User profile: "Bárbara López · MN 4821"]
```

### Actual
Sidebar 240px con secciones "Trabajo" y "Datos", **idéntica estructura** salvo:
- ❌ Falta **org-pill / workspace selector** (con plan + cantidad de usuarios)
- ❌ Falta **badges con counts dinámicos** en cada item (`142`, `2.4k`, `318`, etc.)
- ✅ User profile abajo igual

**Recomendación**: agregar org-pill arriba + counts en sidebar (datos reales del backend).

---

## TopBar

### Template
- **Breadcrumbs dinámicos** por vista (ej. `Tasaciones / TR-2451 / Av. Santa Fe 2350`)
- Search global con shortcut `⌘K`
- Bell con dot + Gear + Botón "+ Nueva tasación" (oculto en Mercado/Estudios/Comparables/Config)

### Actual
- Logo mobile + ThemeSelector
- ❌ Sin breadcrumbs
- ❌ Sin search global
- ❌ Sin shortcut keyboard

**Recomendación**: agregar **breadcrumbs + search global ⌘K** — son patterns CRM esperados.

---

## Bandeja

### Template
- Layout 2 paneles: lista + detalle
- Items por kind: `client_message`, `system_alert`, `model_alert`, `comment_mention`, `appraisal_assigned`, `billing_overdue`
- Dot sin-leer + sender + preview + timestamp
- Detail con asunto, body, **referencia a tasación** (link de vuelta a TR-XXXX)

### Actual
Idéntica estructura — modelo `InboxMessage` ya soporta esos kinds.
- ⚠️ UI de cards algo más cargada, falta el patrón "sender · subject preview · timestamp" tan limpio del template

**Recomendación**: refinar visual con tipografía del template (sender en bold, preview en gris, timestamp mono).

---

## Tasaciones (vista core, la más densa del template)

### Template — layout 3 paneles (sidebar + lista + detalle + rail derecho opcional)

**Lista (centro-izquierda):**
- Tabs `Todas / Asignadas a mí / Urgentes / En revisión` con count
- Filter chips horizontales (Estado, Zona, Cliente, + Más)
- Items con: dirección (h1), ID (mono), zone · sup · amb, valor USD, status pill con dot de color

**Detalle (centro-derecha):**
1. **Header**: ID + status pill + live badge + h1 dirección + sub (zone, CABA, sup, amb, estado). 3 botones: `Compartir`, `Exportar PDF`, **`Enviar a cliente →`** (acento).
2. **Stat row 4 KPIs**: Estimación TasAR (USD 248.300 + rango ±6,5%), USD/m² (3.028 +4,8% vs zona), Confianza del modelo (87%), Cap rate (4,8% anual).
3. **Card "Zona Recoleta · 800m"** con **ZoneHeatmap** (grid 20×9 con pin de la propiedad + label "Esta propiedad").
4. **Card "Histórico valor USD/m² · 17 meses"** con Sparkline animada + gradient fill.
5. **Tabla de 5 comparables** con: dirección, sup, amb, precio, USD/m², distancia, "Hace X días", **barra visual de match %** (96, 92, 89, 84, 81).

**Rail derecho (opcional 280px):**
- Card "Cliente": nombre, contacto, mail, teléfono
- Card "Datos del inmueble": 9 campos (sup cubierta/desc, antigüedad, orientación, expensas, cochera, baulera, estado, etc.)
- Card "Timeline" con 4 eventos (comparables actualizados, revisión, modelo recalculó, solicitud creada)

### Actual
- ✅ ABMPage canónico con search + filtros + pills de status
- ✅ Cards con TR-XXXX, valor, status
- ⚠️ Sin vista detalle 3-paneles — abre wizard modal en vez de detail-view inline
- ❌ Sin ZoneHeatmap por propiedad
- ❌ Sin sparkline de histórico USD/m²
- ❌ Sin tabla de comparables con barra de match visual
- ❌ Sin rail derecho con cliente + datos inmueble + timeline

**Esto es el cambio más grande que propone el template.** Hoy nuestro UX es CRUD (lista → modal) y el template propone **inspector / detail view persistente** (lista a la izquierda, detalle dinámico a la derecha al hacer click). Patrón Linear / Notion / Gmail.

**Recomendación**: replicar el detail-view inline. Es lo que diferencia un CRM real de un ABM CRUD.

---

## Propiedades

### Template
- Vista tabla full-width 12 columnas (no cards)
- Toggle `Tabla / Mapa / Cards` arriba a la derecha
- Filter chips + Search

### Actual
- ABMPage cards (1/2/3 cols)
- Wizard create
- ❌ Sin toggle Tabla/Mapa/Cards
- ❌ Sin vista tabla densa para listas largas

**Recomendación**: agregar toggle de vista (la tabla densa es clave cuando tenés 2.000+ propiedades).

---

## Pipeline (kanban)

### Template
- 5 columnas: `Solicitado → En análisis → Comparables → En revisión → Entregado`
- Cards draggable
- Count por columna

### Actual
- ✅ Idéntico — 5 columnas, scroll horizontal en mobile, drag desktop
- ⚠️ Columnas distintas: `Solicitada → En análisis → Borrador → Firmada → Entregada`

**Conclusión**: alinear nombres de stages al template (más estándar de la industria).

---

## Clientes

### Template
- Lista de orgs/particulares con MRR estimado, # tasaciones, contacto
- Detalle: 4 KPIs (tasaciones, valor total, ticket promedio, última actividad), tabla de contactos, timeline

### Actual
- ✅ ABMPage cards con tipo color-coded, contacto, email, conteo
- ❌ Sin detalle por cliente (4 KPIs + contactos + timeline)
- ❌ Sin MRR / ticket promedio

**Recomendación**: agregar vista detalle (click en card → drill-down con stats).

---

## Mercado

### Template
- Header con period seg `7d / 30d / 90d / 12m / 5a` + botón Exportar
- **Grid 12 cols**:
  - 4 KPIs (Índice / Oferta / Tiempo / Permisos) — cada uno span 3
  - **Heatmap grande de CABA** (BigCityHeatmap, ~30×16 cells) — span 8
  - Ranking por zona top 12 — span 4
  - Sparkline evolución 17 meses — span 8
  - Top movers (5 zonas con flecha) — span 4

### Actual
- ✅ KPIs + período (escalando YoY/MoM/permits)
- ✅ Heatmap grid (recién arreglado el grid-cols-16)
- ✅ Ranking por zona top 12
- ❌ Sin sparkline 17 meses
- ❌ Sin sección "Top movers" (5 zonas con mayor variación)
- ❌ Sin botón Exportar al CSV del mercado completo

**Recomendación**: agregar sparkline + top movers — son señales de mercado importantes.

---

## ⭐ Estudios (la pantalla MÁS distinta — la innovación del template)

**Esto no existe en TasAR actual.** Es un **deliverable editorial scrolleable**, formato revista Bloomberg.

### Template

**Layout**: documento largo centrado en 880px, toolbar sticky arriba.

**Toolbar**:
- ← Volver a Reportes · `Pág. 7/38` + progress bar visual
- Compartir · Descargar PDF · `Suscribirse` (acento)

**Documento** (long-scroll):
1. **Cover** — `#047 · Mayo 2026 · CABA + GBA`, headline hero "El interanual cierra en +14,2% y el m² supera USD 2.800 por primera vez desde 2019", stand (subtítulo), byline con avatar + autor + "38 páginas · lectura 18 min"

2. **TL;DR** — 3 cards numerados con key findings: "01 El índice toca USD 2.847/m²", "02 Stock activo cae -3,4%", "03 Permisos +12% interanual"

3. **§01 Índice** — section number en eyebrow + h2 + párrafos + Sparkline (Fig. 1) con caption

4. **Pull quote** grande con borde verde — "El m² porteño sumó USD 437 en 17 meses..."

5. **§02 Zonas** — barchart de 11 barrios horizontal (Palermo 3420, Recoleta 3180, etc.)

6. **§03 Oferta** — texto sobre caída del stock

7. **§04 Obra nueva** — barchart 13 meses con último mes en color acento

8. **§05 Rentabilidad** — tabla de cap rates (Palermo dpto 4,2% / PH 4,9% / casa 4,7%) + tira de heatmap relativo

9. **§06 Lo que viene** — proyecciones

10. **Footer** — Metodología + Sobre TasAR

### Actual
**No existe**. Hoy Reportes muestra solo las cards/covers, no el contenido.

**Esta es la diferenciación más fuerte que aporta el template.** Es el "producto" que un fondo de inversión o desarrollador paga por leer.

**Recomendación**: implementar `/estudios/:id` con este formato editorial. Largo, pero alto impacto comercial.

---

## Reportes

### Template
- Grid de 3 cols con cards estilo **cover negro** (`background: var(--ink)`)
- Card destacada (featured) span 2
- Cada card: edition `#047`, mes, fecha + pp, KPIs (YoY + USD/m²)

### Actual
- ✅ Idéntico patrón (cover negro, mini heatmap, KPIs)
- ✅ Filtros modal + custom report modal + share + export CSV (ya wireado)
- ⚠️ Falta destacado featured span 2 para la última edición

**Conclusión**: muy alineado. Solo ajustar featured grid.

---

## Comparables

### Template
- Split: mapa grande izq + rail comparables der
- Pin destacado de la propiedad sujeto
- 8 comparables alrededor con % match visual

### Actual
- ✅ Filtros pill (zona, radio, tipo, ambientes, condición, días)
- ✅ Stats (min/max/median)
- ✅ Export CSV
- ⚠️ Layout más cards-grid, no map-split
- ❌ Sin pin del sujeto + comparables alrededor (vista mapa)

**Recomendación**: replicar split mapa + rail con barras de match.

---

## Configuración

### Template — **6 tabs**:
1. Cuenta
2. Equipo
3. Facturación
4. API
5. Notificaciones
6. Metodología

### Actual — single page con secciones:
- ✅ Tema visual (light/dark + 14 paletas)
- ✅ Tipografías (9)
- ✅ IA provider (Claude/Gemini) + modelo
- ✅ Notificaciones (3 toggles + test email Brevo)
- ✅ Cambiar contraseña
- ❌ Sin tab **Equipo** (invitar usuarios, roles)
- ❌ Sin tab **Facturación** (plan, MRR, tarjeta)
- ❌ Sin tab **API** (keys, webhooks, docs)
- ❌ Sin tab **Metodología** (parámetros del modelo de tasación)

**Recomendación**: convertir a tabs y agregar las 4 faltantes (Equipo es prioridad para multi-tenant real).

---

## Resumen ejecutivo

### 🎯 Gaps de alto impacto (recomiendo replicar)

| # | Item | Impacto | Esfuerzo |
|---|---|---|---|
| 1 | **Vista detalle de Tasación (3-paneles)** con ZoneHeatmap + sparkline + tabla comparables con match% + rail | 🔴 Alto | 1 día |
| 2 | **Estudios (`/estudios/:id`)** formato editorial scrolleable | 🔴 Alto | 1 día |
| 3 | **TopBar con breadcrumbs + search global ⌘K** | 🟡 Medio | 4 hs |
| 4 | **Org-pill + counts en sidebar** (datos reales) | 🟡 Medio | 2 hs |
| 5 | **Vista tabla para Propiedades** (toggle Tabla/Cards/Mapa) | 🟡 Medio | 4 hs |
| 6 | **Configuración por tabs** + tab Equipo (invitar usuarios) | 🟡 Medio | 6 hs |
| 7 | Mercado: sparkline 17m + top movers | 🟢 Bajo | 2 hs |
| 8 | Reportes: featured card span 2 | 🟢 Bajo | 30 min |

### ✅ Ya alineado (no tocar)
- Sidebar estructura
- Bandeja 2-paneles
- Pipeline kanban
- Clientes ABM con tipos colored
- Reportes grid 3-cols con cover negro
- Configuración persistencia + email Brevo
- Mapa de calor (ya arreglado)

### 💎 La pantalla más diferenciadora
**Estudios** — el deliverable editorial estilo Bloomberg/revista financiera. Hoy no existe en TasAR. Es lo que justifica el precio de suscripción para fondos/desarrolladores.

---

## Mi recomendación de orden

1. **Vista detalle Tasación 3-paneles** (#1) — es el "core experience" del tasador, hoy se siente como CRUD genérico
2. **Estudios** (#2) — diferenciación comercial fuerte
3. **TopBar breadcrumbs + ⌘K + Sidebar org-pill + counts** (#3, #4) — sensación "CRM serio"
4. **Configuración por tabs con Equipo** (#6) — habilitador de multi-tenant real
5. Resto en orden de esfuerzo

**Total estimado**: 3-4 días para tener TasAR a la altura del template.
