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


@router.get("", response_model=List[ClientOut])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
