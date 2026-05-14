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
from models.market_study import Comparable
from models.price_history import PriceHistoryPoint


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

    # 2) Comparables registrados con coords
    cstmt = select(Comparable).where(
        Comparable.latitude.is_not(None),
        Comparable.longitude.is_not(None),
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

    return out


class ZoneStat(BaseModel):
    city: str
    neighborhood: Optional[str] = None
    avg_price_per_m2: float
    sample_size: int


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
    ).where(PriceHistoryPoint.workspace_id == user.workspace_id)
    if property_type:
        stmt = stmt.where(PriceHistoryPoint.property_type == property_type)
    stmt = stmt.group_by(PriceHistoryPoint.city, PriceHistoryPoint.neighborhood)

    rows = (await db.execute(stmt)).all()
    return [ZoneStat(
        city=r[0], neighborhood=r[1],
        avg_price_per_m2=round(r[2] or 0, 2),
        sample_size=r[3],
    ) for r in rows]
