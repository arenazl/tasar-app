from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from datetime import datetime
import hashlib
import io

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_listing import MarketListing
from models.appraisal import Appraisal, AppraisalSignature, AppraisalComparable
from schemas.appraisal import AppraisalCreate, AppraisalOut, AppraisalSignatureOut
from services.pdf_service import generate_appraisal_pdf
from services.cloudinary_service import upload_image
from services.comparable_ai_service import (
    market_listing_candidates, compute_market_comparable_link,
)
from services.acm_service import compute_market_study


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

    # Filtrar keys del schema que ya no existen como columna en el modelo
    # refactorizado (ej. campos legacy tipo el viejo link a market_study).
    payload = {k: v for k, v in body.model_dump().items() if hasattr(Appraisal, k)}
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
    # La firma NO es un status del workflow (vive en appraisal_signatures).
    # Si estaba en revisión, firmar la aprueba; en cualquier otro estado
    # el status vigente se mantiene sin inventar valores fuera del enum.
    if a.status == "en_revision":
        a.status = "aprobada"

    # Evento de Bandeja: tasación firmada (workspace-wide, best-effort). Se agrega en
    # la MISMA transacción que la firma (inbox_service.notify no commitea).
    try:
        from services import inbox_service
        await inbox_service.appraisal_signed(
            db, workspace_id=user.workspace_id, appraisal_id=a.id,
            signer_name=user.full_name, client_name=a.client_name,
        )
    except Exception as e:
        print(f"[inbox] appraisal_signed event fallo: {e}")

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


@router.get("/{appraisal_id}", response_model=AppraisalOut)
async def get_appraisal(
    appraisal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = (await db.execute(
        select(Appraisal).where(
            Appraisal.id == appraisal_id,
            Appraisal.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Tasación no encontrada")
    return await _serialize(db, a)


@router.get("/{appraisal_id}/comparables")
async def list_appraisal_comparables(
    appraisal_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve los comparables (market_listings) vinculados a la tasación
    via appraisal_comparables. Lista vacía si todavía no se linkeó ninguno."""
    a = (await db.execute(
        select(Appraisal).where(
            Appraisal.id == appraisal_id,
            Appraisal.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Tasación no encontrada")

    rows = (await db.execute(
        select(AppraisalComparable, MarketListing)
        .join(MarketListing, AppraisalComparable.market_listing_id == MarketListing.id)
        .where(AppraisalComparable.appraisal_id == appraisal_id)
    )).all()
    return [{
        "address": listing.address or listing.title,
        "total_area_m2": listing.total_area_m2,
        "rooms": listing.rooms,
        "price": listing.price,
        "currency": listing.currency,
        "price_per_m2": ac.adjusted_price_per_m2 or listing.price_per_m2,
        "distance_m": ac.distance_m,
        "days_on_market": listing.days_on_market,
        "match_score": ac.match_score,
    } for ac, listing in rows]


@router.post("/{appraisal_id}/generate-comparables")
async def generate_appraisal_comparables(
    appraisal_id: int,
    limit: int = 8,
    replace: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Conecta el motor ACM ↔ market_listings para una TASACIÓN.

    Toma la propiedad objetivo de la tasación, busca comparables en el catálogo
    GLOBAL market_listings (tipo + ciudad/barrio + haversine si hay coords),
    homogeneiza precio/m² con ajustes determinísticos y PERSISTE los links en
    appraisal_comparables (market_listing_id, match_score, distance_m,
    adjusted_price_per_m2, adjustments_json, weight). Además refresca el análisis
    embebido de la tasación (suggested_value_*, confidence, comparables_count).

    Es el punto de entrada del poblado de appraisal_comparables que después lee
    GET /api/appraisals/{id}/comparables.
    """
    a = (await db.execute(
        select(Appraisal).where(
            Appraisal.id == appraisal_id,
            Appraisal.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(404, "Tasación no encontrada")

    prop = (await db.execute(
        select(Property).where(Property.id == a.property_id)
    )).scalar_one_or_none()
    if not prop:
        raise HTTPException(404, "Propiedad de la tasación inexistente")

    scored = await market_listing_candidates(db, prop, limit=limit)

    if replace:
        await db.execute(
            delete(AppraisalComparable).where(AppraisalComparable.appraisal_id == a.id)
        )

    comps_payload = []
    created = 0
    for listing, distance_m, match in scored:
        link = compute_market_comparable_link(prop, listing, distance_m, match)
        adjustments = link.pop("adjustments")  # lista (para el cálculo ACM)
        db.add(AppraisalComparable(appraisal_id=a.id, status="included", **link))
        created += 1
        comps_payload.append({
            "id": listing.id,
            "price": listing.price,
            "total_area_m2": listing.total_area_m2,
            "covered_area_m2": listing.covered_area_m2,
            "rooms": listing.rooms,
            "age_years": listing.age_years,
            "adjustments": adjustments,
        })

    # Refrescar análisis embebido con el motor ACM (media ponderada homogeneizada)
    target = {
        "total_area_m2": prop.total_area_m2,
        "covered_area_m2": prop.covered_area_m2,
        "rooms": prop.rooms,
        "age_years": prop.age_years,
    }
    study = compute_market_study(target, comps_payload)
    a.suggested_value_min = study["suggested_value_min"]
    a.suggested_value_max = study["suggested_value_max"]
    a.suggested_value_mode = study["suggested_value_mode"]
    a.confidence_score = study["confidence_score"]
    a.comparables_count = created
    a.last_analyzed_at = datetime.utcnow()

    await db.commit()

    return {
        "appraisal_id": a.id,
        "comparables_created": created,
        "suggested_value_min": a.suggested_value_min,
        "suggested_value_max": a.suggested_value_max,
        "suggested_value_mode": a.suggested_value_mode,
        "confidence_score": a.confidence_score,
    }


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

    # El análisis (antes "market_study" aparte) ahora está embebido en la propia tasación.
    market_study_data = None
    if a.suggested_value_min is not None or a.suggested_value_max is not None:
        market_study_data = {
            "suggested_value_min": a.suggested_value_min,
            "suggested_value_max": a.suggested_value_max,
            "confidence_score": a.confidence_score,
        }

    comps_rows = (await db.execute(
        select(AppraisalComparable, MarketListing)
        .join(MarketListing, AppraisalComparable.market_listing_id == MarketListing.id)
        .where(AppraisalComparable.appraisal_id == a.id)
    )).all()
    comps_data = [{
        "title": listing.title, "total_area_m2": listing.total_area_m2,
        "price": listing.price, "currency": listing.currency,
        "adjusted_price_per_m2": ac.adjusted_price_per_m2 or listing.price_per_m2,
        "weight": ac.weight,
    } for ac, listing in comps_rows] or None

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
        market_study=market_study_data,
        comparables=comps_data,
        signer={"full_name": user.full_name, "license_number": user.license_number},
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tasacion-{a.id}.pdf"'},
    )
