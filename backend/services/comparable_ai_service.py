"""IA-first comparable suggestion service.

Combina:
1. Propiedades del workspace pre-filtradas + rankeadas por similitud
2. ExternalListings cacheados de scrapings previos
3. Evaluación final de Claude que decide cuáles incluir + propone ajustes

Devuelve lista de sugerencias con razón, score, candidato + ajustes propuestos.
"""
import json
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from models.property import Property
from models.market_study import MarketStudy
from models.external_listing import ExternalListing
from services.acm_service import compute_similarity_weight
from services.ai_router import chat_complete
from services.claude_service import _extract_json


SYSTEM_COMPARABLE_PROPOSER = """Sos un tasador inmobiliario experto en el mercado argentino. Recibís:
1) Una PROPIEDAD OBJETIVO con sus datos
2) Una lista de CANDIDATOS pre-filtrados por zona/tipo (workspace + listings externos)

REGLA CRITICA: Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE la
estructura del schema de abajo. Nada de texto antes ni después. La key top-level DEBE
llamarse "suggestions" (plural).

Tu trabajo: evaluar cada candidato y devolver SOLO los comparables válidos para una tasación,
con sus coeficientes de ajuste sugeridos.

REGLAS DE AJUSTE (el coeficiente multiplica el precio del comparable):
- 1.00 = sin ajuste
- > 1.00 = el comparable vale MÁS por algún atributo
- < 1.00 = el comparable vale MENOS por algún atributo

Factores típicos:
- area: si difiere mucho en m² (>15%), ajustar proporcionalmente
- condition: a_estrenar (1.10), excelente (1.05), muy_bueno (1.00), bueno (0.95), regular (0.88), a_reciclar (0.78)
- age_years: por cada 10 años de diferencia, ±0.03
- location: mismo barrio (1.00), barrio adyacente (0.95-1.05), otro (0.85-0.90)
- orientation: solo si hay diferencia clara

REGLAS DE FILTRO (descartá con include=false si):
- Tipo distinto (depto vs casa, terreno vs construcción)
- Antigüedad con diff > 30 años
- Sin precio o sin m²
- Ciudad distinta sin justificación

Devolvé SOLO un JSON con esta estructura (sin texto adicional, sin markdown alrededor):
```json
{
  "suggestions": [
    {
      "candidate_id": <int>,
      "include": true,
      "similarity_reason": "string corto: por qué es buen comparable",
      "adjustments": [
        {"factor": "area", "coefficient": 0.95, "description": "20% más grande que el objetivo"}
      ]
    },
    {
      "candidate_id": <int>,
      "include": false,
      "reject_reason": "string corto: por qué descartar"
    }
  ]
}
```"""


COND_SCORES = {
    "a_estrenar": 1.10, "excelente": 1.05, "muy_bueno": 1.00,
    "bueno": 0.95, "regular": 0.88, "a_reciclar": 0.78,
}


def _property_to_dict(p: Property) -> dict:
    return {
        "id": p.id,
        "candidate_kind": "workspace",
        "title": p.title,
        "property_type": p.property_type,
        "city": p.city,
        "neighborhood": p.neighborhood,
        "address": p.address,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "total_area_m2": p.total_area_m2,
        "covered_area_m2": p.covered_area_m2,
        "rooms": p.rooms,
        "age_years": p.age_years,
        "condition": p.condition,
        "price": p.asking_price,
        "currency": p.currency,
    }


def _external_to_dict(e: ExternalListing) -> dict:
    return {
        "id": e.id,
        "candidate_kind": "external",
        "title": e.title,
        "property_type": e.property_type,
        "city": e.city,
        "neighborhood": e.neighborhood,
        "address": e.address,
        "latitude": e.latitude,
        "longitude": e.longitude,
        "total_area_m2": e.total_area_m2,
        "covered_area_m2": e.covered_area_m2,
        "rooms": e.rooms,
        "age_years": e.age_years,
        "condition": e.condition,
        "price": e.price,
        "currency": e.currency,
        "source": e.source,
        "source_url": e.source_url,
    }


async def _workspace_candidates(
    db: AsyncSession, workspace_id: int, target: Property, limit: int = 12,
) -> List[Property]:
    """Fallback en cascada:
    1) Mismo tipo + misma ciudad/barrio
    2) Mismo tipo + misma provincia
    3) Mismo tipo (cualquier zona) — Claude después filtra por distancia
    """
    target_dict = _property_to_dict(target)

    async def _query(extra_filter):
        stmt = select(Property).where(
            Property.workspace_id == workspace_id,
            Property.id != target.id,
            Property.property_type == target.property_type,
        )
        if extra_filter is not None:
            stmt = stmt.where(extra_filter)
        res = await db.execute(stmt)
        items = list(res.scalars().all())
        scored = [(c, compute_similarity_weight(target_dict, _property_to_dict(c))) for c in items]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored]

    if target.city:
        cands = await _query(
            or_(Property.city == target.city, Property.neighborhood == target.neighborhood)
        )
        if cands:
            return cands[:limit]
    if target.province:
        cands = await _query(Property.province == target.province)
        if cands:
            return cands[:limit]
    cands = await _query(None)
    return cands[:limit]


async def _cached_external_candidates(
    db: AsyncSession, workspace_id: int, target: Property, limit: int = 8,
) -> List[ExternalListing]:
    stmt = select(ExternalListing).where(
        ExternalListing.workspace_id == workspace_id,
        ExternalListing.property_type == target.property_type,
    )
    if target.city:
        stmt = stmt.where(
            or_(ExternalListing.city == target.city, ExternalListing.neighborhood == target.neighborhood)
        )
    res = await db.execute(stmt)
    items = list(res.scalars().all())
    target_dict = _property_to_dict(target)
    scored = [(e, compute_similarity_weight(target_dict, _external_to_dict(e))) for e in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [e for e, _ in scored[:limit]]


def _adjustments_from_dicts(target: dict, comp: dict) -> List[dict]:
    out = []
    ta = target.get("total_area_m2") or target.get("covered_area_m2") or 0
    ca = comp.get("total_area_m2") or comp.get("covered_area_m2") or 0
    if ta and ca and abs(ta - ca) / max(ta, ca) > 0.15:
        ratio = ta / ca
        coef = round(max(0.7, min(1.3, 0.85 + 0.3 * min(1.0, ratio))), 3)
        out.append({
            "factor": "area",
            "coefficient": coef,
            "description": f"Diferencia de área: {ca:.0f}m² vs {ta:.0f}m²",
        })
    t_cond = COND_SCORES.get(target.get("condition") or "", 1.0)
    c_cond = COND_SCORES.get(comp.get("condition") or "", 1.0)
    if c_cond != t_cond:
        coef = round(t_cond / c_cond, 3)
        out.append({
            "factor": "condition",
            "coefficient": coef,
            "description": f"Estado: comparable {comp.get('condition') or 'sin dato'} vs objetivo {target.get('condition') or 'sin dato'}",
        })
    return out


async def suggest_comparables(
    db: AsyncSession,
    study: MarketStudy,
    target: Property,
    max_suggestions: int = 8,
) -> dict:
    """Workflow completo: workspace + externos + IA decide."""

    ws_cands = await _workspace_candidates(db, study.workspace_id, target, limit=10)
    ext_cands = await _cached_external_candidates(db, study.workspace_id, target, limit=6)

    if not ws_cands and not ext_cands:
        return {
            "candidates_evaluated": 0,
            "ai_evaluated": False,
            "fallback_used": True,
            "workspace_candidates": 0,
            "external_candidates": 0,
            "suggestions": [],
            "message": (
                "No se encontraron propiedades similares en el workspace ni listings externos. "
                "Probá agregar comparables manualmente o importar URLs de ZonaProp."
            ),
        }

    target_dict = _property_to_dict(target)
    candidates_payload = (
        [_property_to_dict(c) for c in ws_cands] + [_external_to_dict(e) for e in ext_cands]
    )

    prompt = f"""PROPIEDAD OBJETIVO:
```json
{json.dumps(target_dict, ensure_ascii=False, indent=2)}
```

CANDIDATOS ({len(candidates_payload)}):
```json
{json.dumps(candidates_payload, ensure_ascii=False, indent=2)}
```

Evaluá cada candidato. Hasta {max_suggestions} comparables (los mejores), descartá los irrelevantes.

Devolvé EXCLUSIVAMENTE un bloque ```json ... ``` con EXACTAMENTE esta estructura:

```json
{{
  "suggestions": [
    {{
      "candidate_id": 1,
      "include": true,
      "similarity_reason": "frase corta de por qué es buen comparable",
      "adjustments": [
        {{"factor": "area", "coefficient": 0.95, "description": "20% más grande"}},
        {{"factor": "condition", "coefficient": 1.05, "description": "estado superior"}}
      ]
    }},
    {{
      "candidate_id": 2,
      "include": false,
      "reject_reason": "frase corta de por qué descartar"
    }}
  ]
}}
```

La key top-level DEBE llamarse "suggestions" (plural). Es OBLIGATORIO usar los IDs reales de los candidatos."""
    raw = await chat_complete(prompt, system=SYSTEM_COMPARABLE_PROPOSER)
    parsed = _extract_json(raw)
    ai_evaluated = bool(parsed and parsed.get("suggestions"))

    ws_by_id = {c.id: c for c in ws_cands}
    ext_by_id = {e.id: e for e in ext_cands}
    suggestions = []

    if ai_evaluated:
        for s in parsed["suggestions"]:
            cid = s.get("candidate_id")
            kind = None
            cand_dict = None
            if cid in ws_by_id:
                kind = "workspace"
                cand_dict = _property_to_dict(ws_by_id[cid])
            elif cid in ext_by_id:
                kind = "external"
                cand_dict = _external_to_dict(ext_by_id[cid])
            else:
                continue
            score = compute_similarity_weight(target_dict, cand_dict)
            suggestions.append({
                "candidate_id": cid,
                "candidate_kind": kind,
                "include": bool(s.get("include", True)),
                "similarity_reason": s.get("similarity_reason", ""),
                "reject_reason": s.get("reject_reason", ""),
                "similarity_score": round(score, 3),
                "candidate": cand_dict,
                "adjustments": s.get("adjustments", []) if s.get("include") else [],
            })
    else:
        for c in ws_cands:
            score = compute_similarity_weight(target_dict, _property_to_dict(c))
            suggestions.append({
                "candidate_id": c.id,
                "candidate_kind": "workspace",
                "include": True,
                "similarity_reason": f"Mismo {c.property_type} en {c.neighborhood or c.city}",
                "similarity_score": round(score, 3),
                "candidate": _property_to_dict(c),
                "adjustments": _adjustments_from_dicts(target_dict, _property_to_dict(c)),
            })
        for e in ext_cands:
            score = compute_similarity_weight(target_dict, _external_to_dict(e))
            suggestions.append({
                "candidate_id": e.id,
                "candidate_kind": "external",
                "include": True,
                "similarity_reason": f"Scrapeado de {e.source} en {e.neighborhood or e.city}",
                "similarity_score": round(score, 3),
                "candidate": _external_to_dict(e),
                "adjustments": _adjustments_from_dicts(target_dict, _external_to_dict(e)),
            })

    if not any(s["include"] for s in suggestions):
        for c in ws_cands[:4]:
            score = compute_similarity_weight(target_dict, _property_to_dict(c))
            suggestions.append({
                "candidate_id": c.id,
                "candidate_kind": "workspace",
                "include": True,
                "similarity_reason": f"(Auto) {c.property_type} en {c.neighborhood or c.city}",
                "similarity_score": round(score, 3),
                "candidate": _property_to_dict(c),
                "adjustments": _adjustments_from_dicts(target_dict, _property_to_dict(c)),
            })

    return {
        "candidates_evaluated": len(candidates_payload),
        "ai_evaluated": ai_evaluated,
        "fallback_used": not ai_evaluated,
        "workspace_candidates": len(ws_cands),
        "external_candidates": len(ext_cands),
        "suggestions": suggestions,
    }
