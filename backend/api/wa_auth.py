"""Endpoints maquina-a-maquina para el wa-gateway (Baileys). NO usan JWT.

Auth: header `X-API-Key` == `settings.WA_GATEWAY_KEY`. Si el secreto no esta
configurado, todo responde 503 (fail-closed).

Dos responsabilidades:
  1. Key-value store del auth-state de Baileys (GET/PUT/DELETE /api/wa-auth/{key}).
     Espejo de AgentFlow/backend/api/baileys_auth.py. Las keys ya vienen
     prefijadas por el gateway con `{workspace_slug}-`.
  2. Bootstrap de tenants (GET /api/wa/tenants): workspaces con canal Baileys
     activo, para que el gateway sepa que sesiones arrancar.

Se montan sin prefix (paths absolutos) porque conviven dos familias de rutas
(`/api/wa-auth/*` y `/api/wa/tenants`) bajo `/api/wa*`.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from core.config import settings
from core.database import get_db
from models.wa_session import WaSession
from models.workspace import Workspace

router = APIRouter(tags=["wa-gateway"])


def _check_api_key(x_api_key: Optional[str]) -> None:
    """Valida el secreto compartido gateway<->suite. Fail-closed si no hay key."""
    if not settings.WA_GATEWAY_KEY:
        raise HTTPException(503, "WA_GATEWAY_KEY no configurada")
    if x_api_key != settings.WA_GATEWAY_KEY:
        raise HTTPException(401, "API key invalida")


# ─── Key-value store del auth-state (Baileys) ──────────────────────────────

class AuthSetPayload(BaseModel):
    value: str


class TenantOut(BaseModel):
    id: int
    slug: str
    name: str


@router.get("/api/wa/tenants", response_model=list[TenantOut])
async def list_tenants(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Workspaces con canal Baileys activo (para el bootstrap del gateway).

    TODO(F2-03): filtrar por el flag/config del bot por workspace cuando exista
    ese modelo. Hoy ese modelo NO existe todavia, asi que devolvemos TODOS los
    workspaces (comportamiento seguro documentado en el WO F0-05).
    """
    _check_api_key(x_api_key)
    rows = (await db.execute(select(Workspace).order_by(Workspace.id))).scalars().all()
    return [TenantOut(id=w.id, slug=w.slug, name=w.name) for w in rows]


@router.get("/api/wa-auth/{key:path}")
async def get_value(
    key: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_api_key(x_api_key)
    row = (await db.execute(
        select(WaSession).where(WaSession.key == key)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Not found")
    return {"key": row.key, "value": row.value}


@router.put("/api/wa-auth/{key:path}")
async def set_value(
    key: str,
    payload: AuthSetPayload,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_api_key(x_api_key)
    row = (await db.execute(
        select(WaSession).where(WaSession.key == key)
    )).scalar_one_or_none()
    if row:
        row.value = payload.value
    else:
        db.add(WaSession(key=key, value=payload.value))
    await db.commit()
    return {"ok": True, "key": key, "size": len(payload.value)}


@router.delete("/api/wa-auth/{key:path}")
async def delete_value(
    key: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    _check_api_key(x_api_key)
    row = (await db.execute(
        select(WaSession).where(WaSession.key == key)
    )).scalar_one_or_none()
    if row:
        await db.delete(row)
        await db.commit()
    return {"ok": True, "key": key}
