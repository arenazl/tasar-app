"""Test standalone de performance + cascade (WO F3-05) -- market_studies
serializers (N+1 en detalle de estudio), market/dashboard (N+1 de counts por
zona), cascade delete de MarketStudy -> Comparable -> Adjustment. Sin pytest,
sin MySQL (SQLite en memoria), sigue el mismo patron liviano de
scripts/test_notify_f3_03.py (Report PASS/FAIL, httpx.ASGITransport contra
main.app, SQLite fixture, event listener de SQLAlchemy para contar queries).

Cubre:
  [1] GET /api/market-studies/{id} con 6 comparables x 2 adjustments cada uno
      -> <=4 queries SQL totales contra la DB, INCLUYENDO la query de auth
      de get_current_user (antes de F3-05: auth(1) + comparables(1) +
      adjustments(1 por comparable) = 1+1+6 = 8, mas la query de estudio =
      9; con 6 comparables reales el viejo codigo hacia 1(estudio)+1(comps)
      +6(adjustments, uno por comparable)+1(auth) = 9).
  [2] GET /api/market/dashboard con un monthly_report de 12 zonas -> <=5
      queries SQL totales (antes: auth(1) + latest_report(1) +
      active_listings(1) + 12 counts = 15).
  [3] DELETE /api/market-studies/{id} con 6 comparables (12 adjustments)
      -> 200 OK (antes: IntegrityError, sin cascade) y NINGUN comparable ni
      adjustment sobrevive en la DB.

Uso:
    python backend/scripts/test_perf_f3_05.py

Exit code: 0 si no hubo ningun FAIL.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Satisfacer core.config antes de importar nada de la app (no conecta a MySQL).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx  # noqa: E402
from sqlalchemy import event, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402

PASS, FAIL = "PASS", "FAIL"


@dataclass
class Result:
    name: str
    status: str
    detail: str = ""


@dataclass
class Report:
    results: List[Result] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.results.append(Result(name, status, detail))
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))

    @property
    def exit_code(self) -> int:
        return 1 if any(r.status == FAIL for r in self.results) else 0

    def summary(self) -> str:
        counts = {PASS: 0, FAIL: 0}
        for r in self.results:
            counts[r.status] += 1
        return f"PASS={counts[PASS]}  FAIL={counts[FAIL]}"


async def _make_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    from core.database import Base
    import models  # noqa: F401 -- registra metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class _QueryCounter:
    """Cuenta statements SQL (antes de que lleguen al cursor DBAPI) mientras
    esta activo. Incluye TODO lo que corre en la request (auth + endpoint),
    a proposito -- es lo que el WO pide medir ("echo SQL en dev")."""

    def __init__(self, engine):
        self._sync_engine = engine.sync_engine
        self.count = 0
        self.statements: List[str] = []

    def _on_execute(self, conn, cursor, statement, parameters, context, executemany):
        self.count += 1
        self.statements.append(statement.strip().split("\n")[0][:80])

    def __enter__(self):
        event.listen(self._sync_engine, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *exc):
        event.remove(self._sync_engine, "before_cursor_execute", self._on_execute)


# ---------------------------------------------------------------------------
# [1] GET /api/market-studies/{id} -- <=4 queries con 6 comparables x2 adj.
# ---------------------------------------------------------------------------
async def _run_study_detail_checks(report: Report) -> None:
    import main
    from core.database import get_db
    from core.security import hash_password, create_access_token
    from models.workspace import Workspace
    from models.user import User
    from models.property import Property
    from models.market_study import MarketStudy, Comparable, Adjustment

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())

    async with SessionLocal() as session:
        ws = Workspace(name=f"[TEST] WS {stamp}", slug=f"test-perf-{stamp}", plan="free")
        session.add(ws)
        await session.flush()
        user = User(
            workspace_id=ws.id, email=f"tasador-{stamp}@tasar.local",
            password_hash=hash_password("test12345"), full_name="Tasador Test", role="vendedor",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        prop = Property(
            workspace_id=ws.id, created_by=user.id, title="Depto test",
            property_type="departamento", province="CABA", city="CABA", address="Test 123",
            total_area_m2=60, covered_area_m2=55, rooms=3, age_years=10,
        )
        session.add(prop)
        await session.flush()

        ms = MarketStudy(workspace_id=ws.id, property_id=prop.id, created_by=user.id, status="draft")
        session.add(ms)
        await session.flush()

        for i in range(6):
            c = Comparable(
                market_study_id=ms.id, title=f"Comparable {i}", price=100000 + i * 1000,
                total_area_m2=58, rooms=3, weight=1.0,
            )
            session.add(c)
            await session.flush()
            session.add(Adjustment(comparable_id=c.id, factor="area", coefficient=1.02))
            session.add(Adjustment(comparable_id=c.id, factor="age", coefficient=0.98))

        await session.commit()
        token = create_access_token({"sub": str(user.id)})
        study_id = ms.id

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=main.app)
    with _QueryCounter(engine) as qc:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(f"/api/market-studies/{study_id}", headers=headers)

    ok_status = r.status_code == 200
    body = r.json() if ok_status else {}
    ok_shape = ok_status and len(body.get("comparables", [])) == 6 and all(
        len(c.get("adjustments", [])) == 2 for c in body.get("comparables", [])
    )
    report.add(
        "[1a] GET detalle de estudio devuelve 6 comparables x2 adjustments c/u",
        PASS if ok_shape else FAIL,
        f"status={r.status_code} comparables={len(body.get('comparables', []))}",
    )
    report.add(
        "[1b] GET detalle de estudio <=4 queries SQL (selectinload, sin N+1)",
        PASS if qc.count <= 4 else FAIL,
        f"queries={qc.count} statements={qc.statements}",
    )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


# ---------------------------------------------------------------------------
# [2] GET /api/market/dashboard -- <=5 queries con reporte de 12 zonas.
# ---------------------------------------------------------------------------
async def _run_dashboard_checks(report: Report) -> None:
    import main
    from core.database import get_db
    from core.security import hash_password, create_access_token
    from models.workspace import Workspace
    from models.user import User
    from models.monthly_report import MonthlyReport
    from models.market_listing import MarketListing

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())
    zones = [f"Zona{i}-{stamp}" for i in range(12)]

    async with SessionLocal() as session:
        ws = Workspace(name=f"[TEST] WS dash {stamp}", slug=f"test-dash-{stamp}", plan="free")
        session.add(ws)
        await session.flush()
        user = User(
            workspace_id=ws.id, email=f"dash-{stamp}@tasar.local",
            password_hash=hash_password("test12345"), full_name="Dash Test", role="vendedor",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        top_zones = [{"zone": z, "usd_m2": 2000 + i, "change_pct": 1.0} for i, z in enumerate(zones)]
        session.add(MonthlyReport(
            code=f"TEST-{stamp}", period_year=2026, period_month=7, region="CABA",
            tasar_index=2500, median_price_per_m2=2500, yoy_change_pct=10, mom_change_pct=1,
            avg_days_on_market=60, new_permits=5, top_zones=json.dumps(top_zones),
        ))
        for i, z in enumerate(zones):
            session.add(MarketListing(
                source="seed", title=f"Listing {i}", property_type="departamento",
                neighborhood=z, city="CABA", price=100000, price_per_m2=2000, status="active",
            ))

        await session.commit()
        token = create_access_token({"sub": str(user.id)})

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=main.app)
    with _QueryCounter(engine) as qc:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/market/dashboard", headers=headers)

    ok_status = r.status_code == 200
    body = r.json() if ok_status else {}
    ok_shape = ok_status and len(body.get("top_zones", [])) == 12 and all(
        z.get("listings_count") == 1 for z in body.get("top_zones", [])
    )
    report.add(
        "[2a] GET dashboard devuelve 12 zonas con listings_count correcto (1 c/u)",
        PASS if ok_shape else FAIL,
        f"status={r.status_code} top_zones_len={len(body.get('top_zones', []))}",
    )
    report.add(
        "[2b] GET dashboard <=5 queries SQL (GROUP BY, sin 1 count() por zona)",
        PASS if qc.count <= 5 else FAIL,
        f"queries={qc.count} statements={qc.statements}",
    )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


# ---------------------------------------------------------------------------
# [3] DELETE /api/market-studies/{id} con 6 comparables -- cascade OK.
# ---------------------------------------------------------------------------
async def _run_delete_cascade_checks(report: Report) -> None:
    import main
    from core.database import get_db
    from core.security import hash_password, create_access_token
    from models.workspace import Workspace
    from models.user import User
    from models.property import Property
    from models.market_study import MarketStudy, Comparable, Adjustment

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())

    async with SessionLocal() as session:
        ws = Workspace(name=f"[TEST] WS del {stamp}", slug=f"test-del-{stamp}", plan="free")
        session.add(ws)
        await session.flush()
        user = User(
            workspace_id=ws.id, email=f"del-{stamp}@tasar.local",
            password_hash=hash_password("test12345"), full_name="Del Test", role="vendedor",
            is_active=True,
        )
        session.add(user)
        await session.flush()
        prop = Property(
            workspace_id=ws.id, created_by=user.id, title="Depto test del",
            property_type="departamento", province="CABA", city="CABA", address="Test 456",
            total_area_m2=60, covered_area_m2=55, rooms=3, age_years=10,
        )
        session.add(prop)
        await session.flush()

        ms = MarketStudy(workspace_id=ws.id, property_id=prop.id, created_by=user.id, status="draft")
        session.add(ms)
        await session.flush()

        comp_ids: List[int] = []
        adj_ids: List[int] = []
        for i in range(6):
            c = Comparable(
                market_study_id=ms.id, title=f"Comparable del {i}", price=100000 + i * 1000,
                total_area_m2=58, rooms=3, weight=1.0,
            )
            session.add(c)
            await session.flush()
            comp_ids.append(c.id)
            a1 = Adjustment(comparable_id=c.id, factor="area", coefficient=1.02)
            a2 = Adjustment(comparable_id=c.id, factor="age", coefficient=0.98)
            session.add_all([a1, a2])
            await session.flush()
            adj_ids.extend([a1.id, a2.id])

        await session.commit()
        token = create_access_token({"sub": str(user.id)})
        study_id = ms.id

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.delete(f"/api/market-studies/{study_id}", headers=headers)

    report.add(
        "[3a] DELETE estudio con 6 comparables x2 adjustments -> 200 OK (sin IntegrityError)",
        PASS if r.status_code == 200 else FAIL,
        f"status={r.status_code} body={r.text[:300]}",
    )

    async with SessionLocal() as session:
        remaining_studies = (await session.execute(
            select(MarketStudy).where(MarketStudy.id == study_id)
        )).scalars().all()
        remaining_comps = (await session.execute(
            select(Comparable).where(Comparable.id.in_(comp_ids))
        )).scalars().all()
        remaining_adjs = (await session.execute(
            select(Adjustment).where(Adjustment.id.in_(adj_ids))
        )).scalars().all()

    ok_cascade = not remaining_studies and not remaining_comps and not remaining_adjs
    report.add(
        "[3b] cascade borra el estudio + los 6 comparables + los 12 adjustments",
        PASS if ok_cascade else FAIL,
        f"studies={len(remaining_studies)} comps={len(remaining_comps)} adjs={len(remaining_adjs)}",
    )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def main() -> int:
    print("=" * 70)
    print("TEST F3-05 — market_studies N+1 + dashboard GROUP BY + cascade delete")
    print("=" * 70)
    report = Report()
    asyncio.run(_run_study_detail_checks(report))
    asyncio.run(_run_dashboard_checks(report))
    asyncio.run(_run_delete_cascade_checks(report))
    print("=" * 70)
    print(f"  {report.summary()}")
    print("  EXIT " + ("OK" if report.exit_code == 0 else "FAIL"))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
