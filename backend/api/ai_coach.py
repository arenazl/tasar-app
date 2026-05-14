"""Endpoint /ai/coach — recomendaciones contextuales por pantalla.

El AI Coach Panel del Layout (visible en todas las páginas) llama a este endpoint
con el contexto de la ruta activa. Claude devuelve 1-3 recomendaciones cortas y
accionables relacionadas a lo que el usuario está viendo.
"""
import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.appraisal import Appraisal
from models.property import Property
from models.inbox import InboxMessage
from models.market_listing import MarketListing
from services.ai_router import chat_complete


router = APIRouter(prefix="/api/ai", tags=["ai-coach"])


class CoachRequest(BaseModel):
    route: str
    context: Optional[dict] = None


class CoachTip(BaseModel):
    title: str
    body: str
    severity: str = "info"  # info | warning | success
    action_label: Optional[str] = None
    action_url: Optional[str] = None


class CoachResponse(BaseModel):
    route: str
    tips: List[CoachTip]
    generated_by_ai: bool = True


ROUTE_PROMPTS = {
    "dashboard": "El usuario está en el Dashboard general. Resumí UNA recomendación accionable basada en los KPIs del workspace.",
    "bandeja": "El usuario está en la Bandeja (inbox). Sugerí en qué item enfocarse según prioridad.",
    "tasaciones": "El usuario está viendo el listado de tasaciones. Detectá patrones, riesgos y próximas acciones.",
    "tasacion_detail": "El usuario está en el detalle de una tasación específica. Recomendá próximo paso según el estado.",
    "propiedades": "El usuario está en el ABM de Propiedades. Sugerí mejoras de data quality.",
    "mercado": "El usuario está en el dashboard Mercado. Resumí qué zona está más movida y qué tendencia importa.",
    "comparables": "El usuario está buscando comparables. Sugerí filtros útiles según la zona consultada.",
    "reportes": "El usuario está viendo los reportes mensuales. Sugerí cuál descargar primero.",
    "pipeline": "El usuario está en el pipeline. Detectá embudo trabado.",
    "clientes": "El usuario está en CRM clientes. Sugerí seguimiento.",
    "config": "El usuario está en configuración. Recomendá ajustar modelo IA según uso.",
}


@router.post("/coach", response_model=CoachResponse)
async def get_coach_tips(
    body: CoachRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve tips contextuales para la ruta dada."""
    route = body.route.lower().strip().replace('/', '').replace('-', '_') or "dashboard"
    prompt_intro = ROUTE_PROMPTS.get(route, ROUTE_PROMPTS["dashboard"])

    # Recopilo contexto real del workspace
    ws_ctx = await _collect_workspace_context(db, user)

    user_prompt = f"""{prompt_intro}

CONTEXTO DEL WORKSPACE (datos reales):
```json
{json.dumps(ws_ctx, ensure_ascii=False, indent=2)}
```

{f'CONTEXTO ESPECIFICO de la pantalla: {json.dumps(body.context, ensure_ascii=False)}' if body.context else ''}

Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con esta estructura:
```json
{{
  "tips": [
    {{
      "title": "string corto (máx 60 caracteres)",
      "body": "string accionable (máx 140 caracteres)",
      "severity": "info|warning|success",
      "action_label": "opcional — texto del botón de acción",
      "action_url": "opcional — ruta interna ej /tasaciones/123"
    }}
  ]
}}
```

Devolvé 1-3 tips. Sé conciso, no decoraciones, no saludos, no preguntas. Texto plano sin markdown."""

    system = """Sos AI Coach de TasAR (plataforma de tasaciones inmobiliarias argentinas).
Tu rol es dar recomendaciones contextuales cortas y accionables al tasador.
Hablás en argentino (vos, no tú). Devolvés SOLO JSON estructurado, sin texto antes ni después."""

    raw = await chat_complete(user_prompt, system=system)

    parsed = _extract_tips(raw)

    if not parsed:
        # Fallback: tip genérico si Claude no respondió bien
        parsed = _fallback_tips(route, ws_ctx)
        return CoachResponse(route=route, tips=parsed, generated_by_ai=False)

    return CoachResponse(route=route, tips=parsed, generated_by_ai=True)


def _extract_tips(raw: str) -> list[CoachTip]:
    """Extrae lista de tips del JSON de Claude. Tolerante a markdown."""
    if not raw:
        return []
    text = raw
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return []
    tips = data.get("tips", [])
    out = []
    for t in tips[:3]:
        try:
            out.append(CoachTip(
                title=str(t.get("title", ""))[:80],
                body=str(t.get("body", ""))[:200],
                severity=t.get("severity") if t.get("severity") in ("info", "warning", "success") else "info",
                action_label=t.get("action_label"),
                action_url=t.get("action_url"),
            ))
        except Exception:
            continue
    return out


def _fallback_tips(route: str, ctx: dict) -> list[CoachTip]:
    """Tips estáticos si Claude no responde."""
    if route == "bandeja":
        sin_leer = ctx.get("inbox_unread", 0)
        if sin_leer > 0:
            return [CoachTip(
                title=f"Tenés {sin_leer} mensajes sin leer",
                body="Revisá los marcados como urgentes primero (cliente o sistema).",
                severity="info",
            )]
    if route == "tasaciones":
        en_analisis = ctx.get("appraisals_in_analysis", 0)
        if en_analisis > 0:
            return [CoachTip(
                title=f"{en_analisis} tasaciones en análisis",
                body="Ejecutá el análisis IA en las que aún no tienen valor sugerido.",
                severity="info",
            )]
    return [CoachTip(
        title="Cargá data del workspace",
        body="Sin propiedades ni tasaciones, no hay nada para recomendar.",
        severity="info",
    )]


async def _collect_workspace_context(db: AsyncSession, user: User) -> dict:
    """Snapshot del workspace que Claude puede usar para personalizar tips."""
    n_props = (await db.execute(
        select(func.count()).select_from(Property).where(Property.workspace_id == user.workspace_id)
    )).scalar() or 0
    n_appraisals = (await db.execute(
        select(func.count()).select_from(Appraisal).where(Appraisal.workspace_id == user.workspace_id)
    )).scalar() or 0
    n_in_analysis = (await db.execute(
        select(func.count()).select_from(Appraisal)
        .where(Appraisal.workspace_id == user.workspace_id, Appraisal.status == "en_analisis")
    )).scalar() or 0
    n_inbox_unread = (await db.execute(
        select(func.count()).select_from(InboxMessage)
        .where(InboxMessage.workspace_id == user.workspace_id, InboxMessage.is_read == False)
    )).scalar() or 0
    n_listings_global = (await db.execute(
        select(func.count()).select_from(MarketListing).where(MarketListing.status == "active")
    )).scalar() or 0
    return {
        "user_name": user.full_name,
        "user_role": user.role,
        "properties_count": n_props,
        "appraisals_total": n_appraisals,
        "appraisals_in_analysis": n_in_analysis,
        "inbox_unread": n_inbox_unread,
        "market_listings_count": n_listings_global,
    }
