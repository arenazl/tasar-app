from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_study import MarketStudy
from models.appraisal import Appraisal


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class Kpi(BaseModel):
    label: str
    value: float | int
    delta_pct: Optional[float] = None
    unit: Optional[str] = None


class DashboardOut(BaseModel):
    kpis: List[Kpi]
    properties_by_type: List[dict]
    studies_by_status: List[dict]
    recent_appraisals: List[dict]


@router.get("", response_model=DashboardOut)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ws = user.workspace_id

    n_props = (await db.execute(
        select(func.count()).select_from(Property).where(Property.workspace_id == ws)
    )).scalar() or 0

    n_studies = (await db.execute(
        select(func.count()).select_from(MarketStudy).where(MarketStudy.workspace_id == ws)
    )).scalar() or 0

    n_appraisals = (await db.execute(
        select(func.count()).select_from(Appraisal).where(Appraisal.workspace_id == ws)
    )).scalar() or 0

    avg_val = (await db.execute(
        select(func.avg(Appraisal.final_value)).where(Appraisal.workspace_id == ws)
    )).scalar() or 0

    types_rows = (await db.execute(
        select(Property.property_type, func.count())
        .where(Property.workspace_id == ws)
        .group_by(Property.property_type)
    )).all()
    types = [{"type": r[0], "count": r[1]} for r in types_rows]

    st_rows = (await db.execute(
        select(MarketStudy.status, func.count())
        .where(MarketStudy.workspace_id == ws)
        .group_by(MarketStudy.status)
    )).all()
    statuses = [{"status": r[0], "count": r[1]} for r in st_rows]

    recents = (await db.execute(
        select(Appraisal).where(Appraisal.workspace_id == ws)
        .order_by(Appraisal.created_at.desc()).limit(5)
    )).scalars().all()
    recent_data = [{
        "id": a.id, "purpose": a.purpose, "final_value": a.final_value,
        "currency": a.currency, "status": a.status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in recents]

    return DashboardOut(
        kpis=[
            Kpi(label="Propiedades", value=n_props),
            Kpi(label="Estudios ACM", value=n_studies),
            Kpi(label="Tasaciones", value=n_appraisals),
            Kpi(label="Valor promedio", value=round(avg_val or 0, 2), unit="USD"),
        ],
        properties_by_type=types,
        studies_by_status=statuses,
        recent_appraisals=recent_data,
    )
