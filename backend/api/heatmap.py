"""Mapa de calor: agregados de precio/m² por zona."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_study import Comparable, MarketStudy
from models.price_history import PriceHistoryPoint
from models.market_listing import MarketListing


router = APIRouter(prefix="/api/heatmap", tags=["heatmap"])


class HeatPoint(BaseModel):
    lat: float
    lng: float
    intensity: float
    label: Optional[str] = None
    price_per_m2: Optional[float] = None


@router.get("/points", response_model=List[HeatPoint])
async def points(
    property_type: Optional[str] = None,
    city: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve puntos para el heatmap combinando: propiedades del workspace,
    comparables registrados y price_history (snapshots).
    """
    out: List[HeatPoint] = []

    # 1) Propiedades propias con precio + coords
    stmt = select(Property).where(
        Property.workspace_id == user.workspace_id,
        Property.latitude.is_not(None),
        Property.longitude.is_not(None),
    )
    if property_type:
        stmt = stmt.where(Property.property_type == property_type)
    if city:
        stmt = stmt.where(Property.city == city)
    props = (await db.execute(stmt)).scalars().all()
    for p in props:
        if p.asking_price and (p.total_area_m2 or p.covered_area_m2):
            area = p.total_area_m2 or p.covered_area_m2
            ppm2 = p.asking_price / area
            out.append(HeatPoint(
                lat=p.latitude, lng=p.longitude,
                intensity=min(1.0, ppm2 / 5000),  # 5000 USD/m² = intensity 1
                label=p.title, price_per_m2=round(ppm2, 2),
            ))

    # 2) Comparables registrados con coords — SOLO de estudios del workspace del user
    #    (comparables no tiene workspace_id propio: se filtra por su market_study).
    cstmt = (
        select(Comparable)
        .join(MarketStudy, Comparable.market_study_id == MarketStudy.id)
        .where(
            MarketStudy.workspace_id == user.workspace_id,
            Comparable.latitude.is_not(None),
            Comparable.longitude.is_not(None),
        )
    )
    comps = (await db.execute(cstmt)).scalars().all()
    for c in comps:
        if c.price_per_m2:
            out.append(HeatPoint(
                lat=c.latitude, lng=c.longitude,
                intensity=min(1.0, c.price_per_m2 / 5000),
                label=c.title, price_per_m2=c.price_per_m2,
            ))

    # 3) Price history (snapshots agregados)
    pstmt = select(PriceHistoryPoint).where(
        PriceHistoryPoint.workspace_id == user.workspace_id,
        PriceHistoryPoint.latitude.is_not(None),
        PriceHistoryPoint.longitude.is_not(None),
    )
    if property_type:
        pstmt = pstmt.where(PriceHistoryPoint.property_type == property_type)
    if city:
        pstmt = pstmt.where(PriceHistoryPoint.city == city)
    pts = (await db.execute(pstmt)).scalars().all()
    for pt in pts:
        out.append(HeatPoint(
            lat=pt.latitude, lng=pt.longitude,
            intensity=min(1.0, pt.price_per_m2 / 5000),
            label=f"{pt.neighborhood or pt.city}", price_per_m2=pt.price_per_m2,
        ))

    # 4) Market listings — base macro real (ETL F0-06 + seed), global (sin
    #    workspace_id: WO F4-02, el mapa de Mercado necesita el universo
    #    completo de comparables con coords, no solo lo del workspace).
    mstmt = select(MarketListing).where(
        MarketListing.status == "active",
        MarketListing.latitude.is_not(None),
        MarketListing.longitude.is_not(None),
    )
    if property_type:
        mstmt = mstmt.where(MarketListing.property_type == property_type)
    if city:
        mstmt = mstmt.where(MarketListing.city == city)
    mkts = (await db.execute(mstmt)).scalars().all()
    for m in mkts:
        if m.price_per_m2:
            out.append(HeatPoint(
                lat=m.latitude, lng=m.longitude,
                intensity=min(1.0, m.price_per_m2 / 5000),
                label=m.title, price_per_m2=m.price_per_m2,
            ))

    return out


class ZoneStat(BaseModel):
    city: str
    neighborhood: Optional[str] = None
    avg_price_per_m2: float
    sample_size: int
    # Reales (MIN/MAX del propio subset agregado) — WO F4-02: el drill-down
    # del mapa mostraba avg*0.7 / avg*1.3 inventados. Ahora, si no hay
    # suficiente muestra para un min/max real, quedan en None y el front
    # no los muestra (regla dura 11: nunca un numero fabricado).
    min_price_per_m2: Optional[float] = None
    max_price_per_m2: Optional[float] = None


@router.get("/zones", response_model=List[ZoneStat])
async def zone_stats(
    property_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Stats agregadas por barrio/ciudad."""
    stmt = select(
        PriceHistoryPoint.city,
        PriceHistoryPoint.neighborhood,
        func.avg(PriceHistoryPoint.price_per_m2),
        func.count(PriceHistoryPoint.id),
        func.min(PriceHistoryPoint.price_per_m2),
        func.max(PriceHistoryPoint.price_per_m2),
    ).where(PriceHistoryPoint.workspace_id == user.workspace_id)
    if property_type:
        stmt = stmt.where(PriceHistoryPoint.property_type == property_type)
    stmt = stmt.group_by(PriceHistoryPoint.city, PriceHistoryPoint.neighborhood)

    rows = (await db.execute(stmt)).all()
    return [ZoneStat(
        city=r[0], neighborhood=r[1],
        avg_price_per_m2=round(r[2] or 0, 2),
        sample_size=r[3],
        min_price_per_m2=round(r[4], 2) if r[4] is not None else None,
        max_price_per_m2=round(r[5], 2) if r[5] is not None else None,
    ) for r in rows]
