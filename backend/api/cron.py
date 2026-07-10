"""Endpoint interno de cron (WO F3-03) -- resumen semanal por email.

Maquina-a-maquina: header `X-Cron-Key` == `settings.CRON_KEY`. El scheduler
externo (Cloud Scheduler / cron de Infra) es quien lo dispara periodicamente
-- ese scheduling en si NO se define aca, solo el endpoint que arma y manda
los emails cuando lo llaman.

Antes de este WO, `email_service.notify_weekly_summary` estaba implementado
pero SIN ningun caller (dead switch en Configuracion -> "Email general").
Este endpoint es el primer y unico caller.

Fail-closed (criterio de aceptacion explicito del WO): sin key o key
invalida -> 403 SIEMPRE, incluso si CRON_KEY no esta configurada en env
(a diferencia del patron 503 de wa_auth.py -- el WO pide 403 puntual aca).
"""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from models.user import User
from models.client import Client
from models.visit import Visit
from models.appraisal import AppraisalSignature

router = APIRouter(prefix="/api/cron", tags=["cron"])


def _check_cron_key(x_cron_key: Optional[str]) -> None:
    if not settings.CRON_KEY or x_cron_key != settings.CRON_KEY:
        raise HTTPException(403, "X-Cron-Key invalida o ausente")


async def _user_kpis(db: AsyncSession, user: User, since: datetime) -> dict:
    """KPIs REALES de los ultimos 7 dias para ESTE usuario (COUNT contra la
    DB -- nada simulado, regla dura de la casa)."""
    leads = (await db.execute(
        select(func.count(Client.id)).where(
            Client.assigned_to == user.id, Client.created_at >= since,
        )
    )).scalar_one()
    visitas = (await db.execute(
        select(func.count(Visit.id)).where(
            Visit.vendor_id == user.id, Visit.created_at >= since,
        )
    )).scalar_one()
    firmadas = (await db.execute(
        select(func.count(AppraisalSignature.id)).where(
            AppraisalSignature.user_id == user.id, AppraisalSignature.signed_at >= since,
        )
    )).scalar_one()
    return {
        "Leads nuevos asignados": leads,
        "Visitas agendadas": visitas,
        "Tasaciones firmadas": firmadas,
    }


@router.post("/weekly-summary")
async def weekly_summary(
    x_cron_key: Optional[str] = Header(None, alias="X-Cron-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Arma y manda el resumen semanal por email a los usuarios de los
    workspaces con el toggle `notify_email` activo.

    El gate del toggle vive en UNA sola capa (`email_service._notify_enabled`,
    ya usado por `notify_weekly_summary`) -- este endpoint la consulta UNA
    vez por workspace (no por usuario, para no repetir la misma query N
    veces) y listo: si el workspace tiene el toggle apagado, se saltea
    entero sin llamar a `notify_weekly_summary` por cada uno de sus users."""
    _check_cron_key(x_cron_key)

    from services.email_service import notify_weekly_summary, _notify_enabled

    since = datetime.now(timezone.utc) - timedelta(days=7)
    users = (await db.execute(
        select(User).where(User.is_active == True)  # noqa: E712
    )).scalars().all()

    by_workspace: dict[int, list[User]] = defaultdict(list)
    for u in users:
        if u.email:
            by_workspace[u.workspace_id].append(u)

    sent = 0
    for workspace_id, ws_users in by_workspace.items():
        if not await _notify_enabled(db, workspace_id, "notify_email"):
            continue
        for user in ws_users:
            kpis = await _user_kpis(db, user, since)
            ok = await notify_weekly_summary(db, workspace_id, user.email, user.full_name, kpis)
            if ok:
                sent += 1

    return {"ok": True, "sent": sent}
