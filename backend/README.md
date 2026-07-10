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
