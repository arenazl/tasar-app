"""Fixtures pytest del backend (WO F3-06).

Sigue el mismo patron liviano que los runners standalone de `scripts/`
(`test_bot_f2_03.py`, `test_meta_f3_02.py`, `test_notify_f3_03.py`,
`test_perf_f3_05.py`): SQLite en memoria via aiosqlite, `httpx.ASGITransport`
contra `main.app`, `dependency_overrides` de `get_db`. La diferencia es que
esto corre bajo pytest (con fixtures/aislamiento por test) en vez de un
script suelto con su propio `main()`.

Politica de DB: estos tests NUNCA tocan MySQL/Aiven -- todo corre contra
SQLite en memoria, un engine nuevo por test (aislamiento total, nada de
estado compartido entre tests).
"""
from __future__ import annotations

import os

# Satisfacer core.config ANTES de importar cualquier modulo de la app (no
# conecta a MySQL real -- mismo patron que scripts/test_*_f*.py).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-solo-para-pytest")

import time
from typing import AsyncIterator, Callable

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def unique_stamp() -> str:
    """Sufijo unico para emails/slugs de fixture (evita colisiones entre tests)."""
    return str(int(time.time() * 1_000_000))


@pytest.fixture
async def db_session_factory() -> AsyncIterator[Callable[[], AsyncSession]]:
    """Engine SQLite en memoria fresco por test, con el schema completo
    creado desde `Base.metadata` (todos los modelos, igual que Alembic en
    prod pero sin migraciones)."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    from core.database import Base
    import models  # noqa: F401 -- registra todos los modelos en Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        yield session_local
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_session_factory) -> AsyncIterator[AsyncSession]:
    """Sesion suelta para armar fixtures de datos directo contra el ORM."""
    async with db_session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session_factory) -> AsyncIterator[httpx.AsyncClient]:
    """httpx.AsyncClient in-process contra `main.app`, con `get_db`
    overrideado a la misma SQLite en memoria de este test (dependency
    override real de FastAPI, no un servidor levantado aparte)."""
    import main
    from core.database import get_db

    async def _override_db():
        async with db_session_factory() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db
    transport = httpx.ASGITransport(app=main.app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        main.app.dependency_overrides.pop(get_db, None)


async def register_workspace(
    client: httpx.AsyncClient,
    *,
    email: str | None = None,
    password: str = "test12345",
    full_name: str = "[TEST] Usuario",
    workspace_name: str | None = None,
) -> dict:
    """Registra un workspace + usuario admin via /api/auth/register (ejercita
    el flujo real de auth) y devuelve el body de TokenResponse ya parseado,
    con `headers` listo para usar (`Authorization: Bearer ...`)."""
    stamp = unique_stamp()
    body = {
        "email": email or f"user-{stamp}@example.com",
        "password": password,
        "full_name": full_name,
        "workspace_name": workspace_name or f"[TEST] WS {stamp}",
    }
    r = await client.post("/api/auth/register", json=body)
    assert r.status_code == 200, f"register fallo: {r.status_code} {r.text}"
    data = r.json()
    data["headers"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data
