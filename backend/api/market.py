"""Endpoints para el módulo Mercado (dashboard macro) y Comparables (live search)."""
import json
import math
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.market_listing import MarketListing
from models.monthly_report import MonthlyReport


router = APIRouter(prefix="/api/market", tags=["market"])


class ZoneStat(BaseModel):
    zone: str
    usd_m2: float
    change_pct: Optional[float] = None
    listings_count: int = 0


class MarketDashboard(BaseModel):
    tasar_index: float
    median_price_per_m2: float
    yoy_change_pct: Optional[float]
    mom_change_pct: Optional[float]
    active_listings: int
    avg_days_on_market: int
    new_permits: int
    top_zones: List[ZoneStat]


@router.get("/dashboard", response_model=MarketDashboard)
async def market_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Resumen macro del mercado: usa el último monthly_report si existe,
    + suma de listings activos en tiempo real."""

    latest_report = (await db.execute(
        select(MonthlyReport).where(MonthlyReport.region == "CABA")
        .order_by(MonthlyReport.period_year.desc(), MonthlyReport.period_month.desc())
        .limit(1)
    )).scalar_one_or_none()

    active_listings = (await db.execute(
        select(func.count()).select_from(MarketListing).where(MarketListing.status == "active")
    )).scalar() or 0

    if latest_report:
        try:
            top_raw = json.loads(latest_report.top_zones or "[]")
        except json.JSONDecodeError:
            top_raw = []
        top_zones = []
        for z in top_raw[:12]:
            cnt = (await db.execute(
                select(func.count()).select_from(MarketListing)
                .where(MarketListing.neighborhood == z.get("zone"), MarketListing.status == "active")
            )).scalar() or 0
            top_zones.append(ZoneStat(
                zone=z.get("zone", ""),
                usd_m2=float(z.get("usd_m2", 0)),
                change_pct=z.get("change_pct"),
                listings_count=cnt,
            ))
        return MarketDashboard(
            tasar_index=latest_report.tasar_index or 0,
            median_price_per_m2=latest_report.median_price_per_m2 or 0,
            yoy_change_pct=latest_report.yoy_change_pct,
            mom_change_pct=latest_report.mom_change_pct,
            active_listings=active_listings,
            avg_days_on_market=latest_report.avg_days_on_market or 0,
            new_permits=latest_report.new_permits or 0,
            top_zones=top_zones,
        )

    # Fallback: calculamos desde listings
    median_ppm2 = (await db.execute(
        select(func.avg(MarketListing.price_per_m2)).where(MarketListing.status == "active")
    )).scalar() or 0
    return MarketDashboard(
        tasar_index=float(median_ppm2),
        median_price_per_m2=float(median_ppm2),
        yoy_change_pct=None, mom_change_pct=None,
        active_listings=active_listings,
        avg_days_on_market=90,
        new_permits=0,
        top_zones=[],
    )


# ============ Comparables (live search) ============

class ComparableResult(BaseModel):
    id: int
    title: str
    address: Optional[str]
    neighborhood: Optional[str]
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    total_area_m2: Optional[float]
    rooms: Optional[int]
    price: float
    currency: str
    price_per_m2: Optional[float]
    days_on_market: int
    condition: Optional[str]
    match_score: Optional[float] = None
    distance_m: Optional[int] = None

    class Config:
        from_attributes = True


class ComparablesSearchResponse(BaseModel):
    total: int
    min_ppm2: Optional[float]
    max_ppm2: Optional[float]
    median_ppm2: Optional[float]
    results: List[ComparableResult]


@router.get("/comparables", response_model=ComparablesSearchResponse)
async def search_comparables(
    neighborhood: Optional[str] = None,
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    rooms: Optional[int] = None,
    min_m2: Optional[float] = None,
    max_m2: Optional[float] = None,
    condition: Optional[str] = None,
    target_lat: Optional[float] = None,
    target_lng: Optional[float] = None,
    radius_m: Optional[int] = None,
    last_days: Optional[int] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Buscador en vivo de comparables sobre market_listings.

    Filtros: barrio, ciudad, tipo, ambientes, m² min/max, estado, radio desde
    coords, antigüedad del aviso. Devuelve resultados con match_score si se
    pasaron coords objetivo.
    """
    stmt = select(MarketListing).where(MarketListing.status == "active")
    if neighborhood:
        stmt = stmt.where(MarketListing.neighborhood == neighborhood)
    if city:
        stmt = stmt.where(MarketListing.city == city)
    if property_type:
        stmt = stmt.where(MarketListing.property_type == property_type)
    if rooms is not None:
        stmt = stmt.where(MarketListing.rooms == rooms)
    if min_m2 is not None:
        stmt = stmt.where(MarketListing.total_area_m2 >= min_m2)
    if max_m2 is not None:
        stmt = stmt.where(MarketListing.total_area_m2 <= max_m2)
    if condition:
        stmt = stmt.where(MarketListing.condition == condition)
    if last_days is not None:
        stmt = stmt.where(MarketListing.days_on_market <= last_days)

    rows = (await db.execute(stmt.limit(500))).scalars().all()

    # Filtro por radio + cálculo distancia
    results: List[ComparableResult] = []
    for r in rows:
        distance_m = None
        match_score = None
        if target_lat is not None and target_lng is not None and r.latitude and r.longitude:
            distance_m = int(_haversine_m(target_lat, target_lng, r.latitude, r.longitude))
            if radius_m and distance_m > radius_m:
                continue
            match_score = _match_score(distance_m, r, rooms, min_m2, max_m2)
        item = ComparableResult.model_validate(r)
        item.distance_m = distance_m
        item.match_score = match_score
        results.append(item)

    # Sort por match_score si hay, sino por price_per_m2
    if results and results[0].match_score is not None:
        results.sort(key=lambda x: x.match_score or 0, reverse=True)
    else:
        results.sort(key=lambda x: x.price_per_m2 or 0, reverse=True)

    ppm2_list = [r.price_per_m2 for r in results if r.price_per_m2]
    return ComparablesSearchResponse(
        total=len(results),
        min_ppm2=min(ppm2_list) if ppm2_list else None,
        max_ppm2=max(ppm2_list) if ppm2_list else None,
        median_ppm2=sorted(ppm2_list)[len(ppm2_list) // 2] if ppm2_list else None,
        results=results[:limit],
    )


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def _match_score(distance_m: int, listing: MarketListing, target_rooms, target_min_m2, target_max_m2) -> float:
    """Score 0..1 — combina cercanía + similitud de ambientes/m²."""
    score = 1.0
    # Distancia: hasta 800m score 1.0, decae lineal hasta 2km
    if distance_m > 800:
        score *= max(0.3, 1 - (distance_m - 800) / 2400)
    if target_rooms is not None and listing.rooms is not None:
        diff = abs(target_rooms - listing.rooms)
        score *= max(0.5, 1 - diff * 0.15)
    if target_min_m2 and target_max_m2 and listing.total_area_m2:
        mid = (target_min_m2 + target_max_m2) / 2
        diff = abs(listing.total_area_m2 - mid) / mid if mid else 1
        score *= max(0.5, 1 - diff)
    return round(min(1.0, max(0.0, score)), 3)
