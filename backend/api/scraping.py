"""Scraping puntual on-demand de portales inmobiliarios.

Usa Playwright + Claude headless para extraer datos estructurados de un listing.
NO crashea si Playwright no está instalado — devuelve fallback con instructivo.
Persiste los listings scrapeados en `external_listings` para cache y price_history.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from urllib.parse import urlparse

from core.security import get_current_user
from core.database import get_db
from models.user import User
from models.external_listing import ExternalListing
from services.ai_router import chat_complete
from services.claude_service import _extract_json


router = APIRouter(prefix="/api/scraping", tags=["scraping"])


class ScrapeRequest(BaseModel):
    url: str
    save_as_comparable: bool = False
    market_study_id: Optional[int] = None


SCRAPER_PROMPT = """Extraé del HTML siguiente los datos del listing inmobiliario en JSON:
{
  "title": "string",
  "price": float,
  "currency": "USD|ARS",
  "property_type": "casa|departamento|ph|terreno|local|oficina",
  "operation": "venta|alquiler",
  "total_area_m2": float|null,
  "covered_area_m2": float|null,
  "rooms": int|null,
  "bedrooms": int|null,
  "bathrooms": int|null,
  "age_years": int|null,
  "condition": "a_estrenar|excelente|muy_bueno|bueno|regular|a_reciclar"|null,
  "address": "string"|null,
  "neighborhood": "string"|null,
  "city": "string"|null,
  "province": "string"|null,
  "latitude": float|null,
  "longitude": float|null,
  "description": "string"|null
}

Si no encontrás un campo, dejalo null. NO inventes datos.
"""


def _source_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if "zonaprop" in host: return "zonaprop"
    if "argenprop" in host: return "argenprop"
    if "mercadolibre" in host: return "mercadolibre"
    if "remax" in host: return "remax"
    return "other"


async def _fetch_html(url: str) -> str:
    """Intenta usar Playwright; si no está instalado, fallback a httpx (sin JS)."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            content = await page.content()
            await browser.close()
            return content
    except Exception:
        import httpx
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })
            return r.text


async def _upsert_external_listing(
    db: AsyncSession,
    workspace_id: int,
    url: str,
    data: dict,
) -> Optional[ExternalListing]:
    """Crea o actualiza un ExternalListing a partir de data extraída por Claude."""
    if not data or not data.get("price") or not data.get("title"):
        return None  # data insuficiente

    source = _source_from_url(url)
    existing = (await db.execute(
        select(ExternalListing).where(
            ExternalListing.workspace_id == workspace_id,
            ExternalListing.source_url == url,
        )
    )).scalar_one_or_none()

    price = float(data["price"]) if data.get("price") else 0
    area = data.get("total_area_m2") or data.get("covered_area_m2")
    ppm2 = round(price / area, 2) if (price and area) else None

    payload = dict(
        workspace_id=workspace_id,
        source=source,
        source_url=url,
        title=str(data.get("title", ""))[:250],
        property_type=str(data.get("property_type", "departamento"))[:40],
        operation=str(data.get("operation", "venta"))[:20],
        province=data.get("province"),
        city=data.get("city"),
        neighborhood=data.get("neighborhood"),
        address=data.get("address"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        total_area_m2=data.get("total_area_m2"),
        covered_area_m2=data.get("covered_area_m2"),
        rooms=data.get("rooms"),
        bedrooms=data.get("bedrooms"),
        bathrooms=data.get("bathrooms"),
        age_years=data.get("age_years"),
        condition=data.get("condition"),
        price=price,
        currency=str(data.get("currency", "USD"))[:5],
        price_per_m2=ppm2,
        description=data.get("description"),
        raw_data=json.dumps(data, ensure_ascii=False),
    )

    if existing:
        for k, v in payload.items():
            if k != "workspace_id":
                setattr(existing, k, v)
        await db.commit()
        await db.refresh(existing)
        return existing

    new = ExternalListing(**payload)
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new


@router.post("/extract")
async def extract_from_url(
    body: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Cache: si ya tenemos este URL scrapeado en este workspace, lo devolvemos
    cached = (await db.execute(
        select(ExternalListing).where(
            ExternalListing.workspace_id == user.workspace_id,
            ExternalListing.source_url == body.url,
        )
    )).scalar_one_or_none()
    if cached:
        # Devuelve el cache para que el frontend lo use sin pegar a Claude de nuevo
        data = json.loads(cached.raw_data or "{}") if cached.raw_data else {}
        return {
            "url": body.url,
            "extracted": data,
            "cached": True,
            "external_listing_id": cached.id,
        }

    try:
        html = await _fetch_html(body.url)
    except Exception as e:
        raise HTTPException(502, f"No se pudo descargar la URL: {e}")

    snippet = html[:60000]
    prompt = f"{SCRAPER_PROMPT}\n\nHTML:\n```html\n{snippet}\n```"
    raw = await chat_complete(prompt, system="Sos un extractor de datos web. Devolvé solo JSON válido.")
    data = _extract_json(raw)

    listing = await _upsert_external_listing(db, user.workspace_id, body.url, data)

    return {
        "url": body.url,
        "extracted": data,
        "cached": False,
        "external_listing_id": listing.id if listing else None,
        "raw": raw[:500] if not data else None,
    }
