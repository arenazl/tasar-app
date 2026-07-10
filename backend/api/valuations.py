"""Tasacion express anclada (WO F1-03) — el gancho comercial de la suite.

Flujo:
  1. `anchor_service.get_market_anchor` ancla al catalogo real (market_listings).
  2. El LLM (ai_router.chat_complete) ajusta ANCLADO al segmento similar y
     devuelve bandas + confianza + factores + estrategia (contrato JSON).
  3. Si la IA falla o devuelve algo invalido -> fallback DETERMINISTICO sobre la
     mediana del ancla (patron de comparable_ai_service: la app nunca queda muda).
  4. Cada valuacion se persiste (input + output + ancla) en express_valuations.
  5. PDF brandeado por workspace, descargable.

Multi-tenant: todo filtra/persiste por `user.workspace_id` (JWT).
"""
import io
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.workspace import Workspace
from models.express_valuation import ExpressValuation
from services.anchor_service import AnchorQuery, get_market_anchor, format_anchor_for_prompt
from services.ai_router import chat_complete
from services.claude_service import _extract_json
from services.pdf_service import generate_express_valuation_pdf


log = logging.getLogger("tasar.valuations")
router = APIRouter(prefix="/api/valuations", tags=["valuations"])


SYSTEM_EXPRESS = """Sos un tasador inmobiliario senior del mercado argentino (CABA/GBA/capitales),
metodologia ACM. Recibis una propiedad y un ANCLA REAL del catalogo de mercado
(mediana/p25/p75 de USD/m2 del segmento similar). Tu tarea NO es inventar precios:
es AJUSTAR sobre esa ancla para estimar el VALOR DE CIERRE (no de publicacion).
Devolves EXCLUSIVAMENTE un bloque ```json ... ``` con el contrato pedido. Tono
rioplatense (vos), conciso."""


class ExpressValuationRequest(BaseModel):
    property_type: str
    province: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    address: Optional[str] = None
    total_area_m2: float
    covered_area_m2: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    age_years: Optional[int] = None
    condition: Optional[str] = None
    features: List[str] = []
    notes: Optional[str] = None


# Factor de ajuste por estado respecto de "bueno" (baseline 1.0), para el fallback
# deterministico. Conservador y coherente con las reglas de mercado del prompt del
# valuator original (a estrenar +12%, excelente +6%, ... a reciclar -20%).
_COND_FACTOR = {
    "a_estrenar": 1.12, "excelente": 1.06, "muy_bueno": 1.02,
    "bueno": 1.00, "regular": 0.90, "a_reciclar": 0.80,
}
# Descuento publicacion -> cierre (el ancla es precio de publicacion).
_CLOSING_FACTOR = 0.88
# Ancho de banda segun confianza (deterministico).
_BAND_WIDTH = {"alta": 0.07, "media": 0.10, "baja": 0.15}


def _confidence_from_count(count: int) -> str:
    if count >= 30:
        return "alta"
    if count >= 10:
        return "media"
    return "baja"


def _deterministic_output(anchor: Optional[dict], q: ExpressValuationRequest) -> dict:
    """Fallback sin IA: typical = mediana del ancla * cierre * ajuste-estado.

    Bandas por confianza (mas comparables => banda mas angosta). Sin ancla no hay
    base de precio: devuelve bandas nulas y lo dice en marketSummary.
    """
    if not anchor:
        return {
            "pricePerM2USD": {"low": None, "typical": None, "high": None},
            "totalPriceUSD": {"low": None, "typical": None, "high": None},
            "confidence": "baja",
            "marketSummary": "Sin comparables suficientes en el catalogo para esta propiedad.",
            "factorsUp": [], "factorsDown": [],
            "commercialStrategy": "Cargar comparables manualmente o generar una tasacion completa.",
        }
    median = anchor["price_per_m2"]["median"]
    count = anchor["count"]
    confidence = _confidence_from_count(count)
    width = _BAND_WIDTH[confidence]
    cond_factor = _COND_FACTOR.get(q.condition or "", 1.0)

    typical_ppm2 = median * _CLOSING_FACTOR * cond_factor
    low_ppm2 = typical_ppm2 * (1 - width)
    high_ppm2 = typical_ppm2 * (1 + width)
    area = q.total_area_m2 or 0

    def _r(n: float) -> float:
        return round(n)

    return {
        "pricePerM2USD": {"low": _r(low_ppm2), "typical": _r(typical_ppm2), "high": _r(high_ppm2)},
        "totalPriceUSD": {
            "low": _r(low_ppm2 * area), "typical": _r(typical_ppm2 * area), "high": _r(high_ppm2 * area),
        },
        "confidence": confidence,
        "marketSummary": (
            f"Estimacion anclada a {count} comparables ({anchor['scope']}). "
            f"Mediana del segmento: USD {median:,}/m2 (publicacion)."
        ),
        "factorsUp": [], "factorsDown": [],
        "commercialStrategy": "Valor orientativo; confirmar con inspeccion y tasacion completa.",
    }


def _build_prompt(anchor: dict, q: ExpressValuationRequest) -> str:
    anchor_block = format_anchor_for_prompt(anchor)
    a = anchor["price_per_m2"]
    return f"""Devolve JSON exacto:

{{
  "pricePerM2USD": {{ "low": n, "typical": n, "high": n }},
  "totalPriceUSD": {{ "low": n, "typical": n, "high": n }},
  "confidence": "alta" | "media" | "baja",
  "marketSummary": "max 2 oraciones, <=40 palabras",
  "factorsUp": ["<=8 palabras c/u", "max 3 items"],
  "factorsDown": ["<=8 palabras c/u", "max 3 items"],
  "commercialStrategy": "max 2 oraciones, <=35 palabras"
}}

Reglas (anclaje, criticas para no sobre/subvaluar):
- El ancla es ground-truth. typical de USD/m2 dentro de [P25={a['p25']}, P75={a['p75']}];
  low >= Min={a['min']}, high <= Max={a['max']} (salvo justificacion en marketSummary).
- El ancla es precio de PUBLICACION; tu output es VALOR DE CIERRE (cierre = publicacion - 12-15%;
  bajar a 8% solo si es CABA premium a estrenar).
- Premiums conservadores: "a estrenar" +10-15% (NO 30%), "excelente" +5-8%. Estado
  "regular"/"a_reciclar" descuenta 12-25%, no lo suavices.
- pricePerM2USD.typical x superficie ~= totalPriceUSD.typical.
- Datos insuficientes => confidence "baja" + banda mas amplia.

Propiedad:
- Tipo: {q.property_type}
- Ubicacion: {', '.join(p for p in [q.neighborhood, q.city, q.province] if p) or '-'}
- Direccion: {q.address or '-'}
- Superficie total: {q.total_area_m2} m2{f', cubierta {q.covered_area_m2} m2' if q.covered_area_m2 else ''}
- Ambientes: {q.rooms if q.rooms is not None else '-'} · Dormitorios: {q.bedrooms if q.bedrooms is not None else '-'} · Banos: {q.bathrooms if q.bathrooms is not None else '-'}
- Antiguedad: {f'{q.age_years} anios' if q.age_years is not None else '-'}
- Estado: {q.condition or '-'}
- Caracteristicas: {', '.join(q.features) if q.features else '-'}
{f'- Notas: {q.notes}' if q.notes else ''}

{anchor_block}"""


def _valid_llm_output(parsed: dict) -> bool:
    """El output del LLM sirve si trae las bandas con un typical numerico positivo.

    Cubre tambien el caso de la IA apagada: gemini_service devuelve un string
    tipo "[Gemini no disponible...]" que _extract_json convierte en {} -> invalido
    -> caemos al fallback deterministico.
    """
    try:
        ppm2 = parsed.get("pricePerM2USD") or {}
        total = parsed.get("totalPriceUSD") or {}
        return (
            isinstance(ppm2.get("typical"), (int, float)) and ppm2["typical"] > 0
            and isinstance(total.get("typical"), (int, float)) and total["typical"] > 0
        )
    except (AttributeError, TypeError):
        return False


def _serialize(v: ExpressValuation) -> dict:
    out = json.loads(v.output_json) if v.output_json else {}
    inp = json.loads(v.input_json) if v.input_json else {}
    anchor = out.pop("_anchor", None)
    return {
        "id": v.id,
        "scope": v.anchor_scope,
        "ai_used": v.ai_used,
        "currency": v.currency,
        "input": inp,
        "output": out,
        "anchor": anchor,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


@router.post("/express")
async def create_express_valuation(
    body: ExpressValuationRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Valuacion instantanea anclada + ajuste LLM (con fallback deterministico).

    Devuelve el resultado y persiste la valuacion. El campo `scope` dice el
    alcance del ancla usada (zona | provincia | nacional | sin_datos) para que el
    front sepa que tan localizado fue el dato.
    """
    if not body.total_area_m2 or body.total_area_m2 <= 0:
        raise HTTPException(400, "La superficie total debe ser mayor a 0")

    q = AnchorQuery(
        property_type=body.property_type,
        total_area_m2=body.total_area_m2,
        province=body.province,
        city=body.city,
        neighborhood=body.neighborhood,
        condition=body.condition,
        bedrooms=body.bedrooms,
        features=body.features or [],
    )
    anchor = await get_market_anchor(db, q)
    scope = anchor["scope"] if anchor else "sin_datos"

    # Ajuste LLM anclado; si algo falla, fallback deterministico.
    ai_used = False
    output = None
    if anchor:
        try:
            prompt = _build_prompt(anchor, body)
            raw = await chat_complete(prompt, system=SYSTEM_EXPRESS, workspace_id=user.workspace_id)
            parsed = _extract_json(raw)
            if _valid_llm_output(parsed):
                output = parsed
                ai_used = True
            else:
                log.info("express valuation: LLM output invalido, usando fallback")
        except Exception:
            log.exception("express valuation: LLM fallo, usando fallback")

    if output is None:
        output = _deterministic_output(anchor, body)

    # Persistencia
    input_dict = body.model_dump()
    total = output.get("totalPriceUSD", {}) or {}
    ppm2 = output.get("pricePerM2USD", {}) or {}
    # El ancla viaja embebida en output_json bajo _anchor (para regenerar el PDF).
    output_to_store = dict(output)
    output_to_store["_anchor"] = anchor

    v = ExpressValuation(
        workspace_id=user.workspace_id,
        created_by=user.id,
        property_type=body.property_type,
        province=body.province,
        city=body.city,
        neighborhood=body.neighborhood,
        address=body.address,
        total_area_m2=body.total_area_m2,
        rooms=body.rooms,
        bedrooms=body.bedrooms,
        condition=body.condition,
        anchor_scope=scope,
        anchor_count=anchor["count"] if anchor else None,
        anchor_median_ppm2=anchor["price_per_m2"]["median"] if anchor else None,
        price_per_m2_typical=ppm2.get("typical"),
        total_price_usd=total.get("typical"),
        currency="USD",
        confidence=output.get("confidence"),
        ai_used=ai_used,
        input_json=json.dumps(input_dict, ensure_ascii=False),
        output_json=json.dumps(output_to_store, ensure_ascii=False),
    )
    db.add(v)
    await db.commit()
    await db.refresh(v)

    return _serialize(v)


@router.get("/express/{valuation_id}")
async def get_express_valuation(
    valuation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    v = (await db.execute(
        select(ExpressValuation).where(
            ExpressValuation.id == valuation_id,
            ExpressValuation.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Valuacion no encontrada")
    return _serialize(v)


@router.get("/express/{valuation_id}/pdf")
async def express_valuation_pdf(
    valuation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    v = (await db.execute(
        select(ExpressValuation).where(
            ExpressValuation.id == valuation_id,
            ExpressValuation.workspace_id == user.workspace_id,
        )
    )).scalar_one_or_none()
    if not v:
        raise HTTPException(404, "Valuacion no encontrada")

    ws = (await db.execute(
        select(Workspace).where(Workspace.id == user.workspace_id)
    )).scalar_one_or_none()

    data = _serialize(v)
    pdf_bytes = generate_express_valuation_pdf(
        valuation={
            "input": data["input"],
            "output": data["output"],
            "scope": data["scope"],
            "ai_used": data["ai_used"],
            "currency": data["currency"],
        },
        anchor=data["anchor"],
        brand={
            "name": ws.name if ws else "TasAR",
            "subtitle": "Tasacion express anclada a comparables reales",
        },
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="tasacion-express-{v.id}.pdf"'},
    )
