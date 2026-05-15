from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import statistics

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.market_study import MarketStudy
from models.collaboration import Collaboration, CollaborationComment
from schemas.collaboration import (
    CollaborationInvite, CollaborationOpinion, CollaborationOut,
    CommentCreate, CommentOut, ConsensusOut,
)


router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


@router.post("/invite", response_model=CollaborationOut)
async def invite(
    body: CollaborationInvite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ms = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == body.market_study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    target = (await db.execute(
        select(User).where(User.id == body.user_id, User.workspace_id == user.workspace_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Usuario inexistente")

    existing = (await db.execute(
        select(Collaboration).where(
            Collaboration.market_study_id == body.market_study_id,
            Collaboration.user_id == body.user_id,
        )
    )).scalar_one_or_none()
    if existing:
        return CollaborationOut.model_validate(existing)

    col = Collaboration(
        market_study_id=body.market_study_id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(col)
    await db.commit()
    await db.refresh(col)
    return CollaborationOut.model_validate(col)


@router.post("/{study_id}/opinion", response_model=CollaborationOut)
async def submit_opinion(
    study_id: int,
    body: CollaborationOpinion,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    col = (await db.execute(
        select(Collaboration).where(
            Collaboration.market_study_id == study_id,
            Collaboration.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not col:
        col = Collaboration(
            market_study_id=study_id, user_id=user.id, role="contributor",
        )
        db.add(col)
        await db.flush()

    col.opinion_value = body.opinion_value
    col.opinion_note = body.opinion_note
    await db.commit()
    await db.refresh(col)
    return CollaborationOut.model_validate(col)


@router.get("/{study_id}/consensus", response_model=ConsensusOut)
async def get_consensus(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cols = (await db.execute(
        select(Collaboration).where(Collaboration.market_study_id == study_id)
    )).scalars().all()
    opinions = [c.opinion_value for c in cols if c.opinion_value is not None]

    avg = min_v = max_v = std = agree = None
    if opinions:
        avg = sum(opinions) / len(opinions)
        min_v = min(opinions)
        max_v = max(opinions)
        std = statistics.pstdev(opinions) if len(opinions) > 1 else 0.0
        # agreement = 1 - coef. variación (clipped)
        if avg:
            cv = std / avg
            agree = round(max(0.0, min(1.0, 1 - cv)), 3)

    return ConsensusOut(
        market_study_id=study_id,
        participants=len(cols),
        avg_value=avg, min_value=min_v, max_value=max_v, std_dev=std,
        agreement_score=agree,
        opinions=[CollaborationOut.model_validate(c) for c in cols],
    )


@router.post("/{study_id}/comments", response_model=CommentOut)
async def add_comment(
    study_id: int,
    body: CommentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    c = CollaborationComment(
        market_study_id=study_id,
        user_id=user.id,
        parent_id=body.parent_id,
        body=body.body,
        anchor=body.anchor,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)

    # Notificar a colaboradores del estudio (no al autor)
    try:
        from services.email_service import notify_comment
        from models.collaboration import Collaboration
        from models.market_study import MarketStudy

        study = (await db.execute(select(MarketStudy).where(MarketStudy.id == study_id))).scalar_one_or_none()
        if study:
            study_code = f"ACM-{study.id:04d}"
            collabs = (await db.execute(
                select(Collaboration).where(Collaboration.market_study_id == study_id)
            )).scalars().all()
            collab_user_ids = {x.user_id for x in collabs if x.user_id and x.user_id != user.id}
            if collab_user_ids:
                recipients = (await db.execute(
                    select(User).where(User.id.in_(collab_user_ids))
                )).scalars().all()
                snippet = (body.body or "")[:280]
                for r in recipients:
                    if r.email:
                        await notify_comment(db, user.workspace_id, r.email, user.full_name or user.email, study_code, snippet)
    except Exception as e:
        print(f"[email] notify_comment fallo: {e}")

    return CommentOut.model_validate(c)


@router.get("/{study_id}/comments", response_model=List[CommentOut])
async def list_comments(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(CollaborationComment).where(CollaborationComment.market_study_id == study_id)
        .order_by(CollaborationComment.created_at.asc())
    )
    return [CommentOut.model_validate(c) for c in res.scalars().all()]
