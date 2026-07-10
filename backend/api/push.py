"""Endpoints Web Push (WO F3-03) -- el frontend se suscribe/desuscribe y
puede pedir un push de prueba. Auth JWT normal (get_current_user), scoping
por user_id (cada quien administra sus propias suscripciones).

Portado de AgentFlow (backend/api/push.py), con workspace_id agregado al
alta (consistente con el resto de tablas multi-tenant de la suite).
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel

from core.config import settings
from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.push_subscription import PushSubscription

router = APIRouter(prefix="/api/push", tags=["push"])


@router.get("/vapid-public-key")
async def vapid_public_key():
    """Clave publica VAPID que necesita el frontend para PushManager.subscribe()."""
    return {"public_key": settings.VAPID_PUBLIC_KEY}


class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class SubscribePayload(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


@router.post("/subscribe")
async def subscribe(
    payload: SubscribePayload,
    user_agent: Optional[str] = Header(None, alias="User-Agent"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """El frontend manda aca su PushSubscription cuando el user acepta notifs.
    Idempotente: si el endpoint ya estaba suscripto para este user, solo actualiza."""
    r = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.user_id == user.id,
                PushSubscription.endpoint == payload.endpoint,
            )
        )
    )
    sub = r.scalar_one_or_none()
    if sub:
        sub.p256dh = payload.keys.p256dh
        sub.auth = payload.keys.auth
        sub.user_agent = user_agent
        await db.commit()
        return {"ok": True, "id": sub.id, "updated": True}

    sub = PushSubscription(
        workspace_id=user.workspace_id,
        user_id=user.id,
        endpoint=payload.endpoint,
        p256dh=payload.keys.p256dh,
        auth=payload.keys.auth,
        user_agent=user_agent,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return {"ok": True, "id": sub.id, "created": True}


@router.delete("/subscribe")
async def unsubscribe(
    endpoint: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = await db.execute(
        select(PushSubscription).where(
            and_(
                PushSubscription.user_id == user.id,
                PushSubscription.endpoint == endpoint,
            )
        )
    )
    sub = r.scalar_one_or_none()
    if sub:
        await db.delete(sub)
        await db.commit()
    return {"ok": True}


@router.post("/test")
async def test_push(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Envia una push de prueba al usuario logueado (todas sus suscripciones)."""
    from services.push_notif import notify_user
    await notify_user(
        db, user.id,
        title="Test TasAR",
        body=f"Hola {user.full_name}, las notificaciones funcionan.",
        url="/bandeja",
    )
    await db.commit()  # persiste el cleanup de subs vencidas que haya hecho notify_user
    return {"ok": True}
