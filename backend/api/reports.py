"""Reportes mensuales (cards del screenshot real con +14.2% YoY 2.847 USD/m²).

WO F4-03: agrega POST /custom -- genera un reporte agregando market_listings
REALES por region+tipo+periodo (mediana USD/m2, counts por zona, top zonas),
lo persiste con source='custom' y genera+sube su PDF (ReportLab + Cloudinary).
Tambien poblamos pdf_url de los 6 reportes seed (source='seed') con un PDF
real generado a partir de sus propios campos -- ver _ensure_pdf.
"""
import io
import json
import re
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone

from core.database import get_db
from core.security import get_current_user
from core.config import settings
from models.user import User
from models.monthly_report import MonthlyReport
from models.market_listing import MarketListing
from services.pdf_service import generate_monthly_report_pdf
from services.cloudinary_service import upload_pdf


router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportCard(BaseModel):
    id: int
    code: str
    period_year: int
    period_month: int
    region: str
    kind: str
    source: str
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


def _build_pdf_bytes(r: MonthlyReport) -> bytes:
    """Arma el dict real desde `r` y genera el PDF. Usado tanto para subir a
    Cloudinary (_ensure_pdf) como para el streaming directo del backend
    (GET /{id}/pdf) -- ver hallazgo de infra en el reporte del WO F4-03:
    el account de Cloudinary bloquea la entrega publica de PDFs (raw/image)
    con 401 salvo que se habilite "Allow delivery of PDF and ZIP files" en
    Settings > Security del dashboard (no expuesto por API, requiere 1 click
    manual del dueño). Mientras tanto, /{id}/pdf es la via que SI funciona."""
    try:
        top_zones = json.loads(r.top_zones or "[]")
    except Exception:
        top_zones = []
    sample_size = sum(z.get("listings_count", 0) or 0 for z in top_zones) or None
    return generate_monthly_report_pdf(
        report={
            "code": r.code, "region": r.region, "kind": r.kind,
            "period_year": r.period_year, "period_month": r.period_month,
            "source": r.source,
            "tasar_index": r.tasar_index, "median_price_per_m2": r.median_price_per_m2,
            "yoy_change_pct": r.yoy_change_pct, "mom_change_pct": r.mom_change_pct,
            "active_listings": r.active_listings, "avg_days_on_market": r.avg_days_on_market,
            "new_permits": r.new_permits, "sample_size": r.active_listings or sample_size,
            "top_zones": top_zones,
        },
        brand={"name": settings.APP_NAME, "subtitle": "Inteligencia de mercado inmobiliario"},
    )


async def _ensure_pdf(db: AsyncSession, r: MonthlyReport) -> MonthlyReport:
    """Genera y sube el PDF de un monthly_report si todavia no tiene
    pdf_url. Cubre tanto los reportes custom recien creados como (defensa en
    profundidad) cualquier fila -- seed incluida -- que se haya quedado sin
    PDF. Usa SIEMPRE los campos reales de `r` (ninguna cifra se inventa)."""
    if r.pdf_url:
        return r
    pdf_bytes = _build_pdf_bytes(r)
    # Cloudinary public_id solo admite alfanumericos/guiones/underscore -- el
    # code de los seed trae "#" (ej "#042"), que Cloudinary rechaza.
    safe_code = re.sub(r"[^a-zA-Z0-9_-]", "", r.code)
    upload = await upload_pdf(pdf_bytes, folder="reports", filename=f"report-{r.id}-{safe_code}")
    r.pdf_url = upload["url"]
    r.pages_count = r.pages_count or 2
    await db.commit()
    await db.refresh(r)
    return r


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
    # Defensa en profundidad: si alguna fila quedo sin pdf_url (backfill
    # parcial, fallo puntual de Cloudinary) se genera al vuelo -- cero
    # botones "Abrir PDF" muertos (aceptacion del WO F4-03).
    items = [await _ensure_pdf(db, i) for i in items]
    return [ReportCard.model_validate(i) for i in items]


@router.get("/{report_id}/pdf")
async def report_pdf(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Streamea el PDF directo desde el backend (mismo patron que
    /appraisals/{id}/pdf y /valuations/express/{id}/pdf). Es la via
    garantizada de "Abrir PDF" en el front: no depende de que el toggle de
    seguridad de Cloudinary (bloquea PDF publico por default) este
    habilitado -- ver nota en _build_pdf_bytes."""
    r = (await db.execute(select(MonthlyReport).where(MonthlyReport.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Reporte no encontrado")
    pdf_bytes = _build_pdf_bytes(r)
    safe_code = re.sub(r"[^a-zA-Z0-9_-]", "", r.code)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="reporte-{safe_code}.pdf"'},
    )


@router.get("/{report_id}")
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    r = (await db.execute(select(MonthlyReport).where(MonthlyReport.id == report_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404)
    r = await _ensure_pdf(db, r)
    try:
        top_zones = json.loads(r.top_zones or "[]")
    except Exception:
        top_zones = []
    return {
        **ReportCard.model_validate(r).model_dump(),
        "top_zones": top_zones,
    }


# ============ Reporte custom (WO F4-03) ============

# Mapeo region (front) -> filtro real sobre market_listings.city. Solo CABA,
# Vicente Lopez (proxy de "GBA Norte") y La Plata (proxy de "GBA Sur") tienen
# listings reales en el seed -- GBA Oeste/Cordoba/Rosario NO tienen datos
# todavia, asi que devuelven sample_size=0 en vez de inventar numeros
# (regla dura 11).
REGION_CITY_FILTER: dict[str, list[str]] = {
    "CABA": ["CABA"],
    "GBA Norte": ["Vicente López", "Vicente Lopez"],
    "GBA Sur": ["La Plata"],
}

# El "Tipo" del front (Residencial/Comercial/Industrial/Mixto) no matchea
# 1:1 con MarketListing.property_type (departamento/casa/ph -- todos
# residenciales). Solo Residencial/Mixto tienen listings reales; Comercial e
# Industrial no tienen datos en el catalogo -> sample_size=0.
KIND_PROPERTY_TYPES: dict[str, list[str]] = {
    "Residencial": ["departamento", "casa", "ph"],
    "Mixto": ["departamento", "casa", "ph"],
    "Comercial": [],
    "Industrial": [],
}


class CustomReportRequest(BaseModel):
    region: str
    kind: str
    period_year: int
    period_month: int


@router.post("/custom")
async def create_custom_report(
    body: CustomReportRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Genera un reporte agregando market_listings REALES por region+tipo.

    El periodo (period_year/period_month) es la etiqueta del reporte, NO un
    filtro temporal: market_listings es un snapshot en vivo (no guarda serie
    historica por listing), asi que la agregacion siempre refleja el estado
    actual del catalogo para esa region/tipo -- igual que /market/dashboard.
    """
    cities = REGION_CITY_FILTER.get(body.region)
    ptypes = KIND_PROPERTY_TYPES.get(body.kind, [])

    stmt = select(MarketListing).where(MarketListing.status == "active")
    if cities:
        stmt = stmt.where(MarketListing.city.in_(cities))
    else:
        stmt = stmt.where(MarketListing.id.is_(None))  # sin mapeo -> 0 resultados, no inventar
    if ptypes:
        stmt = stmt.where(MarketListing.property_type.in_(ptypes))
    else:
        stmt = stmt.where(MarketListing.id.is_(None))

    rows = (await db.execute(stmt)).scalars().all()
    sample_size = len(rows)

    ppm2_list = sorted(l.price_per_m2 for l in rows if l.price_per_m2)
    median_ppm2 = ppm2_list[len(ppm2_list) // 2] if ppm2_list else None
    days_list = [l.days_on_market for l in rows if l.days_on_market is not None]
    avg_days = round(sum(days_list) / len(days_list)) if days_list else None

    # Top zonas reales: GROUP BY neighborhood sobre el mismo universo filtrado.
    zone_stats: dict[str, list[float]] = {}
    for l in rows:
        if not l.neighborhood or not l.price_per_m2:
            continue
        zone_stats.setdefault(l.neighborhood, []).append(l.price_per_m2)
    top_zones = sorted(
        (
            {"zone": z, "usd_m2": round(sum(vals) / len(vals)), "listings_count": len(vals)}
            for z, vals in zone_stats.items()
        ),
        key=lambda z: z["listings_count"], reverse=True,
    )[:12]

    existing = (await db.execute(
        select(MonthlyReport).where(
            MonthlyReport.period_year == body.period_year,
            MonthlyReport.period_month == body.period_month,
            MonthlyReport.region == body.region,
        )
    )).scalar_one_or_none()

    if existing:
        r = existing
    else:
        # code (VARCHAR(20)) unico -- (period_year, period_month, region) ya
        # es UNIQUE en la tabla, asi que codificar esos 3 campos alcanza para
        # garantizar unicidad sin necesitar un contador aparte.
        region_slug = body.region.upper().replace(" ", "")[:8]
        r = MonthlyReport(
            code=f"C-{region_slug}-{str(body.period_year)[-2:]}{body.period_month:02d}",
            period_year=body.period_year, period_month=body.period_month,
        )
        db.add(r)

    r.region = body.region
    r.kind = body.kind
    r.source = "custom"
    # Sin base historica real para YoY/MoM/permisos en una agregacion en vivo
    # -- se dejan en None en vez de fabricarlos (regla dura 11).
    r.tasar_index = median_ppm2
    r.median_price_per_m2 = median_ppm2
    r.active_listings = sample_size
    r.avg_days_on_market = avg_days
    r.top_zones = json.dumps(top_zones, ensure_ascii=False)
    r.pdf_url = None  # fuerza regeneracion del PDF con los datos frescos
    r.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(r)

    r = await _ensure_pdf(db, r)

    return {
        **ReportCard.model_validate(r).model_dump(),
        "top_zones": top_zones,
        "sample_size": sample_size,
        "insufficient_data": sample_size == 0,
    }
