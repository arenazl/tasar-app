"""Deals — pipeline de VENTAS del CRM unificado (WO F2-02).

CRUD + endpoint dedicado de cambio de etapa para el drag-and-drop del kanban.
Las 6 etapas legales del circuito inmobiliario argentino:

    captado -> publicado -> visita -> reserva -> boleto -> escrituracion

Multi-tenant + scoping por rol (igual que visits):
  - vendedor: ve/gestiona SOLO sus deals (vendor_id == user.id).
  - supervisor|admin: todo el workspace.

Nombres de display resueltos con JOIN en la misma query (sin N+1).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.client import Client
from models.property import Property
from models.deal import Deal
from schemas.deal import DealCreate, DealUpdate, DealOut, DealStageUpdate

router = APIRouter(prefix="/api/deals", tags=["deals"])

# Etapas legales del pipeline de ventas, EN ORDEN.
LEGAL_STAGES = ["captado", "publicado", "visita", "reserva", "boleto", "escrituracion"]
STAGE_SET = set(LEGAL_STAGES)


def _base_query(user: User):
    q = (
        select(Deal, Client.name, Property.title, User.full_name)
        .join(Client, Client.id == Deal.client_id)
        .join(Property, Property.id == Deal.property_id)
        .join(User, User.id == Deal.vendor_id)
        .where(Deal.workspace_id == user.workspace_id)
    )
    if user.role == "vendedor":
        q = q.where(Deal.vendor_id == user.id)
    return q


def _row_to_out(row) -> DealOut:
    deal, client_name, property_title, vendor_name = row
    out = DealOut.model_validate(deal)
    out.client_name = client_name
    out.property_title = property_title
    out.vendor_name = vendor_name
    return out


async def _fetch_one(db: AsyncSession, user: User, deal_id: int) -> DealOut:
    row = (await db.execute(_base_query(user).where(Deal.id == deal_id))).first()
    if not row:
        raise HTTPException(404, "Deal no encontrado")
    return _row_to_out(row)


async def _resolve_vendor_id(db: AsyncSession, user: User, requested: int) -> int:
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


async def _get_editable(db: AsyncSession, user: User, deal_id: int) -> Deal:
    q = select(Deal).where(Deal.id == deal_id, Deal.workspace_id == user.workspace_id)
    if user.role == "vendedor":
        q = q.where(Deal.vendor_id == user.id)
    d = (await db.execute(q)).scalar_one_or_none()
    if not d:
        raise HTTPException(404, "Deal no encontrado")
    return d


@router.get("", response_model=list[DealOut])
async def list_deals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = _base_query(user).order_by(Deal.updated_at.desc())
    rows = (await db.execute(q)).all()
    return [_row_to_out(r) for r in rows]


@router.get("/stages")
async def get_stages():
    """Catalogo de etapas legales EN ORDEN (para armar el kanban en el front)."""
    return {"stages": LEGAL_STAGES}


@router.post("", response_model=DealOut)
async def create_deal(
    payload: DealCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.stage not in STAGE_SET:
        raise HTTPException(400, f"stage invalido: {payload.stage}")
    await _assert_in_workspace(db, user, payload.client_id, payload.property_id)
    vendor_id = await _resolve_vendor_id(db, user, payload.vendor_id)

    d = Deal(
        workspace_id=user.workspace_id,
        client_id=payload.client_id,
        property_id=payload.property_id,
        vendor_id=vendor_id,
        stage=payload.stage,
        negotiated_price=payload.negotiated_price,
        currency=payload.currency,
        estimated_commission=payload.estimated_commission,
        probability_pct=payload.probability_pct,
        estimated_close_date=payload.estimated_close_date,
        notes=payload.notes,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return await _fetch_one(db, user, d.id)


@router.patch("/{deal_id}/stage", response_model=DealOut)
async def move_deal_stage(
    deal_id: int,
    payload: DealStageUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cambio de etapa al soltar la tarjeta en el kanban (drag-and-drop)."""
    if payload.stage not in STAGE_SET:
        raise HTTPException(400, f"stage invalido: {payload.stage}")
    d = await _get_editable(db, user, deal_id)
    d.stage = payload.stage
    await db.commit()
    return await _fetch_one(db, user, d.id)


@router.patch("/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: int,
    payload: DealUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = await _get_editable(db, user, deal_id)
    data = payload.model_dump(exclude_unset=True)

    if "stage" in data and data["stage"] not in STAGE_SET:
        raise HTTPException(400, f"stage invalido: {data['stage']}")
    if "client_id" in data or "property_id" in data:
        await _assert_in_workspace(
            db, user,
            data.get("client_id", d.client_id),
            data.get("property_id", d.property_id),
        )
    if "vendor_id" in data:
        data["vendor_id"] = await _resolve_vendor_id(db, user, data["vendor_id"])

    for k, val in data.items():
        setattr(d, k, val)
    await db.commit()
    return await _fetch_one(db, user, d.id)


@router.delete("/{deal_id}")
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    d = await _get_editable(db, user, deal_id)
    await db.delete(d)
    await db.commit()
    return {"ok": True}
