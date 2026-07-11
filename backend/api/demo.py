"""Datos de ejemplo del workspace — generar / borrar (WO F5-03).

Paso "cargar datos de ejemplo" del wizard de onboarding + boton "borrar datos
de ejemplo" de Configuracion. Solo administrador+ (mismo criterio que
`api/team.py`: son operaciones que tocan a todo el equipo/cartera del workspace).

El borrado es SIEMPRE dry-run primero (el front llama sin `confirm`, muestra
los counts, y recien si el usuario confirma se reenvia con `confirm=true`) --
protocolo pedido explicitamente por el WO ("dry-run interno + confirm").
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import require_min_role
from models.user import User
from models.workspace import Workspace
from services.demo_service import generate_demo_data, preview_demo_purge, purge_demo_data


router = APIRouter(prefix="/api/demo", tags=["demo"])


class GenerateDemoRequest(BaseModel):
    n_properties: int = Field(default=12, ge=3, le=60)


class PurgeDemoRequest(BaseModel):
    confirm: bool = False


@router.post("/generate")
async def generate_demo(
    body: GenerateDemoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_min_role("administrador")),
):
    """N propiedades + 3 vendedores + DMO asignado + 5 conversaciones, todo
    marcado `is_demo=True` y prefijado "[DEMO]" (regla #11). Idempotente: si
    ya habia demo previo en este workspace, lo reemplaza por un set fresco."""
    ws = (await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))).scalar_one_or_none()
    if not ws:
        raise HTTPException(404, "Workspace no encontrado")
    return await generate_demo_data(db, ws, user, n_properties=body.n_properties)


@router.post("/purge")
async def purge_demo(
    body: PurgeDemoRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_min_role("administrador")),
):
    """Sin `confirm`: dry-run (solo cuenta). Con `confirm=true`: borra SOLO lo
    `is_demo=True` de este workspace; datos reales (incluso mezclados) quedan
    intactos -- ver `services/demo_service.purge_demo_data`."""
    if not body.confirm:
        preview = await preview_demo_purge(db, user.workspace_id)
        return {"dry_run": True, **preview}
    result = await purge_demo_data(db, user.workspace_id)
    return {"dry_run": False, **result}
