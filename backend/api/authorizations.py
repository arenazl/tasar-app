"""Authorizations — autorizaciones de venta firmadas (WO F2-02).

CRUD del CRM unificado. Multi-tenant + scoping por rol:
  - vendedor: ve/gestiona SOLO las que captó (captador_id == user.id).
  - supervisor|admin: todo el workspace.

Nombre de propiedad + captador resueltos con JOIN en la misma query (sin N+1).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.authorization import Authorization
from schemas.authorization import AuthorizationCreate, AuthorizationUpdate, AuthorizationOut

router = APIRouter(prefix="/api/authorizations", tags=["authorizations"])

VALID_STATUS = {"activa", "vencida", "ejecutada", "cancelada"}


def _base_query(user: User):
    q = (
        select(Authorization, Property.title, User.full_name)
        .join(Property, Property.id == Authorization.property_id)
        .join(User, User.id == Authorization.captador_id)
        .where(Authorization.workspace_id == user.workspace_id)
    )
    if user.role == "vendedor":
        q = q.where(Authorization.captador_id == user.id)
    return q


def _row_to_out(row) -> AuthorizationOut:
    auth, property_title, captador_name = row
    out = AuthorizationOut.model_validate(auth)
    out.property_title = property_title
    out.captador_name = captador_name
    return out


async def _fetch_one(db: AsyncSession, user: User, auth_id: int) -> AuthorizationOut:
    row = (await db.execute(_base_query(user).where(Authorization.id == auth_id))).first()
    if not row:
        raise HTTPException(404, "Autorizacion no encontrada")
    return _row_to_out(row)


async def _resolve_captador_id(db: AsyncSession, user: User, requested: int) -> int:
    if user.role == "vendedor":
        return user.id
    v = (await db.execute(
        select(User).where(User.id == requested, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(400, "El captador no pertenece a tu workspace")
    return requested


async def _assert_property(db: AsyncSession, user: User, property_id: int) -> None:
    p = (await db.execute(
        select(Property.id).where(Property.id == property_id, Property.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "Propiedad no encontrada")


async def _get_editable(db: AsyncSession, user: User, auth_id: int) -> Authorization:
    q = select(Authorization).where(
        Authorization.id == auth_id, Authorization.workspace_id == user.workspace_id
    )
    if user.role == "vendedor":
        q = q.where(Authorization.captador_id == user.id)
    a = (await db.execute(q)).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Autorizacion no encontrada")
    return a


@router.get("", response_model=list[AuthorizationOut])
async def list_authorizations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = _base_query(user).order_by(Authorization.signed_date.desc())
    rows = (await db.execute(q)).all()
    return [_row_to_out(r) for r in rows]


@router.post("", response_model=AuthorizationOut)
async def create_authorization(
    payload: AuthorizationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.status not in VALID_STATUS:
        raise HTTPException(400, f"status invalido: {payload.status}")
    await _assert_property(db, user, payload.property_id)
    captador_id = await _resolve_captador_id(db, user, payload.captador_id)

    a = Authorization(
        workspace_id=user.workspace_id,
        property_id=payload.property_id,
        captador_id=captador_id,
        signed_date=payload.signed_date,
        expiry_date=payload.expiry_date,
        min_price=payload.min_price,
        currency=payload.currency,
        commission_pct=payload.commission_pct,
        exclusivity=payload.exclusivity,
        pdf_url=payload.pdf_url,
        notes=payload.notes,
        status=payload.status,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return await _fetch_one(db, user, a.id)


@router.patch("/{auth_id}", response_model=AuthorizationOut)
async def update_authorization(
    auth_id: int,
    payload: AuthorizationUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = await _get_editable(db, user, auth_id)
    data = payload.model_dump(exclude_unset=True)

    if "status" in data and data["status"] not in VALID_STATUS:
        raise HTTPException(400, f"status invalido: {data['status']}")
    if "property_id" in data:
        await _assert_property(db, user, data["property_id"])
    if "captador_id" in data:
        data["captador_id"] = await _resolve_captador_id(db, user, data["captador_id"])

    for k, val in data.items():
        setattr(a, k, val)
    await db.commit()
    return await _fetch_one(db, user, a.id)


@router.delete("/{auth_id}")
async def delete_authorization(
    auth_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = await _get_editable(db, user, auth_id)
    await db.delete(a)
    await db.commit()
    return {"ok": True}
