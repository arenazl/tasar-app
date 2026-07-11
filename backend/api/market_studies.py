from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user, require_min_role
from models.user import User
from models.property import Property
from models.market_study import MarketStudy, Comparable, Adjustment
from models.market_listing import MarketListing
from models.external_listing import ExternalListing
from schemas.market_study import (
    MarketStudyCreate, MarketStudyOut, ComparableCreate, ComparableOut, AdjustmentOut
)
from services.acm_service import compute_market_study
from services.comparable_ai_service import suggest_comparables


router = APIRouter(prefix="/api/market-studies", tags=["market-studies"])


async def _load_study(db: AsyncSession, study_id: int, workspace_id: int) -> Optional[MarketStudy]:
    """Carga el estudio con comparables + adjustments YA resueltos via
    selectinload (WO F3-05): 1 query por el estudio + 1 selectin para
    comparables + 1 selectin para adjustments = 3 queries totales, sin
    importar cuantos comparables/adjustments tenga (antes era 1 query por
    comparable por adjustment, N+1)."""
    res = await db.execute(
        select(MarketStudy)
        .where(MarketStudy.id == study_id, MarketStudy.workspace_id == workspace_id)
        .options(selectinload(MarketStudy.comparables).selectinload(Comparable.adjustments))
    )
    return res.scalar_one_or_none()


def _serialize(ms: MarketStudy) -> MarketStudyOut:
    """Serializa un estudio YA cargado (ms.comparables / c.adjustments deben
    venir precargados via selectinload o via el grafo en memoria de la misma
    transaccion -- esta funcion NO consulta la DB)."""
    comp_outs = []
    for c in ms.comparables:
        co = ComparableOut.model_validate(c)
        co.adjustments = [AdjustmentOut.model_validate(a) for a in c.adjustments]
        comp_outs.append(co)
    out = MarketStudyOut.model_validate(ms)
    out.comparables = comp_outs
    return out


async def _recalc_in_place(db: AsyncSession, ms: MarketStudy) -> None:
    """Recalcula el estudio y actualiza ms + comparables (sin commit).

    Asume ms.comparables/c.adjustments ya cargados (selectinload via
    _load_study, o poblados en memoria en la misma transaccion) -- ya NO
    hace 1 query por comparable por adjustment (hallazgo F3-05)."""
    prop = (await db.execute(select(Property).where(Property.id == ms.property_id))).scalar_one()

    comp_payload = []
    for c in ms.comparables:
        adjs = [{"coefficient": a.coefficient, "factor": a.factor} for a in c.adjustments]
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

    by_id = {c.id: c for c in ms.comparables}
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
        .options(selectinload(MarketStudy.comparables).selectinload(Comparable.adjustments))
    )
    items = res.scalars().all()
    return [_serialize(m) for m in items]


@router.get("/{study_id}", response_model=MarketStudyOut)
async def get_market_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ms = await _load_study(db, study_id, user.workspace_id)
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")
    return _serialize(ms)


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
    # Recargar con selectinload (mismo patron que _load_study en el resto del
    # router): trae created_at/updated_at generados por la DB y deja
    # ms.comparables EAGER-LOADED ([]), evitando el lazy load post-commit que
    # dispara MissingGreenlet en contexto async.
    ms = await _load_study(db, ms.id, user.workspace_id)
    return _serialize(ms)


@router.post("/{study_id}/comparables", response_model=MarketStudyOut)
async def add_comparable(
    study_id: int,
    body: ComparableCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Agrega comparable manual y auto-recalcula. Devuelve el estudio entero."""
    ms = await _load_study(db, study_id, user.workspace_id)
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    data = body.model_dump(exclude={"adjustments"})
    if data.get("price") and (data.get("total_area_m2") or data.get("covered_area_m2")):
        area = data.get("total_area_m2") or data.get("covered_area_m2")
        data["price_per_m2"] = round(data["price"] / area, 2)

    c = Comparable(source_type="manual", **data)
    # Inicializar la collection SIEMPRE en memoria (aunque body.adjustments sea
    # []): si se deja sin tocar, `c.adjustments` queda 'unloaded' y _recalc_in_place
    # la itera disparando un lazy-load fuera del greenlet async -> MissingGreenlet.
    # Asignar la lista la marca como cargada. (El for/append solo la inicializaba
    # cuando venian adjustments; el caso "comparable pelado" reventaba.)
    c.adjustments = [Adjustment(**adj.model_dump()) for adj in body.adjustments]
    # entra a la sesion via relationship (cascade save-update), sin db.add(c)
    # explicito, y mantiene ms.comparables consistente en memoria.
    ms.comparables.append(c)
    await db.flush()

    await _recalc_in_place(db, ms)
    await db.commit()
    # Re-cargar con selectinload: tras commit el comparable recien creado tiene
    # su collection `adjustments` SIN cargar; _serialize la tocaria en lazy-load
    # (MissingGreenlet en async). _load_study trae comparables+adjustments eager.
    ms = await _load_study(db, study_id, user.workspace_id)
    return _serialize(ms)


@router.delete("/{study_id}/comparables/{comp_id}", response_model=MarketStudyOut)
async def delete_comparable(
    study_id: int,
    comp_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Elimina comparable y auto-recalcula."""
    ms = await _load_study(db, study_id, user.workspace_id)
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")

    c = next((x for x in ms.comparables if x.id == comp_id), None)
    if not c:
        raise HTTPException(404, "Comparable no encontrado")

    # cascade="all, delete-orphan" en Comparable.adjustments (modelo, WO
    # F3-05): borra los adjustments del comparable en la misma flush, sin el
    # loop manual que habia antes.
    ms.comparables.remove(c)
    await db.flush()

    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms, attribute_names=["updated_at"])
    return _serialize(ms)


@router.post("/{study_id}/recalc", response_model=MarketStudyOut)
async def recalc_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ms = await _load_study(db, study_id, user.workspace_id)
    if not ms:
        raise HTTPException(404, "Estudio no encontrado")
    await _recalc_in_place(db, ms)
    await db.commit()
    await db.refresh(ms, attribute_names=["updated_at"])
    return _serialize(ms)


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
    market_candidates: int = 0
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
    candidate_kind: str  # workspace | market | external
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
    ms = await _load_study(db, study_id, user.workspace_id)
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
    elif body.candidate_kind == "market":
        # Catálogo GLOBAL market_listings (sin workspace_id). Se snapshotea como
        # Comparable del estudio (fuente = portal/seed de origen).
        m = (await db.execute(
            select(MarketListing).where(MarketListing.id == body.candidate_id)
        )).scalar_one_or_none()
        if not m:
            raise HTTPException(404, "Listing de mercado inexistente")
        source_str = m.source
        source_url = m.source_url
        comp_data = {
            "title": m.title,
            "address": m.address,
            "latitude": m.latitude, "longitude": m.longitude,
            "total_area_m2": m.total_area_m2, "covered_area_m2": m.covered_area_m2,
            "rooms": m.rooms, "bedrooms": m.bedrooms, "bathrooms": m.bathrooms,
            "age_years": m.age_years, "condition": m.condition,
            "price": m.price, "currency": m.currency,
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
        raise HTTPException(400, "candidate_kind inválido (debe ser workspace, market o external)")

    if comp_data.get("price") and (comp_data.get("total_area_m2") or comp_data.get("covered_area_m2")):
        area = comp_data.get("total_area_m2") or comp_data.get("covered_area_m2")
        comp_data["price_per_m2"] = round(comp_data["price"] / area, 2)

    c = Comparable(
        source=source_str,
        source_url=source_url,
        source_type=source_kind,
        ai_reason=body.similarity_reason,
        source_property_id=source_property_id,
        external_listing_id=external_listing_id,
        **comp_data,
    )
    # Mismo fix que add_comparable: inicializar la collection en memoria aunque
    # sea [] para evitar el lazy-load en _recalc_in_place (MissingGreenlet async).
    c.adjustments = [
        Adjustment(factor=adj.factor, coefficient=adj.coefficient, description=adj.description)
        for adj in body.adjustments
    ]
    ms.comparables.append(c)
    await db.flush()

    await _recalc_in_place(db, ms)
    await db.commit()
    # Re-cargar con selectinload (mismo bug que add_comparable): el comparable
    # recien creado tiene `adjustments` sin cargar y _serialize dispararia un
    # lazy-load fuera del greenlet async -> MissingGreenlet.
    ms = await _load_study(db, study_id, user.workspace_id)
    return _serialize(ms)


@router.delete("/{study_id}")
async def delete_market_study(
    study_id: int,
    db: AsyncSession = Depends(get_db),
    # Borrar estudios ACM = accion sensible (WO F6-06): solo administrador+
    # (el coordinador ve todo pero NO borra).
    user: User = Depends(require_min_role("administrador")),
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
