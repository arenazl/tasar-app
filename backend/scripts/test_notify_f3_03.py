"""Test standalone de notificaciones (WO F3-03) -- push PWA + cron de resumen
semanal. Sin pytest, sin MySQL (SQLite en memoria), sin browser/VAPID real
(no disponible en este entorno). Sigue el mismo patron liviano de
`scripts/test_meta_f3_02.py` y `scripts/test_bot_f2_03.py` (Report PASS/FAIL,
httpx.ASGITransport contra `main.app`, SQLite fixture).

Cubre (HONESTO sobre lo NO ejercido):
  [1] POST /api/push/subscribe persiste la suscripcion (JWT); repetir el
      mismo endpoint actualiza en vez de duplicar (idempotencia).
  [2] push_notif.notify_user: una suscripcion que el push service devuelve
      como vencida (410 Gone, mockeado -- pywebpush.webpush jamas pega a la
      red real) se borra; una que devuelve OK sobrevive.
  [3] POST /api/cron/weekly-summary: sin X-Cron-Key -> 403; con key
      incorrecta -> 403; sin CRON_KEY configurada en env -> 403 (fail-closed).
  [4] Con key correcta: filtra por el toggle `notify_email` por workspace
      (uno explicitamente apagado, el otro prendido por default) y el
      conteo devuelto == cantidad de emails realmente "enviados" (SMTP
      mockeado -- no pega a Brevo real).

NO EJERCITADO (sin browser/VAPID real, ver reporte del WO F3-03):
  - Un push real llegando a un Service Worker de un browser de verdad.
  - Firma VAPID real end-to-end contra un push service (FCM/Mozilla) --
    pywebpush.webpush esta mockeado en [2], no se ejercita la crypto real
    ni la red.
  - El scheduler externo (Cloud Scheduler / cron de Infra) que dispara este
    endpoint periodicamente -- eso lo define Infra, fuera de este backend.

Uso:
    python backend/scripts/test_notify_f3_03.py

Exit code: 0 si no hubo ningun FAIL.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Satisfacer core.config antes de importar nada de la app (no conecta a MySQL).
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("SECRET_KEY", "test-secret")

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402
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
    import models  # noqa: F401 — registra metadata
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ---------------------------------------------------------------------------
# [1] POST /api/push/subscribe persiste + es idempotente.
# ---------------------------------------------------------------------------
async def _run_subscribe_checks(report: Report) -> None:
    import main
    from core.database import get_db
    from core.security import hash_password, create_access_token
    from models.workspace import Workspace
    from models.user import User
    from models.push_subscription import PushSubscription

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())

    async with SessionLocal() as session:
        ws = Workspace(name=f"[TEST] WS {stamp}", slug=f"test-notify-{stamp}", plan="free")
        session.add(ws)
        await session.flush()
        user = User(
            workspace_id=ws.id, email=f"vendedor-{stamp}@tasar.local",
            password_hash=hash_password("test12345"), full_name="Vendedor Test", role="vendedor",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token = create_access_token({"sub": str(user.id)})
        user_id = user.id

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    payload = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-1",
        "keys": {"p256dh": "p256dh-fake-key", "auth": "auth-fake-key"},
    }
    headers = {"Authorization": f"Bearer {token}"}

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/push/subscribe", json=payload, headers=headers)
        ok_create = r1.status_code == 200 and r1.json().get("created") is True
        report.add(
            "[1a] POST /api/push/subscribe crea la suscripcion",
            PASS if ok_create else FAIL,
            f"status={r1.status_code} body={r1.text[:200]}",
        )

        r2 = await client.post("/api/push/subscribe", json=payload, headers=headers)
        ok_update = r2.status_code == 200 and r2.json().get("updated") is True
        report.add(
            "[1b] repetir el mismo endpoint actualiza en vez de duplicar (idempotencia)",
            PASS if ok_update else FAIL,
            f"status={r2.status_code} body={r2.text[:200]}",
        )

    async with SessionLocal() as session:
        rows = (await session.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )).scalars().all()
        ok_count = len(rows) == 1 and rows[0].workspace_id == ws.id
        report.add(
            "[1c] persiste UNA sola fila (no duplica) con workspace_id correcto",
            PASS if ok_count else FAIL,
            f"filas={len(rows)}",
        )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


# ---------------------------------------------------------------------------
# [2] push_notif.notify_user borra subs vencidas (410), conserva las OK.
# ---------------------------------------------------------------------------
async def _run_push_cleanup_checks(report: Report) -> None:
    from core.database import Base
    from core.config import settings
    from models.workspace import Workspace
    from models.user import User
    from models.push_subscription import PushSubscription
    from services import push_notif
    from pywebpush import WebPushException

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())

    async with SessionLocal() as session:
        ws = Workspace(name=f"[TEST] WS push {stamp}", slug=f"test-push-{stamp}", plan="free")
        session.add(ws)
        await session.flush()
        user = User(
            workspace_id=ws.id, email=f"u-{stamp}@tasar.local",
            password_hash="x", full_name="U", role="vendedor", is_active=True,
        )
        session.add(user)
        await session.flush()

        sub_ok = PushSubscription(
            workspace_id=ws.id, user_id=user.id,
            endpoint="https://push.example/sub-ok", p256dh="p", auth="a",
        )
        sub_gone = PushSubscription(
            workspace_id=ws.id, user_id=user.id,
            endpoint="https://push.example/sub-gone-410", p256dh="p", auth="a",
        )
        session.add_all([sub_ok, sub_gone])
        await session.commit()
        user_id, ok_id, gone_id = user.id, sub_ok.id, sub_gone.id

        class _FakeResp:
            status_code = 410

        def _fake_webpush(subscription_info, **kwargs):
            if subscription_info["endpoint"].endswith("sub-gone-410"):
                raise WebPushException("Gone", response=_FakeResp())
            return None

        with patch.object(settings, "VAPID_PUBLIC_KEY", "fake-pub"), \
             patch.object(settings, "VAPID_PRIVATE_KEY", "fake-priv"), \
             patch.object(push_notif, "webpush", side_effect=_fake_webpush):
            await push_notif.notify_user(session, user_id, title="t", body="b")
            await session.commit()

    async with SessionLocal() as session:
        remaining = (await session.execute(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )).scalars().all()
        remaining_ids = {s.id for s in remaining}
        ok = remaining_ids == {ok_id} and gone_id not in remaining_ids
        report.add(
            "[2] notify_user borra la sub que devuelve 410 y conserva la que responde OK",
            PASS if ok else FAIL,
            f"remaining_ids={remaining_ids} expected={{ok_id={ok_id}}} gone_id={gone_id}",
        )

    await engine.dispose()


# ---------------------------------------------------------------------------
# [3]/[4] POST /api/cron/weekly-summary -- guard de key + filtro por toggle.
# ---------------------------------------------------------------------------
async def _run_cron_checks(report: Report) -> None:
    import main
    from core.config import settings
    from core.database import get_db
    from models.workspace import Workspace
    from models.user import User
    from models.app_setting import AppSetting

    engine, SessionLocal = await _make_engine()
    stamp = int(time.time())

    async with SessionLocal() as session:
        ws_on = Workspace(name=f"[TEST] WS ON {stamp}", slug=f"test-cron-on-{stamp}", plan="free")
        ws_off = Workspace(name=f"[TEST] WS OFF {stamp}", slug=f"test-cron-off-{stamp}", plan="free")
        session.add_all([ws_on, ws_off])
        await session.flush()

        # ws_off: toggle EXPLICITO en false. ws_on: SIN fila -> default True
        # (mismo default de email_service._notify_enabled, no lo redefinimos aca).
        session.add(AppSetting(workspace_id=ws_off.id, key="notify_email", value="false"))

        u_on = User(
            workspace_id=ws_on.id, email=f"on-{stamp}@tasar.local",
            password_hash="x", full_name="Vendedor ON", role="vendedor", is_active=True,
        )
        u_off = User(
            workspace_id=ws_off.id, email=f"off-{stamp}@tasar.local",
            password_hash="x", full_name="Vendedor OFF", role="vendedor", is_active=True,
        )
        session.add_all([u_on, u_off])
        await session.commit()

    async def _override_db():
        async with SessionLocal() as session:
            yield session

    main.app.dependency_overrides[get_db] = _override_db

    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # [3a] sin CRON_KEY configurada en env -> 403 (fail-closed), incluso
        # mandando un header cualquiera.
        with patch.object(settings, "CRON_KEY", ""):
            r = await client.post("/api/cron/weekly-summary", headers={"X-Cron-Key": "lo-que-sea"})
        report.add(
            "[3a] sin CRON_KEY configurada en env -> 403 (fail-closed)",
            PASS if r.status_code == 403 else FAIL,
            f"status={r.status_code}",
        )

        with patch.object(settings, "CRON_KEY", "secreto-cron-test"):
            # [3b] sin header -> 403.
            r = await client.post("/api/cron/weekly-summary")
            report.add(
                "[3b] sin header X-Cron-Key -> 403",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

            # [3c] header con key incorrecta -> 403.
            r = await client.post("/api/cron/weekly-summary", headers={"X-Cron-Key": "trucha"})
            report.add(
                "[3c] X-Cron-Key incorrecta -> 403",
                PASS if r.status_code == 403 else FAIL,
                f"status={r.status_code}",
            )

            # [4] key correcta -> filtra por toggle y cuenta los envios reales
            # (SMTP mockeado: send_email siempre True, sin pegarle a Brevo).
            with patch("services.email_service._send_sync", return_value=True):
                r = await client.post("/api/cron/weekly-summary", headers={"X-Cron-Key": "secreto-cron-test"})
            body = r.json() if r.status_code == 200 else {}
            ok = r.status_code == 200 and body.get("sent") == 1
            report.add(
                "[4] key correcta -> 200, manda SOLO al workspace con notify_email activo (sent=1)",
                PASS if ok else FAIL,
                f"status={r.status_code} body={body}",
            )

    main.app.dependency_overrides.pop(get_db, None)
    await engine.dispose()


def main() -> int:
    print("=" * 70)
    print("TEST F3-03 — push PWA (subscribe/cleanup) + cron resumen semanal")
    print("=" * 70)
    report = Report()
    asyncio.run(_run_subscribe_checks(report))
    asyncio.run(_run_push_cleanup_checks(report))
    asyncio.run(_run_cron_checks(report))
    print("=" * 70)
    print(f"  {report.summary()}")
    print("  EXIT " + ("OK" if report.exit_code == 0 else "FAIL"))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
