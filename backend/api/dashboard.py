from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime, date as date_cls, timedelta, timezone

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.property import Property
from models.market_study import MarketStudy
from models.appraisal import Appraisal
from models.client import Client
from models.visit import Visit
from models.deal import Deal
from models.dmo import DmoLog


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

MANAGER_ROLES = ("admin", "supervisor")
# Etapas legales del pipeline (mismo orden que api/deals.LEGAL_STAGES).
LEGAL_STAGES = ["captado", "publicado", "visita", "reserva", "boleto", "escrituracion"]
CLOSED_STAGE = "escrituracion"
# Estados de lead que NO cuentan como cliente activo.
INACTIVE_LEAD_STATUS = ("cerrado", "perdido")


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


# =========================== CRM (WO F2-02) ===========================

class CrmKpis(BaseModel):
    scope: str  # "vendedor" | "team"
    active_clients: int
    visits_7d: int
    open_deals: int
    deals_by_stage: Dict[str, int]
    conversations_today: int
    conversations_goal: int


@router.get("/crm", response_model=CrmKpis)
async def get_crm_kpis(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """KPIs del CRM con scoping por rol: el vendedor ve LO SUYO; el
    supervisor/admin ve todo el workspace. Cada metrica es una consulta
    agregada (no hay loops por entidad)."""
    ws = user.workspace_id
    is_vendedor = user.role == "vendedor"
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    today = date_cls.today()

    # 1) Clientes activos (lead_status no cerrado/perdido).
    q_clients = (
        select(func.count(Client.id))
        .where(Client.workspace_id == ws, Client.lead_status.notin_(INACTIVE_LEAD_STATUS))
    )
    if is_vendedor:
        q_clients = q_clients.where(Client.assigned_to == user.id)
    active_clients = (await db.execute(q_clients)).scalar() or 0

    # 2) Visitas de los ultimos 7 dias.
    q_visits = (
        select(func.count(Visit.id))
        .where(Visit.workspace_id == ws, Visit.scheduled_at >= week_ago)
    )
    if is_vendedor:
        q_visits = q_visits.where(Visit.vendor_id == user.id)
    visits_7d = (await db.execute(q_visits)).scalar() or 0

    # 3) Deals por etapa (una sola query agregada con GROUP BY stage).
    q_deals = (
        select(Deal.stage, func.count(Deal.id))
        .where(Deal.workspace_id == ws)
        .group_by(Deal.stage)
    )
    if is_vendedor:
        q_deals = q_deals.where(Deal.vendor_id == user.id)
    stage_counts = {stage: 0 for stage in LEGAL_STAGES}
    for stage, cnt in (await db.execute(q_deals)).all():
        stage_counts[stage] = cnt
    open_deals = sum(c for s, c in stage_counts.items() if s != CLOSED_STAGE)

    # 4) Conversaciones de hoy (suma de metric_value de los logs DMO).
    q_conv = (
        select(func.coalesce(func.sum(DmoLog.metric_value), 0))
        .where(DmoLog.workspace_id == ws, DmoLog.date == today)
    )
    if is_vendedor:
        q_conv = q_conv.where(DmoLog.vendor_id == user.id)
    conversations_today = int((await db.execute(q_conv)).scalar() or 0)

    # Meta de conversaciones: propia (vendedor) o suma del equipo (manager).
    if is_vendedor:
        conversations_goal = user.daily_conversations_goal or 0
    else:
        conversations_goal = int((await db.execute(
            select(func.coalesce(func.sum(User.daily_conversations_goal), 0))
            .where(User.workspace_id == ws, User.role == "vendedor")
        )).scalar() or 0)

    return CrmKpis(
        scope="vendedor" if is_vendedor else "team",
        active_clients=active_clients,
        visits_7d=visits_7d,
        open_deals=open_deals,
        deals_by_stage=stage_counts,
        conversations_today=conversations_today,
        conversations_goal=conversations_goal,
    )


class RankingRow(BaseModel):
    vendor_id: int
    name: str
    conversations_30d: int
    visits_30d: int
    deals_total: int
    deals_closed: int
    conversations_goal: int


@router.get("/ranking", response_model=List[RankingRow])
async def get_ranking(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Ranking de vendedores de los ultimos 30 dias (herramienta de equipo:
    solo supervisor/admin).

    ANTI N+1: en AgentFlow el ranking hacia 3 queries POR vendedor (loop). Aca
    son 4 consultas AGREGADAS totales, CONSTANTES sin importar cuantos
    vendedores haya:
      (a) lista de vendedores del workspace;
      (b) visitas 30d      -> GROUP BY vendor_id;
      (c) deals total+cierre-> GROUP BY vendor_id (sum condicional);
      (d) conversaciones 30d-> GROUP BY vendor_id.
    El merge por vendor_id se hace en memoria.
    """
    if user.role not in MANAGER_ROLES:
        raise HTTPException(403, "Solo supervisor o admin ven el ranking del equipo")

    ws = user.workspace_id
    since_dt = datetime.now(timezone.utc) - timedelta(days=30)
    since_date = date_cls.today() - timedelta(days=30)

    # (a) Vendedores del workspace.
    vendors = (await db.execute(
        select(User.id, User.full_name, User.daily_conversations_goal)
        .where(User.workspace_id == ws, User.role == "vendedor")
    )).all()

    # (b) Visitas 30d por vendedor.
    visits_by_vendor = dict((await db.execute(
        select(Visit.vendor_id, func.count(Visit.id))
        .where(Visit.workspace_id == ws, Visit.scheduled_at >= since_dt)
        .group_by(Visit.vendor_id)
    )).all())

    # (c) Deals total + cerrados por vendedor (una sola query, sum condicional).
    deals_rows = (await db.execute(
        select(
            Deal.vendor_id,
            func.count(Deal.id),
            func.coalesce(func.sum(case((Deal.stage == CLOSED_STAGE, 1), else_=0)), 0),
        )
        .where(Deal.workspace_id == ws)
        .group_by(Deal.vendor_id)
    )).all()
    deals_by_vendor = {vid: (total, closed) for vid, total, closed in deals_rows}

    # (d) Conversaciones 30d por vendedor.
    conv_by_vendor = dict((await db.execute(
        select(DmoLog.vendor_id, func.coalesce(func.sum(DmoLog.metric_value), 0))
        .where(DmoLog.workspace_id == ws, DmoLog.date >= since_date)
        .group_by(DmoLog.vendor_id)
    )).all())

    rows = []
    for vid, full_name, goal in vendors:
        total, closed = deals_by_vendor.get(vid, (0, 0))
        rows.append(RankingRow(
            vendor_id=vid,
            name=full_name,
            conversations_30d=int(conv_by_vendor.get(vid, 0) or 0),
            visits_30d=int(visits_by_vendor.get(vid, 0) or 0),
            deals_total=int(total or 0),
            deals_closed=int(closed or 0),
            conversations_goal=goal or 0,
        ))
    rows.sort(key=lambda r: (r.conversations_30d, r.deals_closed), reverse=True)
    return rows
