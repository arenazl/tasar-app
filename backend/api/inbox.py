"""Bandeja (Inbox) endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.inbox import InboxMessage


router = APIRouter(prefix="/api/inbox", tags=["inbox"])


class InboxItem(BaseModel):
    id: int
    kind: str
    sender_type: str
    sender_name: Optional[str]
    sender_subtitle: Optional[str]
    avatar_color: Optional[str]
    subject: str
    preview: Optional[str]
    body: Optional[str] = None
    is_read: bool
    is_assigned_to_me: bool
    priority: str
    created_at: datetime
    related_appraisal_id: Optional[int] = None
    related_url: Optional[str] = None

    class Config:
        from_attributes = True


class InboxListResponse(BaseModel):
    items: List[InboxItem]
    total: int
    unread: int
    assigned_to_me: int


@router.get("", response_model=InboxListResponse)
async def list_inbox(
    filter: str = "all",  # all | unread | assigned
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    base = select(InboxMessage).where(InboxMessage.workspace_id == user.workspace_id)
    if filter == "unread":
        base = base.where(InboxMessage.is_read == False)
    elif filter == "assigned":
        base = base.where(InboxMessage.is_assigned_to_me == True)
    items = (await db.execute(base.order_by(InboxMessage.created_at.desc()))).scalars().all()

    total = (await db.execute(
        select(func.count()).select_from(InboxMessage)
        .where(InboxMessage.workspace_id == user.workspace_id)
    )).scalar() or 0
    unread = (await db.execute(
        select(func.count()).select_from(InboxMessage)
        .where(InboxMessage.workspace_id == user.workspace_id, InboxMessage.is_read == False)
    )).scalar() or 0
    assigned = (await db.execute(
        select(func.count()).select_from(InboxMessage)
        .where(InboxMessage.workspace_id == user.workspace_id, InboxMessage.is_assigned_to_me == True)
    )).scalar() or 0

    return InboxListResponse(
        items=[InboxItem.model_validate(i) for i in items],
        total=total, unread=unread, assigned_to_me=assigned,
    )


@router.get("/{msg_id}", response_model=InboxItem)
async def get_inbox_msg(
    msg_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = (await db.execute(
        select(InboxMessage).where(
            InboxMessage.id == msg_id,
            InboxMessage.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404, "Mensaje no encontrado")
    return InboxItem.model_validate(m)


@router.post("/{msg_id}/read")
async def mark_read(
    msg_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    m = (await db.execute(
        select(InboxMessage).where(
            InboxMessage.id == msg_id,
            InboxMessage.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not m:
        raise HTTPException(404)
    if not m.is_read:
        m.is_read = True
        m.read_at = datetime.utcnow()
        await db.commit()
    return {"ok": True, "is_read": True}


@router.post("/read-all")
async def read_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await db.execute(
        update(InboxMessage)
        .where(InboxMessage.workspace_id == user.workspace_id, InboxMessage.is_read == False)
        .values(is_read=True, read_at=datetime.utcnow())
    )
    await db.commit()
    return {"ok": True}
