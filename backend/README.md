# Backend — Suite Inmobiliaria (TasAR)

FastAPI + SQLAlchemy async (aiomysql) + Aiven MySQL. Multi-tenant por `workspace_id`.

## Correr en local

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Copiar las credenciales a backend/.env (DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME, SECRET_KEY, etc.)
uvicorn main:app --reload --port 8600
```

## Migraciones (Alembic)

El schema lo gobierna **Alembic**. Contrato del ecosistema (`base-compartida/10-AMBIENTES-Y-MIGRACIONES.md`):
la app **autora** las migraciones; **Infra** las ejecuta en prod (con backup previo).
`Base.metadata.create_all` del lifespan queda SOLO para dev/test, detrás del flag
`AUTO_CREATE_SCHEMA` (default off). En prod, `AUTO_CREATE_SCHEMA` NO se setea → el schema es Alembic.

Alembic toma la URL de conexión desde `settings.database_url` (env vars `DB_*`), NO de `alembic.ini`.
Todos los modelos se registran en `Base.metadata` vía `import models` en `alembic/env.py`.

### Comandos (correr desde `backend/`)

```bash
# Crear una migración nueva a partir de cambios en los modelos:
alembic revision --autogenerate -m "descripcion del cambio"

# Aplicar migraciones pendientes:
alembic upgrade head

# Revertir la última:
alembic downgrade -1

# Ver la revisión actual de la DB:
alembic current
```

### Baseline en una DB que YA tiene el schema (prod)

La migración baseline (`alembic/versions/1e616292cc4e_baseline_schema.py`) crea las 19 tablas
actuales. En una DB donde el schema **ya existe** (creado antes por `create_all`), NO se corre
`upgrade` — se marca la versión sin recrear:

```bash
alembic stamp head
```

A partir de ahí, cada cambio de schema entra como una revisión nueva y se aplica con `upgrade head`.

### Nota de autoría del baseline

El baseline se generó diffeando `Base.metadata` (motor SQLite en memoria, solo como "pizarra en
blanco") porque no había un MySQL disponible al autorarlo y está prohibido correr Alembic contra la
Aiven compartida. Los tipos son genéricos de SQLAlchemy (válidos para MySQL). El primer
`alembic upgrade head` real contra una DB MySQL vacía debe correrse en dev/Infra para confirmar el DDL.

## Smoke de invariantes del núcleo (correr antes de pushear cambios de F1/F2)

`scripts/smoke_core.py` (WO F1-04) es la vara ejecutable del motor ACM, el anclaje de
mercado y el aislamiento multi-tenant. **Corrélo antes de cada push que toque
`services/acm_service.py`, `services/anchor_service.py` o cualquier endpoint con
`workspace_id`:**

```bash
cd backend
python scripts/smoke_core.py
```

Corre en <1s local. Dos invariantes son matemática pura (sin DB, corren siempre):
motor ACM determinista (valor sugerido + confianza + pesos exactos sobre un fixture
de 4 comparables) y anchor determinista (mediana/p25/p75/min/max exactos sobre un
subset congelado de 10 listings). Si tocaste un coeficiente y rompiste algo, esto
lo detecta con exit code != 0.

Las otras dos invariantes (aislamiento multi-tenant entre 2 workspaces de fixture, y
que los endpoints críticos — login, properties, appraisal PDF, valuations/express,
market/comparables — respondan 200) necesitan una DB MySQL local + `uvicorn main:app
--reload --port 8600` corriendo. **Está prohibido correrlas contra la Aiven
compartida** — si `DB_HOST` no es `localhost`/`127.0.0.1`, el script las SKIPPEA
automáticamente sin abrir conexión (no explota, no toca la DB compartida). Para
forzarlas con una DB local o de test propia:

```bash
TASAR_SMOKE_ALLOW_REMOTE_DB=1 python scripts/smoke_core.py   # solo con DB local/propia
```

El bloque de endpoints críticos asume el usuario demo `admin@tasar.demo` /
`admin123` (`scripts/seed_demo.py`).

## Scraping on-demand con JS (Playwright + chromium) — WO F3-04

`api/scraping.py::_fetch_html` intenta Playwright primero y si falla
(excepción de cualquier tipo, incluido "no está el binario") cae a `httpx`
sin JS. Antes de este WO, la imagen Docker **no** instalaba el browser de
Playwright, así que en Cloud Run el fallback a `httpx` era el camino real
para TODAS las URLs (insuficiente para ZonaProp/MercadoLibre, que renderizan
con JS). El `Dockerfile` ahora corre `playwright install --with-deps chromium`
después del `pip install`, para que el `chromium.launch()` real funcione en
Cloud Run.

**Honestidad del fallback (WO F4-02):** cuando SÍ degrada a `httpx`, la
respuesta de `POST /api/scraping/extract` trae `degraded: true` y el
frontend lo tiene que mostrar (antes degradaba en silencio y el usuario
creía que había extraído con JS aunque el HTML sin renderizar rindiera
mucho menos contenido).

**Decisión de peso de imagen:** se instala **solo Chromium** (no Firefox ni
WebKit) sobre `python:3.11-slim`. Estimación (no medida con un build real en
este WO — no se pudo buildear la imagen acá, ver limitación abajo):

| Capa                                              | Estimado    |
|----------------------------------------------------|------------|
| `python:3.11-slim` + `build-essential`/openssl/ffi | ~250-300 MB |
| Deps de `requirements.txt` (fastapi, sqlalchemy, cryptography, reportlab, cloudinary, el driver Node embebido de `playwright`, etc.) | ~150-250 MB |
| Binario de Chromium (`playwright install chromium`) | ~300-320 MB |
| Libs de SO de `--with-deps` (libnss3, libatk, libcups2, libgbm1, fonts-liberation, etc.) | ~250-350 MB |
| **Total estimado**                                  | **~1.0-1.2 GB** |

Queda por debajo del umbral de 2 GB que el WO marcó como límite razonable
para Cloud Run — por eso se optó por instalar el browser directo en vez de
dejar el scraping JS detrás de un flag con mensaje degradado. **Verificar
con un build real** (`docker build` + `docker images`) antes de dar esto por
cerrado; si el tamaño real sorprende para arriba, la alternativa (flag +
`"fuente no soportada en este plan"` en la UI) queda documentada acá como
plan B.

**Nota operativa para Infra:** con Chromium instalado, cada worker de
gunicorn que atienda una request de scraping levanta un proceso browser
(pico de RSS estimado ~300-500 MB por instancia). El `Dockerfile` corre
`-w 2` workers — dimensionar la memoria del servicio de Cloud Run
consecuentemente (no se cambió acá porque es un parámetro de infra, no de
este WO).

## Refresh del dataset Coldwell Banker Argentina — WO F3-04

El dataset importado en F0-06 es un snapshot fijo. `scripts/refresh_cb_dataset.py`
scrapea de nuevo el catálogo público de CB (mismo sitio, mismos campos que el
snapshot original) y reimporta de forma **incremental**, reusando el ETL de
F0-06 (`scripts/import_cb_dataset.py`) tal cual: mismo mapeo, misma sanidad,
mismo dedup por dirección+m²+precio. Cada corrida usa un `source` con la
fecha (`cb-argentina-YYYY-MM-DD`) para dejar provenance de cuándo entró cada
fila.

Es un **port a Python** de los scrapers `.mjs` del repo donante
(`beykercoldwell/scripts/scrape-cb-argentina.mjs` +
`scripts/scrape-details.mjs`), no una invocación de Node: el sitio de CB es
HTML server-rendered (ambos originales usan `fetch()` + regex, sin
Playwright), así que portear evita meter un runtime Node en la imagen del
backend solo para esto.

El refresh es **manual** por ahora — lo corre el dueño/Infra:

```bash
cd backend

# 1) Scrapear listado + fichas de detalle a JSON local (resumable, no toca DB):
python scripts/refresh_cb_dataset.py --stage all

# 2) Ver el reporte del ETL (dry-run, no toca DB) sobre lo recién scrapeado:
python scripts/refresh_cb_dataset.py --stage none

# 3) Importar de verdad (backup de market_listings + insert incremental,
#    pide confirmación explícita "CONFIRMO"):
python scripts/refresh_cb_dataset.py --stage none --apply
```

El dedup incremental (que correr el refresh 2 veces no duplique filas) tiene
un self-test 100% offline (sin red, sin DB):

```bash
python scripts/refresh_cb_dataset.py --dedup-selftest
```

**Cron futuro (no implementado en este WO):** el refresh queda anotado como
candidato a Cloud Scheduler → endpoint protegido (mismo patrón que
`/api/cron/weekly-summary` de F3-03, con `X-Cron-Key`) una vez que el dueño
decida la cadencia. Por ahora no hay automatización — correrlo a mano.
