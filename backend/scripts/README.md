# backend/scripts — inventario

Scripts operativos vivos (usables hoy):

| Script | Para qué sirve |
|---|---|
| `__init__.py` | Marca `scripts/` como paquete Python (vacío). |
| `seed_demo.py` | Seedea workspace + 3 usuarios + 12 propiedades demo en Argentina (coords reales de barrios, marcadas `[DEMO]`) + price_history. |
| `seed_v2.py` | Seedea data demo de `market_listings`, `monthly_reports` e `inbox` (datos `[DEMO]`, coords reales, montos de ejemplo). |
| `add_demo_users.py` | Asegura (idempotente) que existan los usuarios admin/supervisor/vendedor del workspace `tasar-demo`. |
| `smoke.py` | Smoke test síncrono de los endpoints críticos contra `http://127.0.0.1:8600/api` (local). |
| `smoke_ai.py` | Smoke test del flujo IA-first de estudios (local). |
| `smoke_ia_full.py` | Smoke test integral de todos los endpoints que usan IA/Claude (local). |
| `smoke_all_prod.py` | Smoke test del 100% de los endpoints contra producción (Cloud Run: `tasar-api-ka3yn5r7dq-rj.a.run.app`). |

## `_attic/`

Scripts legacy **pre-Alembic** (creaban/migraban el schema a mano antes de que el proyecto
adoptara Alembic para migraciones versionadas — ver WO F0-03). **No usar.** Se conservan
solo como referencia histórica: `_create_db.py`, `create_database.py`, `_migrate_ai_columns.py`,
`_migrate_v2.py`, `_test_analyze_raw.py`.
