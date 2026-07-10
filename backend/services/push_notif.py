"""Servicio de Web Push notifications via VAPID (WO F3-03).

Portado de AgentFlow (backend/services/push_notif.py). Contrato de
transaccion IGUAL al de `inbox_service.notify` y `email_service.send_email`
(patron de la casa): `notify_user` puede hacer `db.delete(...)` sobre subs
vencidas pero **NO commitea** -- si se llama dentro de una transaccion en
curso (ej. `bot_tools._emit_inbox_event`), se persiste con el commit del
caller. Cada llamada esta pensada para envolverse en `try/except` (un fallo
del push NUNCA debe romper el flujo de negocio).
"""
import asyncio
import json
from typing import Optional
from datetime import datetime, timezone

from pywebpush import webpush, WebPushException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models.push_subscription import PushSubscription


def _vapid_claims() -> dict:
    return {"sub": settings.VAPID_SUBJECT}


def _configured() -> bool:
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY)


def _send_one(sub: PushSubscription, payload: dict) -> bool:
    """Envia una push a UN endpoint. Devuelve True si OK, False si fallo
    (incluye 404/410 = subscripcion vencida, y cualquier otro error)."""
    try:
        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=_vapid_claims(),
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        print(f"[push] error {status} a sub {sub.id}: {e}")
        return False
    except Exception as e:  # noqa: BLE001 — cualquier fallo de red/lib no debe romper el caller
        print(f"[push] error inesperado a sub {sub.id}: {e}")
        return False


async def notify_user(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    url: str = "/bandeja",
    tag: Optional[str] = None,
) -> None:
    """Envia una notificacion push a TODAS las suscripciones del usuario.

    Best-effort: si VAPID no esta configurada, no-op (mismo patron que SMTP
    en email_service). Las suscripciones que fallan el envio (404/410 = Gone,
    o cualquier otro error del push service) se eliminan -- el navegador ya
    no las honra, reintentarlas indefinidamente solo acumula basura. NO
    commitea (ver contrato en el docstring del modulo)."""
    if not _configured():
        print("[push] VAPID no configurada, skip")
        return

    r = await db.execute(select(PushSubscription).where(PushSubscription.user_id == user_id))
    subs = r.scalars().all()
    if not subs:
        return

    payload = {
        "title": title,
        "body": body,
        "url": url,
        "tag": tag or f"tasar-{int(datetime.now(timezone.utc).timestamp())}",
    }

    stale_ids = []
    for sub in subs:
        # pywebpush es sync (requests + crypto) -- correrlo en thread pool
        # para no bloquear el event loop async.
        ok = await asyncio.get_event_loop().run_in_executor(None, _send_one, sub, payload)
        if ok:
            sub.last_used_at = datetime.now(timezone.utc)
        else:
            stale_ids.append(sub.id)

    for sub in subs:
        if sub.id in stale_ids:
            await db.delete(sub)

    if stale_ids:
        print(f"[push] {len(stale_ids)} suscripciones vencidas del user {user_id} marcadas para borrar")
