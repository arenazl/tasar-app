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
