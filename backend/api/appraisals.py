from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
import hashlib
import io

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_study import MarketStudy, Comparable
from models.appraisal import Appraisal, AppraisalSignature
from schemas.appraisal import AppraisalCreate, AppraisalOut, AppraisalSignatureOut
from services.pdf_service import generate_appraisal_pdf
from services.cloudinary_service import upload_image


router = APIRouter(prefix="/api/appraisals", tags=["appraisals"])


async def _serialize(db: AsyncSession, a: Appraisal) -> AppraisalOut:
    sig_res = await db.execute(
        select(AppraisalSignature).where(AppraisalSignature.appraisal_id == a.id)
    )
    out = AppraisalOut.model_validate(a)
    out.signatures = [AppraisalSignatureOut.model_validate(s) for s in sig_res.scalars().all()]
    return out


@router.get("", response_model=List[AppraisalOut])
async def list_appraisals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Appraisal).where(Appraisal.workspace_id == user.workspace_id)
        .order_by(Appraisal.created_at.desc())
    )
    return [await _serialize(db, a) for a in res.scalars().all()]


@router.post("", response_model=AppraisalOut)
async def create_appraisal(
    body: AppraisalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Property).where(
            Property.id == body.property_id,
            Property.workspace_id == user.workspace_id,
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(404, "Propiedad inexistente")

    # Filtrar keys que ya no existen en el modelo refactorizado
    payload = body.model_dump(exclude={"market_study_id"})
    a = Appraisal(
        workspace_id=user.workspace_id,
        created_by=user.id,
        **payload,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return await _serialize(db, a)


@router.post("/{appraisal_id}/sign", response_model=AppraisalSignatureOut)
async def sign_appraisal(
    appraisal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Appraisal).where(
            Appraisal.id == appraisal_id,
            Appraisal.workspace_id == user.workspace_id,
        )
    )
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Tasación no encontrada")

    payload = f"{a.id}|{user.id}|{a.final_value}|{datetime.utcnow().isoformat()}"
    sig_hash = hashlib.sha256(payload.encode()).hexdigest()

    sig = AppraisalSignature(
        appraisal_id=a.id,
        user_id=user.id,
        signature_hash=sig_hash,
    )
    db.add(sig)
    a.status = "signed"
    await db.commit()
    await db.refresh(sig)

    # Notificacion email (no-op si SMTP/toggle off, no bloquea respuesta)
    try:
        from services.email_service import notify_appraisal_signed
        if a.client_email:
            await notify_appraisal_signed(
                db, user.workspace_id, a.client_email,
                a.id, a.client_name or "", float(a.final_value or 0), a.currency or "USD",
            )
    except Exception as e:
        print(f"[email] notify_appraisal_signed fallo: {e}")

    return AppraisalSignatureOut.model_validate(sig)


@router.get("/{appraisal_id}/pdf")
async def generate_pdf(
    appraisal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(Appraisal).where(
            Appraisal.id == appraisal_id,
            Appraisal.workspace_id == user.workspace_id,
        )
    )
    a = res.scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Tasación no encontrada")

    prop = (await db.execute(select(Property).where(Property.id == a.property_id))).scalar_one()
    ms = None
    comps_data = None
    if a.market_study_id:
        ms = (await db.execute(select(MarketStudy).where(MarketStudy.id == a.market_study_id))).scalar_one_or_none()
        if ms:
            comps = (await db.execute(
                select(Comparable).where(Comparable.market_study_id == ms.id)
            )).scalars().all()
            comps_data = [{
                "title": c.title, "total_area_m2": c.total_area_m2,
                "price": c.price, "currency": c.currency,
                "adjusted_price_per_m2": c.adjusted_price_per_m2,
                "weight": c.weight,
            } for c in comps]

    pdf_bytes = generate_appraisal_pdf(
        appraisal={
            "final_value": a.final_value, "currency": a.currency,
            "methodology": a.methodology, "observations": a.observations,
        },
        property_={
            "title": prop.title, "property_type": prop.property_type,
            "address": prop.address, "city": prop.city, "province": prop.province,
            "total_area_m2": prop.total_area_m2,
            "covered_area_m2": prop.covered_area_m2,
            "rooms": prop.rooms, "age_years": prop.age_years,
            "condition": prop.condition,
        },
        market_study={
            "suggested_value_min": ms.suggested_value_min,
            "suggested_value_max": ms.suggested_value_max,
            "confidence_score": ms.confidence_score,
        } if ms else None,
        comparables=comps_data,
        signer={"full_name": user.full_name, "license_number": user.license_number},
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tasacion-{a.id}.pdf"'},
    )
