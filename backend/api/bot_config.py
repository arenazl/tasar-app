"""Bot-config API (WO F2-03) — configuracion del bot POR WORKSPACE.

Todo scoped al workspace del JWT (anti-cross-tenant). Restringido a admin/supervisor.
El GET auto-crea la fila con los defaults del gate del dueño si no existe, asi la
pantalla funciona sin depender del seed.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user, require_role
from models.user import User
from models.workspace import Workspace
from models.bot_config import (
    WorkspaceBotConfig, BotFaq,
    DEFAULT_WELCOME, DEFAULT_OFF_HOURS, DEFAULT_DERIVATION,
    DEFAULT_DERIVATION_WORDS, DEFAULT_TONE, DEFAULT_BUSINESS_HOURS, DEFAULT_VOICE_MODE,
)


router = APIRouter(prefix="/api/bot-config", tags=["bot-config"])


async def _get_or_create(db: AsyncSession, workspace_id: int) -> WorkspaceBotConfig:
    cfg = (await db.execute(
        select(WorkspaceBotConfig).where(WorkspaceBotConfig.workspace_id == workspace_id)
    )).scalar_one_or_none()
    if cfg:
        return cfg
    ws = (await db.execute(select(Workspace).where(Workspace.id == workspace_id))).scalar_one_or_none()
    cfg = WorkspaceBotConfig(
        workspace_id=workspace_id,
        enabled=False,
        business_name=ws.name if ws else None,
        welcome_message=DEFAULT_WELCOME,
        off_hours_message=DEFAULT_OFF_HOURS,
        derivation_message=DEFAULT_DERIVATION,
        derivation_words=DEFAULT_DERIVATION_WORDS,
        business_hours=DEFAULT_BUSINESS_HOURS,
        tone=DEFAULT_TONE,
        channel_provider="baileys",
        default_voice_mode=DEFAULT_VOICE_MODE,
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


def _cfg_dict(c: WorkspaceBotConfig) -> dict:
    return {
        "id": c.id,
        "workspace_id": c.workspace_id,
        "enabled": c.enabled,
        "business_name": c.business_name,
        "business_description": c.business_description,
        "address": c.address,
        "zones": c.zones,
        "phone": c.phone,
        "email": c.email,
        "website": c.website,
        "services": c.services,
        "commissions_text": c.commissions_text,
        "differentials": c.differentials,
        "welcome_message": c.welcome_message,
        "off_hours_message": c.off_hours_message,
        "derivation_message": c.derivation_message,
        "business_hours": c.business_hours,
        "derivation_words": c.derivation_words,
        "tone": c.tone,
        "channel_provider": c.channel_provider,
        # Audio full-duplex (WO F3-01). voice_id=None -> voz default global.
        "voice_id": c.voice_id,
        "default_voice_mode": c.default_voice_mode,
    }


@router.get("")
async def get_config(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cfg = await _get_or_create(db, user.workspace_id)
    return _cfg_dict(cfg)


class BotConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    business_name: Optional[str] = None
    business_description: Optional[str] = None
    address: Optional[str] = None
    zones: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    services: Optional[str] = None
    commissions_text: Optional[str] = None
    differentials: Optional[str] = None
    welcome_message: Optional[str] = None
    off_hours_message: Optional[str] = None
    derivation_message: Optional[str] = None
    business_hours: Optional[str] = None
    derivation_words: Optional[str] = None
    tone: Optional[str] = None
    voice_id: Optional[str] = None
    default_voice_mode: Optional[str] = None


_VALID_VOICE_MODES = {"off", "auto", "mirror"}


@router.put("")
async def update_config(
    body: BotConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    cfg = await _get_or_create(db, user.workspace_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("default_voice_mode") is not None and data["default_voice_mode"] not in _VALID_VOICE_MODES:
        raise HTTPException(400, "default_voice_mode inválido (off|auto|mirror)")
    for field, value in data.items():
        setattr(cfg, field, value)
    await db.commit()
    await db.refresh(cfg)
    return _cfg_dict(cfg)


# ── FAQs ───────────────────────────────────────────────────────────────────

def _faq_dict(f: BotFaq) -> dict:
    return {
        "id": f.id, "question": f.question, "answer": f.answer,
        "priority": f.priority, "is_active": f.is_active,
    }


@router.get("/faqs")
async def list_faqs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (await db.execute(
        select(BotFaq).where(BotFaq.workspace_id == user.workspace_id)
        .order_by(BotFaq.priority.desc(), BotFaq.id.asc())
    )).scalars().all()
    return [_faq_dict(f) for f in rows]


class FaqBody(BaseModel):
    question: str
    answer: str
    priority: int = 0
    is_active: bool = True


@router.post("/faqs")
async def create_faq(
    body: FaqBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    f = BotFaq(
        workspace_id=user.workspace_id, question=body.question, answer=body.answer,
        priority=body.priority, is_active=body.is_active,
    )
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return _faq_dict(f)


async def _get_faq_scoped(db: AsyncSession, faq_id: int, user: User) -> BotFaq:
    f = (await db.execute(
        select(BotFaq).where(BotFaq.id == faq_id, BotFaq.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not f:
        raise HTTPException(404, "FAQ no encontrada")
    return f


@router.put("/faqs/{faq_id}")
async def update_faq(
    faq_id: int,
    body: FaqBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    f = await _get_faq_scoped(db, faq_id, user)
    f.question = body.question
    f.answer = body.answer
    f.priority = body.priority
    f.is_active = body.is_active
    await db.commit()
    return _faq_dict(f)


@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("admin", "supervisor")),
):
    f = await _get_faq_scoped(db, faq_id, user)
    await db.delete(f)
    await db.commit()
    return {"ok": True}
