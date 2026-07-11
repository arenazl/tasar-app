"""Coaches — catalogo GLOBAL de metodologias DMO (WO F2-01).

Portado de `AgentFlow/backend/api/coaches.py`. Los coaches son un catalogo
compartido por todos los tenants (sin workspace_id). Solo coordinador+ gestiona
(herramienta comercial de manager); cualquier usuario autenticado puede listarlos.

Vocabulario de roles: jerarquia del rubro (broker>administrador>coordinador>asesor),
ver core.security.ROLE_HIERARCHY (WO F6-06).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from core.security import get_current_user, has_min_role
from models.user import User
from models.dmo import Coach, DmoTemplate
from schemas.dmo import CoachCreate, CoachUpdate, CoachOut

router = APIRouter(prefix="/api/coaches", tags=["coaches"])


def _require_manager(user: User) -> None:
    if not has_min_role(user, "coordinador"):
        raise HTTPException(status_code=403, detail="Solo coordinador o superior puede modificar coaches")


@router.get("", response_model=list[CoachOut])
async def list_coaches(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = await db.execute(
        select(Coach, func.count(DmoTemplate.id))
        .outerjoin(DmoTemplate, DmoTemplate.coach_id == Coach.id)
        .group_by(Coach.id)
        .order_by(Coach.is_official.desc(), Coach.name)
    )
    out = []
    for coach, cnt in rows.all():
        item = CoachOut.model_validate(coach)
        item.templates_count = cnt or 0
        out.append(item)
    return out


@router.post("", response_model=CoachOut)
async def create_coach(
    payload: CoachCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    c = Coach(**payload.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CoachOut.model_validate(c)


@router.patch("/{coach_id}", response_model=CoachOut)
async def update_coach(
    coach_id: int,
    payload: CoachUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    c = (await db.execute(select(Coach).where(Coach.id == coach_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Coach no encontrado")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return CoachOut.model_validate(c)


@router.delete("/{coach_id}")
async def delete_coach(
    coach_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_manager(user)
    c = (await db.execute(select(Coach).where(Coach.id == coach_id))).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Coach no encontrado")
    if c.is_official:
        raise HTTPException(400, "No se puede eliminar un coach oficial")
    await db.delete(c)
    await db.commit()
    return {"ok": True}
