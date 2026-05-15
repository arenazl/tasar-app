"""CRUD de clientes del workspace."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.client import Client
from models.appraisal import Appraisal


router = APIRouter(prefix="/api/clients", tags=["clients"])


class ClientIn(BaseModel):
    name: str
    type: str = "particular"
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    notes: Optional[str] = None


class ClientOut(ClientIn):
    id: int
    appraisals_count: int = 0

    class Config:
        from_attributes = True


def _type_from_name(name: str) -> str:
    n = (name or "").lower()
    if "banco" in n:
        return "banco"
    if "fondo" in n:
        return "fondo"
    if "estudio" in n or "aldao" in n:
        return "estudio"
    if "remax" in n or "argencapital" in n or "atlas" in n or "inmobiliaria" in n:
        return "inmobiliaria"
    return "particular"


async def _autoseed_from_appraisals(db: AsyncSession, workspace_id: int) -> int:
    """Si el workspace tiene appraisals pero la tabla clients esta vacia,
    crea clientes derivados del client_name unico de las appraisals."""
    rows = (await db.execute(
        select(Appraisal.client_name, Appraisal.client_email)
        .where(Appraisal.workspace_id == workspace_id, Appraisal.client_name.isnot(None))
        .distinct()
    )).all()
    created = 0
    for name, email in rows:
        if not name:
            continue
        c = Client(
            workspace_id=workspace_id,
            name=name,
            type=_type_from_name(name),
            email=email,
        )
        db.add(c)
        created += 1
    if created:
        await db.commit()
    return created


@router.get("", response_model=List[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Client).where(Client.workspace_id == user.workspace_id).order_by(Client.name)
    )).scalars().all()

    # Auto-seed: si la tabla esta vacia pero el workspace tiene appraisals con
    # client_name, creamos los clientes derivados. Sucede una sola vez.
    if not rows:
        created = await _autoseed_from_appraisals(db, user.workspace_id)
        if created:
            rows = (await db.execute(
                select(Client).where(Client.workspace_id == user.workspace_id).order_by(Client.name)
            )).scalars().all()

    # Conteo de tasaciones por client_name (legacy: appraisals tienen client_name string)
    name_counts: dict = {}
    counts_q = await db.execute(
        select(Appraisal.client_name, func.count(Appraisal.id))
        .where(Appraisal.workspace_id == user.workspace_id)
        .group_by(Appraisal.client_name)
    )
    for name, cnt in counts_q.all():
        if name:
            name_counts[name] = cnt

    out = []
    for c in rows:
        d = ClientOut.model_validate(c).model_dump()
        d["appraisals_count"] = name_counts.get(c.name, 0)
        out.append(ClientOut(**d))
    return out


@router.post("", response_model=ClientOut)
async def create_client(
    body: ClientIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = Client(workspace_id=user.workspace_id, **body.model_dump())
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ClientOut.model_validate(c)


@router.put("/{client_id}", response_model=ClientOut)
async def update_client(
    client_id: int,
    body: ClientIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = (await db.execute(
        select(Client).where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    for k, v in body.model_dump().items():
        setattr(c, k, v)
    await db.commit()
    await db.refresh(c)
    return ClientOut.model_validate(c)


@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = (await db.execute(
        select(Client).where(Client.id == client_id, Client.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Cliente no encontrado")
    await db.delete(c)
    await db.commit()
    return {"ok": True}
