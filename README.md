# TasAR — Plataforma de Tasaciones y Estudios de Mercado

Stack canónico React + Python según `d:\Code\APP_GUIDE\APP_GUIDE_MASTER.md`.

## Features

1. **AI Tasador conversacional** — chat con Claude headless (subprocess + SSE streaming)
2. **Mapa de calor en vivo** — Leaflet + heatmap layer, USD/m² por barrio
3. **Tasaciones colaborativas multi-tasador** — consenso, opiniones, comentarios
4. **Scraping on-demand de portales** — Claude extrae datos de ZonaProp/Argenprop/MercadoLibre

## Componentes UI canónicos usados (sección 7 de la guía)

`ABMPage`, `ABMTable`, `ABMCard`, `ABMBadge`, `ABMCollapsible`, `ABMInfoPanel`, `WizardModal`, `WizardForm`, `ModernSelect` (autocomplete + searchable), `PageHint` (hints contextuales por pantalla), `Skeleton` (11 variantes), `AutocompleteInput`, `Sheet`, `ConfirmModal`.

## Puertos

- Backend FastAPI: **8600** (uvicorn)
- Frontend Vite: **5600**

## Arrancar (Windows / PowerShell)

### Primera vez

```powershell
# Backend
cd d:\Code\ACM\backend
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe scripts\_create_db.py   # crea DB en Aiven
.\venv\Scripts\python.exe scripts\seed_demo.py    # seed: 1 workspace + 3 users + 12 props

# Frontend
cd d:\Code\ACM\frontend
npm install
```

### Día a día

```powershell
# Terminal 1
cd d:\Code\ACM\backend
.\venv\Scripts\python.exe run.py

# Terminal 2
cd d:\Code\ACM\frontend
npm run dev
```

Abrir http://localhost:5600

## Cuentas demo

- `admin@tasar.demo` / `admin123` (rol admin)
- `tasador@tasar.demo` / `tasador123` (rol tasador, mat. MAT-5678)
- `cliente@tasar.demo` / `cliente123` (rol cliente)

## Smoke test

```powershell
cd d:\Code\ACM\backend
.\venv\Scripts\python.exe scripts\smoke.py
```

## Estructura

```
backend/
├── api/         (auth, properties, market_studies, appraisals, collaboration, ai, scraping, heatmap, dashboard)
├── core/        (config, database, security)
├── models/      (workspace, user, property, market_study, appraisal, collaboration, price_history)
├── schemas/     (pydantic request/response)
├── services/    (claude_service, acm_service, pdf_service, cloudinary_service)
└── scripts/     (create_database, seed_demo, smoke)

frontend/
├── src/
│   ├── components/
│   │   └── ui/   (ABMPage, ModernSelect, WizardModal, Skeleton, PageHint, ConfirmModal, etc — copiados verbatim de sugerenciasMun)
│   ├── contexts/ (AuthContext, ThemeContext con objeto Theme completo)
│   ├── pages/    (Login, Dashboard, Propiedades, Estudios, EstudioDetail, Tasaciones, MapaCalor, TasadorAI, Equipo, Configuracion)
│   ├── services/api.ts
│   ├── config/pageHints.ts
│   └── lib/      (validations, api shim para chatApi)
```

## Integración Claude headless

`services/claude_service.py` ejecuta el binario `claude` (Claude Code CLI) como subprocess con `--print --output-format stream-json`. Reusa el login local del usuario, no necesita `ANTHROPIC_API_KEY`.

- `chat_stream()` — generator async de tokens, alimenta SSE del endpoint `/api/ai/chat/stream`
- `chat_complete()` — versión sync para análisis batch
- `analyze_property()` — pasa la propiedad como JSON y parsea respuesta estructurada
- Scraping (`api/scraping.py`) — descarga HTML con Playwright (o httpx fallback) y le pide a Claude extraer JSON estructurado

## Deploy

- **Backend**: `heroku create tasar-back && git push heroku main` (Procfile listo)
- **Frontend**: `netlify deploy --prod` (netlify.toml listo, redirects SPA configurados)

## Notas

- DB: schema `tasar` en cluster Aiven compartido (host `mysql-aiven-arenazl.e.aivencloud.com:23108`)
- Modelos se autocrean en el `lifespan` de FastAPI (`Base.metadata.create_all`)
- Multi-tenant via `workspace_id` en todos los modelos (cada usuario opera sobre su workspace)
