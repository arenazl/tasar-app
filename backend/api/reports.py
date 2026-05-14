"""Reportes mensuales (cards del screenshot real con +14.2% YoY 2.847 USD/m²)."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.monthly_report import MonthlyReport


router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportCard(BaseModel):
    id: int
    code: str
    period_year: int
    period_month: int
    region: str
    kind: str
    tasar_index: Optional[float]
    median_price_per_m2: Optional[float]
    yoy_change_pct: Optional[float]
    mom_change_pct: Optional[float]
    active_listings: Optional[int]
    pages_count: int
    pdf_url: Optional[str]
    published_at: Optional[datetime]

    class Config:
        from_attributes = True


@router.get("", response_model=List[ReportCard])
async def list_reports(
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(MonthlyReport).order_by(
        MonthlyReport.period_year.desc(), MonthlyReport.period_month.desc()
    )
    if region:
        stmt = stmt.where(MonthlyReport.region == region)
    items = (await db.execute(stmt)).scalars().all()
    return [ReportCard.model_validate(i) for i in items]


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = (await db.execute(select(MonthlyReport).where(MonthlyReport.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404)
    try:
        top_zones = json.loads(r.top_zones or "[]")
    except Exception:
        top_zones = []
    return {
        **ReportCard.model_validate(r).model_dump(),
        "top_zones": top_zones,
    }
