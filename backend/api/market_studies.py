from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_study import MarketStudy, Comparable, Adjustment
from models.external_listing import ExternalListing
from schemas.market_study import (
    MarketStudyCreate, MarketStudyOut, ComparableCreate, ComparableOut, AdjustmentOut
)
from services.acm_service import compute_market_study
from services.comparable_ai_service import suggest_comparables


router = APIRouter(prefix="/api/market-studies", tags=["market-studies"])


async def _serialize(db: AsyncSession, ms: MarketStudy) -> MarketStudyOut:
    comps_res = await db.execute(
        select(Comparable).where(Comparable.market_study_id == ms.id)
    )
    comps = comps_res.scalars().all()
    comp_outs = []
    for c in comps:
        adj_res = await db.execute(
            select(Adjustment).where(Adjustment.comparable_id == c.id)
        )
        adjs = [AdjustmentOut.model_validate(a) for a in adj_res.scalars().all()]
        co = ComparableOut.model_validate(c)
        co.adjustments = adjs
        comp_outs.append(co)
    out = MarketStudyOut.model_validate(ms)
    out.comparables = comp_outs
    return out


async def _recalc_in_place(db: AsyncSession, ms: MarketStudy) -> None:
    """Recalcula el estudio y actualiza ms + comparables (sin commit)."""
    prop = (await db.execute(select(Property).where(Property.id == ms.property_id))).scalar_one()
    comps = (await db.execute(
        select(Comparable).where(Comparable.market_study_id == ms.id)
    )).scalars().all()

    comp_payload = []
    for c in comps:
        adj_res = await db.execute(select(Adjustment).where(Adjustment.comparable_id == c.id))
        adjs = [{"coefficient": a.coefficient, "factor": a.factor} for a in adj_res.scalars().all()]
        comp_payload.append({
            "id": c.id, "price": c.price,
            "total_area_m2": c.total_area_m2, "covered_area_m2": c.covered_area_m2,
            "rooms": c.rooms, "age_years": c.age_years,
            "adjustments": adjs,
        })

    target = {
        "total_area_m2": prop.total_area_m2,
        "covered_area_m2": prop.covered_area_m2,
        "rooms": prop.rooms,
        "age_years": prop.age_years,
    }
    result = compute_market_study(target, comp_payload)

    ms.suggested_value_min = result["suggested_value_min"]
    ms.suggested_value_max = result["suggested_value_max"]
    ms.suggested_value_mode = result["suggested_value_mode"]
    ms.confidence_score = result["confidence_score"]

    by_id = {c.id: c for c in comps}
    for r in result["comparable_results"]:
        c = by_id.get(r["id"])
        if c:
            c.adjusted_price = r["adjusted_price"]
            c.adjusted_price_per_m2 = r["adjusted_price_per_m2"]
            c.weight = r["weight"]


@router.get("", response_model=List[MarketStudyOut])
async def list_market_studies(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MarketStudy).where(MarketStudy.workspace_id == user.workspace_id)
        .order_by(MarketStudy.created_at.desc())
    )
    items = res.scalars().all()
    return [await _serialize(db, m) for m in items]


@router.get("/{study_id}", response_model=MarketStudyOut)
async def get_market_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )
    ms = res.scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")
    return await _serialize(db, ms)


@router.post("", response_model=MarketStudyOut)
async def create_market_study(
    body: MarketStudyCreate,
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

    ms = MarketStudy(
        workspace_id=user.workspace_id,
        property_id=body.property_id,
        created_by=user.id,
        method=body.method,
        notes=body.notes,
        status="draft",
    )
    db.add(ms)
    await db.commit()
    await db.refresh(ms)
    return await _serialize(db, ms)


@router.post("/{study_id}/comparables", response_model=MarketStudyOut)
async def add_comparable(
    study_id: int,
    body: ComparableCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agrega comparable manual y auto-recalcula. Devuelve el estudio entero."""
    res = await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )
    ms = res.scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    data = body.model_dump(exclude={"adjustments"})
    if data.get("price") and (data.get("total_area_m2") or data.get("covered_area_m2")):
        area = data.get("total_area_m2") or data.get("covered_area_m2")
        data["price_per_m2"] = round(data["price"] / area, 2)

    c = Comparable(market_study_id=study_id, source_type="manual", **data)
    db.add(c)
    await db.flush()

    for adj in body.adjustments:
        db.add(Adjustment(comparable_id=c.id, **adj.model_dump()))

    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms)
    return await _serialize(db, ms)


@router.delete("/{study_id}/comparables/{comp_id}", response_model=MarketStudyOut)
async def delete_comparable(
    study_id: int,
    comp_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Elimina comparable y auto-recalcula."""
    ms = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    c = (await db.execute(
        select(Comparable).where(
            Comparable.id == comp_id,
            Comparable.market_study_id == study_id,
        )
    )).scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Comparable no encontrado")

    # Borrar ajustes primero (no hay cascade definido)
    adjs = (await db.execute(select(Adjustment).where(Adjustment.comparable_id == c.id))).scalars().all()
    for a in adjs:
        await db.delete(a)
    await db.delete(c)
    await db.flush()

    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms)
    return await _serialize(db, ms)


@router.post("/{study_id}/recalc", response_model=MarketStudyOut)
async def recalc_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ms = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")
    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms)
    return await _serialize(db, ms)


# ============ IA-first: sugerencias automáticas ============

class SuggestionAdjustment(BaseModel):
    factor: str
    coefficient: float
    description: str | None = None


class SuggestionItem(BaseModel):
    candidate_id: int
    candidate_kind: str  # workspace | external
    include: bool
    similarity_reason: str = ""
    reject_reason: str = ""
    similarity_score: float
    candidate: dict
    adjustments: List[SuggestionAdjustment] = []


class SuggestionsResponse(BaseModel):
    candidates_evaluated: int
    ai_evaluated: bool
    fallback_used: bool
    workspace_candidates: int = 0
    external_candidates: int = 0
    suggestions: List[SuggestionItem]
    message: str | None = None


@router.post("/{study_id}/suggest-comparables", response_model=SuggestionsResponse)
async def ai_suggest(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Claude propone comparables: workspace + externos cacheados + evaluación IA."""
    ms = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    prop = (await db.execute(select(Property).where(Property.id == ms.property_id))).scalar_one()

    result = await suggest_comparables(db, ms, prop, max_suggestions=8)
    return SuggestionsResponse(**result)


class AcceptSuggestionBody(BaseModel):
    candidate_id: int
    candidate_kind: str  # workspace | external
    similarity_reason: str = ""
    adjustments: List[SuggestionAdjustment] = []


@router.post("/{study_id}/accept-suggestion", response_model=MarketStudyOut)
async def accept_suggestion(
    study_id: int,
    body: AcceptSuggestionBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Convierte una sugerencia IA en un Comparable real del estudio + auto-recalcula."""
    ms = (await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    # Cargar datos del candidato según kind
    comp_data: dict = {}
    source_kind = "ai_suggested"
    source_property_id = None
    external_listing_id = None
    source_str = "manual"
    source_url = None

    if body.candidate_kind == "workspace":
        p = (await db.execute(
            select(Property).where(
                Property.id == body.candidate_id,
                Property.workspace_id == user.workspace_id,
            )
        )).scalar_one_or_none()
        if not p:
            raise HTTPException(404, "Propiedad workspace inexistente")
        source_property_id = p.id
        source_str = "workspace"
        comp_data = {
            "title": p.title,
            "address": p.address,
            "latitude": p.latitude, "longitude": p.longitude,
            "total_area_m2": p.total_area_m2, "covered_area_m2": p.covered_area_m2,
            "rooms": p.rooms, "bedrooms": p.bedrooms, "bathrooms": p.bathrooms,
            "age_years": p.age_years, "condition": p.condition,
            "price": p.asking_price or 0,
            "currency": p.currency,
        }
    elif body.candidate_kind == "external":
        e = (await db.execute(
            select(ExternalListing).where(
                ExternalListing.id == body.candidate_id,
                ExternalListing.workspace_id == user.workspace_id,
            )
        )).scalar_one_or_none()
        if not e:
            raise HTTPException(404, "Listing externo inexistente")
        external_listing_id = e.id
        source_str = e.source
        source_url = e.source_url
        comp_data = {
            "title": e.title,
            "address": e.address,
            "latitude": e.latitude, "longitude": e.longitude,
            "total_area_m2": e.total_area_m2, "covered_area_m2": e.covered_area_m2,
            "rooms": e.rooms, "bedrooms": e.bedrooms, "bathrooms": e.bathrooms,
            "age_years": e.age_years, "condition": e.condition,
            "price": e.price, "currency": e.currency,
        }
    else:
        raise HTTPException(400, "candidate_kind inválido (debe ser workspace o external)")

    if comp_data.get("price") and (comp_data.get("total_area_m2") or comp_data.get("covered_area_m2")):
        area = comp_data.get("total_area_m2") or comp_data.get("covered_area_m2")
        comp_data["price_per_m2"] = round(comp_data["price"] / area, 2)

    c = Comparable(
        market_study_id=study_id,
        source=source_str,
        source_url=source_url,
        source_type=source_kind,
        ai_reason=body.similarity_reason,
        source_property_id=source_property_id,
        external_listing_id=external_listing_id,
        **comp_data,
    )
    db.add(c)
    await db.flush()

    for adj in body.adjustments:
        db.add(Adjustment(
            comparable_id=c.id,
            factor=adj.factor,
            coefficient=adj.coefficient,
            description=adj.description,
        ))

    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms)
    return await _serialize(db, ms)


@router.delete("/{study_id}")
async def delete_market_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    res = await db.execute(
        select(MarketStudy).where(
            MarketStudy.id == study_id,
            MarketStudy.workspace_id == user.workspace_id,
        )
    )
    ms = res.scalar_one_or_none()
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")
    await db.delete(ms)
    await db.commit()
    return {"ok": True}
