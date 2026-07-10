"""IA-first comparable suggestion service.

Combina:
1. Propiedades del workspace pre-filtradas + rankeadas por similitud
2. ExternalListings cacheados de scrapings previos
3. Evaluación final de Claude que decide cuáles incluir + propone ajustes

Devuelve lista de sugerencias con razón, score, candidato + ajustes propuestos.
"""
import json
from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from models.property import Property
from models.market_study import MarketStudy
from models.market_listing import MarketListing
from models.external_listing import ExternalListing
from services.acm_service import compute_similarity_weight, haversine_m
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


def _market_to_dict(m: MarketListing) -> dict:
    return {
        "id": m.id,
        "candidate_kind": "market",
        "title": m.title,
        "property_type": m.property_type,
        "city": m.city,
        "neighborhood": m.neighborhood,
        "address": m.address,
        "latitude": m.latitude,
        "longitude": m.longitude,
        "total_area_m2": m.total_area_m2,
        "covered_area_m2": m.covered_area_m2,
        "rooms": m.rooms,
        "age_years": m.age_years,
        "condition": m.condition,
        "price": m.price,
        "currency": m.currency,
        "source": m.source,
        "source_url": m.source_url,
    }


def _market_match_score(distance_m: Optional[int], similarity: float) -> float:
    """Combina cercanía + similitud en un score 0..1.

    Sin coords (distance_m None) el score ES la similitud. Con coords: hasta 800m
    pesa full la cercanía, decae lineal hasta ~3.2km, y se promedia 50/50 con la
    similitud de atributos (área/ambientes/antigüedad).
    """
    if distance_m is None:
        return round(similarity, 3)
    if distance_m <= 800:
        dist_factor = 1.0
    else:
        dist_factor = max(0.3, 1.0 - (distance_m - 800) / 2400)
    return round(min(1.0, 0.5 * dist_factor + 0.5 * similarity), 3)


async def market_listing_candidates(
    db: AsyncSession, target: Property, limit: int = 10,
) -> List[Tuple[MarketListing, Optional[int], float]]:
    """TERCERA fuente: catálogo GLOBAL market_listings (sin workspace_id).

    Filtra por tipo + ciudad/barrio. NO filtra por provincia a propósito: el
    dataset Coldwell Banker usa una convención de provincias ("G.B.A. Zona
    Norte/Sur/Oeste", interior crudo) distinta al seed ("Buenos Aires"), y filtrar
    por provincia exacta partiría el universo en dos (hallazgo F0-06). El scoping
    fino lo da city/neighborhood + haversine.

    Si el target tiene coords, calcula distancia y ordena por match (cercanía +
    similitud); si no, ordena solo por similitud de atributos.
    Devuelve (listing, distance_m|None, match_score) top `limit`.
    """
    target_dict = _property_to_dict(target)
    has_coords = target.latitude is not None and target.longitude is not None

    stmt = select(MarketListing).where(
        MarketListing.status == "active",
        MarketListing.property_type == target.property_type,
    )
    if target.city or target.neighborhood:
        stmt = stmt.where(or_(
            MarketListing.city == target.city,
            MarketListing.neighborhood == target.neighborhood,
        ))
    rows = list((await db.execute(stmt.limit(500))).scalars().all())

    # Fallback: si el filtro ciudad/barrio no trae nada, ampliar a solo tipo.
    if not rows and (target.city or target.neighborhood):
        rows = list((await db.execute(
            select(MarketListing).where(
                MarketListing.status == "active",
                MarketListing.property_type == target.property_type,
            ).limit(500)
        )).scalars().all())

    scored: List[Tuple[MarketListing, Optional[int], float]] = []
    for m in rows:
        similarity = compute_similarity_weight(target_dict, _market_to_dict(m))
        distance_m: Optional[int] = None
        if has_coords and m.latitude is not None and m.longitude is not None:
            distance_m = int(haversine_m(target.latitude, target.longitude, m.latitude, m.longitude))
        match = _market_match_score(distance_m, similarity)
        scored.append((m, distance_m, match))

    scored.sort(key=lambda x: x[2], reverse=True)
    return scored[:limit]


def compute_market_comparable_link(
    target: Property, listing: MarketListing, distance_m: Optional[int], match_score: float,
) -> dict:
    """Arma el payload de un AppraisalComparable a partir de un market_listing +
    su scoring. Aplica los ajustes determinísticos (área/estado) y homogeneiza el
    precio/m². Devuelve dict listo para AppraisalComparable(**payload sin 'adjustments').
    """
    target_dict = _property_to_dict(target)
    comp_dict = _market_to_dict(listing)
    adjustments = _adjustments_from_dicts(target_dict, comp_dict)

    area = listing.total_area_m2 or listing.covered_area_m2 or 0
    base_ppm2 = (listing.price / area) if area and listing.price else None
    factor = 1.0
    for adj in adjustments:
        factor *= adj.get("coefficient", 1.0)
    adjusted_ppm2 = round(base_ppm2 * factor, 2) if base_ppm2 else None
    weight = compute_similarity_weight(target_dict, comp_dict)

    return {
        "market_listing_id": listing.id,
        "match_score": match_score,
        "distance_m": distance_m,
        "weight": weight,
        "adjusted_price": round(adjusted_ppm2 * area, 2) if (adjusted_ppm2 and area) else None,
        "adjusted_price_per_m2": adjusted_ppm2,
        "adjustments": adjustments,
        "adjustments_json": json.dumps(adjustments, ensure_ascii=False),
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
    mkt_scored = await market_listing_candidates(db, target, limit=10)
    mkt_cands = [m for m, _, _ in mkt_scored]
    ext_cands = await _cached_external_candidates(db, study.workspace_id, target, limit=6)

    if not ws_cands and not mkt_cands and not ext_cands:
        return {
            "candidates_evaluated": 0,
            "ai_evaluated": False,
            "fallback_used": True,
            "workspace_candidates": 0,
            "market_candidates": 0,
            "external_candidates": 0,
            "suggestions": [],
            "message": (
                "No se encontraron propiedades similares en el workspace, el catálogo de "
                "mercado ni listings externos. Probá agregar comparables manualmente o "
                "importar URLs de ZonaProp."
            ),
        }

    target_dict = _property_to_dict(target)
    # Orden de fuentes: workspace → market_listings → external_listings
    candidates_payload = (
        [_property_to_dict(c) for c in ws_cands]
        + [_market_to_dict(m) for m in mkt_cands]
        + [_external_to_dict(e) for e in ext_cands]
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
    raw = await chat_complete(prompt, system=SYSTEM_COMPARABLE_PROPOSER, workspace_id=study.workspace_id)
    parsed = _extract_json(raw)
    ai_evaluated = bool(parsed and parsed.get("suggestions"))

    ws_by_id = {c.id: c for c in ws_cands}
    mkt_by_id = {m.id: m for m in mkt_cands}
    ext_by_id = {e.id: e for e in ext_cands}
    suggestions = []

    if ai_evaluated:
        for s in parsed["suggestions"]:
            cid = s.get("candidate_id")
            kind = None
            cand_dict = None
            # Resolución por precedencia de fuente (workspace → market → external).
            # NOTA: los 3 son espacios de IDs independientes; una colisión de id
            # se resuelve por este orden. El contrato JSON del LLM (solo candidate_id)
            # no se toca, así que asumimos IDs suficientemente disjuntos en la práctica.
            if cid in ws_by_id:
                kind = "workspace"
                cand_dict = _property_to_dict(ws_by_id[cid])
            elif cid in mkt_by_id:
                kind = "market"
                cand_dict = _market_to_dict(mkt_by_id[cid])
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
        for m in mkt_cands:
            md = _market_to_dict(m)
            score = compute_similarity_weight(target_dict, md)
            suggestions.append({
                "candidate_id": m.id,
                "candidate_kind": "market",
                "include": True,
                "similarity_reason": f"Mercado ({m.source}) en {m.neighborhood or m.city}",
                "similarity_score": round(score, 3),
                "candidate": md,
                "adjustments": _adjustments_from_dicts(target_dict, md),
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
        # Última red: forzar algunos comparables incluidos (workspace + market).
        combo = (
            [("workspace", _property_to_dict(c)) for c in ws_cands[:4]]
            + [("market", _market_to_dict(m)) for m in mkt_cands[:4]]
        )
        for kind, d in combo[:4]:
            score = compute_similarity_weight(target_dict, d)
            suggestions.append({
                "candidate_id": d["id"],
                "candidate_kind": kind,
                "include": True,
                "similarity_reason": f"(Auto) {d.get('property_type') or ''} en {d.get('neighborhood') or d.get('city') or ''}".strip(),
                "similarity_score": round(score, 3),
                "candidate": d,
                "adjustments": _adjustments_from_dicts(target_dict, d),
            })

    return {
        "candidates_evaluated": len(candidates_payload),
        "ai_evaluated": ai_evaluated,
        "fallback_used": not ai_evaluated,
        "workspace_candidates": len(ws_cands),
        "market_candidates": len(mkt_cands),
        "external_candidates": len(ext_cands),
        "suggestions": suggestions,
    }
