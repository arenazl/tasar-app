"""Test standalone del canal Meta Cloud API oficial (WO F3-02) — sin pytest,
sin MySQL, sin sandbox real de Meta (no disponible en este entorno).

Sigue el mismo patrón liviano de `scripts/test_f3_audio.py` (Report PASS/FAIL,
sin dependencias de test-framework) y el patrón SQLite-en-memoria de
`scripts/test_bot_f2_03.py` para los tests que necesitan DB.

Cubre (con requests mockeados, HONESTO sobre lo NO ejercido):
  [1] Verify-token flow del GET /api/meta/webhook: token correcto -> 200 +
      challenge; token incorrecto/ausente -> 403.
  [2] Firma HMAC del POST /api/meta/webhook: firma inválida -> 403; sin
      META_APP_SECRET configurado -> 403 (fail-closed, ver meta_client.py).
  [3] Firma HMAC válida -> pasa la verificación (200, no 403) aunque el resto
      del payload no tenga workspace (se corta después, en el ruteo).
  [4] Ruteo por meta_phone_number_id: un phone_number_id conocido resuelve el
      workspace correcto (fixture SQLite); uno desconocido no rompe (skip).
  [5] wa_out.send resuelve baileys|meta por channel_provider — ÚNICO lugar
      del backend que compara ese campo (mock de los 2 caminos de envío, sin
      pegarle a la red real).

NO EJERCITADO (sin sandbox Meta real, ver reporte del WO F3-02):
  - El shape real de `message_echoes` (coexistence) — meta_client.parse_echo
    es un best-effort no verificado contra un webhook real.
  - Meta Graph API real (send_text/send_audio/download_media) — mockeados acá.
  - El flujo completo con Gemini function-calling respondiendo (igual que
    test_bot_f2_03.py, eso queda para un entorno con credenciales).

Uso:
    python backend/scripts/test_meta_f3_02.py

Exit code: 0 si no hubo ningún FAIL.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Satisfacer core.config antes de importar nada de la app (no conecta a MySQL).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx  # noqa: E402
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


APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"


def _sign(body: bytes, secret: str = APP_SECRET) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# [1]/[2]/[3] — verify-token + HMAC, sin DB (mockeando settings + client de app).
# ---------------------------------------------------------------------------
async def _run_verify_and_hmac_checks(report: Report) -> None:
    import main
    from core.config import settings
    from core.database import get_db

    async def _noop_db():
        yield None  # las rutas que dependen de db no se llegan a ejercer en estos casos

    main.app.dependency_overrides[get_db] = _noop_db

    with patch.object(settings, "META_WEBHOOK_VERIFY_TOKEN", VERIFY_TOKEN), \
         patch.object(settings, "META_APP_SECRET", APP_SECRET):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # [1a] token correcto -> 200 + challenge en el body.
            r = await client.get("/api/meta/webhook", params={
                "hub.mode": "subscribe", "hub.verify_token": VERIFY_TOKEN, "hub.challenge": "chal-123",
            })
            report.add(
                "[1a] GET /api/meta/webhook con verify_token correcto -> 200 + challenge",
                PASS if r.status_code == 200 and r.text == "chal-123" else FAIL,
                f"status={r.status_code} body={r.text!r}",
            )

            # [1b] token incorrecto -> 403.
            r = await client.get("/api/meta/webhook", params={
                "hub.mode": "subscribe", "hub.verify_token": "token-trucho", "hub.challenge": "chal-123",
            })
            report.add(
                "[1b] GET /api/meta/webhook con verify_token incorrecto -> 403",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

            body = json.dumps({"entry": []}).encode("utf-8")

            # [2a] POST sin firma -> 403.
            r = await client.post("/api/meta/webhook", content=body, headers={"Content-Type": "application/json"})
            report.add(
                "[2a] POST /api/meta/webhook sin X-Hub-Signature-256 -> 403",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

            # [2b] POST con firma inválida (secret incorrecto) -> 403.
            bad_sig = _sign(body, secret="otro-secret-cualquiera")
            r = await client.post(
                "/api/meta/webhook", content=body,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": bad_sig},
            )
            report.add(
                "[2b] POST /api/meta/webhook con firma HMAC inválida -> 403",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

            # [2c] fail-closed: sin META_APP_SECRET configurado, CUALQUIER firma -> 403.
            with patch.object(settings, "META_APP_SECRET", ""):
                good_sig_pero_sin_secret = _sign(body, secret=APP_SECRET)
                r = await client.post(
                    "/api/meta/webhook", content=body,
                    headers={"Content-Type": "application/json", "X-Hub-Signature-256": good_sig_pero_sin_secret},
                )
            report.add(
                "[2c] POST /api/meta/webhook sin META_APP_SECRET configurado -> 403 (fail-closed)",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

    main.app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# [4] Ruteo por meta_phone_number_id — con DB SQLite en memoria.
# ---------------------------------------------------------------------------
async def _run_routing_checks(report: Report) -> None:
    import main
    from core.config import settings
    from core.database import get_db, Base
    import models  # noqa: F401 — registra metadata
    from models.workspace import Workspace
    from models.bot_config import WorkspaceBotConfig

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        ws = Workspace(name="Agencia Meta", slug="agencia-meta", plan="free")
        session.add(ws)
        await session.flush()
        cfg = WorkspaceBotConfig(
            workspace_id=ws.id, enabled=False, channel_provider="meta",
            meta_phone_number_id="123456789",
        )
        session.add(cfg)
        await session.commit()

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    payload_known = {
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "123456789", "display_phone_number": "5491100000000"},
            "contacts": [{"profile": {"name": "Cliente Test"}}],
            "messages": [{"from": "5491122334455", "id": "wamid.TEST1", "type": "text", "text": {"body": "hola"}}],
        }}]}]
    }
    payload_unknown = {
        "entry": [{"changes": [{"value": {
            "metadata": {"phone_number_id": "999999999"},
            "contacts": [{"profile": {"name": "Otro"}}],
            "messages": [{"from": "5491100000009", "id": "wamid.TEST2", "type": "text", "text": {"body": "hola"}}],
        }}]}]
    }

    with patch.object(settings, "META_APP_SECRET", APP_SECRET), \
         patch.object(settings, "META_ACCESS_TOKEN", "token-de-prueba"):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            body = json.dumps(payload_known).encode("utf-8")
            r = await client.post(
                "/api/meta/webhook", content=body,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body)},
            )
            data = r.json() if r.status_code == 200 else {}
            # bot_config.enabled=False -> el pipeline comun corta en "bot: disabled"
            # (ver services/wa_inbound.process_incoming paso 5) sin necesitar Gemini.
            ok = r.status_code == 200 and data.get("bot") == "disabled" and data.get("conversation_id")
            report.add(
                "[4a] POST con meta_phone_number_id conocido -> resuelve el workspace y crea la conversacion",
                PASS if ok else FAIL,
                f"status={r.status_code} body={data}",
            )

            body2 = json.dumps(payload_unknown).encode("utf-8")
            r2 = await client.post(
                "/api/meta/webhook", content=body2,
                headers={"Content-Type": "application/json", "X-Hub-Signature-256": _sign(body2)},
            )
            data2 = r2.json() if r2.status_code == 200 else {}
            ok2 = r2.status_code == 200 and data2.get("modo") == "skip_no_workspace"
            report.add(
                "[4b] POST con meta_phone_number_id desconocido -> skip sin romper (no 500)",
                PASS if ok2 else FAIL,
                f"status={r2.status_code} body={data2}",
            )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


# ---------------------------------------------------------------------------
# [5] wa_out.send — ÚNICO punto que compara channel_provider.
# ---------------------------------------------------------------------------
async def _run_wa_out_dispatch_checks(report: Report) -> None:
    from services import wa_out
    from models.workspace import Workspace
    from models.bot_config import WorkspaceBotConfig

    ws = Workspace(id=1, name="Agencia X", slug="agencia-x", plan="free")

    cfg_baileys = WorkspaceBotConfig(id=1, workspace_id=1, channel_provider="baileys")
    cfg_meta = WorkspaceBotConfig(id=2, workspace_id=1, channel_provider="meta", meta_phone_number_id="123")

    with patch.object(wa_out, "_send_via_baileys", new=AsyncMock(return_value=(True, "mid-1", None))) as baileys_mock, \
         patch.object(wa_out, "_send_via_meta", new=AsyncMock(return_value=(True, "mid-2", None))) as meta_mock:
        await wa_out.send(ws, cfg_baileys, "5491122334455@s.whatsapp.net", "hola")
        baileys_called_meta_not = baileys_mock.await_count == 1 and meta_mock.await_count == 0

        await wa_out.send(ws, cfg_meta, "5491122334455@s.whatsapp.net", "hola")
        meta_called_now = meta_mock.await_count == 1 and baileys_mock.await_count == 1  # baileys sigue en 1, no subio

    ok = baileys_called_meta_not and meta_called_now
    report.add(
        "[5] wa_out.send rutea a _send_via_baileys o _send_via_meta segun channel_provider (unico switch del backend)",
        PASS if ok else FAIL,
        f"baileys_calls={baileys_mock.await_count} meta_calls={meta_mock.await_count}",
    )

    # cfg=None (workspace sin fila de config todavia) -> default baileys, no explota.
    with patch.object(wa_out, "_send_via_baileys", new=AsyncMock(return_value=(True, "mid-3", None))) as baileys_mock2:
        await wa_out.send(ws, None, "5491122334455@s.whatsapp.net", "hola")
    report.add(
        "[5b] wa_out.send sin cfg (None) cae a baileys por default sin romper",
        PASS if baileys_mock2.await_count == 1 else FAIL,
        f"baileys_calls={baileys_mock2.await_count}",
    )


def main() -> int:
    print("=" * 70)
    print("TEST F3-02 — canal Meta Cloud API: verify-token + HMAC + ruteo + wa_out")
    print("=" * 70)
    report = Report()
    asyncio.run(_run_verify_and_hmac_checks(report))
    asyncio.run(_run_routing_checks(report))
    asyncio.run(_run_wa_out_dispatch_checks(report))
    print("=" * 70)
    print(f"  {report.summary()}")
    print("  EXIT " + ("OK" if report.exit_code == 0 else "FAIL"))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
