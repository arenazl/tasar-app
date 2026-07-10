"""Visits — visitas de clientes a propiedades (WO F2-02).

CRUD del CRM unificado. Multi-tenant + scoping por rol:
  - vendedor: ve/gestiona SOLO sus visitas (vendor_id == user.id).
  - supervisor|admin: ven/gestionan todo el workspace.

Los nombres de display (cliente / propiedad / vendedor) se resuelven con un
JOIN en la MISMA query del listado (una sola consulta, sin N+1). Los modelos
`Visit`/`Client`/`Property`/`User` no declaran relationships, asi que armamos
el JOIN a mano en lugar de selectinload.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.client import Client
from models.property import Property
from models.visit import Visit
from schemas.visit import VisitCreate, VisitUpdate, VisitOut

router = APIRouter(prefix="/api/visits", tags=["visits"])

MANAGER_ROLES = ("admin", "supervisor")
VALID_STATUS = {"agendada", "concretada", "cancelada", "ausente"}


def _base_query(user: User):
    """Listado con JOIN a client/property/vendor para traer los nombres en una
    sola query. El scoping por vendedor se aplica encima."""
    q = (
        select(Visit, Client.name, Property.title, User.full_name)
        .join(Client, Client.id == Visit.client_id)
        .join(Property, Property.id == Visit.property_id)
        .join(User, User.id == Visit.vendor_id)
        .where(Visit.workspace_id == user.workspace_id)
    )
    if user.role == "vendedor":
        q = q.where(Visit.vendor_id == user.id)
    return q


def _row_to_out(row) -> VisitOut:
    visit, client_name, property_title, vendor_name = row
    out = VisitOut.model_validate(visit)
    out.client_name = client_name
    out.property_title = property_title
    out.vendor_name = vendor_name
    return out


async def _fetch_one(db: AsyncSession, user: User, visit_id: int) -> VisitOut:
    row = (await db.execute(_base_query(user).where(Visit.id == visit_id))).first()
    if not row:
        raise HTTPException(404, "Visita no encontrada")
    return _row_to_out(row)


async def _resolve_vendor_id(db: AsyncSession, user: User, requested: int) -> int:
    """El vendedor solo puede agendar para si mismo; el manager para cualquier
    vendedor del workspace."""
    if user.role == "vendedor":
        return user.id
    v = (await db.execute(
        select(User).where(User.id == requested, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(400, "El vendedor no pertenece a tu workspace")
    return requested


async def _assert_in_workspace(db: AsyncSession, user: User, client_id: int, property_id: int) -> None:
    c = (await db.execute(
        select(Client.id).where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    p = (await db.execute(
        select(Property.id).where(Property.id == property_id, Property.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")


@router.get("", response_model=list[VisitOut])
async def list_visits(
    upcoming: bool | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = _base_query(user)
    if upcoming:
        q = q.where(Visit.scheduled_at >= datetime.now(timezone.utc) - timedelta(hours=12))
    q = q.order_by(Visit.scheduled_at.desc())
    rows = (await db.execute(q)).all()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=VisitOut)
async def create_visit(
    payload: VisitCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.status not in VALID_STATUS:
        raise HTTPException(400, f"status invalido: {payload.status}")
    await _assert_in_workspace(db, user, payload.client_id, payload.property_id)
    vendor_id = await _resolve_vendor_id(db, user, payload.vendor_id)

    v = Visit(
        workspace_id=user.workspace_id,
        client_id=payload.client_id,
        property_id=payload.property_id,
        vendor_id=vendor_id,
        scheduled_at=payload.scheduled_at,
        status=payload.status,
        result=payload.result,
        voice_notes=payload.voice_notes,
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)
    return await _fetch_one(db, user, v.id)


async def _get_editable(db: AsyncSession, user: User, visit_id: int) -> Visit:
    """Trae la visita respetando scoping (vendedor solo la suya)."""
    q = select(Visit).where(Visit.id == visit_id, Visit.workspace_id == user.workspace_id)
    if user.role == "vendedor":
        q = q.where(Visit.vendor_id == user.id)
    v = (await db.execute(q)).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Visita no encontrada")
    return v


@router.patch("/{visit_id}", response_model=VisitOut)
async def update_visit(
    visit_id: int,
    payload: VisitUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    v = await _get_editable(db, user, visit_id)
    data = payload.model_dump(exclude_unset=True)

    if "status" in data and data["status"] not in VALID_STATUS:
        raise HTTPException(400, f"status invalido: {data['status']}")
    if "client_id" in data or "property_id" in data:
        await _assert_in_workspace(
            db, user,
            data.get("client_id", v.client_id),
            data.get("property_id", v.property_id),
        )
    if "vendor_id" in data:
        data["vendor_id"] = await _resolve_vendor_id(db, user, data["vendor_id"])

    for k, val in data.items():
        setattr(v, k, val)
    await db.commit()
    return await _fetch_one(db, user, v.id)


@router.delete("/{visit_id}")
async def delete_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    v = await _get_editable(db, user, visit_id)
    await db.delete(v)
    await db.commit()
    return {"ok": True}
