"""Smoke de invariantes del nucleo (WO F1-04).

Vara ejecutable a correr ANTES de cada push que toque el motor ACM, el
anclaje de mercado o el aislamiento multi-tenant (F1/F2). Hoy no hay
suite de tests (pytest llega en F3-06) asi que este es un runner
standalone, sin dependencias de test-framework.

Invariantes puras (matematica determinista, SIN DB — corren SIEMPRE):
  [2] Motor ACM (services/acm_service.compute_market_study): con 4
      comparables fijos, suggested_value_min/mode/max y confidence
      tienen que dar un valor EXACTO. Los coeficientes son matematica
      pura: cualquier drift respecto del oraculo hardcodeado de abajo
      es una regresion real.
  [3] Anchor (services/anchor_service._build_anchor): con un subset
      congelado de 10 listings conocidos, la mediana/p25/p75/min/max
      de USD/m2 tienen que dar EXACTO.

Invariantes de infraestructura (requieren DB + API corriendo local):
  [1] Aislamiento multi-tenant: settings IA por workspace, heatmap
      /points y collaboration comment/consensus no se filtran entre
      2 workspaces de fixture.
  [4] Endpoints criticos responden 200: login, properties list,
      appraisal PDF, valuations/express (con fallback deterministico
      sin IA real) y market/comparables.

Politica de DB (ver README de este directorio): esta suite NUNCA debe
correr contra la Aiven COMPARTIDA de la app. Por default, si
DB_HOST no es localhost/127.0.0.1, los bloques [1] y [4] se
SKIPPEAN sin intentar abrir conexion. Para forzarlo (con una DB local
o de test que vos levantaste a proposito) usa:

    TASAR_SMOKE_ALLOW_REMOTE_DB=1 python backend/scripts/smoke_core.py

Uso:
    python backend/scripts/smoke_core.py
    python backend/scripts/smoke_core.py --base-url http://127.0.0.1:8600/api

Exit code: 0 si no hubo ningun FAIL (los SKIP no cuentan como fallo).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
DB_CONNECT_TIMEOUT_S = 5
SERVER_PING_TIMEOUT_S = 3


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
        counts = {PASS: 0, FAIL: 0, SKIP: 0}
        for r in self.results:
            counts[r.status] += 1
        return f"PASS={counts[PASS]}  FAIL={counts[FAIL]}  SKIP={counts[SKIP]}"


def _section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# [2] Motor ACM — invariante pura, sin DB.
# ---------------------------------------------------------------------------
def invariant_acm_engine(report: Report) -> None:
    """Oraculo calculado corriendo services/acm_service.compute_market_study
    con este mismo fixture sobre el codigo actual (2026-07-10, coeficientes
    tal cual estan en el archivo). 4 comparables con precio, area, ambientes
    y antiguedad elegidos a mano para que el peso de similitud de cada uno
    sea distinto (evita que un bug en un termino del score pase
    desapercibido por casualidad)."""
    from services.acm_service import compute_market_study

    target = {"total_area_m2": 100, "rooms": 3, "age_years": 10}
    comparables = [
        {"id": 1, "price": 200000, "total_area_m2": 100, "rooms": 3, "age_years": 10,
         "adjustments": [{"coefficient": 1.0}]},
        {"id": 2, "price": 180000, "total_area_m2": 90, "rooms": 3, "age_years": 15,
         "adjustments": [{"coefficient": 1.05}]},
        {"id": 3, "price": 260000, "total_area_m2": 110, "rooms": 4, "age_years": 5,
         "adjustments": [{"coefficient": 0.95}]},
        {"id": 4, "price": 150000, "total_area_m2": 85, "rooms": 2, "age_years": 25,
         "adjustments": [{"coefficient": 1.1}]},
    ]
    EXPECTED = {
        "suggested_value_min": 194117.65,
        "suggested_value_max": 224545.45,
        "suggested_value_mode": 207530.41,
        "confidence_score": 0.83,
    }
    EXPECTED_WEIGHTS = {1: 1.0, 2: 0.81, 3: 0.716, 4: 0.496}

    r = compute_market_study(target, comparables)

    mismatches = [
        f"{k}: esperado {v} obtuvo {r.get(k)}"
        for k, v in EXPECTED.items() if r.get(k) != v
    ]
    weights = {c["id"]: c["weight"] for c in r.get("comparable_results", [])}
    mismatches += [
        f"weight comparable {cid}: esperado {w} obtuvo {weights.get(cid)}"
        for cid, w in EXPECTED_WEIGHTS.items() if weights.get(cid) != w
    ]

    if mismatches:
        report.add(
            "[2] acm_engine: valor sugerido / confianza / pesos exactos",
            FAIL,
            "; ".join(mismatches),
        )
    else:
        report.add(
            "[2] acm_engine: valor sugerido / confianza / pesos exactos",
            PASS,
            f"mode={r['suggested_value_mode']} conf={r['confidence_score']}",
        )


# ---------------------------------------------------------------------------
# [3] Anchor — invariante pura, sin DB (instancia MarketListing en memoria,
# no persiste nada; solo ejerce la matematica de _build_anchor).
# ---------------------------------------------------------------------------
def invariant_anchor_engine(report: Report) -> None:
    """Oraculo calculado corriendo services/anchor_service._build_anchor con
    este mismo fixture (10 listings, mismo total_area_m2 que la propiedad
    consultada para que el cutoff de superficie +/-50% los deje pasar a
    todos, y USD/m2 en escalera 1000..1900 para que min/p25/mediana/p75/max
    salgan enteros y sin ambiguedad de redondeo)."""
    from services.anchor_service import _build_anchor, AnchorQuery
    from models.market_listing import MarketListing

    listings = []
    for i, ppm2 in enumerate([1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900], start=1):
        listings.append(MarketListing(
            id=i, title=f"[FIXTURE] Casa {i}", property_type="casa", operation="venta",
            province="Buenos Aires", city="Palermo", neighborhood=None, address=None,
            total_area_m2=100.0, covered_area_m2=100.0, rooms=4, bedrooms=3, age_years=8,
            condition="bueno", price=float(ppm2 * 100), currency="USD", status="active",
            source="fixture", description="",
        ))
    q = AnchorQuery(
        property_type="casa", total_area_m2=100.0, province="Buenos Aires",
        city="Palermo", condition="bueno", bedrooms=3, features=[],
    )
    anchor = _build_anchor(listings, "zona", "casa", "Palermo", q)

    EXPECTED_PPM2 = {"min": 1000, "p25": 1225, "median": 1450, "p75": 1675, "max": 1900}

    if anchor is None:
        report.add("[3] anchor: mediana/p25/p75 exactos sobre subset congelado", FAIL,
                    "_build_anchor devolvio None (esperaba anchor con 10 comparables)")
        return

    mismatches = [
        f"{k}: esperado {v} obtuvo {anchor['price_per_m2'].get(k)}"
        for k, v in EXPECTED_PPM2.items() if anchor["price_per_m2"].get(k) != v
    ]
    if anchor.get("count") != 10:
        mismatches.append(f"count: esperado 10 obtuvo {anchor.get('count')}")

    if mismatches:
        report.add("[3] anchor: mediana/p25/p75 exactos sobre subset congelado", FAIL,
                    "; ".join(mismatches))
    else:
        report.add("[3] anchor: mediana/p25/p75 exactos sobre subset congelado", PASS,
                    f"price_per_m2={anchor['price_per_m2']}")


# ---------------------------------------------------------------------------
# Deteccion de DB / servidor disponibles (SKIP elegante, nunca explota).
# ---------------------------------------------------------------------------
def _db_gate() -> tuple[bool, str]:
    """Chequeo de politica (sin abrir conexion). No corremos contra la Aiven
    compartida salvo override explicito del que corre el script a mano."""
    from core.config import settings

    host = (settings.DB_HOST or "").strip().lower()
    if host in LOCAL_DB_HOSTS:
        return True, f"DB_HOST={host} es local"
    if os.environ.get("TASAR_SMOKE_ALLOW_REMOTE_DB") == "1":
        return True, f"DB_HOST={host} remoto, forzado por TASAR_SMOKE_ALLOW_REMOTE_DB=1"
    return False, (
        f"DB_HOST={settings.DB_HOST!r} no es local (no hay MySQL local/docker en este "
        "entorno) y esta PROHIBIDO correr smoke contra la Aiven compartida. "
        "Segui las instrucciones del README para correr esto con DB local."
    )


async def _db_reachable() -> tuple[bool, str]:
    """Intento real de conexion, con timeout, para el caso en que la politica
    ya dio luz verde (DB local o forzada) pero el motor no esta levantado."""
    from core.database import engine

    try:
        conn = await asyncio.wait_for(engine.connect(), timeout=DB_CONNECT_TIMEOUT_S)
        await conn.close()
        return True, "conexion OK"
    except Exception as e:  # noqa: BLE001 — cualquier fallo de conexion = SKIP, no crash
        return False, f"{type(e).__name__}: {e}"


def _server_reachable(base_url: str) -> tuple[bool, str]:
    import httpx

    try:
        r = httpx.get(f"{base_url.rsplit('/api', 1)[0]}/docs", timeout=SERVER_PING_TIMEOUT_S)
        return r.status_code < 500, f"HTTP {r.status_code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# [1] Aislamiento multi-tenant — requiere DB + servidor.
# ---------------------------------------------------------------------------
async def _make_fixture_workspaces(session):
    """Crea 2 workspaces + 1 user broker c/u, prefijo [SMOKE] + timestamp para
    no chocar ni ensuciar datos reales/demo. Devuelve dicts livianos (no ORM)
    para no arrastrar la sesion fuera de este scope."""
    from models.workspace import Workspace
    from models.user import User
    from core.security import hash_password, create_access_token

    stamp = int(time.time())
    wa = Workspace(name=f"[SMOKE] WS-A-{stamp}", slug=f"smoke-a-{stamp}", plan="free")
    wb = Workspace(name=f"[SMOKE] WS-B-{stamp}", slug=f"smoke-b-{stamp}", plan="free")
    session.add_all([wa, wb])
    await session.flush()

    ua = User(workspace_id=wa.id, email=f"smoke-a-{stamp}@tasar.local",
              password_hash=hash_password("smoke12345"), full_name="[SMOKE] User A", role="broker")
    ub = User(workspace_id=wb.id, email=f"smoke-b-{stamp}@tasar.local",
              password_hash=hash_password("smoke12345"), full_name="[SMOKE] User B", role="broker")
    session.add_all([ua, ub])
    await session.commit()
    await session.refresh(ua)
    await session.refresh(ub)

    token_a = create_access_token({"sub": str(ua.id)})
    token_b = create_access_token({"sub": str(ub.id)})
    return {
        "workspace_a": wa, "workspace_b": wb, "user_a": ua, "user_b": ub,
        "token_a": token_a, "token_b": token_b,
    }


async def _teardown_fixture(session, fx: dict) -> None:
    """Best-effort: borra todo lo que este runner creo. Si algo falla no hace
    caer el resultado del smoke (ya se reporto arriba); solo se loguea."""
    from sqlalchemy import delete
    from models.workspace import Workspace
    from models.user import User
    from models.app_setting import AppSetting
    from models.property import Property
    from models.market_study import MarketStudy
    from models.collaboration import Collaboration, CollaborationComment

    try:
        wa_id, wb_id = fx["workspace_a"].id, fx["workspace_b"].id
        ms_id = fx.get("market_study_id")
        if ms_id:
            await session.execute(delete(CollaborationComment).where(CollaborationComment.market_study_id == ms_id))
            await session.execute(delete(Collaboration).where(Collaboration.market_study_id == ms_id))
            await session.execute(delete(MarketStudy).where(MarketStudy.id == ms_id))
        await session.execute(delete(Property).where(Property.workspace_id.in_([wa_id, wb_id])))
        await session.execute(delete(AppSetting).where(AppSetting.workspace_id.in_([wa_id, wb_id])))
        await session.execute(delete(User).where(User.workspace_id.in_([wa_id, wb_id])))
        await session.execute(delete(Workspace).where(Workspace.id.in_([wa_id, wb_id])))
        await session.commit()
    except Exception as e:  # noqa: BLE001
        print(f"  [WARN] teardown de fixtures multi-tenant fallo (no afecta el resultado): {e}")
        await session.rollback()


async def invariant_multi_tenant_isolation(report: Report, base_url: str) -> None:
    import httpx
    from core.database import AsyncSessionLocal
    from models.property import Property
    from models.market_study import MarketStudy

    name = "[1] aislamiento multi-tenant (settings IA / heatmap / collaboration)"

    async with AsyncSessionLocal() as session:
        fx = await _make_fixture_workspaces(session)
        try:
            h_a = {"Authorization": f"Bearer {fx['token_a']}"}
            h_b = {"Authorization": f"Bearer {fx['token_b']}"}

            async with httpx.AsyncClient(base_url=base_url, timeout=15) as client:
                # --- vector 1: settings IA por workspace ---
                put_r = await client.put("/settings/claude_model", headers=h_a, json={"value": "opus"})
                get_b = await client.get("/settings/claude_model", headers=h_b)
                leaked_settings = (
                    put_r.status_code == 200
                    and get_b.status_code == 200
                    and get_b.json().get("value") == "opus"
                )

                # --- vector 2: heatmap /points ---
                prop_a = Property(
                    workspace_id=fx["workspace_a"].id, title="[SMOKE] Depto aislamiento",
                    property_type="departamento", operation="venta", city="Palermo",
                    latitude=-34.588, longitude=-58.430, total_area_m2=50, asking_price=150000,
                )
                session.add(prop_a)
                await session.commit()
                await session.refresh(prop_a)

                heat_b = await client.get("/heatmap/points", headers=h_b)
                leaked_heatmap = heat_b.status_code == 200 and any(
                    pt.get("label") == "[SMOKE] Depto aislamiento" for pt in heat_b.json()
                )

                # --- vector 3: collaboration comment/consensus ---
                study_post = await client.post(
                    "/market-studies", headers=h_a,
                    json={"property_id": prop_a.id, "method": "homogenization"},
                )
                study_id = study_post.json().get("id") if study_post.status_code == 200 else None
                fx["market_study_id"] = study_id

                comment_leaked = consensus_leaked = None
                if study_id:
                    await client.post(
                        f"/collaboration/{study_id}/comments", headers=h_a,
                        json={"body": "[SMOKE] comentario workspace A"},
                    )
                    comments_b = await client.get(f"/collaboration/{study_id}/comments", headers=h_b)
                    consensus_b = await client.get(f"/collaboration/{study_id}/consensus", headers=h_b)
                    # ensure_study_in_workspace debe dar 404 para el otro tenant (anti-IDOR).
                    comment_leaked = comments_b.status_code == 200
                    consensus_leaked = consensus_b.status_code == 200

            failures = []
            if leaked_settings:
                failures.append("settings/claude_model: workspace B ve el valor seteado por A")
            if leaked_heatmap:
                failures.append("heatmap/points: workspace B ve un punto de A")
            if study_id is None:
                failures.append(f"no se pudo crear market-study de fixture (status={study_post.status_code})")
            else:
                if comment_leaked:
                    failures.append("collaboration/comments: workspace B accede a comments de A (esperaba 404)")
                if consensus_leaked:
                    failures.append("collaboration/consensus: workspace B accede a consensus de A (esperaba 404)")

            if failures:
                report.add(name, FAIL, "; ".join(failures))
            else:
                report.add(name, PASS, "settings/heatmap/collaboration aislados por workspace_id")
        finally:
            await _teardown_fixture(session, fx)


# ---------------------------------------------------------------------------
# [4] Endpoints criticos — requiere DB + servidor + usuario demo seedeado
# (scripts/seed_demo.py).
# ---------------------------------------------------------------------------
async def invariant_critical_endpoints(report: Report, base_url: str) -> None:
    import httpx

    name = "[4] endpoints criticos responden 200"
    checks: List[str] = []
    failures: List[str] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        r = await client.post("/auth/login", json={"email": "admin@tasar.demo", "password": "admin123"})
        if r.status_code != 200:
            report.add(name, FAIL, f"login fallo ({r.status_code}) -- corriste scripts/seed_demo.py?")
            return
        checks.append("login")
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = await client.get("/properties", headers=h)
        if r.status_code != 200:
            failures.append(f"GET properties -> {r.status_code}")
        else:
            checks.append("properties list")
        props = r.json() if r.status_code == 200 else []

        r = await client.get("/market/comparables", headers=h, params={"property_type": "departamento", "limit": 5})
        if r.status_code != 200:
            failures.append(f"GET market/comparables -> {r.status_code}")
        else:
            checks.append("market/comparables")

        if props:
            pid = props[0]["id"]
            r = await client.post("/appraisals", headers=h, json={
                "property_id": pid, "purpose": "[SMOKE] verificacion F1-04",
            })
            if r.status_code != 200:
                failures.append(f"POST appraisals -> {r.status_code}: {r.text[:150]}")
            else:
                checks.append("appraisal create")
                aid = r.json()["id"]
                r = await client.get(f"/appraisals/{aid}/pdf", headers=h)
                if r.status_code != 200:
                    failures.append(f"GET appraisals/{{id}}/pdf -> {r.status_code}")
                else:
                    checks.append("appraisal pdf")
        else:
            failures.append("no hay propiedades en el workspace demo -- no se pudo probar appraisal/pdf")

        r = await client.post("/valuations/express", headers=h, json={
            "property_type": "departamento", "city": "Palermo", "total_area_m2": 55,
        })
        if r.status_code != 200:
            failures.append(f"POST valuations/express -> {r.status_code}: {r.text[:150]}")
        else:
            checks.append("valuations/express (fallback deterministico si no hay IA)")

    if failures:
        report.add(name, FAIL, "; ".join(failures))
    else:
        report.add(name, PASS, ", ".join(checks))


async def run_db_dependent_invariants(report: Report, base_url: str) -> None:
    allowed, gate_msg = _db_gate()
    if not allowed:
        report.add("[1] aislamiento multi-tenant", SKIP, gate_msg)
        report.add("[4] endpoints criticos", SKIP, gate_msg)
        return

    db_ok, db_msg = await _db_reachable()
    if not db_ok:
        report.add("[1] aislamiento multi-tenant", SKIP, f"DB no disponible: {db_msg}")
        report.add("[4] endpoints criticos", SKIP, f"DB no disponible: {db_msg}")
        return

    srv_ok, srv_msg = _server_reachable(base_url)
    if not srv_ok:
        report.add("[1] aislamiento multi-tenant", SKIP, f"servidor no disponible en {base_url}: {srv_msg}")
        report.add("[4] endpoints criticos", SKIP, f"servidor no disponible en {base_url}: {srv_msg}")
        return

    await invariant_multi_tenant_isolation(report, base_url)
    await invariant_critical_endpoints(report, base_url)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default="http://127.0.0.1:8600/api",
                         help="Base URL de la API local (default: %(default)s)")
    args = parser.parse_args()

    t0 = time.time()
    report = Report()

    _section("INVARIANTES PURAS (sin DB)")
    invariant_acm_engine(report)
    invariant_anchor_engine(report)

    _section("INVARIANTES DE INFRAESTRUCTURA (requieren DB + API local)")
    asyncio.run(run_db_dependent_invariants(report, args.base_url))

    elapsed = time.time() - t0
    _section("RESULTADO")
    print(f"  {report.summary()}   ({elapsed:.1f}s)")
    print("  EXIT " + ("OK" if report.exit_code == 0 else "FAIL"))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
